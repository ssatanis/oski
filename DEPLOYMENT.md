# 🚀 Oski Deployment Guide

## Overview

The Oski platform consists of two parts:
- **Frontend**: Static HTML/CSS/JavaScript files that can be deployed anywhere
- **Backend**: Python FastAPI server that requires a server environment

## 🌐 Frontend Deployment

The frontend can be deployed to any static hosting service:

### Vercel (Recommended)
```bash
# Deploy to Vercel
vercel --prod
```

### Netlify
```bash
# Deploy to Netlify
netlify deploy --prod --dir .
```

### GitHub Pages
Simply push to a GitHub repository and enable GitHub Pages.

## 🖥️ Backend Deployment Options

### Option 1: Railway (Recommended for beginners)

1. **Fork the repository** to your GitHub account

2. **Create a Railway account** at [railway.app](https://railway.app)

3. **Deploy from GitHub**:
   - Connect your GitHub account
   - Select your forked repository
   - Set the root directory to: `rubrics-to-prompts/backend`

4. **Configure Environment Variables**:
   ```
   AZURE_OPENAI_KEY=your_actual_key_here
   AZURE_OPENAI_ENDPOINT=your_actual_endpoint_here
   AZURE_OPENAI_DEPLOYMENT_NAME=your_actual_deployment_name
   DEBUG=false
   ALLOWED_ORIGINS=https://your-frontend-domain.vercel.app
   ```

5. **Set the Start Command**:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

### Option 2: Heroku

1. **Create a Heroku app**:
   ```bash
   heroku create your-oski-backend
   ```

2. **Add a Procfile** in `rubrics-to-prompts/backend/`:
   ```
   web: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

3. **Deploy**:
   ```bash
   cd rubrics-to-prompts/backend
   git init
   git add .
   git commit -m "Deploy backend"
   git remote add heroku https://git.heroku.com/your-oski-backend.git
   git push heroku main
   ```

4. **Set environment variables**:
   ```bash
   heroku config:set AZURE_OPENAI_KEY=your_key
   heroku config:set AZURE_OPENAI_ENDPOINT=your_endpoint
   heroku config:set AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment
   heroku config:set DEBUG=false
   heroku config:set ALLOWED_ORIGINS=https://your-frontend-domain.vercel.app
   ```

### Option 3: DigitalOcean App Platform

1. **Create a new app** in DigitalOcean
2. **Connect your GitHub repository**
3. **Configure the app**:
   - Source Directory: `rubrics-to-prompts/backend`
   - Build Command: `pip install -r requirements.txt`
   - Run Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

## 🔗 Connecting Frontend to Backend

Once your backend is deployed, you need to update the frontend configuration:

### Method 1: Update PromptGen Configuration

Edit `promptgen.html` and update the `getBackendUrl()` function:

```javascript
const getBackendUrl = () => {
    const hostname = window.location.hostname;
    const isLocal = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '';
    
    if (isLocal) {
        return 'http://localhost:8000';
    } else {
        // Replace with your deployed backend URL
        return 'https://your-oski-backend.railway.app';
    }
};
```

### Method 2: Environment-based Configuration

Create a `config.js` file:

```javascript
const CONFIG = {
    BACKEND_URL: window.location.hostname === 'localhost' 
        ? 'http://localhost:8000' 
        : 'https://your-backend-url.railway.app'
};
```

## 🔒 Security Considerations

1. **CORS Configuration**: Ensure your backend's `ALLOWED_ORIGINS` includes your frontend domain
2. **API Keys**: Never expose Azure OpenAI keys in frontend code
3. **HTTPS**: Always use HTTPS for production deployments
4. **Rate Limiting**: Consider adding rate limiting to prevent abuse

## 📝 Azure OpenAI Setup

1. **Create an Azure OpenAI resource** in the Azure portal
2. **Deploy a model** (GPT-4 recommended)
3. **Get your credentials**:
   - Endpoint URL
   - API Key
   - Deployment Name

## 🧪 Testing Your Deployment

1. **Test Backend Health**:
   ```bash
   curl https://your-backend-url.railway.app/health
   ```

2. **Test Frontend Connection**:
   - Open your deployed frontend
   - Try uploading a test rubric
   - Verify processing works end-to-end

## 🚨 Troubleshooting

### "Cannot connect to backend server"
- ✅ Check backend is running: `curl https://your-backend-url/health`
- ✅ Verify CORS configuration includes your frontend domain
- ✅ Ensure frontend is pointing to correct backend URL

### "Azure OpenAI API Error"
- ✅ Verify your Azure OpenAI credentials are correct
- ✅ Check your deployment name matches exactly
- ✅ Ensure you have quota available

### "File Upload Failed"
- ✅ Check file size limits in your hosting platform
- ✅ Verify supported file formats in backend configuration

## 💡 Local Development

For local development, use the provided script:

```bash
./start-oski.sh
```

This starts the backend locally and opens the frontend in your browser.

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the logs in your hosting platform
3. Open an issue on the GitHub repository

---

**Happy deploying! 🎉** 