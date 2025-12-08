# 🚀 YtLearner - Production Deployment Guide

## 📋 Prerequisites

Before deploying, ensure you have:
- ✅ GitHub repository with your code
- ✅ Gemini API key
- ✅ YouTube Data API v3 key
- ✅ Render/Railway account (or similar platform)

---

## 🔧 Environment Variables

Set these in your deployment platform's dashboard:

```env
# Required - Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Required - YouTube API
YOUTUBE_API_KEY=your_youtube_api_key_here

# Optional - Database (recommended for production)
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/ytlearner

# Auto-provided by platform (do not set manually)
PORT=10000
```

---

## 🌐 Deploy to Render (Recommended)

### Step 1: Prepare Your Repository

1. **Ensure these files exist:**
   ```
   requirements.txt
   backend/
   frontend/
   README.md
   ```

2. **Verify requirements.txt contains:**
   ```txt
   fastapi>=0.104.0
   uvicorn[standard]>=0.24.0
   google-genai>=0.3.0
   httpx>=0.25.0
   motor>=3.3.0
   python-dotenv>=1.0.0
   isodate>=0.6.1
   ```

3. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Ready for production deployment"
   git push origin main
   ```

### Step 2: Create New Web Service on Render

1. **Go to:** [https://render.com/](https://render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select the `YtLearner` repository

### Step 3: Configure Build Settings

| Field | Value |
|-------|-------|
| **Name** | `ytlearner` (or your choice) |
| **Region** | Choose closest to your users |
| **Branch** | `main` |
| **Root Directory** | (leave empty) |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT` |

### Step 4: Set Environment Variables

In Render dashboard, go to **Environment** tab and add:

```
GEMINI_API_KEY = your_actual_gemini_api_key
GEMINI_MODEL = gemini-2.5-flash
YOUTUBE_API_KEY = your_actual_youtube_api_key
```

Optional (for caching):
```
MONGO_URI = mongodb+srv://user:pass@cluster.mongodb.net/ytlearner
```

### Step 5: Deploy

1. Click **"Create Web Service"**
2. Wait 3-5 minutes for deployment
3. Your API will be live at: `https://ytlearner.onrender.com`

---

## 🛤️ Deploy to Railway

### Step 1: Create New Project

1. Go to [railway.app](https://railway.app/)
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your `YtLearner` repository

### Step 2: Configure Service

Railway auto-detects Python projects. If not:

1. Click on your service
2. Go to **Settings** tab
3. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`

### Step 3: Add Environment Variables

In **Variables** tab, add:

```
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
YOUTUBE_API_KEY=your_youtube_api_key
MONGO_URI=your_mongodb_connection_string
```

### Step 4: Deploy

1. Click **"Deploy"**
2. Railway generates a URL: `https://ytlearner-production.up.railway.app`

---

## 🗄️ MongoDB Setup (Optional but Recommended)

### Option 1: MongoDB Atlas (Free Tier)

1. **Sign up:** [https://www.mongodb.com/cloud/atlas/register](https://www.mongodb.com/cloud/atlas/register)

2. **Create Cluster:**
   - Choose **FREE** tier (M0)
   - Select region closest to your deployment
   - Click **"Create"**

3. **Create Database User:**
   - Security → Database Access
   - Add new user with password
   - **Remember credentials!**

4. **Whitelist IP:**
   - Security → Network Access
   - Click **"Add IP Address"**
   - Select **"Allow access from anywhere"** (0.0.0.0/0)

5. **Get Connection String:**
   - Click **"Connect"** → **"Connect your application"**
   - Copy connection string:
     ```
     mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/ytlearner
     ```
   - Replace `username`, `password`, and database name

6. **Add to Environment Variables:**
   ```
   MONGO_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/ytlearner
   ```

### Option 2: No Database (In-Memory Only)

If you skip MongoDB:
- ⚠️ Cache resets on every deployment
- ⚠️ No persistent storage
- ✅ Works fine for testing/low traffic
- Simply **don't set** `MONGO_URI` variable

---

## 🔑 API Keys Setup

### Gemini API Key

1. Go to: [https://ai.google.dev/](https://ai.google.dev/)
2. Click **"Get API key in Google AI Studio"**
3. Create new API key
4. Copy and save securely
5. Add to environment: `GEMINI_API_KEY=your_key_here`

### YouTube Data API Key

1. Go to: [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Create new project (or select existing)
3. Enable **"YouTube Data API v3"**
4. Go to **Credentials** → **Create Credentials** → **API Key**
5. Copy the key
6. Add to environment: `YOUTUBE_API_KEY=your_key_here`

---

## 🧪 Testing Production Deployment

### Test Backend APIs

```bash
# Replace with your actual deployment URL
export API_URL="https://ytlearner.onrender.com"

# Test health check (if you add one)
curl $API_URL/

# Test video metadata
curl "$API_URL/api/video/Ks-_Mh1QhMc/metadata"

# Test summary generation
curl "$API_URL/api/video/Ks-_Mh1QhMc/summary"

# Test learning resources
curl -X POST "$API_URL/api/learning-resources" \
  -H "Content-Type: application/json" \
  -d '{"topic": "Python programming"}'

# Test quiz generation
curl "$API_URL/api/video/Ks-_Mh1QhMc/quiz?num_mcq=3&num_short=2"
```

### Test Frontend

1. **Update API URL in HTML files:**

   Edit all files in `frontend/` folder:
   ```javascript
   // Change from:
   const API_BASE = 'http://127.0.0.1:8000/api';
   
   // To:
   const API_BASE = 'https://ytlearner.onrender.com/api';
   ```

2. **Deploy Frontend Options:**

   **Option A: GitHub Pages**
   ```bash
   # Create gh-pages branch
   git checkout -b gh-pages
   git add frontend/*
   git commit -m "Deploy frontend"
   git push origin gh-pages
   ```
   Access at: `https://yourusername.github.io/YtLearner/frontend/video_summary.html`

   **Option B: Netlify**
   - Drag and drop `frontend/` folder to [netlify.com](https://netlify.com/)
   - Update API_BASE to your Render URL

   **Option C: Vercel**
   - Connect repository to [vercel.com](https://vercel.com/)
   - Set build output to `frontend/`

---

## 🔒 CORS Configuration

If frontend is on different domain, update `backend/app/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourusername.github.io",  # Your frontend URL
        "http://localhost:8000",           # Local development
        "https://ytlearner.netlify.app"    # If using Netlify
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📊 Monitoring & Logs

### Render Logs

1. Go to your service dashboard
2. Click **"Logs"** tab
3. View real-time logs
4. Filter by level: Info, Warning, Error

### Railway Logs

1. Click on your service
2. Go to **"Deployments"** tab
3. Click latest deployment
4. View build and runtime logs

### Common Issues

| Error | Solution |
|-------|----------|
| `GEMINI_API_KEY not set` | Add environment variable in platform dashboard |
| `Module not found` | Check `requirements.txt` has all dependencies |
| `Port already in use` | Use `$PORT` environment variable (auto-set) |
| `CORS error` | Add CORS middleware with your frontend domain |
| `MongoDB connection failed` | Verify `MONGO_URI` format and credentials |

---

## 🚀 Post-Deployment Checklist

- [ ] All environment variables set correctly
- [ ] API endpoints returning 200 OK responses
- [ ] Video metadata loads successfully
- [ ] Summary generation works (may take 15-30s first time)
- [ ] Learning resources API returns course links
- [ ] Quiz generation creates valid questions
- [ ] MongoDB connection established (if using)
- [ ] Frontend updated with production API URL
- [ ] CORS configured for frontend domain
- [ ] Test with multiple video IDs
- [ ] Monitor logs for errors

---

## 🔄 CI/CD Auto-Deployment

### Render
- ✅ Auto-deploys on every `git push` to `main`
- Configure in: Settings → Build & Deploy

### Railway
- ✅ Auto-deploys on every commit
- Configure in: Settings → Triggers

### Manual Deployment
```bash
# Make changes
git add .
git commit -m "Update feature X"
git push origin main

# Platform auto-deploys in 2-5 minutes
```

---

## 💰 Cost Estimation

### Free Tier Limits

**Render (Free):**
- ✅ 750 hours/month
- ✅ Auto-sleeps after 15 min inactivity
- ✅ Cold start: ~30 seconds
- ⚠️ Spins down when idle

**Railway (Free Trial):**
- ✅ $5 free credit
- ✅ ~500 hours with low usage
- ⚠️ Requires credit card after trial

**MongoDB Atlas (Free):**
- ✅ 512 MB storage
- ✅ Shared cluster
- ✅ Perfect for small projects

**API Costs:**
- Gemini API: Pay-per-use (very cheap for Flash model)
- YouTube API: 10,000 free units/day

---

## 🛡️ Security Best Practices

1. **Never commit API keys to Git**
   ```bash
   # Add to .gitignore
   echo ".env" >> .gitignore
   echo "*.env" >> .gitignore
   ```

2. **Rotate API keys periodically**
   - Every 3-6 months
   - Immediately if leaked

3. **Use environment variables**
   - Never hardcode credentials
   - Always use `os.getenv()`

4. **Enable MongoDB authentication**
   - Use strong passwords
   - Restrict IP access when possible

5. **Monitor usage**
   - Check Gemini API quota
   - Check YouTube API quota
   - Set up billing alerts

---

## 📞 Support & Troubleshooting

### Getting Help

1. **Check logs first** - Most errors show in deployment logs
2. **Verify environment variables** - Double-check spelling and values
3. **Test locally first** - Ensure it works on `localhost:8000`
4. **Check API quotas** - You might have hit rate limits

### Useful Commands

```bash
# Test MongoDB connection
mongosh "your_mongo_uri_here"

# Check if port is accessible
curl https://your-app.onrender.com

# View environment variables (Render)
render env list --service your-service-name

# Restart service (Railway)
railway restart
```

---

## 🎉 You're Live!

Your YtLearner app is now deployed and accessible worldwide!

**Example Production URLs:**
- Backend API: `https://ytlearner.onrender.com/api`
- Frontend: `https://yourusername.github.io/YtLearner/frontend/video_summary.html`

**Share your app:**
```
🎓 YtLearner - AI-Powered YouTube Learning
📱 Try it: https://your-frontend-url.com
🚀 Features: Video summaries, quizzes, learning resources
```

---

**Need help?** Check the logs, verify environment variables, and ensure all API keys are valid! 🚀
