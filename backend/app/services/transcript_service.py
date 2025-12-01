from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from fastapi import HTTPException
from typing import Dict, Any, List

async def get_transcript(video_id: str) -> Dict[str, Any]:
    """
    Fetches the transcript for a given video ID.
    """
    try:
        # Instantiate the API
        api = YouTubeTranscriptApi()
        
        # Fetch transcript using the fetch method
        transcript_data = api.fetch(video_id, languages=['en'])
        
        # Format segments
        segments = []
        full_text_parts = []
        
        for item in transcript_data:
            text = item.text
            start = item.start
            duration = item.duration
            end = start + duration
            
            segments.append({
                "start": start,
                "end": end,
                "text": text
            })
            full_text_parts.append(text)
            
        return {
            "transcript_text": " ".join(full_text_parts),
            "segments": segments,
            "source": "captions"
        }

    except (TranscriptsDisabled, NoTranscriptFound):
        raise HTTPException(status_code=404, detail="Captions unavailable for this video")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching transcript: {str(e)}")
