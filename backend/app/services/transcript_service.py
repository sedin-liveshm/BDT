from typing import Dict, Any
from .ytdlp_transcript_service import get_transcript_ytdlp

async def get_transcript(video_id: str) -> Dict[str, Any]:
    """
    Fetches the transcript for a given video ID using yt-dlp.
    Production-ready implementation that downloads subtitles directly.
    """
    return await get_transcript_ytdlp(video_id)
