"""
HybridACI - Intelligent Router between DOM and Visual Control

Extends OSWorldACI with browser extension support.
Routes actions through DOM control when possible, falls back to visual grounding.
"""

import logging
from typing import Dict, List, Optional, Tuple
from functools import wraps

from gui_agents.s3.agents.grounding import OSWorldACI, agent_action
from gui_agents.s3.browser.bridge import get_browser_bridge, BrowserBridge
from gui_agents.s3.utils.window_detector import is_browser_active, get_active_window_info

logger = logging.getLogger("desktopenv.agent")


class HybridACI(OSWorldACI):
    """
    Hybrid Abstract Computational Interface that routes between:
    - DOM control (fast, via Chrome extension) for browser tasks
    - Visual grounding (PyAutoGUI + UI-TARS) for desktop apps or fallback
    """
    
    def __init__(
        self,
        env=None,
        platform: str = "windows",
        engine_params_for_generation: Dict = None,
        engine_params_for_grounding: Dict = None,
        width: int = 1920,
        height: int = 1080,
        enable_browser: bool = True,
        auto_start_bridge: bool = True
    ):
        # Initialize parent OSWorldACI
        super().__init__(
            env=env,
            platform=platform,
            engine_params_for_generation=engine_params_for_generation,
            engine_params_for_grounding=engine_params_for_grounding,
            width=width,
            height=height
        )
        
        self.enable_browser = enable_browser
        self.bridge: Optional[BrowserBridge] = None
        
        if enable_browser and auto_start_bridge:
            try:
                self.bridge = get_browser_bridge(auto_start=True)
                logger.info("HybridACI: Browser bridge started")
            except ImportError as e:
                logger.warning(f"HybridACI: Browser bridge unavailable: {e}")
                self.enable_browser = False
    
    @property
    def browser_available(self) -> bool:
        """Check if browser extension is connected and responsive."""
        if not self.enable_browser or not self.bridge:
            return False
        return self.bridge.connected
    
    def _should_use_browser(self) -> bool:
        """Determine if we should use browser DOM control."""
        if not self.browser_available:
            return False
        
        # Check if a browser is the active window
        return is_browser_active()
    
    def _try_browser_click(self, element_description: str) -> Optional[str]:
        """
        Try to click using browser extension.
        
        Returns:
            Code string if successful, None if should fall back to visual.
        """
        if not self.browser_available:
            return None
        
        # Try to find and click the element
        result = self.bridge.click(text=element_description)
        
        if result.get("success") and result.get("result", {}).get("clicked"):
            logger.info(f"HybridACI: DOM click successful: {result.get('result')}")
            # Return a no-op since the action already happened
            return "import time; time.sleep(0.3)  # DOM click completed"
        
        logger.info(f"HybridACI: DOM click failed, falling back to visual: {result}")
        return None
    
    def _try_browser_type(
        self,
        text: str,
        element_description: str = None,
        clear: bool = False
    ) -> Optional[str]:
        """
        Try to type using browser extension.
        
        Returns:
            Code string if successful, None if should fall back to visual.
        """
        if not self.browser_available:
            return None
        
        # Build params
        selector = None
        if element_description:
            # Try to find element first
            find_result = self.bridge.find_element(text=element_description)
            if not find_result.get("success") or not find_result.get("result", {}).get("found"):
                return None
        
        result = self.bridge.type_text(text=text, clear=clear)
        
        if result.get("success") and result.get("result", {}).get("typed"):
            logger.info(f"HybridACI: DOM type successful")
            return "import time; time.sleep(0.2)  # DOM type completed"
        
        logger.info(f"HybridACI: DOM type failed, falling back to visual: {result}")
        return None
    
    @agent_action
    def click(
        self,
        element_description: str,
        num_clicks: int = 1,
        button_type: str = "left",
        hold_keys: List = [],
    ):
        """
        Click on an element. Uses DOM if browser is active, falls back to visual.
        """
        # Try browser DOM control first
        if self._should_use_browser():
            browser_result = self._try_browser_click(element_description)
            if browser_result is not None:
                return browser_result
        
        # Fall back to visual grounding (parent class)
        return super().click(
            element_description=element_description,
            num_clicks=num_clicks,
            button_type=button_type,
            hold_keys=hold_keys
        )
    
    @agent_action
    def type(
        self,
        text: str,
        element_description: str = "",
        overwrite: bool = False,
        enter: bool = False,
    ):
        """
        Type text. Uses DOM if browser is active, falls back to visual.
        """
        # Try browser DOM control first
        if self._should_use_browser():
            browser_result = self._try_browser_type(
                text=text,
                element_description=element_description if element_description else None,
                clear=overwrite
            )
            if browser_result is not None:
                # Handle enter key if needed
                if enter:
                    self.bridge.send_command("type", {"text": "", "pressEnter": True})
                return browser_result
        
        # Fall back to visual grounding (parent class)
        return super().type(
            text=text,
            element_description=element_description,
            overwrite=overwrite,
            enter=enter
        )
    
    @agent_action
    def scroll(
        self,
        element_description: str = "",
        direction: str = "down",
        amount: int = 3,
    ):
        """
        Scroll the page. Uses DOM if browser is active, falls back to visual.
        """
        # Try browser DOM control first
        if self._should_use_browser():
            # Convert amount to pixels (roughly)
            pixel_amount = amount * 100
            result = self.bridge.scroll(direction=direction, amount=pixel_amount)
            
            if result.get("success"):
                logger.info(f"HybridACI: DOM scroll successful")
                return "import time; time.sleep(0.2)  # DOM scroll completed"
        
        # Fall back to visual grounding (parent class)
        return super().scroll(
            element_description=element_description,
            direction=direction,
            amount=amount
        )
    
    @agent_action
    def goto(self, url: str):
        """
        Navigate to a URL. Uses browser extension if available.
        """
        # Try browser DOM control
        if self.browser_available:
            result = self.bridge.navigate(url)
            
            if result.get("success"):
                logger.info(f"HybridACI: DOM navigation successful to {url}")
                return "import time; time.sleep(1.0)  # Navigation completed"
        
        # Fall back to opening URL via pyautogui (open new browser)
        return f"import webbrowser; webbrowser.open({repr(url)})"
    
    def get_page_content(self) -> Optional[Dict]:
        """
        Get current page content via DOM (browser only).
        Returns None if browser is not active or extension is disconnected.
        """
        # Strict check: acts as a gatekeeper.
        # If the user is in VS Code, we do NOT want to return YouTube DOM.
        if not self._should_use_browser():
            return None
        
        result = self.bridge.get_dom(simplified=True)
        
        if result.get("success"):
            return result.get("result")
        
        return None
    
    def get_browser_screenshot(self) -> Optional[str]:
        """
        Get screenshot from browser extension.
        
        Returns:
            Base64 encoded screenshot or None.
        """
        if not self.browser_available:
            return None
        
        result = self.bridge.screenshot()
        
        if result.get("success"):
            return result.get("result", {}).get("screenshot")
        
        return None
    
    def get_current_context(self) -> Dict:
        """
        Get current execution context for debugging/logging.
        """
        window_info = get_active_window_info()
        
        return {
            "browser_available": self.browser_available,
            "should_use_browser": self._should_use_browser(),
            "active_window": window_info,
            "bridge_connected": self.bridge.connected if self.bridge else False
        }
