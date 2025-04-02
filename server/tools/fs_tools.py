from mcp.server.fastmcp import FastMCP, Context, Image
import os
import shutil
import glob
from typing import List, Dict, Any, Optional
from pathlib import Path
import base64
from PIL import Image as PILImage
from io import BytesIO

def register_fs_tools(mcp: FastMCP):
    """Register filesystem-related tools with the MCP server"""
    
    # List of allowed directories (for security)
    ALLOWED_DIRS = []
    
    def set_allowed_directories(dirs: List[str]):
        """Set allowed directories for filesystem access"""
        ALLOWED_DIRS.extend([os.path.abspath(d) for d in dirs])
        print(f"Filesystem access allowed for: {ALLOWED_DIRS}")
        
    def check_path_allowed(path: str) -> bool:
        """Check if a path is within allowed directories"""
        abs_path = os.path.abspath(path)
        return any(abs_path.startswith(allowed_dir) for allowed_dir in ALLOWED_DIRS)
    
    @mcp.tool()
    def list_directory(path: str) -> str:
        """List contents of a directory
        
        Args:
            path: Directory path to list
            
        Returns:
            Directory listing
        """
        if not ALLOWED_DIRS:
            return "Error: No filesystem directories have been allowed"
            
        if not check_path_allowed(path):
            return f"Error: Access denied to {path}"
            
        try:
            # Get directory listing
            items = os.listdir(path)
            
            # Format results
            files = []
            directories = []
            
            for item in items:
                full_path = os.path.join(path, item)
                
                if os.path.isdir(full_path):
                    directories.append(f"📁 {item}/")
                else:
                    # Get file size
                    try:
                        size = os.path.getsize(full_path)
                        size_str = f"{size} bytes"
                        
                        if size >= 1024:
                            size_str = f"{size / 1024:.1f} KB"
                        if size >= 1024 * 1024:
                            size_str = f"{size / (1024 * 1024):.1f} MB"
                            
                        files.append(f"📄 {item} ({size_str})")
                    except:
                        files.append(f"📄 {item}")
            
            # Sort directories and files
            directories.sort()
            files.sort()
            
            # Combine results
            result = f"Contents of {path}:\n\n"
            
            if directories:
                result += "Directories:\n"
                result += "\n".join(directories)
                result += "\n\n"
                
            if files:
                result += "Files:\n"
                result += "\n".join(files)
            
            return result
        except Exception as e:
            return f"Error listing directory: {str(e)}"
    
    @mcp.tool()
    def read_file(path: str, max_size: int = 10000) -> str:
        """Read a text file
        
        Args:
            path: Path to file
            max_size: Maximum file size to read in bytes
            
        Returns:
            File contents
        """
        if not ALLOWED_DIRS:
            return "Error: No filesystem directories have been allowed"
            
        if not check_path_allowed(path):
            return f"Error: Access denied to {path}"
            
        try:
            if not os.path.exists(path):
                return f"Error: File does not exist: {path}"
                
            # Check file size
            file_size = os.path.getsize(path)
            if file_size > max_size:
                return f"Error: File is too large ({file_size} bytes). Maximum size is {max_size} bytes."
                
            # Try to read as text
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                return "Error: File appears to be binary, not text."
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    @mcp.tool()
    def write_file(path: str, content: str, overwrite: bool = False) -> str:
        """Write content to a text file
        
        Args:
            path: Path to file
            content: Content to write
            overwrite: Whether to overwrite existing file
            
        Returns:
            Result message
        """
        if not ALLOWED_DIRS:
            return "Error: No filesystem directories have been allowed"
            
        if not check_path_allowed(path):
            return f"Error: Access denied to {path}"
            
        try:
            # Check if file exists
            if os.path.exists(path) and not overwrite:
                return f"Error: File already exists and overwrite is False: {path}"
                
            # Write file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return f"Successfully wrote {len(content)} bytes to {path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    @mcp.tool()
    def create_directory(path: str) -> str:
        """Create a directory
        
        Args:
            path: Path to directory
            
        Returns:
            Result message
        """
        if not ALLOWED_DIRS:
            return "Error: No filesystem directories have been allowed"
            
        if not check_path_allowed(path):
            return f"Error: Access denied to {path}"
            
        try:
            os.makedirs(path, exist_ok=True)
            return f"Successfully created directory: {path}"
        except Exception as e:
            return f"Error creating directory: {str(e)}"
    
    @mcp.tool()
    def delete_item(path: str, recursive: bool = False) -> str:
        """Delete a file or directory
        
        Args:
            path: Path to delete
            recursive: Whether to recursively delete (for directories)
            
        Returns:
            Result message
        """
        if not ALLOWED_DIRS:
            return "Error: No filesystem directories have been allowed"
            
        if not check_path_allowed(path):
            return f"Error: Access denied to {path}"
            
        try:
            if not os.path.exists(path):
                return f"Error: File or directory does not exist: {path}"
                
            if os.path.isdir(path):
                if recursive:
                    shutil.rmtree(path)
                    return f"Successfully deleted directory and contents: {path}"
                else:
                    os.rmdir(path)
                    return f"Successfully deleted directory: {path}"
            else:
                os.remove(path)
                return f"Successfully deleted file: {path}"
        except Exception as e:
            return f"Error deleting item: {str(e)}"
    
    @mcp.tool()
    def move_item(source: str, destination: str) -> str:
        """Move a file or directory
        
        Args:
            source: Source path
            destination: Destination path
            
        Returns:
            Result message
        """
        if not ALLOWED_DIRS:
            return "Error: No filesystem directories have been allowed"
            
        if not check_path_allowed(source) or not check_path_allowed(destination):
            return f"Error: Access denied to {source} or {destination}"
            
        try:
            if not os.path.exists(source):
                return f"Error: Source does not exist: {source}"
                
            if os.path.exists(destination):
                return f"Error: Destination already exists: {destination}"
                
            shutil.move(source, destination)
            return f"Successfully moved {source} to {destination}"
        except Exception as e:
            return f"Error moving item: {str(e)}"
    
    @mcp.tool()
    def copy_item(source: str, destination: str) -> str:
        """Copy a file or directory
        
        Args:
            source: Source path
            destination: Destination path
            
        Returns:
            Result message
        """
        if not ALLOWED_DIRS:
            return "Error: No filesystem directories have been allowed"
            
        if not check_path_allowed(source) or not check_path_allowed(destination):
            return f"Error: Access denied to {source} or {destination}"
            
        try:
            if not os.path.exists(source):
                return f"Error: Source does not exist: {source}"
                
            if os.path.exists(destination):
                return f"Error: Destination already exists: {destination}"
                
            if os.path.isdir(source):
                shutil.copytree(source, destination)
                return f"Successfully copied directory {source} to {destination}"
            else:
                shutil.copy2(source, destination)
                return f"Successfully copied file {source} to {destination}"
        except Exception as e:
            return f"Error copying item: {str(e)}"
    
    @mcp.tool()
    def search_files(directory: str, pattern: str, recursive: bool = True) -> str:
        """Search for files matching a pattern
        
        Args:
            directory: Base directory to search in
            pattern: Search pattern (glob style)
            recursive: Whether to search recursively
            
        Returns:
            List of matching files
        """
        if not ALLOWED_DIRS:
            return "Error: No filesystem directories have been allowed"
            
        if not check_path_allowed(directory):
            return f"Error: Access denied to {directory}"
            
        try:
            # Build search pattern
            search_path = os.path.join(directory, pattern)
            
            # Perform search
            if recursive:
                matches = glob.glob(search_path, recursive=True)
            else:
                matches = glob.glob(search_path)
                
            if not matches:
                return f"No files found matching pattern '{pattern}' in {directory}"
                
            # Format results
            results = [f"{i+1}. {match}" for i, match in enumerate(matches)]
            
            header = f"Found {len(matches)} files matching pattern '{pattern}' in {directory}:"
            
            return header + "\n" + "\n".join(results)
        except Exception as e:
            return f"Error searching files: {str(e)}"
    
    @mcp.tool()
    def read_image(path: str) -> Image:
        """Read an image file and return it
        
        Args:
            path: Path to image file
            
        Returns:
            Image object
        """
        if not ALLOWED_DIRS:
            raise ValueError("No filesystem directories have been allowed")
            
        if not check_path_allowed(path):
            raise ValueError(f"Access denied to {path}")
            
        if not os.path.exists(path):
            raise ValueError(f"File does not exist: {path}")
            
        # Read image
        try:
            img = PILImage.open(path)
            
            # Convert to RGB if needed
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
                
            # Create buffer
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Get image data
            image_data = buffer.getvalue()
            
            # Create Image object
            return Image(data=image_data, format="png")
        except Exception as e:
            raise ValueError(f"Error reading image: {str(e)}")
            
    # Expose the configuration function
    return {
        "set_allowed_directories": set_allowed_directories
    }
