import type { AlertFeedback, OfflineFeedbackEvent } from "./types";

const QUEUE_KEY = "phantom.offlineFeedbackQueue.v1";

function readQueue(): OfflineFeedbackEvent[] {
  const raw = window.localStorage.getItem(QUEUE_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as OfflineFeedbackEvent[];
  } catch {
    return [];
  }
}

function writeQueue(events: OfflineFeedbackEvent[]) {
  window.localStorage.setItem(QUEUE_KEY, JSON.stringify(events));
}

export function getQueuedFeedback(): OfflineFeedbackEvent[] {
  return readQueue();
}

export function queueFeedback(alertId: string, feedback: AlertFeedback, sessionId: string, repId: string) {
  const current = readQueue();
  current.push({
    idempotency_key: `${repId}:${crypto.randomUUID()}`,
    alert_id: alertId,
    feedback,
    session_id: sessionId,
    notes: "Queued by browser offline mode"
  });
  writeQueue(current);
  return current.length;
}

export function clearQueuedFeedback() {
  writeQueue([]);
}
