"use client";

import { useState, useEffect } from "react";
import type { PipelineEvent } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8101";

const EVENT_TYPES = [
  "search_started",
  "search_progress",
  "filter_progress",
  "subtitle_progress",
  "comment_progress",
  "storage_progress",
  "pipeline_completed",
  "pipeline_error",
];

export function useSSE(runId: string | null) {
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;

    setEvents([]);
    setIsComplete(false);
    setError(null);

    const eventSource = new EventSource(
      `${API_URL}/api/pipeline/status/${runId}`
    );

    EVENT_TYPES.forEach((type) => {
      eventSource.addEventListener(type, (event) => {
        const data = JSON.parse(event.data);
        setEvents((prev) => [...prev, { type, data }]);

        if (type === "pipeline_completed") {
          setIsComplete(true);
          eventSource.close();
        }
        if (type === "pipeline_error") {
          setError(data.error || "Pipeline failed");
          setIsComplete(true);
          eventSource.close();
        }
      });
    });

    eventSource.onerror = () => {
      if (!isComplete) {
        setError("SSE connection lost");
      }
      eventSource.close();
    };

    return () => eventSource.close();
  }, [runId]);

  return { events, isComplete, error };
}
