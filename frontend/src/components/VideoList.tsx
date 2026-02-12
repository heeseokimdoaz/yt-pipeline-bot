"use client";

import type { VideoMeta } from "@/lib/types";

interface Props {
  videos: VideoMeta[];
  onSelect: (videoId: string) => void;
  selectedId: string | null;
}

export default function VideoList({ videos, onSelect, selectedId }: Props) {
  if (videos.length === 0) return null;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4">
        수집된 영상 ({videos.length}개)
      </h2>
      <div className="space-y-3 max-h-[600px] overflow-y-auto">
        {videos.map((v) => (
          <div
            key={v.id}
            onClick={() => onSelect(v.metadata.video_id)}
            className={`flex gap-4 p-3 rounded-lg cursor-pointer transition-colors ${
              selectedId === v.metadata.video_id
                ? "bg-blue-50 border border-blue-200"
                : "hover:bg-gray-50 border border-transparent"
            }`}
          >
            {v.metadata.thumbnail_url && (
              <img
                src={v.metadata.thumbnail_url}
                alt={v.metadata.title}
                className="w-32 h-20 object-cover rounded flex-shrink-0"
              />
            )}
            <div className="min-w-0">
              <h3 className="font-medium text-sm line-clamp-2">
                {v.metadata.title}
              </h3>
              <p className="text-xs text-gray-500 mt-1">
                {v.metadata.channel_title}
              </p>
              <div className="flex gap-3 text-xs text-gray-400 mt-1">
                <span>
                  조회수{" "}
                  {v.metadata.view_count?.toLocaleString() ?? "N/A"}
                </span>
                <span>
                  {new Date(v.metadata.published_at).toLocaleDateString("ko-KR")}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
