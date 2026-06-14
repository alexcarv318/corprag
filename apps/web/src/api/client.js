export class ApiError extends Error {
  constructor(message, { status, detail } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

const AUTH_SESSION_KEY = "corporate-rag.auth";

export function getAuthSession() {
  try {
    const raw = window.sessionStorage.getItem(AUTH_SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setAuthSession({ user, accessToken }) {
  window.sessionStorage.setItem(AUTH_SESSION_KEY, JSON.stringify({ user, accessToken }));
}

export function clearAuthSession() {
  window.sessionStorage.removeItem(AUTH_SESSION_KEY);
}

export async function apiFetch(path, options = {}) {
  const session = getAuthSession();
  const authHeaders = session?.accessToken ? { Authorization: `Bearer ${session.accessToken}` } : {};
  const response = await fetch(path, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...authHeaders,
      ...options.headers
    }
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : null;

  if (!response.ok) {
    const detail = payload?.detail || response.statusText;
    if (response.status === 401 && !options.suppressAuthExpired) {
      window.dispatchEvent(new CustomEvent("corporate-rag:auth-expired"));
    }
    throw new ApiError(detail, { status: response.status, detail });
  }

  return payload;
}

export function toQueryString(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    if (Array.isArray(value)) {
      value.forEach((item) => query.append(key, item));
      return;
    }
    query.set(key, value);
  });
  const serialized = query.toString();
  return serialized ? `?${serialized}` : "";
}
