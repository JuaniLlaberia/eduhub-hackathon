import { describe, expect, it } from "vitest";
import { ApiRequestError, errorMessage, GENERIC_ERROR_MESSAGE, unwrap } from "./errors";

function response(status: number) {
  return new Response(null, { status });
}

describe("unwrap", () => {
  it("returns the data of a successful response", () => {
    expect(unwrap({ data: { status: "ok" }, response: response(200) })).toEqual({ status: "ok" });
  });

  it("throws the backend's es-AR message, code and status", () => {
    const result = {
      error: { error: { code: "account_not_found", message: "No encontramos la cuenta." } },
      response: response(404),
    };
    expect(() => unwrap(result)).toThrow(ApiRequestError);
    try {
      unwrap(result);
    } catch (error) {
      expect(error).toMatchObject({
        message: "No encontramos la cuenta.",
        code: "account_not_found",
        status: 404,
      });
    }
  });

  it("uses a generic es-AR message when the body is not an ErrorResponse", () => {
    try {
      unwrap({ error: "Bad gateway", response: response(502) });
      expect.unreachable();
    } catch (error) {
      expect(error).toMatchObject({ message: GENERIC_ERROR_MESSAGE, code: "internal_error", status: 502 });
    }
  });
});

describe("errorMessage", () => {
  it("shows the message of an API error", () => {
    expect(errorMessage(new ApiRequestError("No encontramos la cuenta.", "account_not_found", 404))).toBe(
      "No encontramos la cuenta.",
    );
  });

  it("hides network and unexpected errors behind the generic message", () => {
    expect(errorMessage(new TypeError("Failed to fetch"))).toBe(GENERIC_ERROR_MESSAGE);
    expect(errorMessage("boom")).toBe(GENERIC_ERROR_MESSAGE);
  });
});
