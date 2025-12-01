from fastapi import APIRouter, Path
from typing import Dict, Any
from ..services.transcript_service import get_transcript

router = APIRouter()

@router.get("/video/{videoId}/transcript", response_model=Dict[str, Any])
async def get_video_transcript(
    videoId: str = Path(..., description="The ID of the YouTube video")
):
    """
    Get the transcript (captions) for a YouTube video.
    """
    return await get_transcript(videoId)
