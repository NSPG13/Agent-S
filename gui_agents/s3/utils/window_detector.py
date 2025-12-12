"""
Window Detector for Agent-S3

Detects which application window is currently active and whether it's a browser.
"""

import platform
import logging
from typing import Dict, Optional

logger = logging.getLogger("desktopenv.agent")

# Browser process names
BROWSER_PROCESSES = {
    "windows": [
        "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe",
        "opera.exe", "vivaldi.exe", "iexplore.exe"
    ],
    "darwin": [
        "Google Chrome", "Microsoft Edge", "Firefox", "Safari",
        "Brave Browser", "Opera", "Vivaldi"
    ],
    "linux": [
        "chrome", "chromium", "firefox", "brave", "opera", "vivaldi", "edge"
    ]
}


def get_active_window_info() -> Dict:
    """
    Get information about the currently active window.
    
    Returns:
        Dict with keys:
            - title: Window title
            - process: Process name
            - is_browser: Whether the window is a web browser
    """
    system = platform.system().lower()
    
    try:
        if system == "windows":
            return _get_active_window_windows()
        elif system == "darwin":
            return _get_active_window_macos()
        else:
            return _get_active_window_linux()
    except Exception as e:
        logger.warning(f"Failed to detect active window: {e}")
        return {
            "title": "",
            "process": "",
            "is_browser": False,
            "error": str(e)
        }


def _get_active_window_windows() -> Dict:
    """Get active window info on Windows."""
    try:
        import win32gui
        import win32process
        import psutil
    except ImportError:
        # Fallback without win32gui
        return _get_active_window_fallback()
    
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    
    # Get process name
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        process = psutil.Process(pid)
        process_name = process.name()
    except:
        process_name = ""
    
    is_browser = process_name.lower() in [p.lower() for p in BROWSER_PROCESSES["windows"]]
    
    return {
        "title": title,
        "process": process_name,
        "is_browser": is_browser,
        "pid": pid
    }


def _get_active_window_macos() -> Dict:
    """Get active window info on macOS."""
    try:
        from AppKit import NSWorkspace
    except ImportError:
        return _get_active_window_fallback()
    
    active_app = NSWorkspace.sharedWorkspace().frontmostApplication()
    app_name = active_app.localizedName()
    
    is_browser = app_name in BROWSER_PROCESSES["darwin"]
    
    return {
        "title": app_name,
        "process": app_name,
        "is_browser": is_browser
    }


def _get_active_window_linux() -> Dict:
    """Get active window info on Linux."""
    import subprocess
    
    try:
        # Try using xdotool
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True,
            text=True,
            timeout=2
        )
        title = result.stdout.strip()
        
        # Try to get process name
        result2 = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowpid"],
            capture_output=True,
            text=True,
            timeout=2
        )
        pid = result2.stdout.strip()
        
        process_name = ""
        if pid:
            try:
                import psutil
                process = psutil.Process(int(pid))
                process_name = process.name()
            except:
                pass
        
        is_browser = any(
            b in process_name.lower() or b in title.lower()
            for b in BROWSER_PROCESSES["linux"]
        )
        
        return {
            "title": title,
            "process": process_name,
            "is_browser": is_browser
        }
        
    except Exception:
        return _get_active_window_fallback()


def _get_active_window_fallback() -> Dict:
    """Fallback when native methods unavailable."""
    return {
        "title": "",
        "process": "",
        "is_browser": False,
        "fallback": True
    }


def is_browser_active() -> bool:
    """Quick check if browser is the active window."""
    info = get_active_window_info()
    return info.get("is_browser", False)
