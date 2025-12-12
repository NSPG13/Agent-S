"""
Verification script for Agent-S3 HybridACI.
Tests the routing logic and bridge connection.
"""
import logging
import time
import unittest
from unittest.mock import MagicMock, patch

from gui_agents.s3.agents.hybrid_aci import HybridACI
from gui_agents.s3.browser.bridge import get_browser_bridge

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("desktopenv.agent")

class TestHybridACI(unittest.TestCase):
    def setUp(self):
        # Mock engine params
        self.engine_params = {
            "engine_type": "mock",
            "model": "mock",
            "api_key": "mock"
        }
        self.grounding_params = {
            "engine_type": "mock",
            "model": "mock",
            "grounding_width": 1920,
            "grounding_height": 1080
        }
        
    @patch("gui_agents.s3.agents.hybrid_aci.get_browser_bridge")
    @patch("gui_agents.s3.agents.hybrid_aci.is_browser_active")
    def test_routing_logic_dom(self, mock_is_browser, mock_get_bridge):
        """Test 1: Should route to DOM when browser is active and connected."""
        print("\n--- Test 1: DOM Routing Logic ---")
        
        # Setup mocks
        mock_is_browser.return_value = True
        mock_bridge = MagicMock()
        mock_bridge.connected = True
        # Mock successful click
        mock_bridge.click.return_value = {"success": True, "result": {"clicked": True}}
        mock_get_bridge.return_value = mock_bridge
        
        # Init agent
        agent = HybridACI(
            engine_params_for_generation=self.engine_params,
            engine_params_for_grounding=self.grounding_params,
            enable_browser=True
        )
        
        # Action
        result = agent.click("submit button")
        
        # Verification
        print(f"Action Result: {result}")
        self.assertIn("time.sleep", result, "Should return sleep command for DOM action")
        mock_bridge.click.assert_called_once()
        print("✅ DOM Routing Verified")

    @patch("gui_agents.s3.agents.hybrid_aci.get_browser_bridge")
    @patch("gui_agents.s3.agents.hybrid_aci.is_browser_active")
    def test_routing_logic_visual(self, mock_is_browser, mock_get_bridge):
        """Test 2: Should route to Visual when browser is NOT active."""
        print("\n--- Test 2: Visual Routing Logic ---")
        
        # Setup mocks
        mock_is_browser.return_value = False # Not browser
        mock_bridge = MagicMock()
        mock_bridge.connected = True
        mock_get_bridge.return_value = mock_bridge
        
        # Init agent
        agent = HybridACI(
            engine_params_for_generation=self.engine_params,
            engine_params_for_grounding=self.grounding_params,
            enable_browser=True
        )
        
        # Action - we need to patch super().click because it requires real model calls usually
        # But OSWorldACI.click just returns a formatted string if we don't actually run prediction?
        # Actually OSWorldACI.click IS an @agent_action, so it might return the string directly or call LLM.
        # Checking implementation: OSWorldACI.click in grounding.py constructs prompt etc.
        # We'll just check that it calls super().click or bypasses bridge.
        
        with patch("gui_agents.s3.agents.grounding.OSWorldACI.click") as mock_super_click:
            mock_super_click.return_value = "pyautogui.click(100, 100)"
            
            result = agent.click("notepad icon")
            
            print(f"Action Result: {result}")
            self.assertEqual(result, "pyautogui.click(100, 100)")
            mock_bridge.click.assert_not_called()
            print("✅ Visual Routing Verified")

    @patch("gui_agents.s3.agents.hybrid_aci.get_browser_bridge")
    @patch("gui_agents.s3.agents.hybrid_aci.is_browser_active")
    def test_fallback_logic(self, mock_is_browser, mock_get_bridge):
        """Test 3: Should fallback to Visual when DOM fails to find element."""
        print("\n--- Test 3: Fallback Logic ---")
        
        # Setup mocks
        mock_is_browser.return_value = True
        mock_bridge = MagicMock()
        mock_bridge.connected = True
        # Mock FAILED click (element not found in DOM)
        mock_bridge.click.return_value = {"success": False, "error": "Element not found"}
        mock_get_bridge.return_value = mock_bridge
        
        agent = HybridACI(
            engine_params_for_generation=self.engine_params,
            engine_params_for_grounding=self.grounding_params,
            enable_browser=True
        )
        
        with patch("gui_agents.s3.agents.grounding.OSWorldACI.click") as mock_super_click:
            mock_super_click.return_value = "pyautogui.click(500, 500)"
            
            result = agent.click("fancy canvas button")
            
            print(f"Action Result: {result}")
            self.assertEqual(result, "pyautogui.click(500, 500)")
            mock_bridge.click.assert_called_once() # Tried DOM first
            print("✅ Fallback Logic Verified")

def check_real_connection():
    """Check if the real bridge can start and if extension is connected."""
    print("\n--- Checking Real Bridge Connection ---")
    try:
        bridge = get_browser_bridge(auto_start=True)
        print("Bridge started. Waiting 2s for extension...")
        time.sleep(2)
        
        if bridge.connected:
            print("✅ Extension connected successfully!")
            return True
        else:
            print("❌ Extension NOT connected.")
            print("   Make sure you have loaded the extension in chrome://extensions")
            print("   Path: gui_agents/s3/browser/extension")
            return False
    except Exception as e:
        print(f"❌ Bridge failed to start: {e}")
        return False

if __name__ == "__main__":
    # Run unit tests
    unittest.main(exit=False)
    
    # Check real connection
    print("\n" + "="*30)
    check_real_connection()
