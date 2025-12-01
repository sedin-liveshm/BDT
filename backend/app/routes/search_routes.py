from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any
from ..services.youtube_service import search_videos

router = APIRouter()

@router.get("/search", response_model=List[Dict[str, Any]])
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    maxResults: int = Query(10, ge=1, le=50, description="Maximum number of results")
):
    """
    Search for YouTube videos.
    """
    try:
        results = await search_videos(query=q, max_results=maxResults)
        return results
    except Exception as e:
        # In case something slips through the service error handling
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
