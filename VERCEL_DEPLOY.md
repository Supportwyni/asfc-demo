# Deploy to Vercel - Quick Guide

## Frontend Deployment (1 Minute)

### Option 1: Deploy via Vercel Dashboard (Easiest)

1. Go to [vercel.com](https://vercel.com)
2. Click "Add New Project"
3. Import your GitHub repository
4. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Add environment variable:
   - `VITE_API_URL` = `https://your-backend-url.railway.app/api`
6. Click "Deploy"

### Option 2: Deploy via CLI

```bash
cd frontend
npm install -g vercel
vercel login
vercel
```

Follow prompts and deploy.

## Backend Deployment (Railway - 2 Minutes)

### Why Not Vercel for Backend?

Vercel serverless functions have 10-second timeout limits. Since PDF processing can take longer, we use Railway instead.

### Deploy Backend to Railway:

1. Go to [railway.app](https://railway.app)
2. Sign in with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway auto-detects Python app
6. Add environment variables:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   SUPABASE_SERVICE_KEY=your-service-role-key
   OPENROUTER_API_KEY=your-openrouter-key
   ALLOWED_ORIGINS=https://your-app.vercel.app
   ```
7. Railway generates a public URL (e.g., `https://xxx.railway.app`)
8. Copy this URL

### Update Frontend:

Go to Vercel dashboard → Your project → Settings → Environment Variables:
- Add: `VITE_API_URL` = `https://xxx.railway.app/api`
- Redeploy frontend

## Final Steps

1. **Test the deployment**:
   - Visit your Vercel URL
   - Try uploading a PDF
   - Try chatting
   - Check admin panel

2. **Update CORS** if needed:
   - Add your Vercel URL to backend's `ALLOWED_ORIGINS`
   - Redeploy backend on Railway

## Project Structure for Deployment

```
ASFC-training-model/
├── frontend/          ← Deployed to Vercel
│   ├── src/
│   ├── index.html
│   └── package.json
├── backend/           ← Deployed to Railway
│   ├── api.py
│   ├── start.py
│   └── requirements.txt
├── vercel.json        ← Vercel config (frontend)
└── .vercelignore      ← Excludes backend from Vercel
```

## Commands Summary

```bash
# Deploy frontend
cd frontend && vercel --prod

# No command needed for backend - Railway auto-deploys on git push
```

## That's It!

Your app is now live:
- Frontend: `https://your-app.vercel.app`
- Backend: `https://xxx.railway.app`



