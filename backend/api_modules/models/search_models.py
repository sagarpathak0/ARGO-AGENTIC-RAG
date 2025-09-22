"""
Search-related Pydantic models for ARGO API
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    query: str = Field(..., description="Natural language query about oceanographic data")
    limit: int = Field(10, ge=1, le=100, description="Number of results to return")
    similarity_threshold: float = Field(0.3, ge=0.0, le=1.0, description="Minimum similarity score")


class SearchResult(BaseModel):
    profile_id: int
    latitude: float
    longitude: float
    date: str
    institution: str
    platform_number: str
    ocean_data: Dict[str, Any] = {}
    similarity_score: float
    content_summary: str


class AggregatedSearchResponse(BaseModel):
    summary: Dict[str, Any]
    measurements: Dict[str, Any]
    query_understanding: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    filters_applied: List[str] = []


class IntelligentSearchResponse(BaseModel):
    results: List[SearchResult]
    query_understanding: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    filters_applied: List[str] = []