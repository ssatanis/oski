#!/bin/bash

echo "🔍 Oski Backend Deployment Verification Script"
echo "=============================================="

# Check if URL is provided
if [ -z "$1" ]; then
    echo "❌ Error: Please provide your Railway backend URL"
    echo "Usage: ./verify-deployment.sh https://your-backend-url.railway.app"
    exit 1
fi

BACKEND_URL=$1

echo "🌐 Testing backend at: $BACKEND_URL"
echo ""

# Test 1: Health Check
echo "Test 1: Health Check"
echo "--------------------"
health_response=$(curl -s -w "%{http_code}" "$BACKEND_URL/health")
http_code="${health_response: -3}"
response_body="${health_response%???}"

if [ "$http_code" -eq 200 ]; then
    echo "✅ Health check passed (HTTP $http_code)"
    echo "Response: $response_body"
else
    echo "❌ Health check failed (HTTP $http_code)"
    echo "Response: $response_body"
fi
echo ""

# Test 2: CORS Preflight
echo "Test 2: CORS Configuration"
echo "--------------------------"
cors_response=$(curl -s -w "%{http_code}" -X OPTIONS \
    -H "Origin: https://oski-vert.vercel.app" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: Content-Type" \
    "$BACKEND_URL/upload")

cors_http_code="${cors_response: -3}"

if [ "$cors_http_code" -eq 200 ] || [ "$cors_http_code" -eq 204 ]; then
    echo "✅ CORS configuration working (HTTP $cors_http_code)"
else
    echo "❌ CORS configuration issue (HTTP $cors_http_code)"
fi
echo ""

# Test 3: Upload Endpoint Availability
echo "Test 3: Upload Endpoint"
echo "----------------------"
upload_response=$(curl -s -w "%{http_code}" -X POST "$BACKEND_URL/upload")
upload_http_code="${upload_response: -3}"

if [ "$upload_http_code" -eq 422 ]; then
    echo "✅ Upload endpoint available (HTTP $upload_http_code - Expected validation error)"
else
    echo "ℹ️  Upload endpoint response (HTTP $upload_http_code)"
fi
echo ""

# Summary
echo "📋 Deployment Verification Summary"
echo "=================================="
if [ "$http_code" -eq 200 ]; then
    echo "✅ Backend is successfully deployed and healthy!"
    echo ""
    echo "🔗 Next Steps:"
    echo "1. Update promptgen.html with this backend URL:"
    echo "   const RAILWAY_BACKEND_URL = '$BACKEND_URL';"
    echo ""
    echo "2. Deploy your frontend to Vercel"
    echo ""
    echo "3. Test end-to-end functionality"
else
    echo "❌ Backend deployment has issues. Check Railway logs."
    echo ""
    echo "🛠️  Troubleshooting:"
    echo "1. Check Railway deployment logs"
    echo "2. Verify environment variables are set"
    echo "3. Ensure Procfile is correct"
fi

echo ""
echo "🎉 Happy deploying!" 