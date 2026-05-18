const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
const normalizedApiBaseUrl = API_BASE_URL?.replace(/\/+$/, "");
const REQUEST_TIMEOUT_MS = 30000;

async function request(path, options = {}) {
  if (!normalizedApiBaseUrl) {
    throw new Error("VITE_API_BASE_URL is not configured.");
  }

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${normalizedApiBaseUrl}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
      signal: controller.signal,
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(formatErrorDetail(data.detail));
    }
    return data;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("The request timed out. Please try again.");
    }
    if (error instanceof TypeError) {
      throw new Error("Unable to reach the backend server.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function formatErrorDetail(detail) {
  if (!detail) return "Request failed. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const firstError = detail[0];
    return firstError?.msg || "Request validation failed.";
  }
  return detail.message || "Request failed. Please try again.";
}

function withBackendSession(sessionId, payload = {}) {
  if (!sessionId || sessionId.startsWith("local-")) {
    return payload;
  }

  return { sessionId, ...payload };
}

export function parseEmailThread(emailThread) {
  return request("/api/email/parse", {
    method: "POST",
    body: JSON.stringify({ emailThread }),
  });
}

export function addEmail(sessionId, emailContent) {
  return request("/api/email/add", {
    method: "POST",
    body: JSON.stringify({ sessionId, emailContent }),
  });
}

export function getSession(sessionId) {
  return request(`/api/session/${sessionId}`);
}

export function generateReply(sessionId, prompt) {
  const payload =
    typeof prompt === "object"
      ? withBackendSession(sessionId, prompt)
      : withBackendSession(sessionId, { agentInstructions: prompt });

  return request("/api/reply/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function regenerateReply(sessionId, options = {}) {
  return request("/api/reply/regenerate", {
    method: "POST",
    body: JSON.stringify(withBackendSession(sessionId, options)),
  });
}

export function resetSession(sessionId) {
  return request("/api/session/reset", {
    method: "POST",
    body: JSON.stringify({ sessionId }),
  });
}
