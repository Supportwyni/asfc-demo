# Manual Deployment to Vercel (No CLI Needed)

## Step 1: Prepare Your Code (Local)

### A. Make Sure PDFs Are Uploaded First
```bash
# Run backend locally
python backend/start.py

# Open http://localhost:5173
# Upload your PDFs via admin panel
# This creates chunks in Supabase database
```

### B. Push Code to GitHub

```bash
# Initialize git (if not already)
git init

# Add all files
git add .

# Commit
git commit -m "Ready for Vercel deployment"

# Create GitHub repo and push
git remote add origin https://github.com/your-username/asfc-chat.git
git branch -M main
git push -u origin main
```

## Step 2: Deploy via Vercel Dashboard

### A. Go to Vercel
1. Open browser: https://vercel.com
2. Click **"Sign Up"** or **"Log In"**
3. Choose **"Continue with GitHub"**

### B. Import Project
1. Click **"Add New..."** → **"Project"**
2. Find your GitHub repository in the list
3. Click **"Import"**

### C. Configure Project

**Framework Preset:**
- Vercel should auto-detect "Vite"
- If not, select **"Vite"** from dropdown

**Root Directory:**
- Leave as `./` (root)

**Build Settings:**
- **Build Command**: `cd frontend && npm install && npm run build`
- **Output Directory**: `frontend/dist`
- **Install Command**: `npm install`

### D. Add Environment Variables

Click **"Environment Variables"** section:

Add these one by one:

**Variable 1:**
- Name: `SUPABASE_URL`
- Value: `https://vumnlugtiwjamyrkbuuc.supabase.co`
- Environment: Check all (Production, Preview, Development)

**Variable 2:**
- Name: `SUPABASE_KEY`
- Value: Your Supabase anon key (from Supabase dashboard)
- Environment: Check all

**Variable 3:**
- Name: `SUPABASE_SERVICE_KEY`
- Value: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ1bW5sdWd0aXdqYW15cmtidXVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzQ2ODExMywiZXhwIjoyMDc5MDQ0MTEzfQ.0by-Gp_k2SJx-EUPoU4VzLg8YML0aBdJGT62Z9Oc4bs`
- Environment: Check all

**Variable 4:**
- Name: `OPENROUTER_API_KEY`
- Value: Your OpenRouter API key
- Environment: Check all

**Variable 5:**
- Name: `ALLOWED_ORIGINS`
- Value: `*`
- Environment: Check all

### E. Deploy
1. Click **"Deploy"** button
2. Wait 2-3 minutes for build
3. You'll see build logs in real-time

## Step 3: After Deployment

### A. Get Your URL
After successful deployment:
- You'll see: ✅ **Deployed to Production**
- URL: `https://your-project-name.vercel.app`
- Click **"Visit"** to open your app

### B. Test
1. **Open the URL** in browser
2. **Type a question** in chat
3. **Check if AI responds** with answers from your PDFs
4. **Click admin button** (⚙️) to see uploaded PDFs

## Step 4: If Something Goes Wrong

### Check Build Logs
1. Go to Vercel Dashboard
2. Click your project
3. Click **"Deployments"** tab
4. Click latest deployment
5. Look at **"Build Logs"** and **"Function Logs"**

### Common Issues

**Issue: "Failed to build"**
- Check `vercel.json` is in root
- Check `frontend/package.json` exists
- Look at build logs for specific error

**Issue: "Chat not working"**
- Check environment variables are set
- Go to Settings → Environment Variables
- Make sure all 5 variables are there
- Redeploy if you added variables after initial deploy

**Issue: "Connection Error"**
- API endpoints not working
- Check Functions tab in Vercel
- Should show `/api/chat`, `/api/files`, `/api/health`
- If missing, check `api/` folder exists with Python files

**Issue: "No PDFs showing in admin"**
- This is expected if no PDFs in database yet
- Upload PDFs locally first OR
- Deploy backend to Railway for uploads

### Force Redeploy
1. Go to Vercel Dashboard
2. Click your project
3. Click **"Deployments"**
4. Click **"..." menu** on latest deployment
5. Click **"Redeploy"**

## Step 5: Update Later

### When You Change Code:
1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Updated features"
   git push
   ```

2. **Vercel auto-deploys** (if connected to GitHub)
   - No manual action needed
   - Check Deployments tab to see progress

### When You Add Environment Variable:
1. Go to Settings → Environment Variables
2. Add new variable
3. Must redeploy for changes to take effect

## Complete Workflow Summary

```
1. Upload PDFs locally → Creates chunks in Supabase
2. Push code to GitHub
3. Import project on Vercel
4. Configure build settings
5. Add environment variables
6. Deploy
7. Visit URL and test chat
```

## What You Get

✅ **Live URL**: `https://your-app.vercel.app`
✅ **Chat works**: Ask questions, get AI answers from PDFs
✅ **View PDFs**: Can see uploaded PDFs in admin
✅ **Auto-deploy**: Push to GitHub = auto redeploy
❌ **Upload PDFs**: Disabled (use Railway backend for this)

## Need Help?

- **Vercel Docs**: https://vercel.com/docs
- **Vercel Support**: https://vercel.com/support
- **Check logs**: `vercel logs` (if using CLI)
- **Dashboard logs**: Project → Deployments → Click deployment → Logs

---

## Alternative: No GitHub Method

If you don't want to use GitHub:

```bash
# Just use CLI directly
vercel

# Follow prompts
# Uploads code directly from your computer
```

This uploads directly without GitHub.



