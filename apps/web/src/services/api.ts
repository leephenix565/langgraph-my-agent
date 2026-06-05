import type { ErrorCategory, ErrorDetail } from "../types/chat";

export class ApiError extends Error {
  status: number;
  detail?: unknown;
  unavailable: boolean;
  code?: string;
  category?: ErrorCategory;

  constructor(
    message: string,
    options?: {
      status?: number;
      detail?: unknown;
      unavailable?: boolean;
      code?: string;
      category?: ErrorCategory;
    },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options?.status ?? 0;
    this.detail = options?.detail;
    this.unavailable = options?.unavailable ?? false;
    this.code = options?.code;
    this.category = options?.category;
  }
}

function extractDetail(detail: unknown): ErrorDetail | undefined {
  if (!detail || typeof detail !== "object") {
    return undefined;
  }
  if ("detail" in detail) {
    const nested = (detail as { detail?: unknown }).detail;
    if (nested && typeof nested === "object") {
      const typed = nested as ErrorDetail;
      if (typed.message || typed.code || typed.category) {
        return typed;
      }
    }
    if (typeof nested === "string" && nested.trim()) {
      return { message: nested };
    }
  }
  const typed = detail as ErrorDetail;
  if (typed.message || typed.code || typed.category) {
    return typed;
  }
  return undefined;
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function decodeNdjsonLines(buffer: string): { lines: string[]; remainder: string } {
  const normalized = buffer.replace(/\r\n/g, "\n");
  const parts = normalized.split("\n");
  const remainder = parts.pop() ?? "";
  const lines = parts.map((line) => line.trim()).filter(Boolean);
  return { lines, remainder };
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch (error) {
    throw new ApiError("公共 API 不可用", { unavailable: true, detail: error });
  }

  const body = await parseResponseBody(response);
  if (!response.ok) {
    const detail = extractDetail(body);
    throw new ApiError(detail?.message || `API 请求失败，状态码 ${response.status}`, {
      status: response.status,
      detail: body,
      code: detail?.code,
      category: detail?.category,
    });
  }
  return body as T;
}

export async function streamNdjson<T>(
  path: string,
  init: RequestInit | undefined,
  onEvent: (event: T) => void,
): Promise<boolean> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: {
        Accept: "application/x-ndjson, application/json",
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch (error) {
    throw new ApiError("公共 API 不可用", { unavailable: true, detail: error });
  }

  if (!response.ok) {
    const body = await parseResponseBody(response);
    const detail = extractDetail(body);
    throw new ApiError(detail?.message || `API 请求失败，状态码 ${response.status}`, {
      status: response.status,
      detail: body,
      code: detail?.code,
      category: detail?.category,
    });
  }

  if (!response.body || typeof response.body.getReader !== "function") {
    return false;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffered = "";

  while (true) {
    const { value, done } = await reader.read();
    buffered += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const { lines, remainder } = decodeNdjsonLines(buffered);
    buffered = remainder;
    for (const line of lines) {
      onEvent(JSON.parse(line) as T);
    }
    if (done) {
      break;
    }
  }

  const tail = buffered.trim();
  if (tail) {
    onEvent(JSON.parse(tail) as T);
  }
  return true;
}

export function isApiUnavailableError(error: unknown): error is ApiError {
  return error instanceof ApiError && error.unavailable;
}

export function getApiErrorMessage(error: unknown, fallback = "未知 API 错误"): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return fallback;
}
