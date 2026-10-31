import { notImplemented } from "@/lib/todo";

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
export const unwrap: <T>(result: { data?: T; error?: unknown; response: Response }) => T = notImplemented;

/** es-AR message to show for any error thrown by a query or mutation. Tests: errors.test.ts. */
export const errorMessage: (error: unknown) => string = notImplemented;
