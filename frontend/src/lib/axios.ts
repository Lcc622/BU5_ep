import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL || '/';

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const data = error.response?.data;
    const message =
      (typeof data === 'string' ? data : undefined) ||
      data?.detail ||
      data?.message ||
      error.message ||
      'Request failed';
    return Promise.reject(new Error(message));
  }
);
