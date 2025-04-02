from mcp.server.fastmcp import FastMCP, Context
import httpx
import json
import os
from typing import Dict, List, Any, Optional

# Constants for API configuration
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
SONAR_API_KEY = os.getenv("SONAR_API_KEY", "")

def register_search_tools(mcp: FastMCP):
    """Register search-related tools with the MCP server"""

    @mcp.tool()
    async def perplexity_search(query: str, max_results: int = 5, focus: str = "web", ctx: Context) -> str:
        """Search the web using Perplexity AI
        
        Args:
            query: Search query
            max_results: Maximum number of results to return (1-10)
            focus: Search focus - 'web', 'news', 'academic', or 'reddit'
            
        Returns:
            Search results as formatted text
        """
        if not PERPLEXITY_API_KEY:
            return "Error: Perplexity API key not configured"
            
        # Validate parameters
        max_results = min(max(1, max_results), 10)
        
        valid_focus = ["web", "news", "academic", "reddit"]
        if focus not in valid_focus:
            return f"Error: focus must be one of {valid_focus}"
            
        try:
            # Make API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.perplexity.ai/search",
                    headers={
                        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "query": query,
                        "max_results": max_results,
                        "focus": focus
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    return f"Error: API returned status code {response.status_code}"
                    
                # Parse results
                data = response.json()
                
                if "results" not in data or not data["results"]:
                    return "No search results found."
                    
                # Format results
                formatted_results = []
                for i, result in enumerate(data["results"], 1):
                    title = result.get("title", "Untitled")
                    url = result.get("url", "No URL")
                    snippet = result.get("snippet", "No snippet available")
                    
                    formatted_results.append(
                        f"{i}. {title}\n"
                        f"   URL: {url}\n"
                        f"   {snippet}\n"
                    )
                
                # Include search metadata
                search_info = data.get("search_info", {})
                total_found = search_info.get("total", "Unknown")
                search_time = search_info.get("time", "Unknown")
                
                header = f"Search results for '{query}':\n"
                footer = f"\nFound {total_found} results in {search_time} seconds."
                
                return header + "\n".join(formatted_results) + footer
                
        except Exception as e:
            return f"Error performing search: {str(e)}"
            
    @mcp.tool()
    async def sonar_search(query: str, ctx: Context) -> str:
        """Search using Sonar API for real-time information
        
        Args:
            query: The search query
            
        Returns:
            Real-time search results
        """
        if not SONAR_API_KEY:
            return "Error: Sonar API key not configured"
            
        try:
            # Perform Sonar API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.perplexity.ai/sonar/search",
                    headers={
                        "Authorization": f"Bearer {SONAR_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={"query": query},
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    return f"Error: API returned status code {response.status_code}"
                    
                # Parse results
                data = response.json()
                
                if not data or "answer" not in data:
                    return "No search results found."
                    
                answer = data.get("answer", "No answer available")
                
                # Extract relevant information
                sources = data.get("sources", [])
                formatted_sources = []
                
                for i, source in enumerate(sources[:5], 1):  # Limit to top 5 sources
                    title = source.get("title", "Untitled")
                    url = source.get("url", "No URL")
                    
                    formatted_sources.append(
                        f"{i}. {title}\n"
                        f"   URL: {url}"
                    )
                    
                sources_text = "\n\nSources:\n" + "\n".join(formatted_sources) if formatted_sources else ""
                
                return answer + sources_text
                
        except Exception as e:
            return f"Error performing Sonar search: {str(e)}"
