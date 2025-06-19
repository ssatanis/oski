# Rubricon Vercel Deployment Guide

## 🚀 Frontend Deployment (Vercel)

### Step 1: Prepare for Deployment
The `.vercelignore` file excludes large directories to stay under the 300MB limit.

### Step 2: Deploy to Vercel
```bash
vercel --prod
```

Or push to GitHub and connect via Vercel dashboard.

### Step 3: Backend Setup
For full functionality, you need to deploy the backend separately:

#### Option A: Deploy Backend to Railway/Heroku
1. Create new project on Railway/Heroku
2. Upload only the `rubrics-to-prompts/backend/` folder
3. Set environment variables:
   - `AZURE_OPENAI_KEY`
   - `AZURE_OPENAI_ENDPOINT` 
   - `AZURE_OPENAI_DEPLOYMENT_NAME`
4. Deploy and note the URL

#### Option B: Use Vercel Serverless Functions
1. Move backend code to `api/` folder
2. Convert to serverless functions
3. Update CORS settings

### Step 4: Update Backend URL
Replace in `rubricon.html` and `rubricon-clean.html`:
```javascript
const BACKEND_URL = 'https://your-deployed-backend-url.com';
```

## 🧪 Testing

### Local Testing:
```bash
./start-rubricon.sh
```
Open: http://localhost:3000/rubricon.html

### Production Testing:
1. Upload a test file
2. Check browser console for errors
3. Verify backend connectivity

## 📁 Files Included in Deployment

✅ Essential files:
- `rubricon.html` (main app)
- `rubricon-clean.html` (no-cache version)
- `index.html`
- `css/` folder
- `js/` folder
- Essential images

❌ Excluded from deployment:
- `rubrics-to-prompts/` (882MB)
- `venv/` (815MB)  
- `osce-video-grader/` (434MB)
- `node_modules/` (182MB)
- Backend files

## 🔧 File Upload Fix

If file upload doesn't work locally:
1. Check browser console (F12)
2. Verify both servers are running:
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000/health
3. Clear browser cache (Ctrl+Shift+R)

## 🎯 Expected Deployment Size

After exclusions: ~10-20MB (well under 300MB limit)

## 🆘 Troubleshooting

### "Size exceeds 300MB"
- Ensure `.vercelignore` is working
- Run: `git clean -fdx` to remove ignored files locally
- Check deployment logs in Vercel dashboard

### File upload not working
- Backend URL misconfigured
- CORS issues
- Network connectivity problems
- Check browser developer tools console 