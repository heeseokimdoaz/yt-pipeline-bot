import type {
  PipelineRequest,
  PipelineResponse,
  VideoMeta,
  SubtitleChunk,
  Comment,
  SearchResult,
  CrawlRunSummary,
  ChannelConfig,
  CrawlerScheduleInfo,
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

// === Crawler API ===

export async function triggerCrawl() {
  return fetchJSON<CrawlRunSummary>("/api/crawler/trigger/sync", {
    method: "POST",
  });
}

export async function getCrawlHistory() {
  return fetchJSON<CrawlRunSummary[]>("/api/crawler/history");
}

export async function getCrawlStatus(runId: string) {
  return fetchJSON<CrawlRunSummary>(`/api/crawler/status/${runId}`);
}

export async function getChannels() {
  return fetchJSON<{
    channels: ChannelConfig[];
    total: number;
    enabled: number;
  }>("/api/crawler/channels");
}

export async function getCrawlerSchedule() {
  return fetchJSON<CrawlerScheduleInfo>("/api/crawler/schedule");
}

export async function syncChannelsFromCsv() {
  return fetchJSON<{
    total: number;
    added: number;
    removed: string[];
    resolved: number;
    unresolved: string[];
  }>("/api/crawler/sync", { method: "POST" });
}

export async function uploadChannelsCsv(csvContent: string) {
  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8101";
  const res = await fetch(`${API}/api/crawler/upload-csv`, {
    method: "POST",
    headers: { "Content-Type": "text/csv" },
    body: csvContent,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export async function reprocessMissing() {
  return fetchJSON<{
    total_videos: number;
    missing_subtitles: number;
    missing_comments: number;
    subtitles_added: number;
    comments_added: number;
  }>("/api/crawler/reprocess", { method: "POST" });
}
