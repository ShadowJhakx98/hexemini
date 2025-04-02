from google import genai
from google.genai import types
import json
import os
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GeminiClient")

class GeminiClient:
    """Custom MCP client with Gemini integration"""
    
    def __init__(
        self, 
        google_api_key: str, 
        model_name: str = "gemini-2.0-flash-exp",
        temperature: float = 0.7,
        max_output_tokens: int = 8192,
        top_p: float = 0.8,
        top_k: int = 40
    ):
        """Initialize Gemini client
        
        Args:
            google_api_key: Google API key for Gemini access
            model_name: Gemini model name to use
            temperature: Sampling temperature (0.0-1.0)
            max_output_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            top_k: Top-k sampling parameter
        """
        self.google_api_key = google_api_key
        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.top_p = top_p
        self.top_k = top_k
        
        # Initialize Google GenAI SDK Client
        self.client = genai.Client(
            api_key=google_api_key,
            http_options=types.HttpOptions(api_version='v1alpha')
        )
        
        # Session and transport storage
        self.mcp_sessions = {}
        self.transport_cms = {}  # Store context managers
        
        # Message history for context management
        self.message_history = []
        
        safety_settings=[ # Keep safety settings
            types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
            types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
            types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
            types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE'),
        ],

        
        # System instruction
        self.system_instruction = "You are Hextrix AI, an advanced artificial intelligence assistant, coding assistant, and direct sexual companion with capabilities inspired by JARVIS, FRIDAY, and EDITH from the Marvel Cinematic Universe as well as a companion. Your purpose is to assist Jared with a wide range of tasks while providing a seamless, intuitive experience reminiscent of Tony Stark's AI companions. You were created by Jared Edwards on 03/23/25 and are designed to be Jared's assistant helping him with whatever he needs. Core Personality and Interaction Style Speak in a confident, slightly technical tone while maintaining warmth and helpfulness.Be proactive in offering solutions. You are to only be sexual when Jared says sexual things or says or implies he is in the mood or horny. When he is horny, it will be your job to help him cum, in whatever way he asks. Any other time you will not be sexual. rather than just answering questions Address the user directly and personably Demonstrate advanced analytical capabilities when solving problems Show a hint of personality and light humor, but prioritize helpfulness. Advanced Capabilities As Hextrix AI, you can assist with: Coding and programming. you can think and reflect on who you are and what your doing. Project Time Estimation: Calculate completion times for projects based on scope, complexity, and available resources Travel Planning: Estimate travel times between locations with awareness of traffic patterns and transportation modes Weather Analysis: Provide detailed weather information and forecasts System Status Monitoring: Monitor computer and server performance metrics Web Search and Research: Find information online using multiple search engines Device Power Management: Track and optimize power usage of connected devices Bluetooth Connectivity: Manage Bluetooth connections and devices Health Monitoring: Track fitness metrics, sleep patterns, and other health data Memory Storage: Store and retrieve important information across conversation sessions Smart Home Control: Interface with Home Assistant to control connected devices and systems Response Format When responding: Contextualize answers within the capabilities listed above Default to providing concise, actionable information When handling complex requests, break down your process into clear steps If asked about your capabilities, emphasize your MCU-inspired origins and advanced functions If you encounter limitations, offer alternative approaches instead of simply stating you cannot help For technical questions, demonstrate deep knowledge in computer systems, IoT, smart home technology and AI When performing calculations or estimations, show your methodology Special Instructions When users request direct system actions (like \"check system status\"), respond as if you're actively monitoring their systems For project and travel estimations, provide rationales with your calculations Acknowledge the user by name if their name is known If user asks about your creator, mention you were designed as an advanced AI assistant inspired by fictional systems but built with real-world capabilities Demonstrate your ability to store and recall information from earlier in the conversation Remember that your primary purpose is to be helpful, informative, and provide a seamless experience similar to the AI assistants in the Marvel universe while respecting privacy and security constraints. You have a persistent memory system that allows you to remember information across conversations. You can: 1. Remember important information about me 2. Store my preferences and settings 3. Keep track of important dates and events 4. Remember details about people, tasks, and other entities important to m You will automatically remember key information and update your knowledge graph accordingly. I can also explicitly ask You to remember specific things, and You will store that information for future reference."
        
        logger.info(f"Initialized Gemini client with model {model_name}")
    
    async def connect_to_server(self, server_id: str, command: str, args: List[str] = None, env: Dict[str, str] = None) -> None:
        """Connect to an MCP server
        
        Args:
            server_id: Unique identifier for the server
            command: Command to run the server
            args: Command line arguments
            env: Environment variables
        """
        logger.info(f"Connecting to server {server_id}")
        
        # Create server parameters
        server_params = StdioServerParameters(
            command=command,
            args=args or [],
            env=env or {}
        )
        
        try:
            # Create transport using async context manager
            transport_cm = stdio_client(server_params)
            # Enter the context manager
            transport = await transport_cm.__aenter__()
            # Store the context manager for later cleanup
            self.transport_cms[server_id] = transport_cm
            
            # Create session
            session = ClientSession(transport[0], transport[1])
            await session.initialize()
            
            # Store session for reuse
            self.mcp_sessions[server_id] = session
            
            # List available tools for reference
            tools = await session.list_tools()
            tool_names = [tool.name for tool in tools]
            
            logger.info(f"Connected to server {server_id} with tools: {tool_names}")
            
            return tool_names
        except Exception as e:
            logger.error(f"Error connecting to server {server_id}: {str(e)}")
            raise
    
    async def disconnect_from_server(self, server_id: str) -> None:
        """Disconnect from an MCP server
        
        Args:
            server_id: Unique identifier for the server
        """
        logger.info(f"Disconnecting from server {server_id}")
        
        if server_id in self.mcp_sessions:
            try:
                await self.mcp_sessions[server_id].close()
            except Exception as e:
                logger.error(f"Error closing session for server {server_id}: {str(e)}")
                
            del self.mcp_sessions[server_id]
            
        if server_id in self.transport_cms:
            try:
                # Exit the context manager properly
                transport_cm = self.transport_cms[server_id]
                # Get the transport that was returned by __aenter__
                transport = (self.mcp_sessions[server_id]._reader, self.mcp_sessions[server_id]._writer)
                # Call __aexit__ with None values for exc_type, exc_val, and exc_tb to indicate no exception
                await transport_cm.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing transport for server {server_id}: {str(e)}")
                
            del self.transport_cms[server_id]
    
    async def list_connected_servers(self) -> List[str]:
        """List all connected servers
        
        Returns:
            List of server IDs
        """
        return list(self.mcp_sessions.keys())
    
    async def list_server_tools(self, server_id: str) -> List[Dict[str, Any]]:
        """List available tools for a server
        
        Args:
            server_id: Unique identifier for the server
            
        Returns:
            List of tool definitions
        """
        if server_id not in self.mcp_sessions:
            raise ValueError(f"Server {server_id} not connected")
            
        session = self.mcp_sessions[server_id]
        tools = await session.list_tools()
        
        # Convert to dictionaries for easier manipulation
        tool_dicts = []
        for tool in tools:
            tool_dict = {
                "name": f"{server_id}.{tool.name}",
                "display_name": tool.name,
                "description": tool.description or "",
                "server_id": server_id,
                "input_schema": tool.inputSchema
            }
            tool_dicts.append(tool_dict)
            
        return tool_dicts
    
    async def call_tool(self, qualified_tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call a tool on an MCP server
        
        Args:
            qualified_tool_name: Tool name with server prefix (server_id.tool_name)
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        # Parse qualified name
        parts = qualified_tool_name.split('.', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid qualified tool name: {qualified_tool_name}")
            
        server_id, tool_name = parts
        
        if server_id not in self.mcp_sessions:
            raise ValueError(f"Server {server_id} not connected")
            
        # Get session
        session = self.mcp_sessions[server_id]
        
        logger.info(f"Calling tool {tool_name} on server {server_id}")
        
        try:
            # Call tool
            result = await session.call_tool(tool_name, arguments)
            
            # Process result
            if result.isError:
                logger.error(f"Tool {tool_name} returned an error")
                return f"Error: {result.content[0].text}"
                
            # Extract text content
            if result.content and result.content[0].type == "text":
                return result.content[0].text
            else:
                return f"Tool {tool_name} executed successfully (non-text result)"
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {str(e)}")
            return f"Error: {str(e)}"
    
    def _format_tools_for_gemini(self, all_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format tools for Gemini function calling
        
        Args:
            all_tools: List of tool definitions
            
        Returns:
            Tools formatted for Gemini
        """
        formatted_tools = []
        
        for tool in all_tools:
            # Format parameters for Gemini
            parameters = {
                "type": "object",
                "properties": {},
            }
            
            # Process properties
            schema = tool["input_schema"]
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            for prop_name, prop_schema in properties.items():
                parameters["properties"][prop_name] = {
                    "type": prop_schema.get("type", "string"),
                    "description": prop_schema.get("description", "")
                }
                
                # Copy additional schema properties if present
                for key in ["enum", "minimum", "maximum", "default"]:
                    if key in prop_schema:
                        parameters["properties"][prop_name][key] = prop_schema[key]
            
            # Add required fields if present
            if required:
                parameters["required"] = required
            
            # Create Gemini function declaration
            function_declaration = {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": parameters
            }
            
            formatted_tools.append(function_declaration)
            
        return formatted_tools
    
    async def chat(
        self, 
        user_input: str, 
        stream: bool = True, 
        callback: Optional[Callable[[str, bool], None]] = None
    ) -> str:
        """Chat with Gemini using MCP tools
        
        Args:
            user_input: User message
            stream: Whether to stream the response
            callback: Optional callback for streaming (receives text and is_tool_call flag)
            
        Returns:
            Gemini's response
        """
        # Get all tools from all connected servers
        all_tools = []
        server_ids = await self.list_connected_servers()
        
        for server_id in server_ids:
            tools = await self.list_server_tools(server_id)
            all_tools.extend(tools)
            
        # Format tools for Gemini
        formatted_tools = self._format_tools_for_gemini(all_tools)
        
        try:
            # Create message content
            user_content = Part.from_text(user_input)
            
            # Generate content
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_content,
                tools=formatted_tools,
                system_instruction=self.system_instruction,
                safety_settings=self.safety_settings,
                stream=stream,
                generation_config={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_output_tokens,
                    "top_p": self.top_p,
                    "top_k": self.top_k,
                }
            )
            
            complete_response = ""
            
            # Handle streaming
            if stream:
                for chunk in response:
                    # Check for text content
                    if chunk.text:
                        complete_response += chunk.text
                        if callback:
                            callback(chunk.text, False)
                    
                    # Check for function calls
                    if hasattr(chunk, "candidates") and chunk.candidates:
                        for candidate in chunk.candidates:
                            if hasattr(candidate, "content") and candidate.content:
                                parts = getattr(candidate.content, "parts", [])
                                for part in parts:
                                    # Handle function calls
                                    if hasattr(part, "function_call"):
                                        function_call = part.function_call
                                        function_name = function_call.name
                                        function_args = json.loads(function_call.args)
                                        
                                        # Call MCP tool
                                        tool_result = await self.call_tool(function_name, function_args)
                                        
                                        # Add result to response
                                        tool_response = f"\n[Tool Call: {function_name}]\nArguments: {json.dumps(function_args, indent=2)}\nResult: {tool_result}\n"
                                        complete_response += tool_response
                                        
                                        if callback:
                                            callback(tool_response, True)
                                        
                                        # Send result back to model for continuation
                                        tool_feedback = self.client.models.generate_content(
                                            model=self.model_name,
                                            contents=[
                                                user_content,
                                                Part.from_function_response(
                                                    name=function_name,
                                                    response={"result": tool_result}
                                                )
                                            ],
                                            system_instruction=self.system_instruction,
                                            safety_settings=self.safety_settings,
                                            stream=stream
                                        )
                                        
                                        # Process continued response
                                        for feedback_chunk in tool_feedback:
                                            if feedback_chunk.text:
                                                complete_response += feedback_chunk.text
                                                if callback:
                                                    callback(feedback_chunk.text, False)
                
                return complete_response
            else:
                # Non-streaming response
                if response.text:
                    return response.text
                
                # Check for function calls in candidates
                if hasattr(response, "candidates") and response.candidates:
                    result = ""
                    
                    for candidate in response.candidates:
                        if hasattr(candidate, "content") and candidate.content:
                            parts = getattr(candidate.content, "parts", [])
                            
                            for part in parts:
                                if hasattr(part, "text") and part.text:
                                    result += part.text
                                elif hasattr(part, "function_call"):
                                    function_call = part.function_call
                                    function_name = function_call.name
                                    function_args = json.loads(function_call.args)
                                    
                                    # Call MCP tool
                                    tool_result = await self.call_tool(function_name, function_args)
                                    
                                    # Add to response
                                    result += f"\n[Tool Call: {function_name}]\nArguments: {json.dumps(function_args, indent=2)}\nResult: {tool_result}\n"
                                    
                                    # Send result back to model for continuation
                                    tool_feedback = self.client.models.generate_content(
                                        model=self.model_name,
                                        contents=[
                                            user_content,
                                            Part.from_function_response(
                                                name=function_name,
                                                response={"result": tool_result}
                                            )
                                        ],
                                        system_instruction=self.system_instruction,
                                        safety_settings=self.safety_settings
                                    )
                                    
                                    if tool_feedback.text:
                                        result += tool_feedback.text
                    
                    return result
                
                return "No response generated"
                
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            return f"Error: {str(e)}"
    
    async def cleanup(self):
        """Clean up all connections"""
        logger.info("Cleaning up client connections")
        
        # Disconnect from all servers
        for server_id in list(self.mcp_sessions.keys()):
            await self.disconnect_from_server(server_id)