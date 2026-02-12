"use client";

import { useState } from "react";
import { startPipeline } from "@/lib/api";
import type { PipelineRequest } from "@/lib/types";

interface Props {
  onPipelineStarted: (runId: string) => void;
  isRunning: boolean;
}

export default function SearchForm({ onPipelineStarted, isRunning }: Props) {
  const [keywords, setKeywords] = useState("");
  const [filterKeywords, setFilterKeywords] = useState("");
  const [excludeKeywords, setExcludeKeywords] = useState("");
  const [maxResults, setMaxResults] = useState(10);
  const [includeSubtitles, setIncludeSubtitles] = useState(true);
  const [includeComments, setIncludeComments] = useState(true);
  const [maxComments, setMaxComments] = useState(100);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const keywordList = keywords
      .split(",")
      .map((k) => k.trim())
      .filter(Boolean);
    if (keywordList.length === 0) {
      setError("키워드를 하나 이상 입력해주세요");
      return;
    }

    const request: PipelineRequest = {
      keywords: keywordList,
      max_results: maxResults,
      filter_keywords: filterKeywords
        .split(",")
        .map((k) => k.trim())
        .filter(Boolean),
      exclude_keywords: excludeKeywords
        .split(",")
        .map((k) => k.trim())
        .filter(Boolean),
      filter_mode: "any",
      include_subtitles: includeSubtitles,
      include_comments: includeComments,
      subtitle_languages: ["ko", "en"],
      max_comments_per_video: maxComments,
    };

    try {
      const response = await startPipeline(request);
      onPipelineStarted(response.run_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "파이프라인 시작 실패");
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white rounded-lg shadow p-6 space-y-4"
    >
      <h2 className="text-xl font-semibold">YouTube 영상 검색</h2>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          검색 키워드 (쉼표로 구분)
        </label>
        <input
          type="text"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          placeholder="예: 대선 토론, 국회 정치"
          className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={isRunning}
        />
        <p className="text-xs text-gray-500 mt-1">
          YouTube에서 이 키워드로 영상을 검색합니다
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-green-700 mb-1">
            포함 필터 (선택, 쉼표로 구분)
          </label>
          <input
            type="text"
            value={filterKeywords}
            onChange={(e) => setFilterKeywords(e.target.value)}
            placeholder="예: 대선, 총선, 국회"
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-400"
            disabled={isRunning}
          />
          <p className="text-xs text-gray-500 mt-1">
            이 키워드가 포함된 영상<span className="font-semibold text-green-600">만</span> 수집합니다
          </p>
        </div>
        <div>
          <label className="block text-sm font-medium text-red-700 mb-1">
            제외 필터 (선택, 쉼표로 구분)
          </label>
          <input
            type="text"
            value={excludeKeywords}
            onChange={(e) => setExcludeKeywords(e.target.value)}
            placeholder="예: 지난총선, 재보궐, 지방선거"
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400"
            disabled={isRunning}
          />
          <p className="text-xs text-gray-500 mt-1">
            이 키워드가 포함된 영상을 <span className="font-semibold text-red-600">제외</span>합니다
          </p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            키워드당 최대 결과
          </label>
          <input
            type="number"
            value={maxResults}
            onChange={(e) => setMaxResults(Number(e.target.value))}
            min={1}
            max={50}
            className="w-full border border-gray-300 rounded-md px-3 py-2"
            disabled={isRunning}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            영상당 최대 댓글
          </label>
          <input
            type="number"
            value={maxComments}
            onChange={(e) => setMaxComments(Number(e.target.value))}
            min={0}
            max={500}
            className="w-full border border-gray-300 rounded-md px-3 py-2"
            disabled={isRunning}
          />
        </div>
        <div className="flex items-end gap-4">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={includeSubtitles}
              onChange={(e) => setIncludeSubtitles(e.target.checked)}
              disabled={isRunning}
            />
            <span className="text-sm">자막</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={includeComments}
              onChange={(e) => setIncludeComments(e.target.checked)}
              disabled={isRunning}
            />
            <span className="text-sm">댓글</span>
          </label>
        </div>
      </div>

      {error && (
        <p className="text-red-600 text-sm">{error}</p>
      )}

      <button
        type="submit"
        disabled={isRunning}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
      >
        {isRunning ? "파이프라인 실행 중..." : "파이프라인 시작"}
      </button>
    </form>
  );
}
