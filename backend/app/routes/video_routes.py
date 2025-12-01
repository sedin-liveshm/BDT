from fastapi import APIRouter, HTTPException, Path
from typing import Dict, Any
from ..services.video_service import get_video_metadata

router = APIRouter()

@router.get("/video/{videoId}/metadata", response_model=Dict[str, Any])
async def get_metadata(
    videoId: str = Path(..., description="The ID of the YouTube video")
):
    """
    Get detailed metadata for a YouTube video.
    """
    return await get_video_metadata(videoId)
