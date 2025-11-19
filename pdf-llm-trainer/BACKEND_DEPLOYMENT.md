# Backend Deployment Guide

## Important: Vercel Only Hosts Frontend

**Vercel is a static hosting platform** - it can only serve your frontend files (HTML, CSS, JS). It **cannot** run your Python Flask backend.

Your backend needs to be deployed separately to a platform that supports Python applications.

## Quick Deploy Options

### Option 1: Railway (Recommended - Easiest)

1. **Go to Railway**: https://railway.app
2. **Sign in** with GitHub
3. **New Project** → **Deploy from GitHub repo**
4. **Select your repository**
5. **Set Root Directory**: `pdf-llm-trainer/backend`
6. **Add Environment Variables**:
   - `ALLOWED_ORIGINS` = Your Vercel frontend URL (e.g., `https://your-app.vercel.app`)
   - `SUPABASE_URL` = Your Supabase URL
   - `SUPABASE_KEY` = Your Supabase API key
   - `OPENROUTER_API_KEY` = Your OpenRouter API key
   - `OPENROUTER_MODEL` = `qwen/qwen-2.5-72b-instruct:free`
7. **Deploy** - Railway auto-detects Python and runs `python -m backend.start`
8. **Get your backend URL**: `https://your-project.railway.app`

### Option 2: Render

1. **Go to Render**: https://render.com
2. **New** → **Web Service**
3. **Connect GitHub** → Select your repo
4. **Settings**:
   - **Root Directory**: `pdf-llm-trainer/backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m backend.start`
   - **Environment**: Python 3
5. **Add Environment Variables** (same as Railway)
6. **Deploy**

### Option 3: Fly.io

1. **Install Fly CLI**: `curl -L https://fly.io/install.sh | sh`
2. **Login**: `fly auth login`
3. **In backend directory**: `cd pdf-llm-trainer/backend`
4. **Launch**: `fly launch`
5. **Set secrets**: `fly secrets set ALLOWED_ORIGINS=https://your-app.vercel.app`
6. **Deploy**: `fly deploy`

## After Backend Deployment

### Step 1: Get Backend URL
- Railway: `https://your-project.railway.app`
- Render: `https://your-service.onrender.com`
- Fly.io: `https://your-app.fly.dev`

### Step 2: Update Frontend Environment Variable

**In Vercel Dashboard:**
1. Go to your project → **Settings** → **Environment Variables**
2. Add: `VITE_API_URL` = `https://your-backend-url.com/api`
3. **Redeploy** frontend

### Step 3: Update Backend CORS

Make sure your backend's `ALLOWED_ORIGINS` includes your Vercel frontend URL:
```
ALLOWED_ORIGINS=https://your-app.vercel.app,http://localhost:5173
```

## Environment Variables Needed

### Backend (Railway/Render/Fly.io):
- `ALLOWED_ORIGINS` - Your Vercel frontend URL
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase API key
- `OPENROUTER_API_KEY` - Your OpenRouter API key
- `OPENROUTER_MODEL` - `qwen/qwen-2.5-72b-instruct:free`
- `PORT` - Usually auto-set by platform
- `FLASK_ENV` - `production`

### Frontend (Vercel):
- `VITE_API_URL` - Your backend URL (e.g., `https://your-backend.railway.app/api`)

## Testing

After deployment:
1. Backend should be accessible at: `https://your-backend-url.com/api/health`
2. Frontend should connect to backend automatically
3. Check browser console for any CORS errors

## Troubleshooting

**Backend not starting:**
- Check logs in Railway/Render dashboard
- Verify `requirements.txt` has all dependencies
- Check `PORT` environment variable is set

**CORS errors:**
- Make sure `ALLOWED_ORIGINS` includes your Vercel URL
- Check backend logs for CORS rejection messages

**Frontend can't connect:**
- Verify `VITE_API_URL` is set in Vercel
- Check backend URL is correct
- Test backend health endpoint directly

