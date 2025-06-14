VIDEO_PATH="./sample_osce_videos/testvideo.mp4"

curl -X POST http://localhost:8000/index_video/ \
-F "video_file=@$VIDEO_PATH" \
-H "Content-Type: multipart/form-data"