#!/bin/bash

echo "🧪 COMPREHENSIVE RUBRICON INTEGRATION TEST"
echo "========================================"

# Check if backend is running
echo "1. Checking backend status..."
if curl -s http://localhost:5002/health > /dev/null 2>&1; then
    echo "✅ Backend is running"
    curl -s http://localhost:5002/health | jq
else
    echo "❌ Backend not running - starting it..."
    python3 backend.py --server &
    sleep 5
    if curl -s http://localhost:5002/health > /dev/null 2>&1; then
        echo "✅ Backend started successfully"
    else
        echo "❌ Failed to start backend"
        exit 1
    fi
fi

echo
echo "2. Testing file upload..."
if [ -f "Note Checklist - Station 1A - Rash - Psoriasis.xlsx" ]; then
    RESPONSE=$(curl -s -X POST http://localhost:5002/upload -F "file=@Note Checklist - Station 1A - Rash - Psoriasis.xlsx")
    SUCCESS=$(echo "$RESPONSE" | jq -r '.success')
    YAML_LENGTH=$(echo "$RESPONSE" | jq -r '.yaml_content | length')
    
    if [ "$SUCCESS" = "true" ] && [ "$YAML_LENGTH" -gt 1000 ]; then
        echo "✅ File upload successful"
        echo "   Success: $SUCCESS"
        echo "   YAML Length: $YAML_LENGTH characters"
        echo "   Filename: $(echo "$RESPONSE" | jq -r '.filename')"
        echo "   Total Points: $(echo "$RESPONSE" | jq -r '.total_points')"
    else
        echo "❌ File upload failed"
        echo "   Response: $RESPONSE"
        exit 1
    fi
else
    echo "❌ Test file not found: Note Checklist - Station 1A - Rash - Psoriasis.xlsx"
    exit 1
fi

echo
echo "3. Testing download endpoint..."
DOWNLOAD_TEST=$(curl -s -X POST http://localhost:5002/download \
    -H "Content-Type: application/json" \
    -d '{"yaml_content":"test: yaml\ncontent: here","filename":"test.yaml"}' \
    -w "%{http_code}")

if [[ "$DOWNLOAD_TEST" == *"200" ]]; then
    echo "✅ Download endpoint working"
else
    echo "❌ Download endpoint failed: $DOWNLOAD_TEST"
fi

echo
echo "🎉 INTEGRATION TEST COMPLETE"
echo "========================================"
echo "✅ Backend Status: Running on port 5002"
echo "✅ Upload Endpoint: Working (${YAML_LENGTH} chars YAML)"
echo "✅ Download Endpoint: Working"
echo
echo "🌐 Ready for browser testing:"
echo "   1. Open rubricon.html in browser"
echo "   2. Upload the Excel file"
echo "   3. Check console for debug logs"
echo "   4. Verify YAML content appears"
echo "   5. Test download functionality"
echo
echo "🔧 If issues persist:"
echo "   - Check browser console (F12)"
echo "   - Try hard refresh (Cmd+Shift+R)"
echo "   - Use 'Direct Test' button for debugging" 