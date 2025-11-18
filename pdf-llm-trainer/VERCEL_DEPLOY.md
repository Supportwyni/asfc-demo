# Deploy to Vercel - Step by Step Guide

## Quick Deploy (Recommended)

1. **Go to Vercel Dashboard**
   - Visit: https://vercel.com/dashboard
   - Sign in with GitHub

2. **Add New Project**
   - Click "Add New..." button
   - Select "Project"
   - Click "Import Git Repository"
   - Select your repository: `Supportwyni/ASFC-demo` (or your repo name)

3. **Configure Project**
   - **Framework Preset**: Select "Vite" (or leave as "Other")
   - **Root Directory**: Click "Edit" and set to: `pdf-llm-trainer/frontend`
   - **Build Command**: `npm run build` (should auto-detect)
   - **Output Directory**: `dist` (should auto-detect)
   - **Install Command**: `npm ci` (should auto-detect)

4. **Environment Variables** (Optional for now)
   - You can add these later if needed:
     - `VITE_API_URL` = Your backend API URL

5. **Deploy**
   - Click "Deploy"
   - Wait for build to complete (1-2 minutes)

6. **Done!**
   - Your app will be live at: `https://your-project.vercel.app`

## If You Already Have a Project

1. **Go to Project Settings**
   - Vercel Dashboard → Your Project → Settings → General

2. **Set Root Directory**
   - Find "Root Directory" section
   - Click "Edit"
   - Enter: `pdf-llm-trainer/frontend`
   - Click "Save"

3. **Redeploy**
   - Go to "Deployments" tab
   - Click "..." on latest deployment
   - Click "Redeploy"

## Troubleshooting

### 404 Error
- Make sure Root Directory is set to: `pdf-llm-trainer/frontend`
- Check build logs for errors
- Verify `dist` folder is created during build

### Build Fails
- Check that TypeScript is installed: `npm install -D typescript`
- Verify all dependencies are in `package.json`
- Check build logs in Vercel dashboard

### Can't Find Root Directory Setting
- Try re-importing the project (delete and re-add)
- Root Directory appears during project import/configuration

