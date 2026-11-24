export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export async function request(path, { method = "GET", body } = {}) {
  let response;
  try {
    response = await fetch("/api" + path, {
      method,
      cache: "no-store",
      credentials: "same-origin",
      ...(body === undefined ? {} : {
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    });
  } catch {
    throw new ApiError("Сервер недоступний. Спробуйте повторити запит.", 0);
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (response.status === 401 && !path.startsWith("/auth/")) {
    window.dispatchEvent(new Event("session-expired"));
  }
  if (!response.ok || !data) {
    const detail = typeof data?.detail === "string" ? data.detail : "Не вдалося завершити запит.";
    throw new ApiError(detail, response.status);
  }
  return data;
}
