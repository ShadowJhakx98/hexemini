from mcp.server.fastmcp import FastMCP, Context
import pyautogui
import subprocess
import os
import time
import platform
from typing import Dict, List, Any, Optional, Union

# Configure PyAutoGUI
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.5      # Add delay between actions

def register_automation_tools(mcp: FastMCP):
    """Register automation-related tools with the MCP server"""
    
    # Global settings
    AUTOMATION_ENABLED = False
    SAFE_MODE = True  # Restrict certain operations
    
    def enable_automation(enabled: bool = True, safe_mode: bool = True):
        """Enable or disable automation features"""
        nonlocal AUTOMATION_ENABLED, SAFE_MODE
        AUTOMATION_ENABLED = enabled
        SAFE_MODE = safe_mode
        status = "enabled" if enabled else "disabled"
        safety = "with safety restrictions" if safe_mode else "without safety restrictions"
        print(f"Automation features {status} {safety}")
        
    def check_automation_enabled():
        """Check if automation is enabled"""
        if not AUTOMATION_ENABLED:
            raise ValueError("Automation features are disabled. Call enable_automation() first.")
    
    @mcp.tool()
    def mouse_move(x: int, y: int) -> str:
        """Move mouse to specific coordinates
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Result message
        """
        try:
            check_automation_enabled()
            pyautogui.moveTo(x, y)
            return f"Moved mouse to coordinates ({x}, {y})"
        except Exception as e:
            return f"Error moving mouse: {str(e)}"
    
    @mcp.tool()
    def mouse_click(button: str = "left", clicks: int = 1) -> str:
        """Perform mouse click at current position
        
        Args:
            button: Mouse button ('left', 'right', or 'middle')
            clicks: Number of clicks
            
        Returns:
            Result message
        """
        try:
            check_automation_enabled()
            
            # Validate parameters
            valid_buttons = ["left", "right", "middle"]
            if button not in valid_buttons:
                return f"Error: button must be one of {valid_buttons}"
                
            clicks = min(max(1, clicks), 3)  # Limit to 1-3 clicks
            
            # Perform click
            pyautogui.click(button=button, clicks=clicks)
            return f"Performed {clicks} {button} click(s) at current position"
        except Exception as e:
            return f"Error clicking mouse: {str(e)}"
    
    @mcp.tool()
    def mouse_drag(x: int, y: int, duration: float = 0.5) -> str:
        """Drag mouse from current position to specified coordinates
        
        Args:
            x: Target X coordinate
            y: Target Y coordinate
            duration: Duration of drag in seconds
            
        Returns:
            Result message
        """
        try:
            check_automation_enabled()
            
            # Limit duration for safety
            duration = min(max(0.1, duration), 2.0)
            
            # Perform drag
            pyautogui.dragTo(x, y, duration=duration)
            return f"Dragged mouse to coordinates ({x}, {y}) over {duration} seconds"
        except Exception as e:
            return f"Error dragging mouse: {str(e)}"
    
    @mcp.tool()
    def keyboard_type(text: str) -> str:
        """Type text using keyboard
        
        Args:
            text: Text to type
            
        Returns:
            Result message
        """
        try:
            check_automation_enabled()
            
            # Safety checks
            if SAFE_MODE:
                # Limit length for safety
                if len(text) > 100:
                    return "Error: Text too long in safe mode. Maximum 100 characters allowed."
                    
                # Restrict potentially harmful commands
                danger_strings = ["sudo ", "rm -", "format ", "del ", "deltree"]
                if any(danger in text.lower() for danger in danger_strings):
                    return "Error: Potentially harmful command detected in safe mode."
            
            # Type text
            pyautogui.typewrite(text)
            
            # Return truncated text for privacy if long
            if len(text) > 20:
                display_text = text[:17] + "..."
            else:
                display_text = text
                
            return f"Typed text: '{display_text}'"
        except Exception as e:
            return f"Error typing: {str(e)}"
    
    @mcp.tool()
    def keyboard_hotkey(*keys) -> str:
        """Press key combination
        
        Args:
            *keys: Keys to press together (e.g., 'ctrl', 'c')
            
        Returns:
            Result message
        """
        try:
            check_automation_enabled()
            
            # Safety checks for potentially harmful key combinations
            if SAFE_MODE:
                danger_combinations = [
                    ('alt', 'f4'),
                    ('ctrl', 'alt', 'del'),
                    ('command', 'q')
                ]
                
                if any(all(k in keys for k in combo) for combo in danger_combinations):
                    return "Error: Potentially harmful key combination detected in safe mode."
            
            # Press keys
            pyautogui.hotkey(*keys)
            return f"Pressed keys: {', '.join(keys)}"
        except Exception as e:
            return f"Error pressing hotkey: {str(e)}"
    
    @mcp.tool()
    def run_command(command: str, working_dir: str = None, timeout: int = 30) -> str:
        """Run a command in the system shell
        
        Args:
            command: Command to run
            working_dir: Working directory (optional)
            timeout: Maximum execution time in seconds
            
        Returns:
            Command output
        """
        try:
            check_automation_enabled()
            
            # Safety checks
            if SAFE_MODE:
                # Restrict potentially harmful commands
                danger_commands = [
                    "rm -rf", "deltree", "format", 
                    "dd if=", "mkfs", ">", 
                    "sudo ", "su ", "passwd"
                ]
                
                if any(danger in command.lower() for danger in danger_commands):
                    return "Error: Potentially harmful command detected in safe mode."
            
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=working_dir,
                timeout=timeout,
                capture_output=True,
                text=True
            )
            
            # Format result
            output = result.stdout
            errors = result.stderr
            exit_code = result.returncode
            
            response = f"Command executed with exit code {exit_code}\n\n"
            
            if output:
                response += f"Output:\n{output}\n"
                
            if errors:
                response += f"Errors:\n{errors}\n"
                
            return response
        except subprocess.TimeoutExpired:
            return f"Error: Command execution timed out after {timeout} seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"
    
    @mcp.tool()
    def find_image_on_screen(
        image_path: str, 
        confidence: float = 0.9, 
        wait_time: int = 0
    ) -> str:
        """Find an image on screen
        
        Args:
            image_path: Path to image file
            confidence: Match confidence (0.0-1.0)
            wait_time: Time to wait for image to appear (seconds)
            
        Returns:
            Location information or failure message
        """
        try:
            check_automation_enabled()
            
            # Check if image exists
            if not os.path.exists(image_path):
                return f"Error: Image file does not exist: {image_path}"
                
            # Try to find image
            start_time = time.time()
            end_time = start_time + wait_time
            
            while time.time() < end_time:
                try:
                    location = pyautogui.locateOnScreen(
                        image_path, 
                        confidence=confidence
                    )
                    
                    if location:
                        x, y = pyautogui.center(location)
                        return f"Found image at coordinates ({x}, {y})"
                        
                    # Wait a bit before trying again
                    time.sleep(0.5)
                except:
                    # Wait a bit before trying again
                    time.sleep(0.5)
            
            # Try one last time
            try:
                location = pyautogui.locateOnScreen(
                    image_path, 
                    confidence=confidence
                )
                
                if location:
                    x, y = pyautogui.center(location)
                    return f"Found image at coordinates ({x}, {y})"
            except:
                pass
                
            return f"Image not found on screen: {image_path}"
        except Exception as e:
            return f"Error finding image: {str(e)}"
    
    @mcp.tool()
    def screenshot(file_path: str = None) -> str:
        """Take a screenshot
        
        Args:
            file_path: Path to save screenshot (optional)
            
        Returns:
            Result message
        """
        try:
            check_automation_enabled()
            
            # Take screenshot
            if file_path:
                # Ensure directory exists
                os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                
                # Take and save screenshot
                screenshot = pyautogui.screenshot()
                screenshot.save(file_path)
                return f"Screenshot saved to {file_path}"
            else:
                # Generate default filename
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                file_path = f"screenshot-{timestamp}.png"
                
                # Take and save screenshot
                screenshot = pyautogui.screenshot()
                screenshot.save(file_path)
                return f"Screenshot saved to {file_path}"
        except Exception as e:
            return f"Error taking screenshot: {str(e)}"
    
    @mcp.tool()
    def get_screen_info() -> str:
        """Get information about screen size and mouse position
        
        Returns:
            Screen and mouse information
        """
        try:
            check_automation_enabled()
            
            # Get screen size
            screen_width, screen_height = pyautogui.size()
            
            # Get current mouse position
            mouse_x, mouse_y = pyautogui.position()
            
            # Format result
            return (
                f"Screen size: {screen_width}x{screen_height}\n"
                f"Current mouse position: ({mouse_x}, {mouse_y})"
            )
        except Exception as e:
            return f"Error getting screen info: {str(e)}"
            
    # Expose the configuration function
    return {
        "enable_automation": enable_automation
    }
