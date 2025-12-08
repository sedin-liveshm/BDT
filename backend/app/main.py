import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables before importing other modules
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .routes import search_routes, video_routes, transcript_routes, summary_routes, quiz_routes, submit_routes, resources_routes

app = FastAPI(
    title="YtLearner API",
    description="Backend API for YtLearner - YouTube video learning assistant with AI-powered summaries, quizzes, and personalized learning reports",
    version="1.0.0",
    contact={
        "name": "YtLearner Team",
        "email": "support@ytlearner.example.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "null" # For opening HTML file directly
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for simplicity in development/testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_routes.router, prefix="/api", tags=["search"])
app.include_router(video_routes.router, prefix="/api", tags=["video"])
app.include_router(transcript_routes.router, prefix="/api", tags=["transcript"])
app.include_router(summary_routes.router, prefix="/api", tags=["summary"])
app.include_router(quiz_routes.router, prefix="/api", tags=["quiz"])
app.include_router(submit_routes.router, prefix="/api", tags=["submit"])
app.include_router(resources_routes.router, prefix="/api", tags=["resources"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to YtLearner API",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }

@app.get("/export-openapi")
async def export_openapi():
    """
    Export OpenAPI specification to openapi.json file at project root.
    This endpoint generates the file and returns confirmation.
    """
    # Get the OpenAPI schema
    openapi_schema = app.openapi()
    
    # Write to project root (parent of backend directory)
    project_root = Path(__file__).parent.parent.parent
    output_path = project_root / "openapi.json"
    
    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)
    
    return {
        "message": "OpenAPI specification exported successfully",
        "path": str(output_path),
        "size_bytes": output_path.stat().st_size
    }
