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


async def analyze_video_url(video_url: str) -> Dict[str, Any]:
    """
    Analyze a YouTube video directly using Gemini's video understanding capabilities.
    Fallback when transcript is not available.
    """
    prompt = f"""Analyze this YouTube video and provide a comprehensive summary in JSON format.

Video URL: {video_url}

Provide a detailed analysis covering:
1. Main topics and themes discussed
2. Key points and takeaways
3. Important concepts explained
4. Overall focus and purpose of the video

Respond with ONLY a valid JSON object (no markdown, no code fences) with this structure:
{{
  "summary": "A comprehensive 4-6 sentence summary of the entire video",
  "takeaways": ["main takeaway 1", "main takeaway 2", "main takeaway 3", "main takeaway 4"],
  "focus": "The primary focus or theme of the video in one sentence",
  "topics": ["topic 1", "topic 2", "topic 3"],
  "source": "video_analysis"
}}
"""
    
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        
        result_text = response.text
        cleaned = _clean_json_response(result_text)
        
        try:
            summary_data = json.loads(cleaned)
            summary_data['source'] = 'video_analysis'
            return summary_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse video analysis JSON: {e}")
            logger.error(f"Response text: {result_text}")
            # Return a basic structure
            return {
                "summary": cleaned[:500] if len(cleaned) > 500 else cleaned,
                "takeaways": ["Unable to parse detailed analysis"],
                "focus": "Video analysis completed but format parsing failed",
                "source": "video_analysis"
            }
    except Exception as e:
        logger.error(f"Video analysis failed: {e}")
        raise RuntimeError(f"Failed to analyze video: {str(e)}")


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


async def get_learning_resources(topic: str) -> Dict[str, Any]:
    """
    Get curated learning resources for a specific topic from multiple platforms.
    Returns structured recommendations for Udemy, LinkedIn Learning, Coursera, and government resources.
    """
    prompt = f"""You are an expert learning resource curator. A user wants to learn about "{topic}".

Provide a comprehensive list of the BEST learning resources from multiple platforms. For each resource, provide:
1. **Direct URL links** (actual working URLs, not placeholders)
2. Course/resource title
3. Platform name
4. Brief description
5. Difficulty level (Beginner/Intermediate/Advanced)
6. Estimated duration (if applicable)

Include resources from:
1. **Udemy** - At least 3-5 top-rated courses with real Udemy URLs
2. **LinkedIn Learning** - At least 3-5 courses with real LinkedIn Learning URLs
3. **Coursera** - At least 3-5 courses with real Coursera URLs
4. **Government Resources** - Official government learning portals, certifications, or educational websites (e.g., USA.gov learning, state education sites, government-funded MOOCs)
5. **Other Platforms** - FreeCodeCamp, Khan Academy, edX, YouTube channels, official documentation

**IMPORTANT:** 
- Use REAL, WORKING URLs that users can click and access
- For Udemy: https://www.udemy.com/course/[course-name]/
- For LinkedIn: https://www.linkedin.com/learning/[course-name]
- For Coursera: https://www.coursera.org/learn/[course-name]
- For government: actual .gov domains or official educational portals
- Prioritize free or affordable options
- Include a mix of beginner to advanced resources

Respond with ONLY a valid JSON object (no markdown, no code fences) with this structure:
{{
  "topic": "{topic}",
  "udemy": [
    {{
      "title": "Course title",
      "url": "https://www.udemy.com/course/...",
      "description": "Brief description",
      "level": "Beginner/Intermediate/Advanced",
      "duration": "X hours",
      "price": "Free/Paid"
    }}
  ],
  "linkedin_learning": [
    {{
      "title": "Course title",
      "url": "https://www.linkedin.com/learning/...",
      "description": "Brief description",
      "level": "Beginner/Intermediate/Advanced",
      "duration": "X hours"
    }}
  ],
  "coursera": [
    {{
      "title": "Course title",
      "url": "https://www.coursera.org/learn/...",
      "description": "Brief description",
      "level": "Beginner/Intermediate/Advanced",
      "duration": "X weeks",
      "provider": "University/Organization name"
    }}
  ],
  "government_resources": [
    {{
      "title": "Resource title",
      "url": "https://...",
      "description": "Brief description",
      "organization": "Government agency/department",
      "type": "Course/Certification/Portal"
    }}
  ],
  "other_platforms": [
    {{
      "title": "Resource title",
      "platform": "Platform name",
      "url": "https://...",
      "description": "Brief description",
      "level": "Beginner/Intermediate/Advanced",
      "price": "Free/Paid"
    }}
  ],
  "learning_path": "Recommended step-by-step learning path in 2-3 sentences",
  "total_resources": 25
}}
"""
    
    try:
        logger.info(f"Fetching learning resources for topic: {topic}")
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        
        result_text = response.text
        cleaned = _clean_json_response(result_text)
        
        try:
            resources_data = json.loads(cleaned)
            
            # Validate structure
            if not isinstance(resources_data, dict):
                raise ValueError("Response is not a valid JSON object")
            
            # Ensure all required keys exist with defaults
            resources_data.setdefault("topic", topic)
            resources_data.setdefault("udemy", [])
            resources_data.setdefault("linkedin_learning", [])
            resources_data.setdefault("coursera", [])
            resources_data.setdefault("government_resources", [])
            resources_data.setdefault("other_platforms", [])
            resources_data.setdefault("learning_path", "Start with beginner courses and progressively move to advanced topics.")
            
            # Count total resources
            total = (
                len(resources_data.get("udemy", [])) +
                len(resources_data.get("linkedin_learning", [])) +
                len(resources_data.get("coursera", [])) +
                len(resources_data.get("government_resources", [])) +
                len(resources_data.get("other_platforms", []))
            )
            resources_data["total_resources"] = total
            
            logger.info(f"Successfully fetched {total} learning resources")
            return resources_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse learning resources JSON: {e}")
            logger.error(f"Response text: {result_text}")
            # Return a basic structure with error info
            return {
                "topic": topic,
                "udemy": [],
                "linkedin_learning": [],
                "coursera": [],
                "government_resources": [],
                "other_platforms": [],
                "learning_path": "Unable to fetch resources at this time. Please try again.",
                "total_resources": 0,
                "error": "Failed to parse AI response"
            }
    except Exception as e:
        logger.error(f"Learning resources fetch failed: {e}")
        raise RuntimeError(f"Failed to fetch learning resources: {str(e)}")


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

