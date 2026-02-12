"use client";

import { useState } from "react";
import { searchSimilar } from "@/lib/api";
import type { SearchResult } from "@/lib/types";

export default function SearchPanel() {
  const [query, setQuery] = useState("");
  const [collection, setCollection] = useState<
    "subtitles" | "comments" | "videos"
  >("subtitles");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      const data = await searchSimilar(query, collection);
      setResults(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4">벡터 유사도 검색</h2>

      <form onSubmit={handleSearch} className="flex gap-2 mb-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="검색할 텍스트를 입력하세요..."
          className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={collection}
          onChange={(e) =>
            setCollection(e.target.value as "subtitles" | "comments" | "videos")
          }
          className="border border-gray-300 rounded-md px-3 py-2 text-sm"
        >
          <option value="subtitles">자막</option>
          <option value="comments">댓글</option>
          <option value="videos">영상</option>
        </select>
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? "검색 중..." : "검색"}
        </button>
      </form>

      {results.length > 0 && (
        <div className="space-y-2 max-h-[400px] overflow-y-auto">
          {results.map((r, i) => (
            <div key={r.id} className="p-3 bg-gray-50 rounded text-sm">
              <div className="flex justify-between items-start mb-1">
                <span className="font-mono text-xs text-gray-400">
                  #{i + 1}
                </span>
                {r.distance !== null && (
                  <span className="text-xs text-gray-400">
                    유사도: {(1 - r.distance).toFixed(3)}
                  </span>
                )}
              </div>
              <p className="text-gray-700">{r.document}</p>
              {r.metadata.video_id && (
                <p className="text-xs text-gray-400 mt-1">
                  영상: {(r.metadata.video_id as string)}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
