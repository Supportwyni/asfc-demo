# Vercel Deployment Guide

## Quick Deploy to Vercel

### 1. Frontend Deployment (Vercel)

```bash
cd frontend
vercel
```

Or connect your GitHub repository to Vercel for automatic deployments.

### 2. Backend Deployment Options

**Option A: Railway (Recommended)**
1. Go to [railway.app](https://railway.app)
2. Create new project
3. Deploy from GitHub
4. Add environment variables
5. Railway will auto-detect Flask app

**Option B: Render**
1. Go to [render.com](https://render.com)
2. Create new Web Service
3. Connect GitHub repo
4. Build command: `pip install -r backend/requirements.txt`
5. Start command: `cd backend && python start.py`

**Option C: Fly.io**
1. Install flyctl CLI
2. Run `fly launch` in backend directory
3. Configure and deploy

### 3. Environment Variables

**Frontend (.env in Vercel)**
```env
VITE_API_URL=https://your-backend-url.railway.app/api
```

**Backend (in Railway/Render/Fly.io)**
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
OPENROUTER_API_KEY=your-openrouter-key
ALLOWED_ORIGINS=https://your-app.vercel.app,http://localhost:5173
```

### 4. Vercel Configuration

The `vercel.json` is already configured:
- Builds frontend from `frontend/` directory
- Serves static files from `frontend/dist`
- Handles SPA routing

### 5. CORS Configuration

Update `ALLOWED_ORIGINS` in your backend environment to include:
```
https://your-app.vercel.app
```

### 6. Database Setup

1. Go to Supabase dashboard
2. Run SQL from `backend/database/schema.sql`
3. Create storage bucket named `pdf`
4. Set bucket to private (signed URLs will handle access)

## Deployment Checklist

- [ ] Frontend environment variables set in Vercel
- [ ] Backend deployed to Railway/Render/Fly.io
- [ ] Backend environment variables configured
- [ ] Supabase database schema created
- [ ] Supabase storage bucket `pdf` created
- [ ] CORS origins updated in backend
- [ ] Frontend `VITE_API_URL` points to backend
- [ ] Test upload functionality
- [ ] Test chat functionality
- [ ] Test PDF viewing with signed URLs

## Testing Deployment

1. **Test Chat**: Ask a question
2. **Test Upload**: Upload a PDF file
3. **Test Admin**: View uploaded PDFs
4. **Test Delete**: Select and delete a PDF
5. **Check Logs**: Monitor backend logs for errors

## Troubleshooting

### CORS Errors
- Add your Vercel domain to `ALLOWED_ORIGINS`
- Restart backend after changing environment variables

### PDF Upload Fails
- Check Supabase bucket name is `pdf`
- Verify `SUPABASE_SERVICE_KEY` is set
- Check backend logs for errors

### PDFs Don't Load
- Verify signed URLs are being generated
- Check storage bucket permissions
- Ensure service key has storage access

### Backend Not Responding
- Check backend is running
- Verify `VITE_API_URL` in frontend matches backend URL
- Check CORS configuration

## Monitoring

- **Frontend**: Vercel dashboard shows build logs
- **Backend**: Railway/Render dashboard shows runtime logs
- **Database**: Supabase dashboard shows queries and storage

## Updating

**Frontend**:
```bash
cd frontend
git push  # If connected to GitHub, Vercel auto-deploys
# Or: vercel --prod
```

**Backend**:
```bash
git push  # Railway/Render auto-deploys
# Or redeploy from dashboard
```



