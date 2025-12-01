import os
import httpx
import isodate
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

if not YOUTUBE_API_KEY:
    raise RuntimeError("YOUTUBE_API_KEY environment variable is not set.")

db_client = None
if MONGO_URI:
    try:
        db_client = AsyncIOMotorClient(MONGO_URI)
        # Verify connection
        # db_client.admin.command('ping') # Optional: might delay startup
    except Exception as e:
        print(f"Warning: Could not connect to MongoDB: {e}")
        db_client = None

async def search_videos(query: str, max_results: int = 10) -> List[Dict]:
    """
    Searches YouTube for videos matching the query.
    """
    if db_client:
        cache_collection = db_client.get_database("ytlearner").get_collection("search_cache")
        # Check cache
        # We cache by query and max_results. 
        # Ideally we might want to be smarter (e.g. if we have 10 results cached and request 5, we can use cache)
        # For simplicity, exact match on query and max_results >= requested
        cached_entry = await cache_collection.find_one({
            "query": query,
            "max_results": {"$gte": max_results},
            "created_at": {"$gte": datetime.utcnow() - timedelta(hours=1)}
        })
        
        if cached_entry:
            print(f"Cache hit for query: {query}")
            return cached_entry["results"][:max_results]

    async with httpx.AsyncClient() as client:
        # 1. Search for video IDs
        search_params = {
            "part": "id",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "key": YOUTUBE_API_KEY
        }
        
        try:
            search_response = await client.get(YOUTUBE_SEARCH_URL, params=search_params)
            search_response.raise_for_status()
            search_data = search_response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"YouTube Search API error: {e.response.text}")
        except Exception as e:
             raise HTTPException(status_code=500, detail=f"Internal Server Error during Search: {str(e)}")

        video_ids = [item["id"]["videoId"] for item in search_data.get("items", [])]
        
        if not video_ids:
            return []

        # 2. Get video details (snippet, contentDetails)
        videos_params = {
            "part": "snippet,contentDetails",
            "id": ",".join(video_ids),
            "key": YOUTUBE_API_KEY
        }
        
        try:
            videos_response = await client.get(YOUTUBE_VIDEOS_URL, params=videos_params)
            videos_response.raise_for_status()
            videos_data = videos_response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"YouTube Videos API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal Server Error during Video Details fetch: {str(e)}")

        results = []
        for item in videos_data.get("items", []):
            duration_iso = item["contentDetails"]["duration"]
            try:
                duration_seconds = int(isodate.parse_duration(duration_iso).total_seconds())
            except Exception:
                duration_seconds = 0
            
            video_info = {
                "videoId": item["id"],
                "title": item["snippet"]["title"],
                "channelTitle": item["snippet"]["channelTitle"],
                "thumbnailUrl": item["snippet"]["thumbnails"]["high"]["url"],
                "durationSeconds": duration_seconds
            }
            results.append(video_info)

        # Cache results
        if db_client:
            cache_collection = db_client.get_database("ytlearner").get_collection("search_cache")
            await cache_collection.update_one(
                {"query": query},
                {"$set": {
                    "query": query,
                    "max_results": max_results,
                    "results": results,
                    "created_at": datetime.utcnow()
                }},
                upsert=True
            )

        return results
