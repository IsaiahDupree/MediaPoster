"""
Global Input Recorder for macOS
Captures keyboard and mouse events at the OS level using pynput.
Filters events to only capture when Safari is the frontmost application.
"""
import asyncio
import threading
from datetime import datetime
from typing import List, Dict, Optional, Callable
from pathlib import Path
from loguru import logger

try:
    from pynput import keyboard, mouse
    from pynput.keyboard import Key, KeyCode
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    logger.warning("pynput not installed. Global input recording disabled.")

try:
    from AppKit import NSWorkspace
    APPKIT_AVAILABLE = True
except ImportError:
    APPKIT_AVAILABLE = False
    logger.warning("AppKit not available. Cannot filter by active application.")


class GlobalInputRecorder:
    """
    Records global keyboard and mouse events, filtered to Safari.
    
    Requires macOS Accessibility permissions for the Terminal app.
    """
    
    def __init__(self, 
                 target_app: str = "Safari",
                 mask_passwords: bool = True,
                 include_mouse_move: bool = False):
        """
        Initialize the global input recorder.
        
        Args:
            target_app: Only record events when this app is active
            mask_passwords: If True, mask keyboard input when password fields are detected
            include_mouse_move: If True, also record mouse movement (can be verbose)
        """
        self.target_app = target_app
        self.mask_passwords = mask_passwords
        self.include_mouse_move = include_mouse_move
        
        self.events: List[Dict] = []
        self.is_recording = False
        self.start_time: Optional[datetime] = None
        
        # Listeners
        self.keyboard_listener: Optional[keyboard.Listener] = None
        self.mouse_listener: Optional[mouse.Listener] = None
        
        # Thread lock for event list
        self._lock = threading.Lock()
        
        # Track modifier keys
        self._modifiers = set()
        
        # Track if we're in a password field (set externally)
        self.in_password_field = False
        
        # Event buffer for batch retrieval
        self._last_fetch_index = 0
        
        # Check if pynput is available
        if not PYNPUT_AVAILABLE:
            logger.error("pynput is not installed. Run: pip install pynput")
    
    def _get_active_app(self) -> Optional[str]:
        """Get the name of the currently active application."""
        if not APPKIT_AVAILABLE:
            return None
        try:
            workspace = NSWorkspace.sharedWorkspace()
            active_app = workspace.frontmostApplication()
            return active_app.localizedName() if active_app else None
        except Exception as e:
            logger.debug(f"Error getting active app: {e}")
            return None
    
    def _is_target_app_active(self) -> bool:
        """Check if the target application is currently active."""
        active = self._get_active_app()
        return active == self.target_app if active else True  # Default to True if can't detect
    
    def _record_event(self, event_type: str, details: Dict):
        """Record an event with timestamp."""
        if not self.is_recording:
            return
        
        # Check if target app is active
        if not self._is_target_app_active():
            return
        
        timestamp = datetime.now()
        relative_time = None
        if self.start_time:
            relative_time = (timestamp - self.start_time).total_seconds()
        
        event = {
            "type": event_type,
            "timestamp": timestamp.isoformat(),
            "relative_time": relative_time,
            "details": details,
            "source": "global_input"
        }
        
        with self._lock:
            self.events.append(event)
        
        # Log at debug level to avoid spam
        logger.debug(f"Global input: {event_type} - {details.get('description', '')}")
    
    def _on_click(self, x: int, y: int, button, pressed: bool):
        """Handle mouse click events."""
        if not pressed:  # Only record on press, not release
            return
        
        button_name = str(button).replace("Button.", "")
        
        self._record_event("global_click", {
            "x": x,
            "y": y,
            "button": button_name,
            "description": f"Click at ({x}, {y}) with {button_name}"
        })
    
    def _on_scroll(self, x: int, y: int, dx: int, dy: int):
        """Handle mouse scroll events."""
        direction = "down" if dy < 0 else "up"
        self._record_event("global_scroll", {
            "x": x,
            "y": y,
            "dx": dx,
            "dy": dy,
            "direction": direction,
            "description": f"Scroll {direction} at ({x}, {y})"
        })
    
    def _on_move(self, x: int, y: int):
        """Handle mouse movement (optional, can be verbose)."""
        if not self.include_mouse_move:
            return
        # Only record occasionally to avoid flooding
        # This is handled by the caller setting include_mouse_move=False typically
        self._record_event("global_mouse_move", {
            "x": x,
            "y": y,
            "description": f"Mouse at ({x}, {y})"
        })
    
    def _on_key_press(self, key):
        """Handle key press events."""
        # Track modifier keys
        if hasattr(Key, 'shift') and key in (Key.shift, Key.shift_l, Key.shift_r):
            self._modifiers.add('shift')
            return
        if hasattr(Key, 'ctrl') and key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
            self._modifiers.add('ctrl')
            return
        if hasattr(Key, 'alt') and key in (Key.alt, Key.alt_l, Key.alt_r):
            self._modifiers.add('alt')
            return
        if hasattr(Key, 'cmd') and key in (Key.cmd, Key.cmd_l, Key.cmd_r):
            self._modifiers.add('cmd')
            return
        
        # Get key representation
        if isinstance(key, KeyCode):
            # Regular character key
            if self.mask_passwords and self.in_password_field:
                key_str = "*"  # Mask password characters
            else:
                key_str = key.char if key.char else str(key)
        else:
            # Special key (Enter, Tab, etc.)
            key_str = str(key).replace("Key.", "")
        
        # Build modifiers string
        mod_str = "+".join(sorted(self._modifiers)) + "+" if self._modifiers else ""
        
        self._record_event("global_keypress", {
            "key": key_str,
            "modifiers": list(self._modifiers),
            "is_special": not isinstance(key, KeyCode),
            "masked": self.mask_passwords and self.in_password_field,
            "description": f"Key: {mod_str}{key_str}"
        })
    
    def _on_key_release(self, key):
        """Handle key release events (mainly for tracking modifiers)."""
        # Remove modifiers when released
        if hasattr(Key, 'shift') and key in (Key.shift, Key.shift_l, Key.shift_r):
            self._modifiers.discard('shift')
        if hasattr(Key, 'ctrl') and key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
            self._modifiers.discard('ctrl')
        if hasattr(Key, 'alt') and key in (Key.alt, Key.alt_l, Key.alt_r):
            self._modifiers.discard('alt')
        if hasattr(Key, 'cmd') and key in (Key.cmd, Key.cmd_l, Key.cmd_r):
            self._modifiers.discard('cmd')
    
    def start(self) -> bool:
        """
        Start recording global input events.
        
        Returns:
            True if started successfully, False otherwise.
        """
        if not PYNPUT_AVAILABLE:
            logger.error("Cannot start global input recorder: pynput not available")
            return False
        
        if self.is_recording:
            logger.warning("Global input recorder is already running")
            return True
        
        try:
            self.start_time = datetime.now()
            self.events = []
            self._last_fetch_index = 0
            self.is_recording = True
            
            # Start keyboard listener
            self.keyboard_listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            )
            self.keyboard_listener.start()
            
            # Start mouse listener
            self.mouse_listener = mouse.Listener(
                on_click=self._on_click,
                on_scroll=self._on_scroll,
                on_move=self._on_move if self.include_mouse_move else None
            )
            self.mouse_listener.start()
            
            # Check if listeners are trusted (have permissions)
            if hasattr(self.keyboard_listener, 'IS_TRUSTED'):
                if not self.keyboard_listener.IS_TRUSTED:
                    logger.warning("⚠️  Keyboard listener not trusted. Grant Accessibility permissions.")
            
            logger.success(f"✅ Global input recorder started (target: {self.target_app})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start global input recorder: {e}")
            self.is_recording = False
            return False
    
    def stop(self) -> List[Dict]:
        """
        Stop recording and return all captured events.
        
        Returns:
            List of all recorded events.
        """
        if not self.is_recording:
            return self.events
        
        self.is_recording = False
        
        # Stop listeners
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
        
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
        
        logger.info(f"Global input recorder stopped. Captured {len(self.events)} events.")
        return self.events
    
    def get_events_since_last(self) -> List[Dict]:
        """
        Get events captured since the last call to this method.
        
        Returns:
            List of new events since last fetch.
        """
        with self._lock:
            new_events = self.events[self._last_fetch_index:]
            self._last_fetch_index = len(self.events)
        return new_events
    
    def get_all_events(self) -> List[Dict]:
        """
        Get all captured events.
        
        Returns:
            List of all events.
        """
        with self._lock:
            return list(self.events)
    
    def set_password_field_active(self, active: bool):
        """
        Signal that a password field is currently active.
        When True, keyboard input will be masked.
        
        Args:
            active: True if password field is focused.
        """
        self.in_password_field = active
    
    def get_summary(self) -> Dict:
        """
        Get a summary of recorded events.
        
        Returns:
            Dict with event counts by type.
        """
        summary = {
            "total_events": len(self.events),
            "clicks": 0,
            "keypresses": 0,
            "scrolls": 0,
            "duration_seconds": None
        }
        
        for event in self.events:
            event_type = event.get("type", "")
            if "click" in event_type:
                summary["clicks"] += 1
            elif "keypress" in event_type:
                summary["keypresses"] += 1
            elif "scroll" in event_type:
                summary["scrolls"] += 1
        
        if self.start_time:
            summary["duration_seconds"] = (datetime.now() - self.start_time).total_seconds()
        
        return summary


# Convenience function to check if global recording is available
def is_global_recording_available() -> bool:
    """Check if global input recording is available on this system."""
    return PYNPUT_AVAILABLE and APPKIT_AVAILABLE


# Test function
async def test_recorder():
    """Test the global input recorder."""
    if not is_global_recording_available():
        print("Global recording not available. Install: pip install pynput pyobjc-framework-Cocoa")
        return
    
    print("Starting global input recorder test...")
    print("Click and type in Safari for 10 seconds...")
    print()
    
    recorder = GlobalInputRecorder(target_app="Safari")
    recorder.start()
    
    await asyncio.sleep(10)
    
    events = recorder.stop()
    
    print(f"\nCaptured {len(events)} events:")
    for event in events[:20]:  # Show first 20
        print(f"  {event['type']}: {event['details'].get('description', '')}")
    
    if len(events) > 20:
        print(f"  ... and {len(events) - 20} more events")
    
    print(f"\nSummary: {recorder.get_summary()}")


if __name__ == "__main__":
    asyncio.run(test_recorder())
