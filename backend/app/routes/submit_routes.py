from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List, Union
from pydantic import BaseModel
from ..services.grading_service import grade_quiz_submission

router = APIRouter()

class QuizAnswer(BaseModel):
    questionId: int
    answer: Union[str, int]  # MCQ answers are integers (option index), short answers are strings

class QuizSubmission(BaseModel):
    answers: List[QuizAnswer]

@router.post("/quiz/{quizId}/submit", response_model=Dict[str, Any])
async def submit_quiz(
    quizId: str,
    submission: QuizSubmission = Body(...)
):
    """
    Submit quiz answers for grading.
    Returns score, per-question details, and AI-generated report.
    """
    try:
        # Convert answers to dict format expected by grading service
        answers_dict = {a.questionId: a.answer for a in submission.answers}
        
        result = await grade_quiz_submission(
            quiz_id=quizId,
            answers=answers_dict
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Grading failed: {str(e)}")
