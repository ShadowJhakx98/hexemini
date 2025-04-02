import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
import uuid
import os
import json
import asyncio
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity

class VectorStore:
    """Persistent vector-based memory graph and storage"""
    
    def __init__(self, storage_path: str = "./vector_storage"):
        self.storage_path = storage_path
        self.vectors = {}  # id -> vector
        self.metadata = {}  # id -> metadata
        self.connections = {}  # id -> list of connected ids
        self.lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the vector store"""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load existing vectors if any
        if os.path.exists(os.path.join(self.storage_path, "vectors.json")):
            await self._load_from_disk()
            print(f"Loaded {len(self.vectors)} memories from storage")
        else:
            print("No existing memory found, creating new storage")
    
    async def close(self):
        """Close and save the vector store"""
        await self._save_to_disk()
        print(f"Saved {len(self.vectors)} memories to storage")
    
    async def _load_from_disk(self):
        """Load vectors from disk"""
        async with self.lock:
            try:
                with open(os.path.join(self.storage_path, "vectors.json"), "r") as f:
                    data = json.load(f)
                    self.vectors = {k: np.array(v) for k, v in data["vectors"].items()}
                    self.metadata = data["metadata"]
                    self.connections = data["connections"]
            except Exception as e:
                print(f"Error loading vectors: {e}")
                # Initialize empty if loading fails
                self.vectors = {}
                self.metadata = {}
                self.connections = {}
    
    async def _save_to_disk(self):
        """Save vectors to disk"""
        async with self.lock:
            try:
                # Convert numpy arrays to lists for JSON serialization
                serializable_vectors = {k: v.tolist() for k, v in self.vectors.items()}
                
                data = {
                    "vectors": serializable_vectors,
                    "metadata": self.metadata,
                    "connections": self.connections
                }
                
                with open(os.path.join(self.storage_path, "vectors.json"), "w") as f:
                    json.dump(data, f)
            except Exception as e:
                print(f"Error saving vectors: {e}")
    
    async def add_item(self, vector: np.ndarray, metadata: Dict[str, Any]) -> str:
        """Add a vector to the store"""
        item_id = str(uuid.uuid4())
        
        async with self.lock:
            # Add timestamp if not provided
            if "timestamp" not in metadata:
                metadata["timestamp"] = datetime.now().isoformat()
                
            self.vectors[item_id] = vector
            self.metadata[item_id] = metadata
            self.connections[item_id] = []
            
            # Auto-save
            await self._save_to_disk()
            
        return item_id
    
    async def add_connection(self, from_id: str, to_id: str, relation_type: str = "related"):
        """Add a connection between two vectors"""
        async with self.lock:
            if from_id not in self.vectors or to_id not in self.vectors:
                raise ValueError("Both IDs must exist in the vector store")
                
            connection = {"to": to_id, "type": relation_type}
            if connection not in self.connections[from_id]:
                self.connections[from_id].append(connection)
                
            # Auto-save
            await self._save_to_disk()
    
    async def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        """Search for similar vectors"""
        async with self.lock:
            if not self.vectors:
                return []
                
            results = []
            
            for item_id, vector in self.vectors.items():
                # Compute cosine similarity
                similarity = cosine_similarity(
                    query_vector.reshape(1, -1), 
                    vector.reshape(1, -1)
                )[0][0]
                
                results.append((item_id, float(similarity), self.metadata[item_id]))
            
            # Sort by similarity (descending)
            results.sort(key=lambda x: x[1], reverse=True)
            
            return results[:top_k]
    
    async def get_subgraph(self, root_id: str, max_depth: int = 2) -> Dict:
        """Get a subgraph starting from the given root"""
        async with self.lock:
            if root_id not in self.vectors:
                raise ValueError(f"ID {root_id} not found in vector store")
            
            result = {
                "nodes": {},
                "edges": []
            }
            
            # BFS to explore the graph
            visited = set()
            queue = [(root_id, 0)]  # (id, depth)
            
            while queue:
                node_id, depth = queue.pop(0)
                
                if node_id in visited or depth > max_depth:
                    continue
                    
                visited.add(node_id)
                
                # Add node
                result["nodes"][node_id] = self.metadata[node_id]
                
                # Process connections
                for connection in self.connections[node_id]:
                    to_id = connection["to"]
                    relation = connection["type"]
                    
                    # Add edge
                    result["edges"].append({
                        "from": node_id,
                        "to": to_id,
                        "relation": relation
                    })
                    
                    # Add to queue if not visited
                    if to_id not in visited and depth < max_depth:
                        queue.append((to_id, depth + 1))
            
            return result
            
    async def get_all_memories(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get all memories with pagination"""
        async with self.lock:
            # Get all memories sorted by timestamp (newest first)
            all_memories = []
            
            for memory_id, metadata in self.metadata.items():
                memory_info = {
                    "id": memory_id,
                    "metadata": metadata,
                    "connections": len(self.connections[memory_id])
                }
                all_memories.append(memory_info)
            
            # Sort by timestamp (newest first)
            all_memories.sort(
                key=lambda x: x["metadata"].get("timestamp", ""), 
                reverse=True
            )
            
            # Apply pagination
            return all_memories[offset:offset+limit]
