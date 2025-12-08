import os
import httpx
import isodate
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

# In-memory cache fallback
memory_cache = {}

db_client = None
if MONGO_URI:
    try:
        db_client = AsyncIOMotorClient(MONGO_URI)
    except Exception as e:
        print(f"Warning: Could not connect to MongoDB: {e}")
        db_client = None

async def get_video_metadata(video_id: str) -> Dict[str, Any]:
    """
    Fetches video metadata from cache or YouTube API.
    """
    # 1. Check Cache
    cached_data = await _get_from_cache(video_id)
    if cached_data:
        print(f"Cache hit for video: {video_id}")
        return cached_data

    # 2. Fetch from YouTube
    async with httpx.AsyncClient() as client:
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": video_id,
            "key": YOUTUBE_API_KEY
        }
        
        try:
            response = await client.get(YOUTUBE_VIDEOS_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"YouTube API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    items = data.get("items", [])
    if not items:
        raise HTTPException(status_code=404, detail="Video not found")

    item = items[0]
    snippet = item["snippet"]
    content_details = item["contentDetails"]
    statistics = item["statistics"]

    # Parse duration
    try:
        duration_seconds = int(isodate.parse_duration(content_details["duration"]).total_seconds())
    except Exception:
        duration_seconds = 0

    metadata = {
        "videoId": video_id,
        "title": snippet["title"],
        "description": snippet["description"],
        "channelTitle": snippet["channelTitle"],
        "thumbnailUrl": snippet["thumbnails"].get("high", snippet["thumbnails"].get("default"))["url"],
        "durationSeconds": duration_seconds,
        "publishedAt": snippet["publishedAt"],
        "statistics": {
            "viewCount": statistics.get("viewCount", "0"),
            "likeCount": statistics.get("likeCount", "0"),
            "commentCount": statistics.get("commentCount", "0")
        },
        "youtubeUrl": f"https://www.youtube.com/watch?v={video_id}",
        "embedUrl": f"https://www.youtube.com/embed/{video_id}",
        "metadataFetchedAt": datetime.utcnow().isoformat()
    }

    # 3. Save to Cache
    await _save_to_cache(video_id, metadata)

    return metadata

async def _get_from_cache(video_id: str) -> Optional[Dict]:
    cutoff = datetime.utcnow() - timedelta(days=7)
    
    if db_client:
        collection = db_client.get_database("ytlearner").get_collection("videos")
        # Find document where videoId matches and metadataFetchedAt > cutoff
        # Note: metadataFetchedAt is stored as ISO string, so string comparison works for ISO dates
        # but better to parse if we want strict date comparison. 
        # For simplicity/speed, we'll fetch first then check date or use string comparison if format is consistent.
        # Let's fetch and check in python to be safe with string formats.
        doc = await collection.find_one({"videoId": video_id})
        if doc:
            fetched_at = datetime.fromisoformat(doc["metadataFetchedAt"])
            if fetched_at > cutoff:
                # Remove _id before returning
                doc.pop("_id", None)
                return doc
    else:
        if video_id in memory_cache:
            doc = memory_cache[video_id]
            fetched_at = datetime.fromisoformat(doc["metadataFetchedAt"])
            if fetched_at > cutoff:
                return doc
    return None

async def _save_to_cache(video_id: str, data: Dict):
    if db_client:
        collection = db_client.get_database("ytlearner").get_collection("videos")
        await collection.update_one(
            {"videoId": video_id},
            {"$set": data},
            upsert=True
        )
    else:
        memory_cache[video_id] = data
