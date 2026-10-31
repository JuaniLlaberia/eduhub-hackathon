export const GENERIC_ERROR_MESSAGE = "No pudimos conectar con el servidor. Probá de nuevo en unos minutos.";

/** A non-2xx API response. `message` is es-AR and safe to show in the UI. */
export class ApiRequestError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

/**
 * Returns `data` from an openapi-fetch result, or throws an ApiRequestError built from the
 * ErrorResponse body (generic es-AR message when the body is not an ErrorResponse).
 * Tests: errors.test.ts.
 */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error === undefined && result.response.ok) return result.data as T;
  const body = result.error as { error?: { code?: unknown; message?: unknown } } | undefined;
  const apiError = typeof body === "object" && body !== null ? body.error : undefined;
  if (apiError && typeof apiError.message === "string" && typeof apiError.code === "string") {
    throw new ApiRequestError(apiError.message, apiError.code, result.response.status);
  }
  throw new ApiRequestError(GENERIC_ERROR_MESSAGE, "internal_error", result.response.status);
}

/** es-AR message to show for any error thrown by a query or mutation. Tests: errors.test.ts. */
export function errorMessage(error: unknown): string {
  return error instanceof ApiRequestError ? error.message : GENERIC_ERROR_MESSAGE;
}
