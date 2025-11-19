# DEPLOYMENT_NOT_FOUND Error - Complete Analysis

## 1. THE FIX

### Immediate Solution

**Option A: Set Root Directory (Recommended)**
1. Vercel Dashboard → Your Project → Settings → General
2. Set "Root Directory" to: `pdf-llm-trainer/frontend`
3. Keep root `vercel.json` as is (it uses relative paths)
4. Redeploy

**Option B: Fix vercel.json for Root Directory = Repo Root**
If Root Directory is NOT set (or set to repo root), update root `vercel.json`:

```json
{
  "buildCommand": "cd pdf-llm-trainer/frontend && npm ci && npm run build",
  "outputDirectory": "pdf-llm-trainer/frontend/dist",
  "installCommand": "cd pdf-llm-trainer/frontend && npm ci",
  "framework": "vite",
  "rewrites": [
    {
      "source": "/admin",
      "destination": "/admin.html"
    },
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

## 2. ROOT CAUSE ANALYSIS

### What Was Happening vs. What Should Happen

**What Was Happening:**
- Root `vercel.json` says: `buildCommand: "npm ci && npm run build"`
- This assumes commands run from the frontend directory
- If Root Directory is NOT set, Vercel runs from repo root (`pdf-llm-trainer/`)
- Vercel tries to run `npm ci` in `pdf-llm-trainer/` → **No package.json exists there!**
- Build fails → No `dist` folder created → **DEPLOYMENT_NOT_FOUND**

**What Should Happen:**
- Vercel needs to know WHERE your frontend code lives
- Build commands must run in the directory containing `package.json`
- Output directory path must be relative to where Vercel is "looking"

### Conditions That Triggered This Error

1. **Root Directory NOT set** → Vercel looks in repo root
2. **vercel.json uses relative paths** → Assumes it's already in frontend directory
3. **Build command fails** → No output created
4. **Vercel can't find `dist` folder** → DEPLOYMENT_NOT_FOUND

### The Misconception

**Misconception:** "vercel.json at root will automatically find my frontend"
**Reality:** Vercel needs explicit configuration about:
- WHERE to run build commands (Root Directory OR absolute paths in vercel.json)
- WHERE to find the output (relative to Root Directory)

## 3. UNDERSTANDING THE CONCEPT

### Why This Error Exists

**Vercel's Deployment Model:**
1. **Monorepo Support:** Vercel supports monorepos (multiple apps in one repo)
2. **Explicit Configuration:** You must tell Vercel which part to deploy
3. **Safety:** Prevents deploying wrong directory or failing silently

**What It's Protecting You From:**
- Accidentally deploying wrong part of monorepo
- Silent failures where build seems to work but outputs wrong location
- Confusion about which directory is being deployed

### The Correct Mental Model

```
Repository Root (pdf-llm-trainer/)
├── backend/          (not deployed)
├── frontend/         (THIS is what we want to deploy)
│   ├── package.json
│   ├── dist/         (build output - THIS is what Vercel needs)
│   └── src/
└── vercel.json       (configuration)

Vercel's Perspective:
1. "Where should I run commands?" → Root Directory tells it: "frontend/"
2. "Where is the output?" → Relative to Root Directory: "dist/"
3. "How do I route requests?" → vercel.json rewrites
```

**Key Insight:** 
- Root Directory = "cd into this directory first"
- All paths in vercel.json are relative to Root Directory
- If Root Directory = `pdf-llm-trainer/frontend`, then `dist` means `pdf-llm-trainer/frontend/dist`

### How This Fits Into Vercel's Framework

**Vercel's Deployment Flow:**
```
1. Clone repo
2. Set working directory = Root Directory (if set)
3. Run installCommand
4. Run buildCommand  
5. Look for outputDirectory
6. Deploy files from outputDirectory
```

**If step 4 fails → step 5 finds nothing → DEPLOYMENT_NOT_FOUND**

## 4. WARNING SIGNS

### What to Look For

**Red Flags:**
- ✅ Build logs show "npm: command not found" or "package.json not found"
- ✅ Build succeeds but shows "No output directory found"
- ✅ Multiple `vercel.json` files with conflicting paths
- ✅ Root Directory not set in monorepo
- ✅ Build command uses relative paths but Root Directory not set

**Code Smells:**
```json
// BAD: Assumes you're already in frontend/
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist"
}
// Without Root Directory set → FAILS

// GOOD: Explicit path
{
  "buildCommand": "cd frontend && npm run build",
  "outputDirectory": "frontend/dist"
}
// Works from repo root

// BEST: Set Root Directory to "frontend"
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist"
}
// Works because Root Directory = frontend/
```

### Similar Mistakes

1. **Wrong outputDirectory path**
   - Using absolute paths when Root Directory is set
   - Using relative paths when Root Directory is NOT set

2. **Build command in wrong directory**
   - Running `npm install` in repo root when package.json is in subdirectory

3. **Multiple vercel.json confusion**
   - Root vercel.json vs frontend/vercel.json
   - Which one does Vercel use? (Root one, unless Root Directory points elsewhere)

## 5. ALTERNATIVES & TRADE-OFFS

### Approach 1: Set Root Directory (Recommended)

**Pros:**
- Clean, simple vercel.json
- Standard Vercel pattern
- Easy to understand

**Cons:**
- Requires Vercel UI configuration
- Can't be version-controlled (but can be documented)

**When to Use:**
- Monorepo with clear frontend/backend separation
- You have access to Vercel dashboard

### Approach 2: Absolute Paths in vercel.json

**Pros:**
- Everything in code (version controlled)
- No Vercel UI configuration needed
- Works regardless of Root Directory setting

**Cons:**
- More verbose vercel.json
- Harder to read
- Paths must match your repo structure exactly

**When to Use:**
- Want everything in code
- Can't access Vercel dashboard
- Multiple environments with different structures

### Approach 3: Move Frontend to Repo Root

**Pros:**
- Simplest configuration
- No Root Directory needed
- Standard single-app pattern

**Cons:**
- Requires restructuring repo
- Loses monorepo organization
- Not ideal if you have backend too

**When to Use:**
- Only deploying frontend
- Willing to restructure
- Starting fresh

### Approach 4: Use Vercel CLI with --cwd

**Pros:**
- Explicit in deployment command
- No configuration needed

**Cons:**
- Only works with CLI deployments
- Not for GitHub integration

**When to Use:**
- Manual deployments
- CI/CD pipelines

## RECOMMENDED SOLUTION

**For your case:** Use Approach 1 (Set Root Directory) because:
1. You have a monorepo structure
2. You want clean configuration
3. It's the Vercel-recommended pattern

**Implementation:**
1. Set Root Directory: `pdf-llm-trainer/frontend`
2. Keep root vercel.json with relative paths
3. Remove frontend/vercel.json (routing handled by root one)

