from typing import Dict, Any
from .ytdlp_transcript_service import get_transcript_ytdlp
from fastapi import HTTPException

async def get_transcript(video_id: str) -> Dict[str, Any]:
    """
    Fetches the transcript for a given video ID using yt-dlp.
    Production-ready implementation that downloads subtitles directly.
    Returns dict with 'success' flag and either transcript data or error info.
    """
    try:
        result = await get_transcript_ytdlp(video_id)
        result['success'] = True
        return result
    except HTTPException as e:
        # Return failure status instead of raising
        return {
            'success': False,
            'video_id': video_id,
            'error': str(e.detail),
            'transcript_text': '',
            'segments': []
        }
    except Exception as e:
        return {
            'success': False,
            'video_id': video_id,
            'error': str(e),
            'transcript_text': '',
            'segments': []
        }
