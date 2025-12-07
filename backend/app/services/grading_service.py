import os
import math
from datetime import datetime
from typing import Dict, Any, List, Tuple
from motor.motor_asyncio import AsyncIOMotorClient

from . import llm_client

MONGO_URI = os.getenv("MONGO_URI")

# In-memory cache fallback
memory_quiz_cache = {}
memory_attempts_cache = []

# Grading thresholds (configurable)
SIMILARITY_THRESHOLD_FULL = 0.85
SIMILARITY_THRESHOLD_PARTIAL = 0.70
PARTIAL_CREDIT_PERCENTAGE = 0.5
KEYWORD_BONUS_POINTS = 0.1  # Bonus per matched keyword (max 0.5 points)
MAX_KEYWORD_BONUS = 0.5

db_client = None
if MONGO_URI:
    try:
        db_client = AsyncIOMotorClient(MONGO_URI)
    except Exception as e:
        print(f"Warning: Could not connect to MongoDB: {e}")
        db_client = None


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


def count_keyword_matches(response: str, keywords: List[str]) -> int:
    """Count how many rubric keywords are present in the response."""
    response_lower = response.lower()
    matches = 0
    for keyword in keywords:
        if keyword.lower() in response_lower:
            matches += 1
    return matches


async def get_quiz_from_cache(quiz_id: str) -> Dict[str, Any] | None:
    """Retrieve full quiz data (including correct answers) from cache."""
    if db_client:
        collection = db_client.get_database("ytlearner").get_collection("quizzes")
        doc = await collection.find_one({"quizId": quiz_id})
        if doc:
            doc.pop("_id", None)
            return doc
    else:
        if quiz_id in memory_quiz_cache:
            return memory_quiz_cache[quiz_id]
    
    return None


async def save_attempt(attempt_data: Dict[str, Any]):
    """Save quiz attempt to database."""
    attempt_data["submittedAt"] = datetime.utcnow().isoformat()
    
    if db_client:
        collection = db_client.get_database("ytlearner").get_collection("attempts")
        await collection.insert_one(attempt_data)
    else:
        memory_attempts_cache.append(attempt_data)


async def grade_question(
    question: Dict[str, Any],
    user_response: Any  # Can be int (MCQ) or str (short answer)
) -> Tuple[float, str]:
    """
    Grade a single question.
    Returns: (points_earned, feedback_string)
    """
    max_points = question.get("points", 1)
    correct_answer = question.get("correct_answer", "")
    rubric_keywords = question.get("rubric_keywords", [])
    
    points_earned = 0.0
    feedback = ""
    
    if question["type"] == "mcq":
        # MCQ: user_response is an integer (option index)
        # correct_answer is also stored as an integer
        if isinstance(user_response, int) and user_response == correct_answer:
            points_earned = max_points
            feedback = "Correct!"
        else:
            points_earned = 0
            # Get the correct option text for feedback
            correct_option = question.get("options", [])[correct_answer] if isinstance(correct_answer, int) and correct_answer < len(question.get("options", [])) else str(correct_answer)
            feedback = f"Incorrect. The correct answer was: {correct_option}"
    
    else:  # short answer
        # Convert to string if not already
        user_response_str = str(user_response) if user_response else ""
        
        # Compute embedding similarity
        user_embedding = await llm_client.embed_text(user_response_str)
        correct_embedding = question.get("answer_embedding")
        
        if user_embedding and correct_embedding:
            similarity = cosine_similarity(user_embedding, correct_embedding)
            
            if similarity >= SIMILARITY_THRESHOLD_FULL:
                points_earned = max_points
                feedback = f"Excellent answer! (Similarity: {similarity:.2f})"
            elif similarity >= SIMILARITY_THRESHOLD_PARTIAL:
                points_earned = max_points * PARTIAL_CREDIT_PERCENTAGE
                feedback = f"Partially correct ({int(PARTIAL_CREDIT_PERCENTAGE * 100)}% credit). Consider adding more detail. (Similarity: {similarity:.2f})"
            else:
                points_earned = 0
                feedback = f"Answer needs improvement. Review the video content. (Similarity: {similarity:.2f})"
        else:
            # Fallback: simple keyword matching
            keyword_matches = count_keyword_matches(user_response_str, rubric_keywords)
            if keyword_matches >= len(rubric_keywords) * 0.7:
                points_earned = max_points
                feedback = "Good answer based on keywords."
            elif keyword_matches >= len(rubric_keywords) * 0.4:
                points_earned = max_points * PARTIAL_CREDIT_PERCENTAGE
                feedback = "Partial credit for covering some key points."
            else:
                points_earned = 0
                feedback = "Answer missing key concepts."
        
        # Keyword bonus
        if rubric_keywords:
            keyword_matches = count_keyword_matches(user_response_str, rubric_keywords)
            bonus = min(keyword_matches * KEYWORD_BONUS_POINTS, MAX_KEYWORD_BONUS)
            points_earned += bonus
            
            if bonus > 0:
                feedback += f" (+{bonus:.1f} bonus for keywords)"
    
    return round(points_earned, 2), feedback


async def grade_quiz_submission(
    quiz_id: str,
    answers: Dict[int, Any]
) -> Dict[str, Any]:
    """
    Grade a complete quiz submission.
    Returns score, per-question details, and AI-generated report.
    
    Args:
        quiz_id: The ID of the quiz being submitted
        answers: Dict mapping questionId (int) to answer (str for short, int for MCQ)
    """
    # Retrieve quiz from cache
    quiz = await get_quiz_from_cache(quiz_id)
    if not quiz:
        raise ValueError(f"Quiz {quiz_id} not found")
    
    # Grade each question
    total_points_possible = 0
    total_points_earned = 0
    question_feedbacks = []
    
    for idx, question in enumerate(quiz.get("questions", [])):
        user_response = answers.get(idx, "")
        
        points_earned, feedback = await grade_question(question, user_response)
        
        total_points_possible += question.get("points", 1)
        total_points_earned += points_earned
        
        question_feedbacks.append({
            "questionId": idx,
            "type": question["type"],
            "studentAnswer": user_response,
            "pointsEarned": points_earned,
            "maxPoints": question.get("points", 1),
            "feedback": feedback
        })
    
    # Calculate percentage
    score_percent = (total_points_earned / total_points_possible * 100) if total_points_possible > 0 else 0
    
    # Fetch video summary for report generation (import at top to avoid circular import)
    from ..routes.summary_routes import get_cached_summary, get_summary
    
    video_id = quiz.get("videoId")
    summary_data = None
    if video_id:
        try:
            # Try cache first, then generate if needed
            summary_data = await get_cached_summary(video_id)
            if not summary_data:
                summary_data = await get_summary(video_id)
        except Exception as e:
            print(f"Warning: Could not fetch summary for report: {e}")
    
    # Generate AI report
    attempt_data = {
        "quizId": quiz_id,
        "videoId": video_id,
        "scorePercent": round(score_percent, 2),
        "pointsEarned": round(total_points_earned, 2),
        "pointsPossible": total_points_possible,
        "questionFeedbacks": question_feedbacks,
        "submittedAt": datetime.utcnow().isoformat()
    }
    
    report = await llm_client.generate_report(
        attempt=attempt_data,
        quiz=quiz,
        summary=summary_data
    )
    
    # Save attempt
    full_attempt = {
        **attempt_data,
        "report": report
    }
    await save_attempt(full_attempt)
    
    # Return grading results
    return {
        "attempt": attempt_data,
        "report": report
    }
