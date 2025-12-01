# backend/app/services/llm_client.py
import os
import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger("app.services.llm_client")
logger.setLevel(logging.INFO)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Prompts for summarization
CHUNK_SUMMARY_PROMPT = """Analyze the following transcript chunk and provide a structured summary in JSON format.

Transcript:
{chunk_text}

Respond with ONLY a valid JSON object (no markdown, no code fences) with this structure:
{{
  "chunk_summary": "A concise 2-3 sentence summary of the main points",
  "takeaways": ["key point 1", "key point 2", "key point 3"],
  "highlights": [{{"text": "important quote or fact", "start": 0}}]
}}
"""

MERGE_SUMMARY_PROMPT = """Merge the following chunk summaries into a comprehensive final summary in JSON format.

Chunk Summaries:
{chunk_summaries}

Respond with ONLY a valid JSON object (no markdown, no code fences) with this structure:
{{
  "summary": "A comprehensive 3-5 sentence summary of the entire video",
  "takeaways": ["main takeaway 1", "main takeaway 2", "main takeaway 3"],
  "focus": "The primary focus or theme of the video in one sentence"
}}
"""

# Initialize Gemini client
try:
    from google import genai
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set in environment")
    client = genai.Client(api_key=GEMINI_API_KEY)
    MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    logger.info(f"Initialized Gemini client with model: {MODEL_NAME}")
except ImportError:
    logger.error("google-genai package not installed. Install with: pip install google-genai")
    raise RuntimeError("google-genai package is required but not installed")
except Exception as e:
    logger.error(f"Failed to initialize Gemini client: {e}")
    raise



def _clean_json_response(text: str) -> str:
    """Strip markdown code fences and extract JSON content."""
    text = text.strip()
    
    # Remove markdown code fences
    if "```json" in text:
        parts = text.split("```json", 1)[1].split("```", 1)
        text = parts[0].strip()
    elif "```" in text:
        parts = text.split("```", 1)[1].split("```", 1)
        text = parts[0].strip()
    
    return text


async def generate_text(prompt: str, max_tokens: int = 1000) -> str:
    """
    Generate text using Gemini API with the new google-genai SDK.
    """
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        return response.text
    except Exception as e:
        logger.error(f"Error generating text with Gemini: {e}")
        # Log the full error for debugging
        import traceback
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Failed to generate text: {str(e)}")


async def summarize_chunk(chunk_text: str) -> Dict[str, Any]:
    """
    Summarize a transcript chunk using Gemini.
    Returns a dict with chunk_summary, takeaways, and highlights.
    """
    try:
        prompt = CHUNK_SUMMARY_PROMPT.format(chunk_text=chunk_text)
        logger.info(f"Summarizing chunk of {len(chunk_text)} characters")
        
        raw_response = await generate_text(prompt, max_tokens=600)
        logger.info(f"Raw response: {raw_response[:200]}...")
        
        # Clean and parse JSON
        cleaned = _clean_json_response(raw_response)
        parsed = json.loads(cleaned)
        
        if not isinstance(parsed, dict):
            raise ValueError("Response is not a JSON object")
        
        # Ensure required fields exist
        result = {
            "chunk_summary": parsed.get("chunk_summary", ""),
            "takeaways": parsed.get("takeaways", []),
            "highlights": parsed.get("highlights", [])
        }
        
        logger.info(f"Successfully parsed chunk summary")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON. Raw output: {raw_response[:500]}")
        # Fallback: return a basic summary
        return {
            "chunk_summary": raw_response[:200] if raw_response else "Failed to generate summary",
            "takeaways": [],
            "highlights": []
        }
    except Exception as e:
        logger.error(f"Error in summarize_chunk: {e}")
        raise


async def merge_summaries(chunk_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge multiple chunk summaries into a final comprehensive summary.
    """
    try:
        # Prepare summaries text
        summaries_text = "\n\n".join([
            f"Chunk {i+1}:\nSummary: {s.get('chunk_summary', '')}\nTakeaways: {', '.join(s.get('takeaways', []))}"
            for i, s in enumerate(chunk_summaries)
        ])
        
        prompt = MERGE_SUMMARY_PROMPT.format(chunk_summaries=summaries_text)
        logger.info(f"Merging {len(chunk_summaries)} chunk summaries")
        
        raw_response = await generate_text(prompt, max_tokens=1000)
        logger.info(f"Raw merge response: {raw_response[:200]}...")
        
        # Clean and parse JSON
        cleaned = _clean_json_response(raw_response)
        parsed = json.loads(cleaned)
        
        if not isinstance(parsed, dict):
            raise ValueError("Response is not a JSON object")
        
        # Collect all highlights from chunks
        all_highlights = []
        for s in chunk_summaries:
            all_highlights.extend(s.get("highlights", []))
        
        # Build final result
        result = {
            "summary": parsed.get("summary", ""),
            "takeaways": parsed.get("takeaways", []),
            "focus": parsed.get("focus", ""),
            "highlights": all_highlights[:10]  # Limit to top 10 highlights
        }
        
        logger.info("Successfully merged summaries")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse merged JSON. Raw output: {raw_response[:500]}")
        # Fallback: return basic merged data
        all_takeaways = []
        for s in chunk_summaries:
            all_takeaways.extend(s.get("takeaways", []))
        
        return {
            "summary": raw_response[:300] if raw_response else "Failed to generate summary",
            "takeaways": all_takeaways[:5],
            "focus": "Video content summary",
            "highlights": []
        }
    except Exception as e:
        logger.error(f"Error in merge_summaries: {e}")
        raise


QUIZ_GENERATION_PROMPT = """Based on the following video summary, generate quiz questions in JSON format.

Video Summary:
Summary: {summary}
Key Takeaways: {takeaways}
Focus: {focus}

Generate {num_mcq} multiple choice questions and {num_short} short answer questions.

Respond with ONLY a valid JSON array (no markdown, no code fences) with this structure:
[
  {{
    "id": "q1",
    "type": "mcq",
    "prompt": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "Option B",
    "max_points": 1,
    "rubric_keywords": ["keyword1", "keyword2"]
  }},
  {{
    "id": "q2",
    "type": "short",
    "prompt": "Explain the main concept discussed in the video.",
    "correct_answer": "A detailed answer here",
    "max_points": 2,
    "rubric_keywords": ["concept1", "concept2", "concept3"]
  }}
]
"""


def generate_fallback_quiz(summary_data: Dict[str, Any], num_mcq: int, num_short: int) -> List[Dict[str, Any]]:
    """Generate deterministic placeholder quiz when Gemini API is unavailable."""
    questions = []
    question_id = 1
    
    summary = summary_data.get("summary", "video content")
    takeaways = summary_data.get("takeaways", [])
    
    # Generate MCQ questions
    for i in range(num_mcq):
        questions.append({
            "id": f"q{question_id}",
            "type": "mcq",
            "prompt": f"Based on the video, which statement is most accurate about the topic discussed?",
            "options": [
                f"The video primarily focuses on {summary[:30]}...",
                f"The main topic is unrelated to {summary[:20]}...",
                f"The video discusses {takeaways[0] if takeaways else 'various concepts'}",
                "None of the above"
            ],
            "correct_answer": f"The video discusses {takeaways[0] if takeaways else 'various concepts'}",
            "max_points": 1,
            "rubric_keywords": takeaways[:3] if takeaways else ["content", "topic", "video"],
            "answer_embedding": None
        })
        question_id += 1
    
    # Generate short answer questions
    for i in range(num_short):
        questions.append({
            "id": f"q{question_id}",
            "type": "short",
            "prompt": f"Describe the main concept discussed in the video.",
            "correct_answer": summary[:150] if summary else "Summary of video content",
            "max_points": 2,
            "rubric_keywords": takeaways[:5] if takeaways else ["concept", "main", "topic"],
            "answer_embedding": None
        })
        question_id += 1
    
    return questions


async def generate_quiz(summary_data: Dict[str, Any], num_mcq: int = 3, num_short: int = 2) -> List[Dict[str, Any]]:
    """
    Generate quiz questions based on video summary.
    Returns questions with correct_answer and answer_embedding (server-side only).
    """
    # Check if Gemini API is available
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set, using fallback quiz generation")
        return generate_fallback_quiz(summary_data, num_mcq, num_short)
    
    try:
        # Prepare prompt
        summary = summary_data.get("summary", "")
        takeaways = ", ".join(summary_data.get("takeaways", []))
        focus = summary_data.get("focus", "")
        
        prompt = QUIZ_GENERATION_PROMPT.format(
            summary=summary,
            takeaways=takeaways,
            focus=focus,
            num_mcq=num_mcq,
            num_short=num_short
        )
        
        logger.info(f"Generating quiz: {num_mcq} MCQ, {num_short} short answer questions")
        
        # Generate quiz
        raw_response = await generate_text(prompt, max_tokens=2000)
        logger.info(f"Raw quiz response: {raw_response[:200]}...")
        
        # Clean and parse JSON
        cleaned = _clean_json_response(raw_response)
        questions = json.loads(cleaned)
        
        if not isinstance(questions, list):
            raise ValueError("Response is not a JSON array")
        
        # Generate embeddings for correct answers
        for q in questions:
            if "correct_answer" in q and q["correct_answer"]:
                try:
                    # Use simple embedding (store the text itself as a basic fallback)
                    # In production, you'd use a proper embedding model
                    q["answer_embedding"] = await embed_text(q["correct_answer"])
                except Exception as e:
                    logger.warning(f"Failed to generate embedding: {e}")
                    q["answer_embedding"] = None
        
        logger.info(f"Successfully generated {len(questions)} quiz questions")
        return questions
        
    except Exception as e:
        logger.error(f"Error generating quiz with Gemini, using fallback: {e}")
        return generate_fallback_quiz(summary_data, num_mcq, num_short)


async def embed_text(text: str) -> List[float] | None:
    """
    Generate embeddings for text.
    Uses a simple fallback approach (normalized character frequencies).
    In production, use Gemini embeddings API or a dedicated embedding model.
    """
    try:
        # Simple fallback: normalized character frequency vector
        # This is just a placeholder - in production use proper embeddings
        char_counts = {}
        for char in text.lower():
            if char.isalnum():
                char_counts[char] = char_counts.get(char, 0) + 1
        
        # Create a simple 128-dimensional vector
        embedding = [0.0] * 128
        for char, count in char_counts.items():
            idx = ord(char) % 128
            embedding[idx] = count / max(len(text), 1)
        
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None


REPORT_GENERATION_PROMPT = """Generate a detailed learning report for a student who just completed a quiz.

Student Performance:
Score: {score_percent}%
Points: {points_earned}/{points_possible}

Video Summary:
{summary}

Quiz Questions & Student Performance:
{question_details}

Provide a comprehensive learning report in JSON format with:
{{
  "overall_percent": {score_percent},
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "detailed_feedback": ["feedback point 1", "feedback point 2", "feedback point 3"],
  "micro_exercises": [
    {{"task": "exercise 1", "purpose": "reinforce concept X"}},
    {{"task": "exercise 2", "purpose": "practice skill Y"}}
  ]
}}

Respond with ONLY valid JSON (no markdown, no code fences).
"""


def generate_fallback_report(attempt: Dict[str, Any], quiz: Dict[str, Any], summary: Dict[str, Any] | None) -> Dict[str, Any]:
    """Generate a simple deterministic report when Gemini API is unavailable."""
    score_percent = attempt.get("scorePercent", 0)
    
    # Determine strengths and weaknesses based on score
    if score_percent >= 80:
        strengths = [
            "Strong understanding of the video content",
            "Excellent performance on quiz questions"
        ]
        weaknesses = [
            "Minor areas for improvement in detail retention"
        ]
    elif score_percent >= 60:
        strengths = [
            "Good grasp of main concepts",
            "Adequate comprehension of key points"
        ]
        weaknesses = [
            "Some concepts need reinforcement",
            "Consider reviewing sections where points were lost"
        ]
    else:
        strengths = [
            "Attempted all questions"
        ]
        weaknesses = [
            "Need to review video content more thoroughly",
            "Key concepts not fully understood",
            "Recommend re-watching the video"
        ]
    
    # Generate feedback based on question performance
    detailed_feedback = []
    for q_feedback in attempt.get("questionFeedbacks", []):
        if q_feedback["pointsEarned"] < q_feedback["maxPoints"]:
            detailed_feedback.append(
                f"Question {q_feedback['questionId']}: Review this topic for better understanding"
            )
    
    if not detailed_feedback:
        detailed_feedback = ["Great job! All questions answered correctly."]
    
    # Suggest micro exercises
    micro_exercises = [
        {
            "task": "Re-watch the video and take notes on key concepts",
            "purpose": "Reinforce understanding"
        },
        {
            "task": "Explain the main idea to someone else",
            "purpose": "Test comprehension through teaching"
        }
    ]
    
    if score_percent < 70:
        micro_exercises.append({
            "task": "Create a mind map of the video's main topics",
            "purpose": "Visualize concept relationships"
        })
    
    return {
        "overall_percent": score_percent,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "detailed_feedback": detailed_feedback,
        "micro_exercises": micro_exercises
    }


async def generate_report(attempt: Dict[str, Any], quiz: Dict[str, Any], summary: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Generate a personalized learning report based on quiz performance.
    """
    # Check if Gemini API is available
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set, using fallback report generation")
        return generate_fallback_report(attempt, quiz, summary)
    
    try:
        # Prepare data for prompt
        score_percent = attempt.get("scorePercent", 0)
        points_earned = attempt.get("pointsEarned", 0)
        points_possible = attempt.get("pointsPossible", 1)
        
        summary_text = ""
        if summary:
            summary_text = f"Summary: {summary.get('summary', '')}\nKey Points: {', '.join(summary.get('takeaways', []))}"
        else:
            summary_text = "Summary not available"
        
        # Format question details
        question_details = []
        for q_feedback in attempt.get("questionFeedbacks", []):
            detail = f"Q{q_feedback['questionId']} ({q_feedback['type']}): {q_feedback['pointsEarned']}/{q_feedback['maxPoints']} pts - {q_feedback['feedback']}"
            question_details.append(detail)
        
        prompt = REPORT_GENERATION_PROMPT.format(
            score_percent=score_percent,
            points_earned=points_earned,
            points_possible=points_possible,
            summary=summary_text,
            question_details="\n".join(question_details)
        )
        
        logger.info(f"Generating report for score: {score_percent}%")
        
        # Generate report
        raw_response = await generate_text(prompt, max_tokens=1500)
        logger.info(f"Raw report response: {raw_response[:200]}...")
        
        # Clean and parse JSON
        cleaned = _clean_json_response(raw_response)
        report = json.loads(cleaned)
        
        if not isinstance(report, dict):
            raise ValueError("Response is not a JSON object")
        
        # Ensure required fields
        report.setdefault("overall_percent", score_percent)
        report.setdefault("strengths", [])
        report.setdefault("weaknesses", [])
        report.setdefault("detailed_feedback", [])
        report.setdefault("micro_exercises", [])
        
        logger.info("Successfully generated report")
        return report
        
    except Exception as e:
        logger.error(f"Error generating report with Gemini, using fallback: {e}")
        return generate_fallback_report(attempt, quiz, summary)



# Example local test runner (only run directly)
if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("Testing Gemini API integration...")
        
        # Test simple generation
        sample_prompt = "Write a 1-sentence summary of why unit tests are useful."
        result = await generate_text(sample_prompt)
        print(f"\nSimple generation test:\n{result}\n")
        
        # Test chunk summarization
        sample_chunk = "This is a test transcript about machine learning. Machine learning is a subset of artificial intelligence that focuses on training algorithms to learn from data."
        chunk_result = await summarize_chunk(sample_chunk)
        print(f"\nChunk summary test:")
        print(json.dumps(chunk_result, indent=2))
    
    asyncio.run(test())

