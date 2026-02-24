"use client";

import { useState, useEffect } from "react";
import SearchForm from "@/components/SearchForm";
import PipelineStatus from "@/components/PipelineStatus";
import VideoList from "@/components/VideoList";
import VideoDetail from "@/components/VideoDetail";
import SearchPanel from "@/components/SearchPanel";
import CrawlerPanel from "@/components/CrawlerPanel";
import { getVideos } from "@/lib/api";
import type { VideoMeta } from "@/lib/types";

type Tab = "keyword" | "crawler";

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("crawler");
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

  useEffect(() => {
    if (!pipelineComplete || !runId) return;

    const fetchVideos = async () => {
      try {
        const data = await getVideos(runId);
        setVideos(data.videos);
      } catch {
        // ChromaDB may not have data yet
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
      <header>
        <h1 className="text-3xl font-bold">YouTube Pipeline Bot</h1>
        <p className="text-gray-500 text-sm mt-1">
          YouTube 영상 자막/댓글 크롤링 파이프라인
        </p>
      </header>

      {/* Tab Navigation */}
      <nav className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab("crawler")}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "crawler"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          채널 크롤러
        </button>
        <button
          onClick={() => setActiveTab("keyword")}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "keyword"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          키워드 검색
        </button>
      </nav>

      {/* Crawler Tab */}
      {activeTab === "crawler" && <CrawlerPanel />}

      {/* Keyword Search Tab */}
      {activeTab === "keyword" && (
        <>
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
        </>
      )}
    </main>
  );
}
