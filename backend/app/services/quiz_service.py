import os
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException

from . import llm_client

MONGO_URI = os.getenv("MONGO_URI")

# In-memory cache fallback
memory_quiz_cache = {}

db_client = None
if MONGO_URI:
    try:
        db_client = AsyncIOMotorClient(MONGO_URI)
    except Exception as e:
        print(f"Warning: Could not connect to MongoDB: {e}")
        db_client = None


def generate_quiz_id(video_id: str, num_mcq: int, num_short: int) -> str:
    """Generate a unique quiz ID based on video ID and question counts."""
    key = f"{video_id}_{num_mcq}_{num_short}"
    return hashlib.md5(key.encode()).hexdigest()


async def get_cached_quiz(quiz_id: str) -> Dict[str, Any] | None:
    """Check if quiz exists in cache and is fresh (< 30 days)."""
    cutoff = datetime.utcnow() - timedelta(days=30)
    
    if db_client:
        collection = db_client.get_database("ytlearner").get_collection("quizzes")
        doc = await collection.find_one({"quizId": quiz_id})
        
        if doc and "createdAt" in doc:
            created_at = datetime.fromisoformat(doc["createdAt"])
            if created_at > cutoff:
                # Remove MongoDB _id field
                doc.pop("_id", None)
                return doc
    else:
        if quiz_id in memory_quiz_cache:
            quiz = memory_quiz_cache[quiz_id]
            if "createdAt" in quiz:
                created_at = datetime.fromisoformat(quiz["createdAt"])
                if created_at > cutoff:
                    return quiz
    
    return None


async def save_quiz(quiz_id: str, quiz_data: Dict[str, Any]):
    """Save quiz to cache."""
    quiz_data["quizId"] = quiz_id
    quiz_data["createdAt"] = datetime.utcnow().isoformat()
    
    if db_client:
        collection = db_client.get_database("ytlearner").get_collection("quizzes")
        await collection.update_one(
            {"quizId": quiz_id},
            {"$set": quiz_data},
            upsert=True
        )
    else:
        memory_quiz_cache[quiz_id] = quiz_data


def strip_sensitive_data(quiz_data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove correct answers and embeddings from quiz for client response."""
    client_quiz = quiz_data.copy()
    
    if "questions" in client_quiz:
        client_questions = []
        for q in client_quiz["questions"]:
            client_q = q.copy()
            # Remove server-only fields
            client_q.pop("correct_answer", None)
            client_q.pop("answer_embedding", None)
            client_questions.append(client_q)
        client_quiz["questions"] = client_questions
    
    # Keep quizId for client (needed for submission)
    # Only remove internal metadata
    client_quiz.pop("createdAt", None)
    
    return client_quiz


async def get_or_generate_quiz(
    video_id: str,
    num_mcq: int,
    num_short: int
) -> Dict[str, Any]:
    """
    Get or generate a quiz for a video.
    Returns quiz without correct answers (server-side only).
    """
    # Generate quiz ID
    quiz_id = generate_quiz_id(video_id, num_mcq, num_short)
    
    # Check cache
    cached = await get_cached_quiz(quiz_id)
    if cached:
        print(f"Cache hit for quiz: {quiz_id}")
        return strip_sensitive_data(cached)
    
    # Fetch summary to generate quiz from (import at top to avoid circular import)
    from ..routes.summary_routes import get_cached_summary, get_summary
    
    try:
        # Try cache first, then generate if needed
        summary_data = await get_cached_summary(video_id)
        if not summary_data:
            summary_data = await get_summary(video_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch summary for quiz generation: {str(e)}"
        )
    
    # Generate quiz using LLM
    try:
        quiz_questions = await llm_client.generate_quiz(
            summary_data,
            num_mcq=num_mcq,
            num_short=num_short
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate quiz: {str(e)}"
        )
    
    # Prepare full quiz data (including sensitive fields)
    full_quiz_data = {
        "videoId": video_id,
        "num_mcq": num_mcq,
        "num_short": num_short,
        "questions": quiz_questions,
        "totalPoints": sum(q.get("max_points", 1) for q in quiz_questions)
    }
    
    # Save to cache (with sensitive data)
    await save_quiz(quiz_id, full_quiz_data)
    
    # Return client-safe version
    return strip_sensitive_data(full_quiz_data)
