from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChromaCollectionBase(BaseModel):
    name: str = Field(..., description="Collection name")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Collection metadata")
    owner_type: str = Field(..., description="Owner type: 'user' or 'group'")
    owner_id: str = Field(..., description="Owner ID (user_id or group_id)")

class ChromaCollectionCreate(ChromaCollectionBase):
    pass

class ChromaCollectionResponse(ChromaCollectionBase):
    id: str = Field(..., description="Collection ID")
    display_name: Optional[str] = Field(default=None, description="Display name for UI (from RAG datasource)")
    description: Optional[str] = Field(default=None, description="Description from RAG datasource")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(default=True, description="Whether collection is active")

    class Config:
        from_attributes = True

class ChromaDocumentAdd(BaseModel):
    documents: List[str] = Field(..., description="List of document texts")
    metadatas: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of metadata for each document")
    ids: Optional[List[str]] = Field(default=None, description="List of document IDs")

class ChromaQueryRequest(BaseModel):
    query_texts: List[str] = Field(..., description="Query texts")
    n_results: Optional[int] = Field(default=10, description="Number of results to return")
    where: Optional[Dict[str, Any]] = Field(default=None, description="Where clause for filtering")
    include: Optional[List[str]] = Field(default=["documents", "metadatas", "distances"], description="What to include in results")

class ChromaQueryResponse(BaseModel):
    ids: List[List[str]]
    distances: List[List[float]]
    documents: List[List[str]]
    metadatas: List[List[Dict[str, Any]]] 