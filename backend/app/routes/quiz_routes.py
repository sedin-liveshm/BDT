from fastapi import APIRouter, Path, Query, HTTPException
from typing import Dict, Any
from ..services.quiz_service import get_or_generate_quiz

router = APIRouter()

@router.get("/video/{videoId}/quiz", response_model=Dict[str, Any])
async def get_quiz(
    videoId: str = Path(..., description="The ID of the YouTube video"),
    num_mcq: int = Query(3, ge=0, le=10, description="Number of multiple choice questions"),
    num_short: int = Query(2, ge=0, le=10, description="Number of short answer questions")
):
    """
    Get or generate a quiz for a YouTube video based on its summary.
    Returns quiz questions without correct answers (server-side only).
    """
    return await get_or_generate_quiz(videoId, num_mcq, num_short)
