# Environment Variables Setup Guide

## ⚠️ Important: Two Separate Deployments Need Different Variables

### Frontend (Vercel) - Only Needs:
- `VITE_API_URL` = Your backend URL (e.g., `https://your-backend.railway.app/api`)

**That's it!** The frontend only needs to know where the backend is.

### Backend (Railway/Render/Fly.io) - Needs All These:

#### Database & API Keys:
- `SUPABASE_URL` = Your Supabase project URL
- `SUPABASE_KEY` = Your Supabase API key (anon key)
- `OPENROUTER_API_KEY` = Your OpenRouter API key
- `OPENROUTER_MODEL` = `qwen/qwen-2.5-72b-instruct:free`

#### CORS & Deployment:
- `ALLOWED_ORIGINS` = Your Vercel frontend URL (e.g., `https://your-app.vercel.app`)
- `PORT` = Usually auto-set by platform (don't set manually)
- `FLASK_ENV` = `production` (optional)

## Step-by-Step Setup

### Step 1: Deploy Backend First

**In Railway/Render/Fly.io**, add these environment variables:

```
SUPABASE_URL=https://vumnlugtiwjamyrkbuuc.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
OPENROUTER_API_KEY=your-openrouter-key
OPENROUTER_MODEL=qwen/qwen-2.5-72b-instruct:free
ALLOWED_ORIGINS=https://your-app.vercel.app
FLASK_ENV=production
```

**Get your backend URL** (e.g., `https://your-backend.railway.app`)

### Step 2: Configure Frontend

**In Vercel Dashboard:**
1. Go to your project → **Settings** → **Environment Variables**
2. Add **ONLY**:
   ```
   VITE_API_URL = https://your-backend.railway.app/api
   ```
3. **Redeploy** frontend

## ❌ Common Mistakes

### ❌ DON'T Put Backend Variables in Vercel
- Vercel can't use `SUPABASE_URL`, `OPENROUTER_API_KEY`, etc.
- These are backend-only variables
- Putting them in Vercel does nothing

### ❌ DON'T Put Frontend Variables in Backend
- Backend doesn't need `VITE_API_URL`
- That's only for the frontend build process

### ✅ DO Split Them Correctly
- **Frontend (Vercel)**: Only `VITE_API_URL`
- **Backend (Railway)**: All the API keys and database URLs

## How It Works

```
┌─────────────────┐         ┌──────────────────┐
│   Frontend      │         │    Backend       │
│   (Vercel)      │────────▶│  (Railway/etc)   │
│                 │         │                  │
│ VITE_API_URL    │         │ SUPABASE_URL     │
│ (points to      │         │ SUPABASE_KEY     │
│  backend)       │         │ OPENROUTER_KEY   │
│                 │         │ etc...           │
└─────────────────┘         └──────────────────┘
```

The frontend uses `VITE_API_URL` to make API calls to your backend.
The backend uses its own variables to connect to Supabase and OpenRouter.

## Testing

After setup:
1. **Backend health check**: `https://your-backend.railway.app/api/health`
2. **Frontend**: Should connect to backend automatically
3. **Check browser console**: Should see API calls to your backend URL

