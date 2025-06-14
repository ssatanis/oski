"use client"

import type React from "react"

import { useState, useEffect, RefObject, useCallback } from "react"

export function useVideoUpload(fileInputRef?: RefObject<HTMLInputElement>) {
  const [uploadedVideo, setUploadedVideo] = useState<File | null>(null)
  const [objectUrl, setObjectUrl] = useState<string | null>(null)

  const handleVideoUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      setUploadedVideo(file)

      // If a previous object URL exists, revoke it 
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl)
      }

      const newObjectUrl = URL.createObjectURL(file);
      setObjectUrl(newObjectUrl)
    } else {
      // If no file is selected e.g. user hits cancel, clear the existing video 
      setUploadedVideo(null)
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl)
        setObjectUrl(null);
      }
    }
  }, [objectUrl])

  const clearVideo = useCallback(() => {
    setUploadedVideo(null)
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl)
      setObjectUrl(null)
    }

    // Reset the file input's value if a ref is provided 
    if (fileInputRef?.current) {
      fileInputRef.current.value = "";
    }
  }, [fileInputRef, objectUrl])

  // Clean up the object URL when the component unmounts 
  useEffect(() => {
    return () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    }
  }, [objectUrl]);

  return {
    uploadedVideo,
    objectUrl,
    handleVideoUpload,
    clearVideo,
  }
}
