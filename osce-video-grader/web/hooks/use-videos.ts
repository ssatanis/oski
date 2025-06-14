import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getIndexedVideos, uploadAndIndexVideo } from "@/services/api";
import { ApiVideoItem } from "@/types/assessment";

export const VIDEO_QUERY_KEYS = {
  all: (filters?: { skip?: number, limit?: number }) => ['videos', 'list', filters ?? {}] as const,
  detail: (id: string | null) => ['videos', 'detail', id] as const,
};

export function useGetIndexedVideos(
    skip: number = 0, 
    limit: number = 100
) {
    return useQuery({
        queryKey: [VIDEO_QUERY_KEYS, { skip, limit }], 
        queryFn: () => getIndexedVideos(skip, limit),
        placeholderData: (prevData) => prevData, // Keep previous data while loading new.
    })
}

export function useUploadAndIndexVideoMutation() {
    const queryClient = useQueryClient();

    return useMutation<ApiVideoItem, Error, FormData>({
        mutationFn: (formData: FormData) => uploadAndIndexVideo(formData), 
        onSuccess: (newVideo) => {
            queryClient.invalidateQueries({ queryKey: VIDEO_QUERY_KEYS.all() });
            queryClient.setQueryData(VIDEO_QUERY_KEYS.detail(newVideo.id), newVideo)
        },
        onError: (error) => {
            // This is handled in the component 
        }
    })
}