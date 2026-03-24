import axios from "axios";

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

export function getImageUrl(path: string): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `/uploads/${path}?t=${Date.now()}`;
}

export default apiClient;
