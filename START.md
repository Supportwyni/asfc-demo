# How to Start the ASFC App Locally

## Quick Start (3 Steps)

### Step 1: Start Backend Server

Open a terminal:

```bash
cd backend
python start.py
```

You should see:
```
Starting ASFC API server on http://localhost:5000
 * Running on http://127.0.0.1:5000
```

**Keep this terminal open!**

### Step 2: Start Frontend (New Terminal)

Open a **NEW** terminal:

```bash
cd frontend
npm install
npm run dev
```

You should see:
```
  VITE v7.x.x  ready in XXX ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

### Step 3: Open in Browser

Go to: **http://localhost:5173**

## What You Should See

1. **Chat interface** with "AFSC Aviation Chat Assistant" title
2. **Input box** at the bottom to ask questions
3. **Admin button** (⚙️) in the top-right corner

## Testing the App

### Test Chat:
1. Type a question: "What is fuel quality requirement?"
2. Press **Send** or **Enter**
3. AI should respond based on your PDFs

### Test Admin Panel:
1. Click **⚙️** icon (top-right)
2. Admin panel opens with:
   - **View Uploaded PDFs** button
   - **Upload New PDF** section
3. Click "View Uploaded PDFs" to see your documents
4. Select PDFs and delete them

## Troubleshooting

### Backend won't start:

**Error: ModuleNotFoundError**
```bash
# Install dependencies
cd backend
pip install -r requirements.txt
```

**Error: Missing .env file**
Create `.env` file in project root:
```env
SUPABASE_URL=https://vumnlugtiwjamyrkbuuc.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
OPENROUTER_API_KEY=your-openrouter-key
```

### Frontend won't start:

**Error: command not found: npm**
- Install Node.js from https://nodejs.org

**Error: Cannot find module**
```bash
cd frontend
npm install
npm run dev
```

### Chat says "Backend not connected":

- Make sure backend is running on http://localhost:5000
- Check backend terminal for errors
- Try restarting backend

### PDFs not showing:

- Check Supabase dashboard for data
- Make sure you uploaded PDFs first
- Check backend console for errors

## Port Already in Use?

**If port 5000 is busy:**
Edit `backend/api.py` at the bottom:
```python
app.run(debug=True, port=5001)  # Change to 5001
```

**If port 5173 is busy:**
Frontend will auto-use next available port (5174, 5175, etc.)

## Stopping the App

**In each terminal:**
- Press `Ctrl + C` (Windows/Linux)
- Press `Cmd + C` (Mac)

## Full Command Reference

```bash
# Backend
cd backend
python start.py

# Frontend (new terminal)
cd frontend
npm install       # First time only
npm run dev       # Every time
```

## Next Steps

Once running locally:
1. Upload PDFs via admin panel
2. Test chat with questions
3. Then deploy to Vercel (follow DEPLOY_MANUAL.md)

