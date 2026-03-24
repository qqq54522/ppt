import axios from "axios";
import { useProjectStore } from "../store/useProjectStore";

const apiClient = axios.create({
  baseURL: "",
  timeout: 300_000,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  if (config.data instanceof FormData) {
    delete config.headers["Content-Type"];
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!(error.config as Record<string, unknown>)?._silentError) {
      const msg =
        error.response?.data?.message ||
        error.response?.data?.error ||
        error.message ||
        "请求失败";
      useProjectStore.getState().setError(msg);
    }
    return Promise.reject(error);
  }
);

export function getImageUrl(path: string): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `/uploads/${path}?t=${Date.now()}`;
}

export default apiClient;
