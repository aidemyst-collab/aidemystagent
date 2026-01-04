import { getApiUrl } from '../config/api';
import { useAuthStore } from '../features/auth/authStore';

interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
}

class ApiClient {
  private isRefreshing = false;
  private refreshPromise: Promise<void> | null = null;

  private async refreshToken(): Promise<void> {
    const { tokens, updateTokens, logout } = useAuthStore.getState();

    if (!tokens?.refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await fetch(getApiUrl('/auth/refresh'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: tokens.refreshToken }),
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const data = await response.json();
      updateTokens({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
      });
    } catch (error) {
      // If refresh fails, clear auth and force re-login
      logout();
      throw error;
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { skipAuth, ...fetchOptions } = options;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(fetchOptions.headers as Record<string, string>),
    };

    if (!skipAuth) {
      const { tokens, switchedOrganization } = useAuthStore.getState();
      if (tokens?.accessToken) {
        headers['Authorization'] = `Bearer ${tokens.accessToken}`;
      }
      // Include organization switch header for platform admins
      if (switchedOrganization?.id) {
        headers['X-Organization-Id'] = switchedOrganization.id;
      }
    }

    const response = await fetch(getApiUrl(endpoint), {
      ...fetchOptions,
      headers,
    });

    const contentType = response.headers.get('content-type');
    const isJson = contentType?.includes('application/json');

    // Handle 401 Unauthorized - attempt token refresh
    if (response.status === 401 && !skipAuth && !endpoint.includes('/auth/')) {
      // Prevent multiple simultaneous refresh attempts
      if (this.isRefreshing) {
        await this.refreshPromise;
      } else {
        this.isRefreshing = true;
        this.refreshPromise = this.refreshToken();
        try {
          await this.refreshPromise;
        } finally {
          this.isRefreshing = false;
          this.refreshPromise = null;
        }
      }

      // Retry the original request with the new token
      return this.request<T>(endpoint, options);
    }

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

      if (isJson) {
        const error = await response.json().catch(() => null);
        errorMessage = error?.message || error?.detail || errorMessage;
      }

      throw new Error(errorMessage);
    }

    // Handle 204 No Content (common for DELETE requests)
    if (response.status === 204) {
      return undefined as T;
    }

    // Only parse JSON if content-type is JSON
    if (isJson) {
      return response.json();
    }

    // If no content type or empty response, return undefined
    if (!contentType || response.headers.get('content-length') === '0') {
      return undefined as T;
    }

    // If expecting JSON but got something else, throw error
    throw new Error(`Expected JSON response but got ${contentType || 'unknown'}`);
  }

  get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  post<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  put<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  patch<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();
