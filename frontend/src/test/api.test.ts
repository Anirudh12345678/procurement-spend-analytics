import { afterEach, describe, expect, it, vi } from "vitest";
import { api, queryString } from "../api/client";

describe("API client", () => {
  afterEach(() => vi.restoreAllMocks());

  it("returns typed JSON data", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ total: 47 }), { status: 200 }));
    await expect(api.get<{ total: number }>("/sample")).resolves.toEqual({ total: 47 });
  });

  it("retries a read-only request once after a transient network failure", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(new Response(JSON.stringify({ total: 47 }), { status: 200 }));

    await expect(api.get<{ total: number }>("/sample")).resolves.toEqual({ total: 47 });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("exposes consistent backend errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ error: { code: "NOT_FOUND", message: "Missing" } }), { status: 404 }));
    await expect(api.get("/missing")).rejects.toEqual(expect.objectContaining({ status: 404, code: "NOT_FOUND", message: "Missing" }));
  });

  it("omits empty query parameters", () => {
    expect(queryString({ page: 2, supplier_id: "", country: null })).toBe("?page=2");
  });
});
