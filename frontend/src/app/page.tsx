"use client";

import { useState, useEffect } from "react";
import SearchForm from "@/components/SearchForm";
import PipelineStatus from "@/components/PipelineStatus";
import VideoList from "@/components/VideoList";
import VideoDetail from "@/components/VideoDetail";
import SearchPanel from "@/components/SearchPanel";
import { getVideos } from "@/lib/api";
import type { VideoMeta } from "@/lib/types";

export default function Home() {
  const [runId, setRunId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [videos, setVideos] = useState<VideoMeta[]>([]);
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);
  const [pipelineComplete, setPipelineComplete] = useState(false);

  const handlePipelineStarted = (newRunId: string) => {
    setRunId(newRunId);
    setIsRunning(true);
    setVideos([]);
    setSelectedVideoId(null);
    setPipelineComplete(false);
  };

  // Poll for videos once pipeline completes
  useEffect(() => {
    if (!pipelineComplete || !runId) return;

    const fetchVideos = async () => {
      try {
        const data = await getVideos(runId);
        setVideos(data.videos);
      } catch {
        // ChromaDB may not have data yet, retry
      }
    };

    fetchVideos();
  }, [pipelineComplete, runId]);

  const handlePipelineComplete = () => {
    setIsRunning(false);
    setPipelineComplete(true);
  };

  const handlePipelineError = () => {
    setIsRunning(false);
  };

  return (
    <main className="max-w-7xl mx-auto p-6 space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">YouTube Pipeline Bot</h1>
          <p className="text-gray-500 text-sm mt-1">
            키워드 기반 YouTube 영상 자막/댓글 크롤링 파이프라인
          </p>
        </div>
      </header>

      <SearchForm
        onPipelineStarted={handlePipelineStarted}
        isRunning={isRunning}
      />

      <PipelineStatus
        runId={runId}
        onComplete={handlePipelineComplete}
        onError={handlePipelineError}
      />

      {videos.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <VideoList
            videos={videos}
            onSelect={setSelectedVideoId}
            selectedId={selectedVideoId}
          />
          {selectedVideoId && <VideoDetail videoId={selectedVideoId} />}
        </div>
      )}

      {pipelineComplete && <SearchPanel />}
    </main>
  );
}
