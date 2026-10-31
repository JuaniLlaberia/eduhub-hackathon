import createClient from "openapi-fetch";
import { createMockFetch, type MockFetch } from "./mock-fetch";
import type { paths } from "./schema";

export const isMockMode = process.env.NEXT_PUBLIC_API_MOCK === "1";

const baseUrl = isMockMode
  ? "http://mock.eduhub.local"
  : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000");

let mockFetch: MockFetch | undefined;

/** Typed client for contract C4. The only way the app talks to the backend. */
export const api = createClient<paths>({
  baseUrl,
  fetch: isMockMode ? (request) => (mockFetch ??= createMockFetch({ delayMs: 400 }))(request) : undefined,
});
