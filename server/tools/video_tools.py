from mcp.server.fastmcp import FastMCP, Context, Image
import os
import subprocess
import tempfile
import base64
import io
from PIL import Image as PILImage
import httpx
import time
from typing import Dict, List, Any, Optional
import json

# We're using a simplified approach that doesn't require OpenCV
# In a more comprehensive implementation, you'd want to use OpenCV for better video processing

def register_video_tools(mcp: FastMCP):
    """Register video-related tools with the MCP server"""

    # OpenAI API key for vision analysis
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    @mcp.tool()
    def extract_video_frame(video_path: str, timestamp: str) -> Image:
        """Extract a frame from a video at a specific timestamp
        
        Args:
            video_path: Path to video file
            timestamp: Timestamp in format HH:MM:SS
            
        Returns:
            Frame image
        """
        try:
            # Check if video exists
            if not os.path.exists(video_path):
                raise ValueError(f"Video file does not exist: {video_path}")
                
            # Create temporary file for frame
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp:
                temp_path = temp.name
                
            # Use ffmpeg to extract frame
            subprocess.run([
                "ffmpeg",
                "-i", video_path,
                "-ss", timestamp,
                "-frames:v", "1",
                "-q:v", "2",
                temp_path
            ], check=True, capture_output=True)
            
            # Check if frame was extracted
            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise ValueError(f"Failed to extract frame at timestamp {timestamp}")
                
            # Read frame
            with open(temp_path, 'rb') as f:
                image_data = f.read()
                
            # Clean up
            try:
                os.remove(temp_path)
            except:
                pass
                
            # Return Image object
            return Image(data=image_data, format="png")
        except Exception as e:
            raise ValueError(f"Error extracting video frame: {str(e)}")
    
    @mcp.tool()
    def video_info(video_path: str) -> str:
        """Get information about a video
        
        Args:
            video_path: Path to video file
            
        Returns:
            Video information
        """
        try:
            # Check if video exists
            if not os.path.exists(video_path):
                return f"Error: Video file does not exist: {video_path}"
                
            # Use ffprobe to get video information
            result = subprocess.run([
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ], check=True, capture_output=True, text=True)
            
            # Parse result
            info = json.loads(result.stdout)
            
            # Extract relevant information
            video_info = {}
            
            # Get format information
            format_info = info.get("format", {})
            video_info["filename"] = format_info.get("filename", "Unknown")
            video_info["format"] = format_info.get("format_name", "Unknown")
            video_info["duration"] = format_info.get("duration", "Unknown")
            
            # Calculate file size
            size_bytes = int(format_info.get("size", 0))
            if size_bytes < 1024:
                size_str = f"{size_bytes} bytes"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
                
            video_info["size"] = size_str
            
            # Get video stream information
            video_streams = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
            audio_streams = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
            
            if video_streams:
                video_stream = video_streams[0]
                video_info["codec"] = video_stream.get("codec_name", "Unknown")
                video_info["resolution"] = f"{video_stream.get('width', 'Unknown')}x{video_stream.get('height', 'Unknown')}"
                video_info["fps"] = eval(video_stream.get("r_frame_rate", "0/1"))
                
            if audio_streams:
                audio_stream = audio_streams[0]
                video_info["audio_codec"] = audio_stream.get("codec_name", "Unknown")
                video_info["audio_channels"] = audio_stream.get("channels", "Unknown")
                video_info["audio_sample_rate"] = audio_stream.get("sample_rate", "Unknown")
                
            # Format result
            result = (
                f"Video: {os.path.basename(video_info['filename'])}\n"
                f"Format: {video_info['format']}\n"
                f"Duration: {float(video_info['duration']):.2f} seconds\n"
                f"Size: {video_info['size']}\n"
            )
            
            if "codec" in video_info:
                result += (
                    f"Video codec: {video_info['codec']}\n"
                    f"Resolution: {video_info['resolution']}\n"
                    f"Frame rate: {video_info['fps']:.2f} fps\n"
                )
                
            if "audio_codec" in video_info:
                result += (
                    f"Audio codec: {video_info['audio_codec']}\n"
                    f"Audio channels: {video_info['audio_channels']}\n"
                    f"Audio sample rate: {video_info['audio_sample_rate']} Hz\n"
                )
                
            return result
        except Exception as e:
            return f"Error getting video info: {str(e)}"
    
    @mcp.tool()
    def extract_video_frames(
        video_path: str, 
        start_time: str, 
        duration: float, 
        frame_count: int, 
        output_dir: str
    ) -> str:
        """Extract multiple frames from a video
        
        Args:
            video_path: Path to video file
            start_time: Start timestamp in format HH:MM:SS
            duration: Duration in seconds
            frame_count: Number of frames to extract
            output_dir: Directory to save frames
            
        Returns:
            Result message
        """
        try:
            # Check if video exists
            if not os.path.exists(video_path):
                return f"Error: Video file does not exist: {video_path}"
                
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
                
            # Calculate frame rate
            frame_rate = frame_count / duration
                
            # Use ffmpeg to extract frames
            subprocess.run([
                "ffmpeg",
                "-i", video_path,
                "-ss", start_time,
                "-t", str(duration),
                "-vf", f"fps={frame_rate}",
                "-q:v", "2",
                os.path.join(output_dir, "frame_%04d.png")
            ], check=True, capture_output=True)
                
            # Check if frames were extracted
            extracted_frames = [f for f in os.listdir(output_dir) if f.startswith("frame_")]
            
            if not extracted_frames:
                return f"Error: No frames were extracted"
                
            return f"Successfully extracted {len(extracted_frames)} frames to {output_dir}"
        except Exception as e:
            return f"Error extracting video frames: {str(e)}"
    
    @mcp.tool()
    async def analyze_video_frame(video_path: str, timestamp: str, ctx: Context) -> str:
        """Analyze a video frame using vision API
        
        Args:
            video_path: Path to video file
            timestamp: Timestamp in format HH:MM:SS
            
        Returns:
            Analysis results
        """
        if not OPENAI_API_KEY:
            return "Error: OpenAI API key not configured"
            
        try:
            # Extract frame
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp:
                temp_path = temp.name
                
            # Use ffmpeg to extract frame
            subprocess.run([
                "ffmpeg",
                "-i", video_path,
                "-ss", timestamp,
                "-frames:v", "1",
                "-q:v", "2",
                temp_path
            ], check=True, capture_output=True)
            
            # Convert frame to base64
            with open(temp_path, "rb") as f:
                image_data = f.read()
                base64_image = base64.b64encode(image_data).decode("utf-8")
                
            # Clean up
            try:
                os.remove(temp_path)
            except:
                pass
                
            # Call Vision API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4-vision-preview",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"Analyze this video frame from timestamp {timestamp}. Describe what you see in detail."
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 300
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    return f"Error: API returned status code {response.status_code}"
                    
                # Parse response
                data = response.json()
                
                if "choices" not in data or not data["choices"]:
                    return "Error: No analysis result in response"
                    
                # Get analysis text
                analysis = data["choices"][0]["message"]["content"]
                
                return f"Video frame analysis (timestamp {timestamp}):\n\n{analysis}"
        except Exception as e:
            return f"Error analyzing video frame: {str(e)}"
