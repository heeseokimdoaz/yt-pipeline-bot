import type {
  PipelineRequest,
  PipelineResponse,
  VideoMeta,
  SubtitleChunk,
  Comment,
  SearchResult,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8101";

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export async function startPipeline(
  request: PipelineRequest
): Promise<PipelineResponse> {
  return fetchJSON("/api/pipeline/run", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getPipelineHistory() {
  return fetchJSON<
    {
      run_id: string;
      keywords: string[];
      status: string;
      started_at: string;
      video_count: number;
      subtitle_count: number;
      comment_count: number;
    }[]
  >("/api/pipeline/history");
}

export async function getQuota() {
  return fetchJSON<{ remaining: number; daily_limit: number; used: number }>(
    "/api/pipeline/quota"
  );
}

export async function getVideos(runId?: string) {
  const query = runId ? `?run_id=${runId}` : "";
  return fetchJSON<{ videos: VideoMeta[]; total: number }>(
    `/api/videos${query}`
  );
}

export async function getVideoDetail(videoId: string) {
  return fetchJSON<{
    video_id: string;
    subtitles: SubtitleChunk[];
    comments: Comment[];
  }>(`/api/videos/${videoId}`);
}

export async function searchSimilar(
  query: string,
  collection: "videos" | "subtitles" | "comments" = "subtitles",
  nResults: number = 10
) {
  return fetchJSON<SearchResult[]>("/api/search/similar", {
    method: "POST",
    body: JSON.stringify({
      query,
      collection,
      n_results: nResults,
    }),
  });
}
