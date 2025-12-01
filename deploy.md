# YtLearner API - Deployment Guide

This guide covers deploying the YtLearner API backend to popular cloud platforms with free tiers.

## Table of Contents
- [Render Deployment](#render-deployment)
- [Railway Deployment](#railway-deployment)
- [Environment Variables](#environment-variables)
- [Free Tier Limits](#free-tier-limits)
- [Post-Deployment Testing](#post-deployment-testing)

---

## Render Deployment

[Render](https://render.com) offers a free tier with 750 hours/month for web services.

### Step-by-Step Instructions

1. **Create Account**
   - Sign up at [render.com](https://render.com)
   - Connect your GitHub account

2. **Push Code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/ytlearner.git
   git push -u origin main
   ```

3. **Create New Web Service**
   - Go to Render Dashboard
   - Click "New +" → "Web Service"
   - Connect your repository
   - Select `ytlearner` repository

4. **Configure Service**
   - **Name**: `ytlearner-api` (or your preferred name)
   - **Environment**: `Python 3`
   - **Region**: Choose closest to your users
   - **Branch**: `main`
   - **Root Directory**: Leave empty (or `backend` if you restructure)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: 
     ```
     uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
     ```

5. **Set Environment Variables**
   - Click "Environment" tab
   - Add variables (see [Environment Variables](#environment-variables) section):
     - `YOUTUBE_API_KEY` (required)
     - `GEMINI_API_KEY` (optional, recommended)
     - `MONGO_URI` (optional)
     - `GEMINI_MODEL` (optional, default: `gemini-2.5-flash`)

6. **Deploy**
   - Click "Create Web Service"
   - Wait 5-10 minutes for initial deployment
   - Your API will be live at `https://ytlearner-api.onrender.com`

### Render Considerations

- **Free Tier Spins Down**: After 15 minutes of inactivity, the service goes to sleep
- **Cold Start**: First request after sleep takes 30-60 seconds
- **Auto-Deploy**: Automatically redeploys on git push
- **Custom Domain**: Can add custom domain even on free tier

---

## Railway Deployment

[Railway](https://railway.app) offers $5 free credits per month (approx. 500 hours).

### Step-by-Step Instructions

1. **Create Account**
   - Sign up at [railway.app](https://railway.app)
   - Connect GitHub account

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `ytlearner` repository

3. **Add Procfile** (recommended)
   Create `Procfile` at project root:
   ```
   web: uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
   ```

4. **Configure Service**
   - Railway auto-detects Python
   - It will automatically install from `requirements.txt`
   - The Procfile defines the start command

5. **Set Environment Variables**
   - Go to "Variables" tab
   - Add variables (see [Environment Variables](#environment-variables)):
     - `YOUTUBE_API_KEY` (required)
     - `GEMINI_API_KEY` (optional, recommended)
     - `MONGO_URI` (optional)
     - `GEMINI_MODEL` (optional)
     - `PORT` (Railway sets this automatically)

6. **Deploy**
   - Railway deploys automatically
   - Your API will be live at `https://ytlearner-production.up.railway.app`

### Railway Considerations

- **Always On**: No cold starts on Railway
- **Credits**: $5/month free, then pay-as-you-go
- **Auto-Deploy**: Redeploys on git push
- **Custom Domain**: Available on free tier

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `YOUTUBE_API_KEY` | YouTube Data API v3 key from [Google Cloud Console](https://console.cloud.google.com/) | `AIzaSyC9x...` |

### Optional Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `GEMINI_API_KEY` | Google Gemini API key for AI summaries/quizzes | None (uses fallback) | `AIzaSyA0I_...` |
| `GEMINI_MODEL` | Gemini model to use | `gemini-2.5-flash` | `gemini-2.0-flash-exp` |
| `MONGO_URI` | MongoDB connection string for caching | In-memory cache | `mongodb+srv://user:pass@cluster.mongodb.net/ytlearner` |

### How to Get API Keys

**YouTube API Key:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project
3. Enable "YouTube Data API v3"
4. Create credentials → API Key
5. (Optional) Restrict key to YouTube Data API v3

**Gemini API Key:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key

**MongoDB (Optional):**
1. Sign up at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create free cluster (M0)
3. Create database user
4. Get connection string
5. Replace `<password>` with your password

### Security Best Practices

⚠️ **NEVER commit API keys to Git!**

- Use environment variables only
- Add `.env` to `.gitignore`
- Rotate keys if accidentally exposed
- Set up API key restrictions in Google Cloud Console

---

## Free Tier Limits

### Render Free Tier
- **Hours**: 750 hours/month
- **Memory**: 512 MB RAM
- **Disk**: Shared
- **Sleep**: After 15 min inactivity
- **Build Time**: 15 minutes max
- **Bandwidth**: Shared

### Railway Free Tier
- **Credits**: $5/month (~500 hours)
- **Memory**: 512 MB RAM
- **Disk**: 1 GB
- **Sleep**: Never (always on)
- **Build Time**: No limit
- **Bandwidth**: No limit on free tier

### YouTube API Limits
- **Quota**: 10,000 units/day (free)
- **Search**: ~100 searches/day
- **Video Details**: ~10,000 requests/day
- **Rate Limit**: 100 requests/100 seconds/user

### Gemini API Limits (Free Tier)
- **Requests**: 15 requests/min
- **Tokens**: 1M tokens/min
- **Daily**: 1,500 requests/day

### MongoDB Atlas Free Tier
- **Storage**: 512 MB
- **RAM**: Shared
- **Connections**: 500 concurrent
- **Bandwidth**: No limit

---

## Post-Deployment Testing

### 1. Test Health Endpoint
```bash
curl https://your-app.onrender.com/
```

Expected response:
```json
{
  "message": "Welcome to YtLearner API",
  "version": "1.0.0",
  "docs": "/docs",
  "openapi": "/openapi.json"
}
```

### 2. Test API Documentation
Visit: `https://your-app.onrender.com/docs`

You should see the interactive Swagger UI.

### 3. Test Search Endpoint
```bash
curl "https://your-app.onrender.com/api/search?q=python&maxResults=5"
```

### 4. Export OpenAPI Spec
```bash
curl https://your-app.onrender.com/export-openapi
```

### 5. Use Postman Collection
1. Import `postman_collection.json` into Postman
2. Update `base_url` variable to your deployed URL
3. Run requests to test all endpoints

### 6. Test with Frontend
Update frontend files to use your deployed URL:
```javascript
const API_BASE = 'https://your-app.onrender.com/api';
```

---

## Troubleshooting

### Build Fails
- **Check Python version**: Ensure `runtime.txt` specifies `python-3.11` or later
- **Missing dependencies**: Verify all packages in `requirements.txt`
- **Import errors**: Check relative imports in backend code

### Service Won't Start
- **Check logs**: View deployment logs in Render/Railway dashboard
- **Port binding**: Ensure using `--host 0.0.0.0 --port $PORT`
- **Environment variables**: Verify `YOUTUBE_API_KEY` is set

### API Returns Errors
- **YouTube quota exceeded**: Check usage in Google Cloud Console
- **Gemini API errors**: Verify API key is valid and not rate-limited
- **MongoDB connection**: Check URI format and network access settings

### Cold Starts (Render Free Tier)
- First request after sleep takes 30-60 seconds
- Keep service warm with periodic pings:
  ```bash
  */10 * * * * curl https://your-app.onrender.com/
  ```
- Consider upgrading to paid tier for production

---

## Next Steps

1. **Custom Domain**: Add your own domain in platform settings
2. **Monitoring**: Set up uptime monitoring (e.g., UptimeRobot)
3. **Analytics**: Add application monitoring (e.g., Sentry)
4. **HTTPS**: Automatically enabled on Render and Railway
5. **CI/CD**: Auto-deploys on git push to main branch

---

## Support Resources

- **Render Docs**: https://render.com/docs
- **Railway Docs**: https://docs.railway.app
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/
- **YouTube API**: https://developers.google.com/youtube/v3
- **Gemini API**: https://ai.google.dev/docs

---

## Cost Estimates (Paid Tiers)

If you exceed free tier limits:

### Render Pricing
- **Starter**: $7/month (no sleep, 512 MB)
- **Standard**: $25/month (1 GB RAM)

### Railway Pricing
- **Pay as you go**: $0.000231/GB-hour (~$5-10/month for small apps)

### MongoDB Atlas
- **M2**: $9/month (2 GB storage)
- **M5**: $25/month (5 GB storage)

Choose based on your traffic and requirements.
