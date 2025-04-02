from mcp.server.fastmcp import FastMCP, Context
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime

def register_memory_tools(mcp: FastMCP):
    """Register memory-related tools with the MCP server"""
    
    @mcp.tool()
    async def memory_store(text: str, metadata: dict = None, tags: List[str] = None, ctx: Context) -> str:
        """Store information in the memory graph
        
        Args:
            text: The text to store
            metadata: Additional metadata (optional)
            tags: List of tags to categorize this memory
        
        Returns:
            The ID of the stored memory
        """
        # Get vector store from context
        vector_store = ctx.request_context.lifespan_context.vector_store
        
        # Simple embedding function (in production, use a real embedding model)
        # This is just a placeholder - in real implementation, use proper embeddings
        vector = np.random.rand(768)  # Simulate a 768-dim embedding
        
        # Add metadata
        full_metadata = {
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "tags": tags or []
        }
        
        # Add any additional metadata
        if metadata:
            full_metadata.update(metadata)
        
        # Store in vector store
        memory_id = await vector_store.add_item(vector, full_metadata)
        
        return f"Memory stored successfully with ID: {memory_id}"
    
    @mcp.tool()
    async def memory_recall(query: str, top_k: int = 5, ctx: Context) -> str:
        """Recall information from memory based on semantic similarity
        
        Args:
            query: The text to search for
            top_k: Number of results to return
            
        Returns:
            The recalled memories
        """
        # Get vector store from context
        vector_store = ctx.request_context.lifespan_context.vector_store
        
        # Simple embedding function (in production, use a real embedding model)
        query_vector = np.random.rand(768)  # Simulate an embedding
        
        # Search
        results = await vector_store.search(query_vector, top_k)
        
        # Format results
        if not results:
            return "No memories found matching the query."
            
        formatted_results = []
        for i, (item_id, similarity, metadata) in enumerate(results, 1):
            tags = metadata.get('tags', [])
            tags_str = f" [Tags: {', '.join(tags)}]" if tags else ""
            timestamp = metadata.get('timestamp', 'Unknown time')
            
            formatted_results.append(
                f"{i}. [ID: {item_id[:8]}...] ({similarity:.2f}){tags_str}\n"
                f"   {metadata['text']}\n"
                f"   Stored: {timestamp}\n"
            )
        
        return "Recalled memories:\n\n" + "\n".join(formatted_results)
    
    @mcp.tool()
    async def memory_connect(from_id: str, to_id: str, relation_type: str, ctx: Context) -> str:
        """Connect two memories with a relationship
        
        Args:
            from_id: The source memory ID
            to_id: The target memory ID
            relation_type: The type of relationship
            
        Returns:
            Confirmation message
        """
        # Get vector store from context
        vector_store = ctx.request_context.lifespan_context.vector_store
        
        try:
            # Add connection
            await vector_store.add_connection(from_id, to_id, relation_type)
            return f"Connected memory {from_id[:8]}... to {to_id[:8]}... with relation '{relation_type}'"
        except ValueError as e:
            return f"Error: {str(e)}"
    
    @mcp.tool()
    async def memory_graph(root_id: str, max_depth: int = 2, ctx: Context) -> str:
        """Get a subgraph of connected memories
        
        Args:
            root_id: The root memory ID
            max_depth: Maximum traversal depth
            
        Returns:
            The subgraph information
        """
        # Get vector store from context
        vector_store = ctx.request_context.lifespan_context.vector_store
        
        try:
            # Get subgraph
            subgraph = await vector_store.get_subgraph(root_id, max_depth)
            
            # Format results
            node_count = len(subgraph["nodes"])
            edge_count = len(subgraph["edges"])
            
            result = f"Memory graph with {node_count} nodes and {edge_count} edges:\n\n"
            
            result += "Nodes:\n"
            for node_id, metadata in subgraph["nodes"].items():
                text = metadata.get('text', 'No text')
                # Truncate text if too long
                if len(text) > 50:
                    text = text[:47] + "..."
                result += f"- {node_id[:8]}...: {text}\n"
                
            result += "\nConnections:\n"
            for edge in subgraph["edges"]:
                from_id = edge["from"][:8]
                to_id = edge["to"][:8]
                result += f"- {from_id}... --[{edge['relation']}]--> {to_id}...\n"
                
            return result
        except ValueError as e:
            return f"Error: {str(e)}"
            
    @mcp.tool()
    async def memory_list(limit: int = 10, offset: int = 0, ctx: Context) -> str:
        """List recent memories
        
        Args:
            limit: Maximum number of memories to return
            offset: Pagination offset
            
        Returns:
            List of memories
        """
        # Get vector store from context
        vector_store = ctx.request_context.lifespan_context.vector_store
        
        # Get all memories
        memories = await vector_store.get_all_memories(limit, offset)
        
        if not memories:
            return "No memories found."
            
        result = f"Found {len(memories)} memories:\n\n"
        
        for i, memory in enumerate(memories, 1):
            memory_id = memory["id"]
            metadata = memory["metadata"]
            text = metadata.get("text", "No text")
            timestamp = metadata.get("timestamp", "Unknown time")
            tags = metadata.get("tags", [])
            tags_str = f" [Tags: {', '.join(tags)}]" if tags else ""
            
            # Truncate text if too long
            if len(text) > 50:
                text = text[:47] + "..."
                
            result += (
                f"{i}. [ID: {memory_id[:8]}...]{tags_str}\n"
                f"   {text}\n"
                f"   Stored: {timestamp}\n"
                f"   Connections: {memory['connections']}\n\n"
            )
            
        return result
