"""
Agent-S3 Browser Extension Bridge

WebSocket server that bridges Agent-S3 with the Chrome extension.
"""

import asyncio
import json
import logging
from typing import Dict, Optional, Callable, Any
import threading

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    websockets = None
    WebSocketServerProtocol = None

logger = logging.getLogger("desktopenv.agent")


class BrowserBridge:
    """
    WebSocket server that communicates with the Agent-S3 browser extension.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 9333):
        if websockets is None:
            raise ImportError(
                "websockets package required. Install with: pip install websockets"
            )
        
        self.host = host
        self.port = port
        self.server = None
        self.client: Optional[WebSocketServerProtocol] = None
        self.connected = False
        self._command_id = 0
        self._pending_commands: Dict[str, asyncio.Future] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
    
    def start(self):
        """Start the WebSocket server in a background thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        
        # Wait for server to start
        import time
        for _ in range(50):  # 5 seconds max
            if self.server is not None:
                break
            time.sleep(0.1)
        
        logger.info(f"BrowserBridge started on ws://{self.host}:{self.port}")
    
    def stop(self):
        """Stop the WebSocket server."""
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2)
    
    def _run_server(self):
        """Run the async server in a dedicated thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._start_server())
            self._loop.run_forever()
        except Exception as e:
            logger.error(f"BrowserBridge server error: {e}")
        finally:
            self._loop.close()
    
    async def _start_server(self):
        """Start the WebSocket server."""
        self.server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10
        )
        logger.info(f"BrowserBridge WebSocket server listening on ws://{self.host}:{self.port}")
    
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle incoming WebSocket connections."""
        print(f"DEBUG: Browser extension connecting from {websocket.remote_address}")
        logger.info(f"Browser extension connected from {websocket.remote_address}")
        
        self.client = websocket
        self.connected = True
        
        try:
            async for message in websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Browser extension disconnected. Code: {e.code}, Reason: {e.reason}")
        except Exception as e:
            logger.exception(f"Unexpected error in WebSocket handler: {e}")
        finally:
            self.client = None
            self.connected = False
            
            # Cancel pending commands
            for future in self._pending_commands.values():
                if not future.done():
                    future.set_exception(ConnectionError("Extension disconnected"))
            self._pending_commands.clear()
    
    async def _handle_message(self, message: str):
        """Handle incoming message from extension."""
        try:
            data = json.loads(message)
            
            # Handle handshake
            if data.get("type") == "handshake":
                logger.info(f"Extension handshake: {data}")
                return
            
            # Handle command response
            cmd_id = data.get("id")
            if cmd_id and cmd_id in self._pending_commands:
                future = self._pending_commands.pop(cmd_id)
                if not future.done():
                    future.set_result(data)
                    
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from extension: {message}")
    
    def send_command(
        self,
        action: str,
        params: Dict[str, Any] = None,
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """
        Send a command to the browser extension and wait for response.
        
        Args:
            action: Command action (e.g., 'click', 'type', 'navigate')
            params: Command parameters
            timeout: Maximum time to wait for response
            
        Returns:
            Response from extension
        """
        if not self.connected or not self._loop:
            return {"success": False, "error": "Extension not connected"}
        
        # Create command
        self._command_id += 1
        cmd_id = f"cmd-{self._command_id}"
        
        command = {
            "id": cmd_id,
            "action": action,
            "params": params or {}
        }
        
        # Create future for response
        future = self._loop.create_future()
        self._pending_commands[cmd_id] = future
        
        # Send command
        asyncio.run_coroutine_threadsafe(
            self.client.send(json.dumps(command)),
            self._loop
        )
        
        # Wait for response with timeout
        try:
            result_future = asyncio.run_coroutine_threadsafe(
                asyncio.wait_for(future, timeout),
                self._loop
            )
            result = result_future.result(timeout + 1)
            return result
        except asyncio.TimeoutError:
            self._pending_commands.pop(cmd_id, None)
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            self._pending_commands.pop(cmd_id, None)
            return {"success": False, "error": str(e)}
    
    # Convenience methods
    
    def navigate(self, url: str) -> Dict:
        """Navigate to URL."""
        return self.send_command("navigate", {"url": url})
    
    def click(
        self,
        selector: str = None,
        text: str = None,
        coordinates: tuple = None
    ) -> Dict:
        """Click an element."""
        params = {}
        if selector:
            params["selector"] = selector
        if text:
            params["text"] = text
        if coordinates:
            params["coordinates"] = list(coordinates)
        return self.send_command("click", params)
    
    def type_text(
        self,
        text: str,
        selector: str = None,
        clear: bool = False
    ) -> Dict:
        """Type text into an element."""
        params = {"text": text, "clear": clear}
        if selector:
            params["selector"] = selector
        return self.send_command("type", params)
    
    def scroll(
        self,
        direction: str = "down",
        amount: int = 300,
        selector: str = None
    ) -> Dict:
        """Scroll the page or element."""
        params = {"direction": direction, "amount": amount}
        if selector:
            params["selector"] = selector
        return self.send_command("scroll", params)
    
    def screenshot(self) -> Dict:
        """Take a screenshot."""
        return self.send_command("screenshot")
    
    def get_dom(self, simplified: bool = True) -> Dict:
        """Get DOM content."""
        return self.send_command("get_dom", {"simplified": simplified})
    
    def find_element(
        self,
        selector: str = None,
        text: str = None
    ) -> Dict:
        """Find an element."""
        params = {}
        if selector:
            params["selector"] = selector
        if text:
            params["text"] = text
        return self.send_command("find_element", params)
    
    def get_url(self) -> Dict:
        """Get current URL."""
        return self.send_command("get_url")
    
    def ping(self) -> bool:
        """Check if extension is responsive."""
        result = self.send_command("ping", timeout=2.0)
        return result.get("success", False) and result.get("result", {}).get("pong", False)


# Global bridge instance
_bridge: Optional[BrowserBridge] = None


def get_browser_bridge(auto_start: bool = True) -> BrowserBridge:
    """Get or create the global browser bridge instance."""
    global _bridge
    
    if _bridge is None:
        _bridge = BrowserBridge()
        if auto_start:
            _bridge.start()
    
    return _bridge
