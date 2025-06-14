import { ApiAssessVideoPayload, ApiAssessVideoResponse, ApiDeleteVideoResponse, ApiVideoItem, ApiVideosListResponse } from "@/types/assessment";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorDetail = "An unknown API error occurred.";
    try {
      const errorData = await response.json();
      errorDetail = errorData.detail || JSON.stringify(errorData);
    } catch (e) {
      // If parsing JSON fails, use the status text or a generic message
      errorDetail = response.statusText || `HTTP error ${response.status}`;
    }
    console.error("API Error:", errorDetail, "Status:", response.status);
    throw new Error(errorDetail);
  }
  return response.json() as Promise<T>;
}


export async function getIndexedVideos(
    skip: number = 0, 
    limit: number = 100
): Promise<ApiVideosListResponse> {
    const url = `${API_BASE_URL}/api/v1/videos/?skip=${skip}&limit=${limit}`
    const response = await fetch(url)

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({
            detail: "Failed to fetch videos."
        }))

        throw new Error(errorData.detail || "Failed to fetch videos")
    }

    return response.json();
}

export async function getVideoDetails(videoId: string): Promise<ApiVideoItem> {
    const response = await fetch(`${API_BASE_URL}/api/v1/videos/${videoId}`)
    return handleResponse<ApiVideoItem>(response)
}

export async function uploadAndIndexVideo(formData: FormData): Promise<ApiVideoItem> {
    const response = await fetch(`${API_BASE_URL}/api/v1/index_video`, {
        method: "POST", 
        body: formData, 
        // Content-Type is set by browser for FormData 
    });

    return handleResponse<ApiVideoItem>(response)
}

export async function assessVideo(payload: ApiAssessVideoPayload, useAllTools: boolean = false): Promise<ApiAssessVideoResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/assess_video/?use_all_tools=${useAllTools}`, {
        method: "POST", 
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    })

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Video assessment failed.")
    }

    return response.json();
}

export async function deleteVideo(videoId: string): Promise<ApiDeleteVideoResponse> {
    const response = await fetch(`${API_BASE_URL}/videos/${videoId}`, {
        method: "DELETE"
    })

    return handleResponse<ApiDeleteVideoResponse>(response)
}