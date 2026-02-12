"use client";

import { useEffect } from "react";
import { useSSE } from "@/hooks/useSSE";

interface Props {
  runId: string | null;
  onComplete?: () => void;
  onError?: () => void;
}

function formatEvent(type: string, data: Record<string, unknown>): string {
  switch (type) {
    case "search_started":
      return `검색 시작: ${(data.keywords as string[])?.join(", ")}`;
    case "search_progress":
      return `"${data.keyword}" 검색 완료 - ${data.found}개 영상 발견 (총 ${data.total_so_far}개)`;
    case "filter_progress":
      return `필터링: ${data.total_searched}개 중 ${data.passed}개 통과 (${data.filtered_out}개 제외)`;
    case "subtitle_progress":
      return `자막 [${data.progress}]: "${data.title}" - ${data.status === "ok" ? `${data.chunks}개 청크 저장` : "자막 없음"}`;
    case "comment_progress":
      return `댓글 [${data.progress}]: "${data.title}" - ${data.count}개 수집`;
    case "storage_progress":
      return `저장 완료: 영상 ${data.videos_stored}개, 자막 ${data.subtitle_chunks_stored}개 청크, 댓글 ${data.comments_stored}개`;
    case "pipeline_completed":
      return `파이프라인 완료! 영상 ${data.video_count}개, 자막 ${data.subtitle_chunks}개 청크, 댓글 ${data.comment_count}개`;
    case "pipeline_error":
      return `오류: ${data.error}`;
    default:
      return JSON.stringify(data);
  }
}

function getEventColor(type: string): string {
  if (type === "pipeline_completed") return "text-green-700 bg-green-50";
  if (type === "pipeline_error") return "text-red-700 bg-red-50";
  if (type.includes("progress")) return "text-blue-700";
  return "text-gray-700";
}

export default function PipelineStatus({ runId, onComplete, onError }: Props) {
  const { events, isComplete, error } = useSSE(runId);

  useEffect(() => {
    if (isComplete && !error) onComplete?.();
    if (isComplete && error) onError?.();
  }, [isComplete, error]);

  if (!runId) return null;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">파이프라인 진행 상황</h2>
        {!isComplete && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
            <span className="text-sm text-blue-600">실행 중</span>
          </div>
        )}
        {isComplete && !error && (
          <span className="text-sm text-green-600 font-medium">완료</span>
        )}
        {error && (
          <span className="text-sm text-red-600 font-medium">오류</span>
        )}
      </div>

      <div className="space-y-1 max-h-80 overflow-y-auto font-mono text-sm">
        {events.map((event, i) => (
          <div
            key={i}
            className={`px-2 py-1 rounded ${getEventColor(event.type)}`}
          >
            {formatEvent(event.type, event.data)}
          </div>
        ))}
        {events.length === 0 && (
          <p className="text-gray-400">이벤트 대기 중...</p>
        )}
      </div>
    </div>
  );
}
