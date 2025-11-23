import { getApiUrl } from '../config/api';
import { useAuthStore } from '../features/auth/authStore';

interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
}

class ApiClient {
  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { skipAuth, ...fetchOptions } = options;

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...fetchOptions.headers,
    };

    if (!skipAuth) {
      const { tokens } = useAuthStore.getState();
      if (tokens?.accessToken) {
        headers['Authorization'] = `Bearer ${tokens.accessToken}`;
      }
    }

    const response = await fetch(getApiUrl(endpoint), {
      ...fetchOptions,
      headers,
    });

    const contentType = response.headers.get('content-type');
    const isJson = contentType?.includes('application/json');

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

      if (isJson) {
        const error = await response.json().catch(() => null);
        errorMessage = error?.message || error?.detail || errorMessage;
      }

      throw new Error(errorMessage);
    }

    // Only parse JSON if content-type is JSON
    if (isJson) {
      return response.json();
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

  delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();
