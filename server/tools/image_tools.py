from mcp.server.fastmcp import FastMCP, Context, Image
from PIL import Image as PILImage, ImageFilter, ImageEnhance, ImageOps
import httpx
import base64
import io
import os
import numpy as np
from typing import Dict, List, Any, Optional
import tempfile
import requests

# Image generation API keys
DALL_E_API_KEY = os.getenv("OPENAI_API_KEY", "")
STABLE_DIFFUSION_API_KEY = os.getenv("STABLE_DIFFUSION_API_KEY", "")

def register_image_tools(mcp: FastMCP):
    """Register image-related tools with the MCP server"""
    
    @mcp.tool()
    async def generate_image(prompt: str, model: str = "dall-e-3", size: str = "1024x1024", ctx: Context) -> Image:
        """Generate an image based on a text prompt
        
        Args:
            prompt: Description of the image to generate
            model: Model to use ('dall-e-3', 'stable-diffusion')
            size: Image size (width x height)
            
        Returns:
            Generated image
        """
        if model == "dall-e-3":
            if not DALL_E_API_KEY:
                raise ValueError("DALL-E API key not configured")
                
            try:
                # Call DALL-E API
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.openai.com/v1/images/generations",
                        headers={
                            "Authorization": f"Bearer {DALL_E_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "prompt": prompt,
                            "model": "dall-e-3",
                            "n": 1,
                            "size": size,
                            "response_format": "b64_json"
                        },
                        timeout=60.0
                    )
                    
                    if response.status_code != 200:
                        raise ValueError(f"API returned status code {response.status_code}")
                        
                    # Parse response
                    data = response.json()
                    
                    if "data" not in data or not data["data"]:
                        raise ValueError("No image data in response")
                        
                    # Get image data
                    image_data = base64.b64decode(data["data"][0]["b64_json"])
                    
                    # Return Image object
                    return Image(data=image_data, format="png")
            except Exception as e:
                raise ValueError(f"Error generating image: {str(e)}")
        elif model == "stable-diffusion":
            if not STABLE_DIFFUSION_API_KEY:
                raise ValueError("Stable Diffusion API key not configured")
                
            try:
                # Call Stable Diffusion API
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                        headers={
                            "Authorization": f"Bearer {STABLE_DIFFUSION_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "text_prompts": [{"text": prompt}],
                            "cfg_scale": 7,
                            "height": int(size.split("x")[1]),
                            "width": int(size.split("x")[0]),
                            "samples": 1,
                            "steps": 30
                        },
                        timeout=60.0
                    )
                    
                    if response.status_code != 200:
                        raise ValueError(f"API returned status code {response.status_code}")
                        
                    # Parse response
                    data = response.json()
                    
                    if "artifacts" not in data or not data["artifacts"]:
                        raise ValueError("No image data in response")
                        
                    # Get image data
                    image_data = base64.b64decode(data["artifacts"][0]["base64"])
                    
                    # Return Image object
                    return Image(data=image_data, format="png")
            except Exception as e:
                raise ValueError(f"Error generating image: {str(e)}")
        else:
            raise ValueError(f"Unsupported model: {model}")
    
    @mcp.tool()
    def image_filter(image_path: str, filter_type: str) -> Image:
        """Apply filter to an image
        
        Args:
            image_path: Path to image file
            filter_type: Type of filter to apply
            
        Returns:
            Filtered image
        """
        try:
            # Check if image exists
            if not os.path.exists(image_path):
                raise ValueError(f"Image file does not exist: {image_path}")
                
            # Open image
            img = PILImage.open(image_path)
            
            # Apply filter
            if filter_type == "blur":
                img = img.filter(ImageFilter.BLUR)
            elif filter_type == "sharpen":
                img = img.filter(ImageFilter.SHARPEN)
            elif filter_type == "contour":
                img = img.filter(ImageFilter.CONTOUR)
            elif filter_type == "emboss":
                img = img.filter(ImageFilter.EMBOSS)
            elif filter_type == "grayscale":
                img = ImageOps.grayscale(img)
            elif filter_type == "sepia":
                sepia_img = img.convert("RGB")
                r, g, b = 1.0, 0.8, 0.6
                matrix = [
                    r, r, r, 0,
                    g, g, g, 0,
                    b, b, b, 0,
                    0, 0, 0, 1
                ]
                img = sepia_img.convert("RGB", matrix)
            elif filter_type == "edge_enhance":
                img = img.filter(ImageFilter.EDGE_ENHANCE)
            elif filter_type == "smooth":
                img = img.filter(ImageFilter.SMOOTH)
            else:
                raise ValueError(f"Unsupported filter type: {filter_type}")
                
            # Convert to RGB if needed
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
                
            # Create buffer
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Get image data
            image_data = buffer.getvalue()
            
            # Return Image object
            return Image(data=image_data, format="png")
        except Exception as e:
            raise ValueError(f"Error applying filter: {str(e)}")
    
    @mcp.tool()
    def image_adjust(
        image_path: str, 
        brightness: float = 1.0, 
        contrast: float = 1.0, 
        saturation: float = 1.0
    ) -> Image:
        """Adjust image properties
        
        Args:
            image_path: Path to image file
            brightness: Brightness factor (0.0-2.0)
            contrast: Contrast factor (0.0-2.0)
            saturation: Saturation factor (0.0-2.0)
            
        Returns:
            Adjusted image
        """
        try:
            # Check if image exists
            if not os.path.exists(image_path):
                raise ValueError(f"Image file does not exist: {image_path}")
                
            # Open image
            img = PILImage.open(image_path)
            
            # Apply adjustments
            if brightness != 1.0:
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(brightness)
                
            if contrast != 1.0:
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(contrast)
                
            if saturation != 1.0:
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(saturation)
                
            # Convert to RGB if needed
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
                
            # Create buffer
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Get image data
            image_data = buffer.getvalue()
            
            # Return Image object
            return Image(data=image_data, format="png")
        except Exception as e:
            raise ValueError(f"Error adjusting image: {str(e)}")
    
    @mcp.tool()
    def image_resize(image_path: str, width: int, height: int) -> Image:
        """Resize an image
        
        Args:
            image_path: Path to image file
            width: New width
            height: New height
            
        Returns:
            Resized image
        """
        try:
            # Check if image exists
            if not os.path.exists(image_path):
                raise ValueError(f"Image file does not exist: {image_path}")
                
            # Open image
            img = PILImage.open(image_path)
            
            # Resize image
            img = img.resize((width, height), PILImage.LANCZOS)
            
            # Convert to RGB if needed
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
                
            # Create buffer
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Get image data
            image_data = buffer.getvalue()
            
            # Return Image object
            return Image(data=image_data, format="png")
        except Exception as e:
            raise ValueError(f"Error resizing image: {str(e)}")
    
    @mcp.tool()
    def image_crop(image_path: str, left: int, top: int, right: int, bottom: int) -> Image:
        """Crop an image
        
        Args:
            image_path: Path to image file
            left: Left coordinate
            top: Top coordinate
            right: Right coordinate
            bottom: Bottom coordinate
            
        Returns:
            Cropped image
        """
        try:
            # Check if image exists
            if not os.path.exists(image_path):
                raise ValueError(f"Image file does not exist: {image_path}")
                
            # Open image
            img = PILImage.open(image_path)
            
            # Crop image
            img = img.crop((left, top, right, bottom))
            
            # Convert to RGB if needed
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
                
            # Create buffer
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Get image data
            image_data = buffer.getvalue()
            
            # Return Image object
            return Image(data=image_data, format="png")
        except Exception as e:
            raise ValueError(f"Error cropping image: {str(e)}")
    
    @mcp.tool()
    def image_info(image_path: str) -> str:
        """Get information about an image
        
        Args:
            image_path: Path to image file
            
        Returns:
            Image information
        """
        try:
            # Check if image exists
            if not os.path.exists(image_path):
                return f"Error: Image file does not exist: {image_path}"
                
            # Open image
            img = PILImage.open(image_path)
            
            # Get image information
            width, height = img.size
            format = img.format
            mode = img.mode
            info = img.info
            
            # Format result
            result = (
                f"Image: {os.path.basename(image_path)}\n"
                f"Format: {format}\n"
                f"Size: {width}x{height} pixels\n"
                f"Mode: {mode}\n"
            )
            
            # Add additional info
            if "dpi" in info:
                result += f"DPI: {info['dpi']}\n"
                
            # Add file size
            file_size = os.path.getsize(image_path)
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
            result += f"File size: {size_str}"
            
            return result
        except Exception as e:
            return f"Error getting image info: {str(e)}"
    
    @mcp.tool()
    async def analyze_image(image_path: str, ctx: Context) -> str:
        """Analyze image content using vision API
        
        Args:
            image_path: Path to image file
            
        Returns:
            Analysis results
        """
        if not DALL_E_API_KEY:  # Use OpenAI API key for vision as well
            return "Error: OpenAI API key not configured"
            
        try:
            # Check if image exists
            if not os.path.exists(image_path):
                return f"Error: Image file does not exist: {image_path}"
                
            # Convert image to base64
            with open(image_path, "rb") as f:
                image_data = f.read()
                base64_image = base64.b64encode(image_data).decode("utf-8")
                
            # Call Vision API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {DALL_E_API_KEY}",
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
                                        "text": "Analyze this image and describe what you see in detail."
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}"
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
                
                return f"Image analysis:\n\n{analysis}"
        except Exception as e:
            return f"Error analyzing image: {str(e)}"
