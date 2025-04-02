from mcp.server.fastmcp import FastMCP
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

# Initialize FastMCP server
mcp = FastMCP("GeminiMemoryServer")

# Import vector store
from server.memory.vector_store import VectorStore

@dataclass
class AppContext:
    """Application context with initialized components"""
    vector_store: VectorStore

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with vector store initialization"""
    # Initialize vector store
    print("Initializing vector memory store...")
    vector_store = VectorStore()
    await vector_store.initialize()
    
    try:
        yield AppContext(vector_store=vector_store)
    finally:
        # Cleanup
        print("Shutting down and saving vector memory...")
        await vector_store.close()

# Pass lifespan to server
mcp = FastMCP("GeminiMemoryServer", lifespan=app_lifespan)
