import { notImplemented } from "@/lib/todo";

export type MockFetch = (input: Request) => Promise<Response>;

export interface MockFetchOptions {
  /** Artificial latency per request, so loading states are visible. */
  delayMs?: number;
}

/** Analyzing this handle in mock mode ends in a failed job, to exercise the error UI. */
export const MOCK_FAILING_HANDLE = "error";

/**
 * Fake backend for mock mode (NEXT_PUBLIC_API_MOCK=1): answers every contract route with the
 * shared fixtures, and keeps analysis jobs in memory (one status step per poll).
 * Behavior: mock-fetch.test.ts.
 */
export const createMockFetch: (options?: MockFetchOptions) => MockFetch = notImplemented;
