# Import server
from .server import mcp

# Configuration functions are exported here for easy access
__all__ = ['configure_server', 'set_allowed_directories', 'enable_automation']

def configure_server(allowed_dirs=None, enable_auto=False, safe_mode=True):
    """Configure the MCP server with all tools and settings
    
    Args:
        allowed_dirs: List of directories to allow filesystem access to
        enable_auto: Whether to enable automation features
        safe_mode: Whether to enable safety restrictions for automation
        
    Returns:
        Configured MCP server instance
    """
    # Import tool modules
    from .tools import memory_tools
    from .tools import search_tools
    from .tools import fs_tools
    from .tools import weather_tools
    from .tools import automation_tools
    from .tools import image_tools
    from .tools import video_tools
    from .tools import code_tools
    from .tools import util_tools
    
    # Register tool modules
    memory_tools.register_memory_tools(mcp)
    search_tools.register_search_tools(mcp)
    fs_config = fs_tools.register_fs_tools(mcp)
    weather_tools.register_weather_tools(mcp)
    auto_config = automation_tools.register_automation_tools(mcp)
    image_tools.register_image_tools(mcp)
    video_tools.register_video_tools(mcp)
    code_tools.register_code_tools(mcp)
    util_tools.register_util_tools(mcp)
    
    # Configure filesystem access if directories specified
    if allowed_dirs:
        fs_config["set_allowed_directories"](allowed_dirs)
    
    # Configure automation features
    auto_config["enable_automation"](enable_auto, safe_mode)
    
    # Store configuration functions for later use
    global _fs_config, _auto_config
    _fs_config = fs_config
    _auto_config = auto_config
    
    return mcp

# Global references to configuration functions
_fs_config = None
_auto_config = None

def set_allowed_directories(dirs):
    """Configure allowed directories for filesystem access"""
    if _fs_config is None:
        raise RuntimeError("Server not configured. Call configure_server() first.")
    _fs_config["set_allowed_directories"](dirs)

def enable_automation(enabled=True, safe_mode=True):
    """Enable or disable automation features"""
    if _auto_config is None:
        raise RuntimeError("Server not configured. Call configure_server() first.")
    _auto_config["enable_automation"](enabled, safe_mode)
