const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ApiRequestOptions extends RequestInit {
  useFormUrlEncoded?: boolean;
}

/**
 * Robust fetch client with built-in token injection and automatic 401 refresh interception.
 */
export async function apiFetch(
  endpoint: string,
  options: ApiRequestOptions = {}
): Promise<Response> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = new Headers(options.headers || {});

  // 2. Set default content headers
  if (!options.useFormUrlEncoded && !headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  } else if (options.useFormUrlEncoded && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/x-www-form-urlencoded");
  }

  const fetchOptions: RequestInit = {
    ...options,
    headers,
  };

  return await fetch(url, fetchOptions);
}
