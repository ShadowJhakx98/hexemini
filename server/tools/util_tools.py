from mcp.server.fastmcp import FastMCP, Context
import subprocess
import re
import os
import time
import platform
import psutil
from typing import Dict, List, Any, Optional

def register_util_tools(mcp: FastMCP):
    """Register utility tools with the MCP server"""
    
    @mcp.tool()
    def grep_search(
        pattern: str, 
        directory: str, 
        file_pattern: str = "*.*", 
        recursive: bool = True, 
        case_sensitive: bool = False
    ) -> str:
        """Search for a pattern in files (grep-like functionality)
        
        Args:
            pattern: Search pattern
            directory: Directory to search in
            file_pattern: File name pattern
            recursive: Whether to search recursively
            case_sensitive: Whether to perform case-sensitive search
            
        Returns:
            Search results
        """
        try:
            # Check if directory exists
            if not os.path.exists(directory) or not os.path.isdir(directory):
                return f"Error: Directory does not exist: {directory}"
                
            # Determine platform to use appropriate command
            system = platform.system()
            
            if system == "Windows":
                # Use findstr on Windows
                command = ["findstr"]
                
                # Add options
                if not case_sensitive:
                    command.append("/i")
                    
                if recursive:
                    command.append("/s")
                    
                # Add pattern and files
                command.append("/n")  # Line numbers
                command.append(pattern)
                
                # Specify file pattern
                file_path = os.path.join(directory, file_pattern)
                command.append(file_path)
            else:
                # Use grep on Unix-like systems
                command = ["grep"]
                
                # Add options
                if not case_sensitive:
                    command.append("-i")
                    
                if recursive:
                    command.append("-r")
                    
                # Add pattern and files
                command.append("-n")  # Line numbers
                command.append(pattern)
                
                # Specify directory and file pattern
                command.append("--include=" + file_pattern)
                command.append(directory)
                
            # Execute command
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Process output
            if process.returncode in [0, 1]:  # 0 = matches found, 1 = no matches
                output = process.stdout.strip()
                
                if not output:
                    return f"No matches found for pattern '{pattern}' in {directory}"
                    
                # Format results
                matches = output.split("\n")
                result = f"Found {len(matches)} matches for pattern '{pattern}' in {directory}:\n\n"
                
                # Limit number of results if too many
                max_results = 100
                if len(matches) > max_results:
                    result += "\n".join(matches[:max_results])
                    result += f"\n\n(Showing first {max_results} of {len(matches)} matches)"
                else:
                    result += output
                    
                return result
            else:
                return f"Error searching for pattern: {process.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: Search timed out (limited to 60 seconds)"
        except Exception as e:
            return f"Error searching for pattern: {str(e)}"
    
    @mcp.tool()
    def find_files(
        directory: str, 
        name_pattern: str = "*", 
        recursive: bool = True, 
        only_files: bool = False, 
        only_dirs: bool = False,
        newer_than: Optional[str] = None,
        max_depth: int = -1,
        min_size: Optional[str] = None,
        max_size: Optional[str] = None
    ) -> str:
        """Find files matching criteria
        
        Args:
            directory: Base directory to search in
            name_pattern: File name pattern (glob or regex)
            recursive: Whether to search recursively
            only_files: Only list files
            only_dirs: Only list directories
            newer_than: Only list items newer than this (e.g., '2d', '1w', '3m')
            max_depth: Maximum directory depth (-1 for unlimited)
            min_size: Minimum file size (e.g., '100k', '2M', '1G')
            max_size: Maximum file size (e.g., '100k', '2M', '1G')
            
        Returns:
            List of matching files
        """
        try:
            # Check if directory exists
            if not os.path.exists(directory) or not os.path.isdir(directory):
                return f"Error: Directory does not exist: {directory}"
                
            # Process newer_than parameter
            newer_than_timestamp = None
            if newer_than:
                match = re.match(r'(\d+)([dwmy])', newer_than.lower())
                if match:
                    value, unit = match.groups()
                    value = int(value)
                    
                    now = time.time()
                    if unit == 'd':
                        newer_than_timestamp = now - (value * 24 * 60 * 60)
                    elif unit == 'w':
                        newer_than_timestamp = now - (value * 7 * 24 * 60 * 60)
                    elif unit == 'm':
                        newer_than_timestamp = now - (value * 30 * 24 * 60 * 60)
                    elif unit == 'y':
                        newer_than_timestamp = now - (value * 365 * 24 * 60 * 60)
                else:
                    return f"Error: Invalid newer_than format: {newer_than}. Use format like '2d', '1w', '3m', '1y'."
            
            # Process size parameters
            min_size_bytes = None
            if min_size:
                match = re.match(r'(\d+)([kmg]?)', min_size.lower())
                if match:
                    value, unit = match.groups()
                    value = int(value)
                    
                    if unit == 'k':
                        min_size_bytes = value * 1024
                    elif unit == 'm':
                        min_size_bytes = value * 1024 * 1024
                    elif unit == 'g':
                        min_size_bytes = value * 1024 * 1024 * 1024
                    else:
                        min_size_bytes = value
                else:
                    return f"Error: Invalid min_size format: {min_size}. Use format like '100k', '2M', '1G'."
                    
            max_size_bytes = None
            if max_size:
                match = re.match(r'(\d+)([kmg]?)', max_size.lower())
                if match:
                    value, unit = match.groups()
                    value = int(value)
                    
                    if unit == 'k':
                        max_size_bytes = value * 1024
                    elif unit == 'm':
                        max_size_bytes = value * 1024 * 1024
                    elif unit == 'g':
                        max_size_bytes = value * 1024 * 1024 * 1024
                    else:
                        max_size_bytes = value
                else:
                    return f"Error: Invalid max_size format: {max_size}. Use format like '100k', '2M', '1G'."
            
            # Check if name pattern is a glob pattern or regex
            is_glob = any(c in name_pattern for c in '*?[]{}')
            if is_glob:
                import fnmatch
                matcher = lambda name: fnmatch.fnmatch(name, name_pattern)
            else:
                pattern = re.compile(name_pattern)
                matcher = lambda name: bool(pattern.search(name))
            
            # Walk directory and find matches
            matches = []
            
            for root, dirs, files in os.walk(directory):
                # Check depth
                if max_depth >= 0:
                    depth = root[len(directory):].count(os.sep)
                    if depth > max_depth:
                        dirs[:] = []  # Prune subdirectories
                        continue
                
                # Process directories
                if not only_files:
                    for dir_name in dirs:
                        if matcher(dir_name):
                            dir_path = os.path.join(root, dir_name)
                            
                            # Check newer_than
                            if newer_than_timestamp:
                                dir_mtime = os.path.getmtime(dir_path)
                                if dir_mtime < newer_than_timestamp:
                                    continue
                                    
                            matches.append(("DIR", dir_path))
                
                # Process files
                if not only_dirs:
                    for file_name in files:
                        if matcher(file_name):
                            file_path = os.path.join(root, file_name)
                            
                            # Check newer_than
                            if newer_than_timestamp:
                                file_mtime = os.path.getmtime(file_path)
                                if file_mtime < newer_than_timestamp:
                                    continue
                            
                            # Check size constraints
                            if min_size_bytes or max_size_bytes:
                                try:
                                    file_size = os.path.getsize(file_path)
                                    
                                    if min_size_bytes and file_size < min_size_bytes:
                                        continue
                                        
                                    if max_size_bytes and file_size > max_size_bytes:
                                        continue
                                except:
                                    continue
                                    
                            matches.append(("FILE", file_path))
                
                # Stop if not recursive
                if not recursive:
                    break
            
            # Format results
            if not matches:
                return f"No matches found for pattern '{name_pattern}' in {directory}"
                
            # Sort matches
            matches.sort(key=lambda x: x[1])
            
            # Format results
            result = f"Found {len(matches)} matches for pattern '{name_pattern}' in {directory}:\n\n"
            
            # Limit number of results if too many
            max_results = 100
            if len(matches) > max_results:
                for item_type, item_path in matches[:max_results]:
                    rel_path = os.path.relpath(item_path, directory)
                    result += f"[{item_type}] {rel_path}\n"
                    
                result += f"\n(Showing first {max_results} of {len(matches)} matches)"
            else:
                for item_type, item_path in matches:
                    rel_path = os.path.relpath(item_path, directory)
                    result += f"[{item_type}] {rel_path}\n"
                    
            return result
        except Exception as e:
            return f"Error finding files: {str(e)}"
    
    @mcp.tool()
    def system_info() -> str:
        """Get system information
        
        Returns:
            System information
        """
        try:
            # Get platform information
            system = platform.system()
            release = platform.release()
            version = platform.version()
            machine = platform.machine()
            processor = platform.processor()
            
            # Get CPU information
            cpu_count = psutil.cpu_count(logical=False)
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Get memory information
            memory = psutil.virtual_memory()
            total_memory = memory.total
            available_memory = memory.available
            memory_percent = memory.percent
            
            # Get disk information
            disk = psutil.disk_usage('/')
            total_disk = disk.total
            free_disk = disk.free
            disk_percent = disk.percent
            
            # Format memory sizes
            def format_size(bytes):
                if bytes < 1024:
                    return f"{bytes} bytes"
                elif bytes < 1024 * 1024:
                    return f"{bytes / 1024:.1f} KB"
                elif bytes < 1024 * 1024 * 1024:
                    return f"{bytes / (1024 * 1024):.1f} MB"
                else:
                    return f"{bytes / (1024 * 1024 * 1024):.1f} GB"
            
            # Format result
            result = (
                f"System Information:\n"
                f"Platform: {system} {release} ({version})\n"
                f"Architecture: {machine}\n"
                f"Processor: {processor}\n\n"
                
                f"CPU Information:\n"
                f"Physical cores: {cpu_count}\n"
                f"Logical cores: {cpu_count_logical}\n"
                f"Current CPU usage: {cpu_percent}%\n\n"
                
                f"Memory Information:\n"
                f"Total memory: {format_size(total_memory)}\n"
                f"Available memory: {format_size(available_memory)}\n"
                f"Memory usage: {memory_percent}%\n\n"
                
                f"Disk Information:\n"
                f"Total disk space: {format_size(total_disk)}\n"
                f"Free disk space: {format_size(free_disk)}\n"
                f"Disk usage: {disk_percent}%\n"
            )
            
            return result
        except Exception as e:
            return f"Error getting system information: {str(e)}"
