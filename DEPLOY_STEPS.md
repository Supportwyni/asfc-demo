# Step-by-Step Vercel Deployment

## Prerequisites (Do These First)

### 1. Make Sure PDFs Are Uploaded to Database
```bash
# Run backend locally
python backend/start.py

# Open http://localhost:5173 in browser
# Go to admin panel (⚙️ icon)
# Upload your PDFs
# Wait for processing to complete
```

This creates chunks in your Supabase database that the AI will use.

### 2. Install Vercel CLI (If Not Already Installed)
```bash
npm install -g vercel
```

## Deployment Steps

### Step 1: Login to Vercel
```bash
vercel login
```

Choose your login method (GitHub, Email, etc.)

### Step 2: Navigate to Project Root
```bash
cd "C:\Users\Albert\Documents\Wyni Technology\ASFC\ASFC-training-model"
```

### Step 3: Deploy to Vercel
```bash
vercel
```

### Step 4: Answer Vercel's Questions

**Q: Set up and deploy?**
→ Answer: `Y` (Yes)

**Q: Which scope?**
→ Choose your account/team

**Q: Link to existing project?**
→ Answer: `N` (No, create new) - Unless you have an existing project

**Q: What's your project's name?**
→ Answer: `asfc-chat` (or any name you want)

**Q: In which directory is your code located?**
→ Answer: `./` (just press Enter for root)

Vercel will:
- Detect the configuration
- Build the frontend
- Deploy serverless functions

### Step 5: Add Environment Variables

After deployment, you'll see:
```
✅ Deployed to production: https://your-app.vercel.app
```

Now add environment variables:

**Option A: Via Web Dashboard (Easier)**
1. Go to https://vercel.com/dashboard
2. Click your project
3. Go to **Settings** → **Environment Variables**
4. Add these variables:

```
SUPABASE_URL = https://vumnlugtiwjamyrkbuuc.supabase.co
SUPABASE_KEY = [your anon key]
SUPABASE_SERVICE_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ1bW5sdWd0aXdqYW15cmtidXVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzQ2ODExMywiZXhwIjoyMDc5MDQ0MTEzfQ.0by-Gp_k2SJx-EUPoU4VzLg8YML0aBdJGT62Z9Oc4bs
OPENROUTER_API_KEY = [your OpenRouter key]
ALLOWED_ORIGINS = *
```

5. Click **Save**

**Option B: Via CLI**
```bash
vercel env add SUPABASE_URL
# Paste your Supabase URL, press Enter

vercel env add SUPABASE_KEY
# Paste your anon key, press Enter

vercel env add SUPABASE_SERVICE_KEY
# Paste your service key, press Enter

vercel env add OPENROUTER_API_KEY
# Paste your OpenRouter key, press Enter

vercel env add ALLOWED_ORIGINS
# Type: *
```

### Step 6: Redeploy with Environment Variables
```bash
vercel --prod
```

This redeploys with the environment variables.

### Step 7: Test Your Deployment

Visit your URL: `https://your-app.vercel.app`

**Test Chat:**
1. Type a question about your aviation documents
2. Press Send
3. Should get AI response based on your PDF chunks

**Test Admin (View Only):**
1. Click ⚙️ icon (top right)
2. Click "View Uploaded PDFs"
3. Should see your uploaded PDFs

**Upload won't work** on Vercel (that's expected - need Railway for that)

## Troubleshooting

### If Chat Doesn't Work:

**Check 1: Environment Variables**
```bash
vercel env ls
```

Should show all 4-5 variables.

**Check 2: Logs**
```bash
vercel logs
```

Shows error messages.

**Check 3: Functions**
Go to Vercel Dashboard → Your Project → Functions
Should show:
- `/api/chat`
- `/api/files`
- `/api/health`

### If "Connection Error":

- Environment variables missing
- Supabase credentials wrong
- OpenRouter API key invalid

## Quick Commands Reference

```bash
# Deploy
vercel

# Deploy to production
vercel --prod

# View logs
vercel logs

# List environment variables
vercel env ls

# Remove deployment
vercel remove
```

## Success Checklist

- [ ] `vercel login` completed
- [ ] `vercel` deployment successful
- [ ] Environment variables added
- [ ] `vercel --prod` redeployed
- [ ] Website loads at Vercel URL
- [ ] Chat responds to questions
- [ ] Admin panel shows PDFs

## Next Steps After Deployment

1. **Custom Domain** (Optional):
   - Vercel Dashboard → Domains
   - Add your custom domain

2. **Railway Backend** (For uploads):
   - Deploy backend to Railway
   - Upload PDFs there
   - Chunks sync to Supabase
   - Vercel chat uses those chunks

## That's It!

Your chat app with AI + PDF knowledge is now live on Vercel! 🚀

Any errors? Run `vercel logs` and check what's wrong.



