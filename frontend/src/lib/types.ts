export interface PipelineRequest {
  keywords: string[];
  max_results: number;
  filter_keywords: string[];
  filter_mode: "any" | "all";
  include_subtitles: boolean;
  include_comments: boolean;
  subtitle_languages: string[];
  max_comments_per_video: number;
}

export interface PipelineResponse {
  run_id: string;
  status: string;
  sse_url: string;
}

export interface PipelineEvent {
  type: string;
  data: Record<string, unknown>;
}

export interface VideoMeta {
  id: string;
  metadata: {
    video_id: string;
    run_id: string;
    title: string;
    channel_title: string;
    published_at: string;
    view_count: number;
    like_count: number;
    thumbnail_url: string;
    tags: string;
  };
}

export interface SubtitleChunk {
  id: string;
  text: string;
  metadata: {
    video_id: string;
    language: string;
    start_time: number;
    end_time: number;
    chunk_index: number;
  };
}

export interface Comment {
  id: string;
  text: string;
  metadata: {
    video_id: string;
    comment_id: string;
    author: string;
    like_count: number;
    published_at: string;
    is_reply: boolean;
  };
}

export interface SearchResult {
  id: string;
  document: string;
  metadata: Record<string, unknown>;
  distance: number | null;
}
