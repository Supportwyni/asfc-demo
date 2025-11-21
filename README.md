# ASFC Aviation Chat Assistant

An AI-powered chat assistant for aviation documentation with PDF upload, processing, and RAG (Retrieval-Augmented Generation) capabilities.

## Features

- **Chat Interface**: Ask questions about aviation documents
- **PDF Upload & Processing**: Upload PDFs, extract text, create searchable chunks
- **Admin Panel**: Manage uploaded PDFs with selection and bulk delete
- **RAG System**: Retrieves relevant document chunks to answer questions
- **Supabase Integration**: Database storage with embeddings and file storage
- **Signed URLs**: Secure file access for private storage buckets

## Project Structure

```
ASFC-training-model/
├── frontend/               # Vite + TypeScript frontend
│   ├── src/
│   │   ├── main.ts        # Main application logic
│   │   ├── style.css      # Main styles
│   │   └── selection-styles.css  # PDF selection UI
│   ├── index.html
│   └── package.json
├── backend/               # Flask API backend
│   ├── api.py            # Main API endpoints
│   ├── rag.py            # RAG implementation
│   ├── pdf_processor.py  # PDF processing logic
│   ├── embeddings.py     # Embedding generation
│   ├── config.py         # Backend configuration
│   ├── start.py          # Backend server startup
│   ├── database/         # Database layer
│   │   ├── client.py     # Supabase client
│   │   ├── config.py     # Database configuration
│   │   ├── models.py     # Data models
│   │   ├── repository.py # Database operations
│   │   └── schema.sql    # Database schema
│   └── requirements.txt
└── data/
    └── chunks/           # Processed PDF chunks (JSONL)
```

## Setup Instructions

### 1. Environment Variables

Create a `.env` file in the project root:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# OpenRouter API (for LLM)
OPENROUTER_API_KEY=your-openrouter-key

# Optional
ALLOWED_ORIGINS=http://localhost:5173,https://your-vercel-app.vercel.app
```

### 2. Database Setup

Run the schema SQL in your Supabase SQL editor:

```bash
# The schema file is at: backend/database/schema.sql
```

This creates:
- `pdf_documents` table
- `chunks` table with embeddings
- `chat_history` table

### 3. Backend Setup

```bash
cd backend
pip install -r requirements.txt
python start.py
```

Backend runs on `http://localhost:5000`

### 4. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`

## Deployment to Vercel

### Prerequisites
- Vercel account
- Supabase project set up
- Environment variables configured

### Steps

1. **Install Vercel CLI** (optional):
```bash
npm install -g vercel
```

2. **Configure Environment Variables** in Vercel Dashboard:
   - Go to your project settings
   - Add all variables from `.env` file
   - Include `ALLOWED_ORIGINS` with your Vercel domain

3. **Deploy Frontend**:
```bash
cd frontend
vercel
```

4. **Deploy Backend Separately**:
   - Backend needs to be deployed to a Python hosting service (Railway, Render, Fly.io)
   - Or use Vercel serverless functions (requires restructuring)
   - Update `VITE_API_URL` in frontend to point to your backend URL

5. **Update CORS**:
   - Add your Vercel frontend URL to `ALLOWED_ORIGINS` in backend

## API Endpoints

### Chat
- `POST /api/chat` - Send a question, get AI response
- `GET /api/chat/history` - Load chat history
- `POST /api/chat/history` - Save chat messages

### File Management
- `POST /api/upload` - Upload PDF file
- `GET /api/files` - List all uploaded PDFs
- `GET /api/files/<id>/pdf` - Get PDF by ID (returns signed URL)
- `GET /api/files/by-name/<filename>/pdf` - Get PDF by filename
- `DELETE /api/files/<id>` - Delete PDF (also deletes chunks)

### Health
- `GET /api/health` - Health check

## Admin Panel Features

- **Upload PDFs**: Drag & drop or select PDF files
- **View PDFs**: Browse all uploaded documents
- **Select Multiple**: Checkbox selection with "Select All"
- **Bulk Delete**: Delete multiple PDFs at once
- **Persistent State**: URL hash keeps you on the same page after refresh
- **Caching**: Fast navigation with 30-second cache

## Technology Stack

### Frontend
- **Vite**: Build tool
- **TypeScript**: Type-safe JavaScript
- **Marked**: Markdown rendering
- **DOMPurify**: XSS protection

### Backend
- **Flask**: Python web framework
- **Supabase**: PostgreSQL database + storage
- **OpenRouter**: LLM API
- **PyPDF2**: PDF processing
- **Sentence-Transformers**: Embeddings

### Database
- **Supabase PostgreSQL**: Main database
- **pgvector**: Vector embeddings for semantic search

## Notes

- PDFs are stored in Supabase storage bucket `pdf`
- Chunks are stored with embeddings in the database
- Signed URLs expire after 1 hour (regenerated on each access)
- Files can be served from storage or database fallback
