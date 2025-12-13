import asyncio
import websockets
import logging
import sys

# Configure logging to show EVERYTHING
logging.basicConfig(
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.DEBUG,
    stream=sys.stdout
)

async def handler(websocket):
    logging.info(f"Client connected from {websocket.remote_address}!")
    try:
        async for message in websocket:
            logging.info(f"Received message: {message}")
            # Echo back to confirm bidirectional link
            await websocket.send(message)
    except websockets.exceptions.ConnectionClosed as e:
        logging.info(f"Client disconnected. Code: {e.code}, Reason: {e.reason}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

async def main():
    print("----------------------------------------------------------------")
    print("STARTING STANDALONE WEBSOCKET SERVER ON 0.0.0.0:9333")
    print("Please check your Chrome Extension. It should connect now.")
    print("----------------------------------------------------------------")
    
    # Simple server, no complex options
    async with websockets.serve(handler, "0.0.0.0", 9333):
        logging.info("Server bound and listening. Press Ctrl+C to stop.")
        await asyncio.get_running_loop().create_future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped.")
