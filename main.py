#!/usr/bin/env python3
import asyncio
import os
import sys
import argparse
import logging
import time
import traceback
import subprocess
from dotenv import load_dotenv

# Set Windows event loop policy right at the start
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Load environment variables
load_dotenv()

# Import our modules
from server import configure_server, set_allowed_directories, enable_automation
from client import GeminiClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)-8s %(message)s',
    datefmt='%m/%d/%y %H:%M:%S'
)
logger = logging.getLogger("Main")

# Default values
DEFAULT_SERVER_COMMAND = "python"
DEFAULT_SERVER_SCRIPT = "server_runner.py"
DEFAULT_ALLOWED_DIRS = [os.path.expanduser("~/Documents"), os.path.expanduser("~/Downloads")]

async def run_server(args):
    """Run the MCP server"""
    logger.info("Starting MCP server")
    
    # Configure server with all tools
    server = configure_server(
        allowed_dirs=args.allowed_dirs,
        enable_auto=args.enable_automation,
        safe_mode=not args.disable_safety
    )
    
    # Run server
    await server.run()

async def start_server_process(command, args):
    """Start a server process using a method compatible with Windows"""
    full_command = [command] + args
    logger.info(f"Starting server process: {' '.join(full_command)}")
    
    # Use a direct subprocess call instead of asyncio.create_subprocess_exec
    try:
        # Start process with subprocess module
        process = subprocess.Popen(
            full_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Log confirmation
        logger.info(f"Server process started with PID: {process.pid}")
        return process
    except Exception as e:
        logger.error(f"Failed to start server process: {e}")
        raise

async def run_client(args):
    """Run the custom Gemini MCP client"""
    # Get API keys
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        logger.error("GOOGLE_API_KEY environment variable not set")
        sys.exit(1)
        
    logger.info("Starting Gemini MCP client")
    
    # Create client
    client = GeminiClient(
        google_api_key=google_api_key,
        model_name=args.model,
        temperature=args.temperature,
        max_output_tokens=args.max_tokens
    )
    
    # Server process tracking
    server_process = None
    
    try:
        # Connect to our server
        server_id = "main"
        
        # Determine server command
        if args.start_server:
            # Start our own server
            script_path = os.path.abspath("server_runner.py")
            
            # Create runner script that configures and starts the server
            with open(script_path, "w") as f:
                f.write("""#!/usr/bin/env python3
import asyncio
import sys
import os
import logging
from server import configure_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)-8s %(message)s',
    datefmt='%m/%d/%y %H:%M:%S'
)
logger = logging.getLogger("ServerRunner")

# Parse allowed directories
allowed_dirs = sys.argv[1:] if len(sys.argv) > 1 else []
if allowed_dirs:
    logger.info(f"Using allowed directories: {allowed_dirs}")
else:
    logger.info("No directories specified. File access will be restricted.")

# Configure and run server
async def main():
    server = configure_server(allowed_dirs=allowed_dirs)
    await server.run()

if __name__ == "__main__":
    # Set Windows event loop policy if needed
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
""")
            
            # Make script executable
            os.chmod(script_path, 0o755)
            
            # Start server in a separate process
            server_command = DEFAULT_SERVER_COMMAND
            server_args = [script_path] + args.allowed_dirs
            
            logger.info(f"Starting internal server with command: {server_command} {' '.join(server_args)}")
            
            # Start server as a separate process
            try:
                # Use our custom function to start the server process
                server_process = await start_server_process(server_command, server_args)
                
                # Add startup delay to ensure server is ready
                logger.info("Waiting 5 seconds for server to initialize...")
                await asyncio.sleep(5)
            except Exception as e:
                error_details = traceback.format_exc()
                logger.error(f"Failed to start internal server: {str(e)}")
                logger.error(f"Error details: {error_details}")
                print(f"\nError starting server: {str(e)}")
                print("\nPlease check the following:")
                print("1. Make sure your Python environment is properly set up")
                print("2. Check that all required packages are installed")
                print("3. Verify the server path and permissions")
                await client.cleanup()
                return  # Exit if server start fails
            
            try:
                logger.info("Connecting to server main...")
                tool_names = await client.connect_to_server(
                    server_id=server_id,
                    command=server_command,
                    args=server_args
                )
                logger.info(f"Successfully connected to internal server with tools: {tool_names}")
            except Exception as e:
                error_details = traceback.format_exc()
                logger.error(f"Failed to connect to internal server: {str(e)}")
                logger.error(f"Error details: {error_details}")
                print(f"\nError connecting to server: {str(e)}")
                print("\nPlease check the following:")
                print("1. Make sure your Python environment is properly set up")
                print("2. Check that all required packages are installed")
                print("3. Verify the server path and permissions")
                # Try to read server output for debugging
                if server_process:
                    stdout, stderr = server_process.communicate(timeout=1)
                    if stdout:
                        logger.info(f"Server stdout: {stdout}")
                    if stderr:
                        logger.error(f"Server stderr: {stderr}")
                await client.cleanup()
                return  # Exit if server connection fails
        else:
            # Connect to external server
            logger.info(f"Connecting to external server: {args.server_command} {' '.join(args.server_args)}")
            
            try:
                await client.connect_to_server(
                    server_id=server_id,
                    command=args.server_command,
                    args=args.server_args
                )
            except Exception as e:
                error_details = traceback.format_exc()
                logger.error(f"Failed to connect to external server: {str(e)}")
                logger.error(f"Error details: {error_details}")
                print(f"\nError connecting to server: {str(e)}")
                await client.cleanup()
                return  # Exit if server connection fails
            
        # Connect to Perplexity server if specified
        if args.perplexity_server:
            logger.info(f"Connecting to Perplexity server: {args.perplexity_server}")
            perplexity_parts = args.perplexity_server.split()
            
            perplexity_command = perplexity_parts[0]
            perplexity_args = perplexity_parts[1:] if len(perplexity_parts) > 1 else []
            
            try:
                await client.connect_to_server(
                    server_id="perplexity",
                    command=perplexity_command,
                    args=perplexity_args,
                    env={
                        "PERPLEXITY_API_KEY": os.environ.get("PERPLEXITY_API_KEY", ""),
                        "SONAR_API_KEY": os.environ.get("SONAR_API_KEY", "")
                    }
                )
            except Exception as e:
                error_details = traceback.format_exc()
                logger.error(f"Failed to connect to Perplexity server: {str(e)}")
                logger.error(f"Error details: {error_details}")
                print(f"\nWarning: Perplexity server connection failed: {str(e)}")
                # Continue even if Perplexity connection fails
        
        # Interactive chat loop
        print("\n=== Gemini MCP Client ===")
        connected_servers = await client.list_connected_servers()
        if not connected_servers:
            print("No servers connected. Exiting.")
            return
            
        print("Connected to servers: " + ", ".join(connected_servers))
        print('Type "exit" to quit.')
        print()
        
        # Stream callback for printing chunks
        def print_chunk(text, is_tool_call):
            if is_tool_call:
                # Print tool calls in a distinct format
                print(f"\033[93m{text}\033[0m", end="", flush=True)
            else:
                print(text, end="", flush=True)
        
        # Chat loop
        while True:
            try:
                # Get user input
                user_input = input("\nYou: ")
                
                if user_input.lower() in ["exit", "quit"]:
                    break
                    
                # Process with Gemini
                print("\nGemini: ", end="", flush=True)
                response = await client.chat(user_input, stream=True, callback=print_chunk)
                print()  # Add newline after response
                
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                error_details = traceback.format_exc()
                logger.error(f"Error in chat loop: {str(e)}")
                logger.error(f"Error details: {error_details}")
                print(f"\nError: {str(e)}")
    finally:
        # Clean up
        await client.cleanup()
        
        # Terminate server process if we started it
        if server_process:
            logger.info("Terminating server process...")
            try:
                server_process.terminate()
                server_process.wait(timeout=5)
                logger.info("Server process terminated")
            except Exception as e:
                logger.error(f"Error terminating server process: {e}")

def main():
    """Parse arguments and run the appropriate function"""
    # Set Windows event loop policy right at the start of the program
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    parser = argparse.ArgumentParser(description="Gemini MCP System")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Server command
    server_parser = subparsers.add_parser("server", help="Run MCP server")
    server_parser.add_argument(
        "--allowed-dirs",
        nargs="+",
        default=DEFAULT_ALLOWED_DIRS,
        help="Directories to allow filesystem access to"
    )
    server_parser.add_argument(
        "--enable-automation",
        action="store_true",
        help="Enable automation features"
    )
    server_parser.add_argument(
        "--disable-safety",
        action="store_true",
        help="Disable safety restrictions for automation"
    )
    
    # Client command
    client_parser = subparsers.add_parser("client", help="Run Gemini MCP client")
    client_parser.add_argument(
        "--model",
        default="gemini-2.0-flash-exp",
        help="Gemini model to use"
    )
    client_parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature (0.0-1.0)"
    )
    client_parser.add_argument(
        "--max-tokens",
        type=int,
        default=2048,
        help="Maximum tokens to generate"
    )
    server_group = client_parser.add_mutually_exclusive_group(required=True)
    server_group.add_argument(
        "--start-server",
        action="store_true",
        help="Start internal MCP server"
    )
    server_group.add_argument(
        "--server-command",
        help="Command to run external MCP server"
    )
    client_parser.add_argument(
        "--server-args",
        nargs="+",
        default=[],
        help="Arguments for external MCP server"
    )
    client_parser.add_argument(
        "--allowed-dirs",
        nargs="+",
        default=DEFAULT_ALLOWED_DIRS,
        help="Directories to allow filesystem access to (for internal server)"
    )
    client_parser.add_argument(
        "--perplexity-server",
        help="Command to run Perplexity MCP server (space-separated command and args)"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Run appropriate function
    if args.command == "server":
        asyncio.run(run_server(args))
    elif args.command == "client":
        try:
            asyncio.run(run_client(args))
        except KeyboardInterrupt:
            print("\nExiting due to user interrupt...")
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"Fatal error: {str(e)}")
            logger.error(f"Error details: {error_details}")
            print(f"\nFatal error: {str(e)}")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()