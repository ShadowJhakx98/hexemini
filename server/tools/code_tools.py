from mcp.server.fastmcp import FastMCP, Context
import httpx
import os
import subprocess
import tempfile
import shutil
import time
from typing import Dict, List, Any, Optional
import sys
import json

def register_code_tools(mcp: FastMCP):
    """Register code-related tools with the MCP server"""
    
    # OpenAI API key for code generation
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    @mcp.tool()
    async def generate_code(prompt: str, language: str = "python", ctx: Context) -> str:
        """Generate code based on a text prompt
        
        Args:
            prompt: Description of the code to generate
            language: Programming language
            
        Returns:
            Generated code
        """
        if not OPENAI_API_KEY:
            return "Error: OpenAI API key not configured"
            
        try:
            # Call OpenAI API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4-turbo",
                        "messages": [
                            {
                                "role": "system",
                                "content": f"You are an expert {language} programmer. Generate clean, efficient, and well-commented code based on the user's request. Only output code and brief comments."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2000
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    return f"Error: API returned status code {response.status_code}"
                    
                # Parse response
                data = response.json()
                
                if "choices" not in data or not data["choices"]:
                    return "Error: No code generation result in response"
                    
                # Get generated code
                generated_code = data["choices"][0]["message"]["content"]
                
                # Remove markdown code blocks if present
                if generated_code.startswith("```") and generated_code.endswith("```"):
                    # Extract language identifier if present
                    first_line = generated_code.split("\n")[0].strip("`").strip()
                    if first_line:
                        generated_code = generated_code[len(first_line) + 4:-3].strip()
                    else:
                        generated_code = generated_code[3:-3].strip()
                
                return f"Generated {language} code:\n\n{generated_code}"
        except Exception as e:
            return f"Error generating code: {str(e)}"
    
    @mcp.tool()
    def execute_python_code(code: str, timeout: int = 30) -> str:
        """Execute Python code
        
        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            Execution results
        """
        try:
            # Create temporary directory for execution
            temp_dir = tempfile.mkdtemp()
            temp_file = os.path.join(temp_dir, "script.py")
            
            try:
                # Write code to temporary file
                with open(temp_file, "w") as f:
                    f.write(code)
                    
                # Set up process environment
                env = os.environ.copy()
                
                # Execute code in isolated environment
                process = subprocess.run(
                    [sys.executable, temp_file],
                    env=env,
                    cwd=temp_dir,
                    timeout=timeout,
                    capture_output=True,
                    text=True
                )
                
                # Format result
                stdout = process.stdout
                stderr = process.stderr
                exit_code = process.returncode
                
                result = f"Python code executed with exit code {exit_code}\n\n"
                
                if stdout:
                    result += f"Output:\n{stdout}\n"
                    
                if stderr:
                    result += f"Errors:\n{stderr}\n"
                    
                return result
            finally:
                # Clean up
                shutil.rmtree(temp_dir)
        except subprocess.TimeoutExpired:
            return f"Error: Code execution timed out after {timeout} seconds"
        except Exception as e:
            return f"Error executing Python code: {str(e)}"
    
    @mcp.tool()
    def execute_javascript_code(code: str, timeout: int = 30) -> str:
        """Execute JavaScript code using Node.js
        
        Args:
            code: JavaScript code to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            Execution results
        """
        try:
            # Create temporary directory for execution
            temp_dir = tempfile.mkdtemp()
            temp_file = os.path.join(temp_dir, "script.js")
            
            try:
                # Write code to temporary file
                with open(temp_file, "w") as f:
                    f.write(code)
                    
                # Execute code using Node.js
                process = subprocess.run(
                    ["node", temp_file],
                    cwd=temp_dir,
                    timeout=timeout,
                    capture_output=True,
                    text=True
                )
                
                # Format result
                stdout = process.stdout
                stderr = process.stderr
                exit_code = process.returncode
                
                result = f"JavaScript code executed with exit code {exit_code}\n\n"
                
                if stdout:
                    result += f"Output:\n{stdout}\n"
                    
                if stderr:
                    result += f"Errors:\n{stderr}\n"
                    
                return result
            finally:
                # Clean up
                shutil.rmtree(temp_dir)
        except subprocess.TimeoutExpired:
            return f"Error: Code execution timed out after {timeout} seconds"
        except Exception as e:
            return f"Error executing JavaScript code: {str(e)}"
    
    @mcp.tool()
    def execute_bash_script(script: str, timeout: int = 30) -> str:
        """Execute Bash script
        
        Args:
            script: Bash script to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            Execution results
        """
        try:
            # Create temporary directory for execution
            temp_dir = tempfile.mkdtemp()
            temp_file = os.path.join(temp_dir, "script.sh")
            
            try:
                # Write script to temporary file
                with open(temp_file, "w") as f:
                    f.write(script)
                    
                # Make script executable
                os.chmod(temp_file, 0o755)
                
                # Execute script
                process = subprocess.run(
                    ["/bin/bash", temp_file],
                    cwd=temp_dir,
                    timeout=timeout,
                    capture_output=True,
                    text=True
                )
                
                # Format result
                stdout = process.stdout
                stderr = process.stderr
                exit_code = process.returncode
                
                result = f"Bash script executed with exit code {exit_code}\n\n"
                
                if stdout:
                    result += f"Output:\n{stdout}\n"
                    
                if stderr:
                    result += f"Errors:\n{stderr}\n"
                    
                return result
            finally:
                # Clean up
                shutil.rmtree(temp_dir)
        except subprocess.TimeoutExpired:
            return f"Error: Script execution timed out after {timeout} seconds"
        except Exception as e:
            return f"Error executing Bash script: {str(e)}"
            
    @mcp.tool()
    async def explain_code(code: str, ctx: Context) -> str:
        """Explain code functionality
        
        Args:
            code: Code to explain
            
        Returns:
            Explanation of the code
        """
        if not OPENAI_API_KEY:
            return "Error: OpenAI API key not configured"
            
        try:
            # Call OpenAI API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4-turbo",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert programmer. Explain the provided code in a clear, concise way. Break down the functionality, identify key components, and highlight any potential issues or improvements."
                            },
                            {
                                "role": "user",
                                "content": f"Explain this code:\n\n{code}"
                            }
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1000
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    return f"Error: API returned status code {response.status_code}"
                    
                # Parse response
                data = response.json()
                
                if "choices" not in data or not data["choices"]:
                    return "Error: No explanation result in response"
                    
                # Get explanation
                explanation = data["choices"][0]["message"]["content"]
                
                return f"Code explanation:\n\n{explanation}"
        except Exception as e:
            return f"Error explaining code: {str(e)}"
