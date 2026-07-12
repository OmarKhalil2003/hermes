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

  // 1. Inject Bearer Access Token if present
  const accessToken = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  if (accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

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

  let response = await fetch(url, fetchOptions);

  // 3. Handle 401 Unauthorized via token refresh flow
  if (response.status === 401 && !endpoint.includes("/auth/login") && !endpoint.includes("/auth/refresh")) {
    const refreshToken = typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null;
    
    if (refreshToken) {
      try {
        // Attempt token refresh
        const refreshResponse = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshResponse.ok) {
          const tokenData = await refreshResponse.json();
          
          if (typeof window !== "undefined") {
            localStorage.setItem("access_token", tokenData.access_token);
            localStorage.setItem("refresh_token", tokenData.refresh_token);
          }

          // Retry original request with new access token
          headers.set("Authorization", `Bearer ${tokenData.access_token}`);
          fetchOptions.headers = headers;
          response = await fetch(url, fetchOptions);
        } else {
          // Refresh token expired or invalid - clear session
          handleLogout();
        }
      } catch (error) {
        console.error("Token refresh failed:", error);
        handleLogout();
      }
    } else {
      handleLogout();
    }
  }

  return response;
}

function handleLogout(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    // Trigger redirect to login
    window.location.href = "/login";
  }
}
