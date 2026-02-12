"use client";

import { useEffect, useState } from "react";
import { getVideoDetail } from "@/lib/api";
import type { SubtitleChunk, Comment } from "@/lib/types";

interface Props {
  videoId: string;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function VideoDetail({ videoId }: Props) {
  const [subtitles, setSubtitles] = useState<SubtitleChunk[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"subtitles" | "comments">("subtitles");

  useEffect(() => {
    setLoading(true);
    getVideoDetail(videoId)
      .then((data) => {
        setSubtitles(data.subtitles);
        setComments(data.comments);
      })
      .finally(() => setLoading(false));
  }, [videoId]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-400">로딩 중...</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setTab("subtitles")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === "subtitles"
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          자막 ({subtitles.length}개 청크)
        </button>
        <button
          onClick={() => setTab("comments")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === "comments"
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          댓글 ({comments.length}개)
        </button>
      </div>

      {tab === "subtitles" && (
        <div className="space-y-2 max-h-[500px] overflow-y-auto">
          {subtitles.length === 0 ? (
            <p className="text-gray-400 text-sm">자막이 없습니다</p>
          ) : (
            subtitles.map((s) => (
              <div
                key={s.id}
                className="flex gap-3 p-2 hover:bg-gray-50 rounded text-sm"
              >
                <span className="text-blue-500 font-mono whitespace-nowrap flex-shrink-0">
                  {formatTime(s.metadata.start_time)}
                </span>
                <p className="text-gray-700">{s.text}</p>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "comments" && (
        <div className="space-y-3 max-h-[500px] overflow-y-auto">
          {comments.length === 0 ? (
            <p className="text-gray-400 text-sm">댓글이 없습니다</p>
          ) : (
            comments.map((c) => (
              <div
                key={c.id}
                className={`p-3 rounded text-sm ${
                  c.metadata.is_reply ? "ml-6 bg-gray-50" : "bg-white border border-gray-100"
                }`}
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="font-medium text-gray-800">
                    {c.metadata.author}
                  </span>
                  <div className="flex gap-2 text-xs text-gray-400">
                    {c.metadata.like_count > 0 && (
                      <span>좋아요 {c.metadata.like_count}</span>
                    )}
                    <span>
                      {new Date(c.metadata.published_at).toLocaleDateString(
                        "ko-KR"
                      )}
                    </span>
                  </div>
                </div>
                <p className="text-gray-700">{c.text}</p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
