import os
from fastapi import APIRouter, Path, HTTPException
from typing import Dict, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

from ..services import llm_client

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
    Get or generate a summary for a YouTube video using Gemini AI.
    Directly analyzes the video without requiring transcripts.
    """
    # Check cache
    cached = await get_cached_summary(videoId)
    if cached:
        print(f"Cache hit for summary: {videoId}")
        return cached
    
    # Generate summary using Gemini video analysis
    print(f"Generating summary for {videoId} using Gemini video analysis")
    try:
        video_url = f"https://www.youtube.com/watch?v={videoId}"
        video_summary = await llm_client.analyze_video_url(video_url)
        video_summary["generatedAt"] = datetime.utcnow().isoformat()
        video_summary["method"] = "gemini_video_analysis"
        
        # Save to cache
        await save_summary(videoId, video_summary)
        
        return video_summary
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate video summary: {str(e)}"
        )
