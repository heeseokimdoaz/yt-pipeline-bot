"use client";

import { useState, useEffect, useCallback } from "react";
import {
  triggerCrawl,
  getCrawlHistory,
  getChannels,
  getCrawlerSchedule,
  getVideos,
  getVideoDetail,
  reprocessMissing,
  uploadChannelsCsv,
} from "@/lib/api";
import type {
  CrawlRunSummary,
  ChannelConfig,
  CrawlerScheduleInfo,
  VideoMeta,
  SubtitleChunk,
  Comment,
} from "@/lib/types";

const CATEGORY_COLORS: Record<string, string> = {
  "중립/종합": "bg-gray-100 text-gray-700",
  진보: "bg-blue-100 text-blue-700",
  보수: "bg-red-100 text-red-700",
};

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    running: "bg-yellow-100 text-yellow-800",
    completed: "bg-green-100 text-green-800",
    completed_with_errors: "bg-orange-100 text-orange-800",
    error: "bg-red-100 text-red-800",
  };
  return (
    <span
      className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] || "bg-gray-100 text-gray-700"}`}
    >
      {status === "running" && "실행 중"}
      {status === "completed" && "완료"}
      {status === "completed_with_errors" && "일부 오류"}
      {status === "error" && "오류"}
    </span>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function CrawlerPanel() {
  const [channels, setChannels] = useState<ChannelConfig[]>([]);
  const [history, setHistory] = useState<CrawlRunSummary[]>([]);
  const [schedule, setSchedule] = useState<CrawlerScheduleInfo | null>(null);
  const [isCrawling, setIsCrawling] = useState(false);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [activeCrawl, setActiveCrawl] = useState<CrawlRunSummary | null>(null);
  const [reprocessResult, setReprocessResult] = useState<{
    total_videos: number;
    missing_subtitles: number;
    missing_comments: number;
    subtitles_added: number;
    comments_added: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"videos" | "status" | "channels">("videos");

  // Video browsing state
  const [videos, setVideos] = useState<VideoMeta[]>([]);
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);
  const [subtitles, setSubtitles] = useState<SubtitleChunk[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailTab, setDetailTab] = useState<"subtitles" | "comments">("subtitles");
  const [filterCategory, setFilterCategory] = useState<string>("all");

  const loadData = useCallback(async () => {
    try {
      const [channelData, historyData, scheduleData, videoData] =
        await Promise.all([
          getChannels(),
          getCrawlHistory(),
          getCrawlerSchedule(),
          getVideos(),
        ]);
      setChannels(channelData.channels);
      setHistory(historyData);
      setSchedule(scheduleData);
      setVideos(videoData.videos);
    } catch {
      // Server might not be running
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Load video detail when selected
  useEffect(() => {
    if (!selectedVideoId) return;
    setDetailLoading(true);
    getVideoDetail(selectedVideoId)
      .then((data) => {
        setSubtitles(data.subtitles);
        setComments(data.comments);
      })
      .finally(() => setDetailLoading(false));
  }, [selectedVideoId]);

  const handleTrigger = async () => {
    setIsCrawling(true);
    setError(null);
    setActiveCrawl(null);

    try {
      const result = await triggerCrawl();
      setActiveCrawl(result);
      setHistory((prev) => [result, ...prev]);
      // Reload videos after crawl
      const videoData = await getVideos();
      setVideos(videoData.videos);
    } catch (err) {
      setError(err instanceof Error ? err.message : "크롤링 실행 실패");
    } finally {
      setIsCrawling(false);
    }
  };

  const handleReprocess = async () => {
    setIsReprocessing(true);
    setError(null);
    setReprocessResult(null);

    try {
      const result = await reprocessMissing();
      setReprocessResult(result);
      // Reload videos after reprocess
      const videoData = await getVideos();
      setVideos(videoData.videos);
    } catch (err) {
      setError(err instanceof Error ? err.message : "재수집 실행 실패");
    } finally {
      setIsReprocessing(false);
    }
  };

  const enabledCount = channels.filter(
    (ch) => ch.enabled && ch.channel_id
  ).length;

  const byCategory = channels.reduce(
    (acc, ch) => {
      if (!acc[ch.category]) acc[ch.category] = [];
      acc[ch.category].push(ch);
      return acc;
    },
    {} as Record<string, ChannelConfig[]>
  );

  // Build channel name -> category map
  const channelCategoryMap = channels.reduce(
    (acc, ch) => {
      acc[ch.channel_name] = ch.category;
      return acc;
    },
    {} as Record<string, string>
  );

  // Filter videos by category
  const filteredVideos =
    filterCategory === "all"
      ? videos
      : videos.filter((v) => {
          const cat =
            (v.metadata as Record<string, unknown>).channel_category ||
            channelCategoryMap[v.metadata.channel_title] ||
            "";
          return cat === filterCategory;
        });

  // Sort by published date descending
  const sortedVideos = [...filteredVideos].sort(
    (a, b) =>
      new Date(b.metadata.published_at).getTime() -
      new Date(a.metadata.published_at).getTime()
  );

  return (
    <div className="space-y-6">
      {/* Header + Trigger */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold">채널 자동 크롤러</h2>
            <p className="text-sm text-gray-500 mt-1">
              {enabledCount}개 채널 / 최근 {schedule?.days_back ?? 7}일 영상 /
              수집된 영상 {videos.length}개
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleTrigger}
              disabled={isCrawling || isReprocessing}
              className="bg-blue-600 text-white px-5 py-2.5 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {isCrawling ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  크롤링 중...
                </span>
              ) : (
                "수동 크롤링 실행"
              )}
            </button>
            <button
              onClick={handleReprocess}
              disabled={isCrawling || isReprocessing}
              className="bg-green-600 text-white px-5 py-2.5 rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {isReprocessing ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  재수집 중...
                </span>
              ) : (
                "자막/댓글 재수집"
              )}
            </button>
          </div>
        </div>

        {/* Schedule Info */}
        {schedule && (
          <div className="flex flex-wrap gap-4 text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
            <span>
              자동 실행:{" "}
              <span className="font-medium">
                {schedule.enabled ? "활성" : "비활성"}
              </span>
            </span>
            <span>|</span>
            <span>
              스케줄:{" "}
              <span className="font-medium">{schedule.cron} (매일)</span>
            </span>
            {schedule.next_run && (
              <>
                <span>|</span>
                <span>
                  다음 실행:{" "}
                  <span className="font-medium">
                    {new Date(schedule.next_run).toLocaleString("ko-KR")}
                  </span>
                </span>
              </>
            )}
          </div>
        )}

        {error && <p className="text-red-600 text-sm mt-3">{error}</p>}

        {reprocessResult && (
          <div className="mt-3 bg-green-50 rounded-lg p-4 text-sm">
            <h4 className="font-semibold text-green-800 mb-2">재수집 결과</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="text-center">
                <div className="text-lg font-bold text-green-700">{reprocessResult.subtitles_added}</div>
                <div className="text-green-600 text-xs">자막 청크 추가</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-green-700">{reprocessResult.comments_added}</div>
                <div className="text-green-600 text-xs">댓글 추가</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-gray-600">{reprocessResult.missing_subtitles}</div>
                <div className="text-gray-500 text-xs">자막 없던 영상</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-gray-600">{reprocessResult.missing_comments}</div>
                <div className="text-gray-500 text-xs">댓글 없던 영상</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Active Crawl Result */}
      {activeCrawl && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold">크롤 결과</h3>
            <StatusBadge status={activeCrawl.status} />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div className="bg-blue-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-blue-700">
                {activeCrawl.new_videos_found}
              </div>
              <div className="text-blue-600">새 영상</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-gray-700">
                {activeCrawl.videos_skipped_duplicate}
              </div>
              <div className="text-gray-600">중복 스킵</div>
            </div>
            <div className="bg-green-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-green-700">
                {activeCrawl.subtitles_collected}
              </div>
              <div className="text-green-600">자막 청크</div>
            </div>
            <div className="bg-purple-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-purple-700">
                {activeCrawl.comments_collected}
              </div>
              <div className="text-purple-600">댓글</div>
            </div>
          </div>
          {activeCrawl.errors.length > 0 && (
            <div className="mt-3 space-y-1">
              {activeCrawl.errors.map((err, i) => (
                <div
                  key={i}
                  className="text-sm text-red-600 bg-red-50 px-3 py-1 rounded"
                >
                  {err.channel
                    ? `[${err.channel}] ${err.error}`
                    : err.message}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab Switch */}
      <div className="flex gap-2">
        <button
          onClick={() => setTab("videos")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === "videos"
              ? "bg-blue-600 text-white"
              : "bg-white text-gray-700 hover:bg-gray-100 shadow"
          }`}
        >
          수집된 영상 ({videos.length})
        </button>
        <button
          onClick={() => setTab("status")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === "status"
              ? "bg-blue-600 text-white"
              : "bg-white text-gray-700 hover:bg-gray-100 shadow"
          }`}
        >
          크롤링 이력
        </button>
        <button
          onClick={() => setTab("channels")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === "channels"
              ? "bg-blue-600 text-white"
              : "bg-white text-gray-700 hover:bg-gray-100 shadow"
          }`}
        >
          채널 목록 ({channels.length})
        </button>
      </div>

      {/* Tab: Videos */}
      {tab === "videos" && (
        <div className="space-y-4">
          {/* Category Filter */}
          <div className="flex gap-2">
            {["all", "중립/종합", "진보", "보수"].map((cat) => (
              <button
                key={cat}
                onClick={() => setFilterCategory(cat)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  filterCategory === cat
                    ? cat === "all"
                      ? "bg-blue-600 text-white"
                      : cat === "진보"
                        ? "bg-blue-600 text-white"
                        : cat === "보수"
                          ? "bg-red-600 text-white"
                          : "bg-gray-600 text-white"
                    : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
                }`}
              >
                {cat === "all" ? `전체 (${videos.length})` : cat}
              </button>
            ))}
          </div>

          {sortedVideos.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-8 text-center text-gray-400">
              <p>수집된 영상이 없습니다.</p>
              <p className="text-sm mt-1">
                "수동 크롤링 실행" 버튼을 눌러 영상을 수집하세요.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Video List */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="font-semibold mb-3">
                  영상 목록 ({sortedVideos.length}개)
                </h3>
                <div className="space-y-2 max-h-[700px] overflow-y-auto">
                  {sortedVideos.map((v) => {
                    const cat =
                      (v.metadata as Record<string, unknown>)
                        .channel_category ||
                      channelCategoryMap[v.metadata.channel_title] ||
                      "";
                    return (
                      <div
                        key={v.id}
                        onClick={() => {
                          setSelectedVideoId(v.metadata.video_id);
                          setDetailTab("subtitles");
                        }}
                        className={`flex gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                          selectedVideoId === v.metadata.video_id
                            ? "bg-blue-50 border border-blue-200"
                            : "hover:bg-gray-50 border border-transparent"
                        }`}
                      >
                        {v.metadata.thumbnail_url && (
                          <img
                            src={v.metadata.thumbnail_url}
                            alt=""
                            className="w-28 h-16 object-cover rounded flex-shrink-0"
                          />
                        )}
                        <div className="min-w-0 flex-1">
                          <h4 className="font-medium text-sm line-clamp-2 leading-tight">
                            {v.metadata.title}
                          </h4>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-gray-500">
                              {v.metadata.channel_title}
                            </span>
                            {cat && (
                              <span
                                className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${CATEGORY_COLORS[cat as string] || ""}`}
                              >
                                {cat as string}
                              </span>
                            )}
                          </div>
                          <div className="flex gap-3 text-[11px] text-gray-400 mt-1">
                            <span>
                              조회수{" "}
                              {v.metadata.view_count?.toLocaleString() ?? "N/A"}
                            </span>
                            <span>
                              {new Date(
                                v.metadata.published_at
                              ).toLocaleDateString("ko-KR")}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Video Detail */}
              <div className="bg-white rounded-lg shadow p-6">
                {!selectedVideoId ? (
                  <p className="text-gray-400 text-sm text-center py-12">
                    영상을 선택하면 자막과 댓글을 볼 수 있습니다.
                  </p>
                ) : detailLoading ? (
                  <p className="text-gray-400 text-sm text-center py-12">
                    로딩 중...
                  </p>
                ) : (
                  <>
                    <div className="flex gap-2 mb-4">
                      <button
                        onClick={() => setDetailTab("subtitles")}
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                          detailTab === "subtitles"
                            ? "bg-blue-600 text-white"
                            : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                        }`}
                      >
                        자막 ({subtitles.length}개 청크)
                      </button>
                      <button
                        onClick={() => setDetailTab("comments")}
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                          detailTab === "comments"
                            ? "bg-blue-600 text-white"
                            : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                        }`}
                      >
                        댓글 ({comments.length}개)
                      </button>
                    </div>

                    {detailTab === "subtitles" && (
                      <div className="space-y-2 max-h-[600px] overflow-y-auto">
                        {subtitles.length === 0 ? (
                          <p className="text-gray-400 text-sm">
                            자막이 없습니다
                          </p>
                        ) : (
                          subtitles.map((s) => (
                            <div
                              key={s.id}
                              className="flex gap-3 p-2 hover:bg-gray-50 rounded text-sm"
                            >
                              <span className="text-blue-500 font-mono whitespace-nowrap flex-shrink-0 text-xs">
                                {formatTime(s.metadata.start_time)}
                              </span>
                              <p className="text-gray-700">{s.text}</p>
                            </div>
                          ))
                        )}
                      </div>
                    )}

                    {detailTab === "comments" && (
                      <div className="space-y-3 max-h-[600px] overflow-y-auto">
                        {comments.length === 0 ? (
                          <p className="text-gray-400 text-sm">
                            댓글이 없습니다
                          </p>
                        ) : (
                          comments.map((c) => (
                            <div
                              key={c.id}
                              className={`p-3 rounded text-sm ${
                                c.metadata.is_reply
                                  ? "ml-6 bg-gray-50"
                                  : "bg-white border border-gray-100"
                              }`}
                            >
                              <div className="flex justify-between items-center mb-1">
                                <span className="font-medium text-gray-800">
                                  {c.metadata.author}
                                </span>
                                <div className="flex gap-2 text-xs text-gray-400">
                                  {c.metadata.like_count > 0 && (
                                    <span>
                                      좋아요 {c.metadata.like_count}
                                    </span>
                                  )}
                                  <span>
                                    {new Date(
                                      c.metadata.published_at
                                    ).toLocaleDateString("ko-KR")}
                                  </span>
                                </div>
                              </div>
                              <p className="text-gray-700">{c.text}</p>
                            </div>
                          ))
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab: History */}
      {tab === "status" && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="font-semibold mb-4">크롤링 이력</h3>
          {history.length === 0 ? (
            <p className="text-gray-400 text-sm">
              아직 크롤링 이력이 없습니다.
            </p>
          ) : (
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {history.map((run) => (
                <div
                  key={run.run_id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg text-sm"
                >
                  <div>
                    <div className="font-mono text-xs text-gray-500">
                      {run.run_id}
                    </div>
                    <div className="text-gray-700 mt-1">
                      {new Date(run.started_at).toLocaleString("ko-KR")}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right text-xs text-gray-500">
                      <div>
                        새 영상 {run.new_videos_found}개 / 스킵{" "}
                        {run.videos_skipped_duplicate}개
                      </div>
                      <div>
                        채널 {run.channels_processed}/{run.channels_total}
                      </div>
                    </div>
                    <StatusBadge status={run.status} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab: Channels */}
      {tab === "channels" && (
        <div className="space-y-4">
          {/* CSV Upload */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="font-semibold">채널 목록 관리</h3>
                <p className="text-xs text-gray-500 mt-1">
                  CSV 파일을 업로드하면 채널 목록이 자동으로 동기화됩니다.
                </p>
              </div>
              <label className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors font-medium text-sm cursor-pointer">
                CSV 업로드
                <input
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    const text = await file.text();
                    try {
                      const result = await uploadChannelsCsv(text);
                      const channelData = await getChannels();
                      setChannels(channelData.channels);
                      alert(
                        `동기화 완료: ${result.total}개 채널\n` +
                          (result.added > 0
                            ? `추가: ${result.added}개\n`
                            : "") +
                          (result.removed?.length
                            ? `제거: ${result.removed.join(", ")}\n`
                            : "") +
                          (result.unresolved?.length
                            ? `미연결: ${result.unresolved.join(", ")}`
                            : "")
                      );
                    } catch (err) {
                      setError(
                        err instanceof Error ? err.message : "CSV 업로드 실패"
                      );
                    }
                    e.target.value = "";
                  }}
                />
              </label>
            </div>
            <div className="text-xs text-gray-400">
              CSV 형식: 카테고리, 연번, 채널명, 유튜브 주소, 주요 특징
            </div>
          </div>

          {(["중립/종합", "진보", "보수"] as const).map((category) => (
            <div key={category} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center gap-2 mb-3">
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${CATEGORY_COLORS[category]}`}
                >
                  {category}
                </span>
                <span className="text-sm text-gray-500">
                  {byCategory[category]?.length ?? 0}개 채널
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {byCategory[category]?.map((ch) => (
                  <div
                    key={ch.channel_name}
                    className={`flex items-center justify-between p-3 rounded-lg border ${
                      ch.channel_id
                        ? "border-gray-200"
                        : "border-red-200 bg-red-50"
                    }`}
                  >
                    <div className="min-w-0">
                      <div className="font-medium text-sm truncate">
                        {ch.channel_name}
                      </div>
                      <div className="text-xs text-gray-500 truncate">
                        {ch.description}
                      </div>
                    </div>
                    <div className="flex-shrink-0 ml-2">
                      {ch.channel_id ? (
                        <span className="text-xs text-green-600 font-medium">
                          연결됨
                        </span>
                      ) : (
                        <span className="text-xs text-red-600 font-medium">
                          미연결
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
