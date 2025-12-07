import os
from fastapi import APIRouter, Path, HTTPException
from typing import Dict, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

from ..services import llm_client
from ..services.transcript_service import get_transcript

router = APIRouter()

MONGO_URI = os.getenv("MONGO_URI")

# In-memory cache fallback
memory_cache = {}

db_client = None
if MONGO_URI:
    try:
        db_client = AsyncIOMotorClient(MONGO_URI)
    except Exception as e:
        print(f"Warning: Could not connect to MongoDB: {e}")
        db_client = None


def chunk_transcript(transcript_text: str, chunk_size: int = 2000, overlap: int = 50) -> list[str]:
    """
    Split transcript into chunks with overlap.
    """
    words = transcript_text.split()
    chunks = []
    
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunks.append(' '.join(chunk_words))
        i += chunk_size - overlap
    
    return chunks


async def get_cached_summary(video_id: str) -> Dict[str, Any] | None:
    """Check if summary exists in cache and is fresh (< 30 days)."""
    cutoff = datetime.utcnow() - timedelta(days=30)
    
    if db_client:
        collection = db_client.get_database("ytlearner").get_collection("videos")
        doc = await collection.find_one({"videoId": video_id, "summary": {"$exists": True}})
        
        if doc and doc.get("summary"):
            summary = doc["summary"]
            if "generatedAt" in summary:
                generated_at = datetime.fromisoformat(summary["generatedAt"])
                if generated_at > cutoff:
                    return summary
    else:
        cache_key = f"summary_{video_id}"
        if cache_key in memory_cache:
            summary = memory_cache[cache_key]
            if "generatedAt" in summary:
                generated_at = datetime.fromisoformat(summary["generatedAt"])
                if generated_at > cutoff:
                    return summary
    
    return None


async def save_summary(video_id: str, summary: Dict[str, Any]):
    """Save summary to cache."""
    if db_client:
        collection = db_client.get_database("ytlearner").get_collection("videos")
        await collection.update_one(
            {"videoId": video_id},
            {"$set": {"summary": summary}},
            upsert=True
        )
    else:
        cache_key = f"summary_{video_id}"
        memory_cache[cache_key] = summary


@router.get("/video/{videoId}/summary", response_model=Dict[str, Any])
async def get_summary(
    videoId: str = Path(..., description="The ID of the YouTube video")
):
    """
    Get or generate a summary for a YouTube video.
    """
    # Check cache
    cached = await get_cached_summary(videoId)
    if cached:
        print(f"Cache hit for summary: {videoId}")
        return cached
    
    # Fetch transcript directly (no HTTP call)
    try:
        transcript_data = await get_transcript(videoId)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch transcript: {str(e)}")
    
    transcript_text = transcript_data.get("transcript_text", "")
    
    if not transcript_text:
        raise HTTPException(status_code=404, detail="No transcript available for summarization")
    
    # Chunk transcript
    chunks = chunk_transcript(transcript_text)
    
    # Summarize each chunk
    chunk_summaries = []
    for chunk in chunks:
        try:
            chunk_summary = await llm_client.summarize_chunk(chunk)
            chunk_summaries.append(chunk_summary)
        except Exception as e:
            print(f"Error summarizing chunk: {e}")
            # Continue with other chunks
    
    if not chunk_summaries:
        raise HTTPException(status_code=500, detail="Failed to generate any summaries")
    
    # Merge summaries
    try:
        final_summary = await llm_client.merge_summaries(chunk_summaries)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to merge summaries: {str(e)}")
    
    # Add metadata
    final_summary["generatedAt"] = datetime.utcnow().isoformat()
    
    # Save to cache
    await save_summary(videoId, final_summary)
    
    return final_summary
