from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List
from ..services import llm_client

router = APIRouter()

@router.post("/resources/recommendations", response_model=Dict[str, Any])
async def get_learning_resources(
    request: Dict[str, str] = Body(..., example={"topic": "Python Programming"})
):
    """
    Get curated learning resources for a specific topic.
    Returns courses from Udemy, LinkedIn Learning, Coursera, and government resources.
    """
    topic = request.get("topic", "").strip()
    
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required")
    
    if len(topic) < 2:
        raise HTTPException(status_code=400, detail="Topic must be at least 2 characters long")
    
    try:
        resources = await llm_client.get_learning_resources(topic)
        return resources
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch learning resources: {str(e)}"
        )
