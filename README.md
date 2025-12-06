# YtLearner

## Feature 1: YouTube Search (Standalone)

### Prerequisites
- Python 3.11+
- MongoDB (Optional, for caching)
- YouTube Data API Key

### Setup

1. **Environment Variables**
   - Rename `env.template` to `.env`.
   - Add your `YOUTUBE_API_KEY`.
   - (Optional) Add `MONGO_URI` if you want caching.

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   Or install manually:
   ```bash
   pip install fastapi uvicorn httpx motor python-dotenv isodate yt-dlp webvtt-py google-genai
   ```

### Running the Backend

1. Navigate to the `backend` directory (or root if running as module).
   ```bash
   # From project root
   python -m uvicorn app.main:app --reload
   ```
   The API will be available at `http://127.0.0.1:8000`.

### Running the Frontend

1. Simply open `frontend/search.html` in your web browser.

### Testing

1. **Curl Test**:
   ```bash
   curl "http://127.0.0.1:8000/api/search?q=python&maxResults=5"
   ```

2. **API Documentation**:
   - Open `http://127.0.0.1:8000/docs` to see the Swagger UI.

## Feature 2: Video Metadata

### Usage
- **Endpoint**: `GET /api/video/{videoId}/metadata`
- **Caching**: Results are cached for 7 days. If `MONGO_URI` is set, MongoDB is used. Otherwise, an in-memory dictionary is used.

### Testing
1. **Curl**:
   ```bash
   curl "http://127.0.0.1:8000/api/video/Ks-_Mh1QhMc/metadata"
   ```
2. **Frontend**:
   - Open `frontend/metadata.html` in your browser.
   - Enter a Video ID (e.g., `Ks-_Mh1QhMc`) and click "Get Metadata".

## Feature 3: Transcript Endpoint (Production)

### Usage
- **Endpoint**: `GET /api/video/{videoId}/transcript`
- **Technology**: Uses **yt-dlp** to download subtitles directly from YouTube
- **Production-Ready**: Works reliably in production environments (no API blocking issues)
- **Support**: Auto-generated and manual captions in English

### How It Works
1. Downloads subtitle files using yt-dlp Python library
2. Parses VTT/JSON subtitle formats
3. Returns timestamped transcript segments
4. Works even when youtube-transcript-api is blocked

### Testing
1. **Curl**:
   ```bash
   curl "http://127.0.0.1:8000/api/video/Ks-_Mh1QhMc/transcript"
   ```
2. **Frontend**:
   - Open `frontend/transcript.html` in your browser.
   - Enter a Video ID (e.g., `Ks-_Mh1QhMc`) and click "Get Transcript".
3. **Test UI**:
   - Open `frontend/transcript_test.html` for detailed testing with performance metrics

## Feature 4: Summary Generation

### Usage
- **Endpoint**: `GET /api/video/{videoId}/summary`
- **LLM Support**: 
  - If `GEMINI_API_KEY` is set in `.env`, uses Gemini API for intelligent summarization
  - If not set, uses a fallback extractive summarizer for testing
- **Caching**: Summaries are cached for 30 days

### Setup (Optional - for Gemini API)
1. Get a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Add to your `.env` file:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

### Testing
1. **Curl (Fallback)**:
   ```bash
   curl "http://127.0.0.1:8000/api/video/Ks-_Mh1QhMc/summary"
   ```
2. **Curl (With Gemini)**: Same command after adding `GEMINI_API_KEY` to `.env`
3. **Frontend**:
   - Open `frontend/summary.html` in your browser.
   - Enter a Video ID and click "Generate Summary".
   - Note: First-time generation may take 30-60 seconds.

## Feature 5: Quiz Generation

### Usage
- **Endpoint**: `GET /api/video/{videoId}/quiz?num_mcq=3&num_short=2`
- **Parameters**:
  - `num_mcq`: Number of multiple choice questions (0-10, default: 3)
  - `num_short`: Number of short answer questions (0-10, default: 2)
- **Caching**: Quizzes are cached for 30 days in the `quizzes` collection
- **Security**: Correct answers and embeddings are stored server-side only and NOT returned to clients

### Quiz Storage & Security

**Server-Side Storage** (in MongoDB or in-memory):
```json
{
  "quizId": "unique_hash",
  "videoId": "video_id",
  "questions": [
    {
      "id": "q1",
      "type": "mcq",
      "prompt": "Question text?",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "B",  // SERVER-SIDE ONLY
      "answer_embedding": [...],  // SERVER-SIDE ONLY
      "max_points": 1,
      "rubric_keywords": ["keyword1", "keyword2"]
    }
  ],
  "createdAt": "2025-12-01T..."
}
```

**Client Response** (correct answers stripped):
```json
{
  "videoId": "video_id",
  "questions": [
    {
      "id": "q1",
      "type": "mcq",
      "prompt": "Question text?",
      "options": ["A", "B", "C", "D"],
      "max_points": 1
    }
  ],
  "totalPoints": 5
}
```

**Security Features**:
- Correct answers are never sent to the client
- Answer embeddings are computed and stored server-side for future grading
- Quiz ID is hashed based on video ID and question counts
- Fallback quiz generation works without Gemini API for testing

### Testing
1. **Curl**:
   ```bash
   curl "http://127.0.0.1:8000/api/video/Ks-_Mh1QhMc/quiz?num_mcq=2&num_short=1"
   ```
2. **Frontend**:
   - Open `frontend/quiz.html` in your browser.
   - Enter a Video ID and configure question counts.
   - Click "Generate Quiz" to fetch questions.
   - Answer questions (correct answers are not shown).
3. **Verify Storage**:
   - Check MongoDB `quizzes` collection or inspect `memory_quiz_cache` in logs
   - Confirm `correct_answer` and `answer_embedding` fields exist server-side

## Feature 6: Quiz Submission, Grading & Report Generation

### Usage
- **Endpoint**: `POST /api/quiz/{quizId}/submit`
- **Request Body**:
  ```json
  {
    "answers": [
      {"questionId": 0, "answer": "Option B"},
      {"questionId": 1, "answer": "My detailed short answer"}
    ]
  }
  ```
- **Response**: Includes graded attempt, score, per-question feedback, and personalized AI-generated learning report

### Grading Algorithm

**Multiple Choice Questions (MCQ)**:
- Exact match comparison with stored correct answer
- Full points for correct, 0 points for incorrect

**Short Answer Questions**:
Uses semantic similarity with configurable thresholds:
- **Full Credit** (100%): Cosine similarity ≥ 0.85
- **Partial Credit** (70%): Cosine similarity ≥ 0.70 and < 0.85
- **No Credit** (0%): Cosine similarity < 0.70
- **Keyword Bonus**: +0.1 similarity if student answer contains rubric keywords

**Configurable Thresholds** (in `backend/app/services/grading_service.py`):
```python
SIMILARITY_THRESHOLD_FULL = 0.85    # Full credit threshold
SIMILARITY_THRESHOLD_PARTIAL = 0.70  # Partial credit threshold
KEYWORD_BONUS = 0.10                 # Bonus for keyword matches
```

### Report Generation

The AI-generated report includes:
- **Overall Percentage**: Final score percentage
- **Strengths**: Areas where student performed well
- **Weaknesses**: Concepts needing improvement
- **Detailed Feedback**: Specific guidance per question
- **Micro Exercises**: Personalized practice tasks to reinforce learning

**Fallback**: If `GEMINI_API_KEY` is not set, generates a deterministic report based on score thresholds.

### Data Storage

**Attempt Storage** (in MongoDB `quiz_attempts` or in-memory):
```json
{
  "attemptId": "unique_id",
  "quizId": "quiz_hash",
  "submittedAt": "2025-12-01T...",
  "pointsEarned": 4,
  "pointsPossible": 5,
  "scorePercent": 80.0,
  "questionFeedbacks": [
    {
      "questionId": 0,
      "type": "mcq",
      "studentAnswer": "B",
      "pointsEarned": 1,
      "maxPoints": 1,
      "feedback": "Correct!"
    },
    {
      "questionId": 1,
      "type": "short",
      "studentAnswer": "This is my answer",
      "pointsEarned": 2,
      "maxPoints": 3,
      "feedback": "Partial credit: Missing key detail about X"
    }
  ]
}
```

### Tuning Grading Parameters

To adjust grading strictness, edit `backend/app/services/grading_service.py`:

1. **Make it easier** (more partial credit):
   ```python
   SIMILARITY_THRESHOLD_FULL = 0.80  # Lower from 0.85
   SIMILARITY_THRESHOLD_PARTIAL = 0.60  # Lower from 0.70
   ```

2. **Make it harder** (stricter grading):
   ```python
   SIMILARITY_THRESHOLD_FULL = 0.90  # Raise from 0.85
   SIMILARITY_THRESHOLD_PARTIAL = 0.80  # Raise from 0.70
   ```

3. **Adjust keyword importance**:
   ```python
   KEYWORD_BONUS = 0.15  # Increase from 0.10 for more keyword weight
   ```

### Testing

1. **Curl**:
   ```bash
   # First, get a quiz and note its quizId
   curl "http://127.0.0.1:8000/api/video/Ks-_Mh1QhMc/quiz"
   
   # Then submit answers (use actual quizId from previous response)
   curl -X POST "http://127.0.0.1:8000/api/quiz/{quizId}/submit" \
     -H "Content-Type: application/json" \
     -d '{
       "answers": [
         {"questionId": 0, "answer": "B"},
         {"questionId": 1, "answer": "The main topic is about X and Y"}
       ]
     }'
   ```

2. **Frontend**:
   - Open `frontend/quiz.html` to generate a quiz
   - Complete the quiz questions
   - Click "Submit Quiz" (or open `frontend/submit_quiz.html?quizId={quizId}`)
   - View your personalized learning report with score, feedback, and exercises

3. **Verify Grading**:
   - Check server logs for similarity scores and grading decisions
   - Review stored attempts in MongoDB `quiz_attempts` collection
   - Confirm report includes strengths, weaknesses, and micro exercises

## Feature 7: API Documentation & Deployment

### OpenAPI Specification Export

Generate and share the complete API documentation:

1. **Export OpenAPI Spec**:
   - Start your server: `python -m uvicorn backend.app.main:app --reload`
   - Visit: `http://127.0.0.1:8000/export-openapi`
   - This creates `openapi.json` at project root

2. **Interactive Documentation**:
   - Swagger UI: `http://127.0.0.1:8000/docs`
   - ReDoc: `http://127.0.0.1:8000/redoc`

3. **Share with Others**:
   - Send `openapi.json` to teammates
   - They can import it into API tools (Postman, Insomnia, etc.)
   - Or generate client libraries using OpenAPI Generator

### Postman Collection

Import the ready-made collection for easy testing:

1. **Import Collection**:
   - Open Postman
   - Click "Import" → "Upload Files"
   - Select `postman_collection.json`

2. **Configure Environment**:
   - The collection includes variables:
     - `base_url`: Default `http://127.0.0.1:8000`
     - `video_id`: Default `Ks-_Mh1QhMc`
     - `quiz_id`: Auto-populated after quiz generation

3. **Test Endpoints**:
   - Health Check → Search → Metadata → Transcript → Summary → Quiz → Submit
   - The "Generate Quiz" request automatically saves `quiz_id` for submission

### API Test UI

Quick manual testing with a visual interface:

1. **Open Test Page**:
   - Open `frontend/api-test.html` in your browser

2. **Configure**:
   - Set API Base URL (default: `http://127.0.0.1:8000`)
   - Set default Video ID for quick testing

3. **Test All Endpoints**:
   - Click buttons to test each endpoint
   - View formatted JSON responses
   - Copy Quiz ID from response to test submission

### Deployment

Deploy your API to the cloud with free-tier options:

1. **Read Deployment Guide**:
   - See `deploy.md` for complete instructions
   - Covers Render and Railway platforms

2. **Quick Start (Render)**:
   ```bash
   # Push to GitHub
   git add .
   git commit -m "Ready for deployment"
   git push
   
   # On Render dashboard:
   # - Connect GitHub repo
   # - Set start command: uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
   # - Add environment variables (YOUTUBE_API_KEY, GEMINI_API_KEY, etc.)
   # - Deploy!
   ```

3. **Quick Start (Railway)**:
   ```bash
   # Procfile is already included
   # Push to GitHub
   git push
   
   # On Railway:
   # - Import GitHub repo
   # - Add environment variables
   # - Automatically deploys
   ```

4. **Environment Variables Required**:
   - `YOUTUBE_API_KEY` (required)
   - `GEMINI_API_KEY` (optional but recommended)
   - `MONGO_URI` (optional, uses in-memory cache if not set)
   - `GEMINI_MODEL` (optional, default: `gemini-2.5-flash`)

5. **After Deployment**:
   - Test with: `curl https://your-app.onrender.com/`
   - View docs: `https://your-app.onrender.com/docs`
   - Update frontend files with your deployed URL

### Sharing Your API

**For Developers:**
1. Share `openapi.json` - they can generate client code
2. Share `postman_collection.json` - for testing in Postman
3. Share deployment URL - direct API access

**For Non-Developers:**
1. Share deployed URL + `/docs` (interactive documentation)
2. Share `frontend/api-test.html` (hosted version for testing)

**Security Reminders:**
- Never commit `.env` file to Git
- Never share API keys publicly
- Rotate keys if accidentally exposed
- Set API key restrictions in Google Cloud Console








