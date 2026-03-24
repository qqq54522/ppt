import apiClient from "./client";
import type {
  ApiResponse,
  Project,
  Page,
  TaskInfo,
  ReferenceFile,
} from "../types";

// ── Projects ──

export async function createProject(data: Partial<Project>) {
  const res = await apiClient.post<ApiResponse<Project>>("/api/projects", data);
  return res.data.data;
}

export async function getProject(id: string) {
  const res = await apiClient.get<ApiResponse<Project>>(`/api/projects/${id}`);
  return res.data.data;
}

export async function listProjects() {
  const res = await apiClient.get<ApiResponse<Project[]>>("/api/projects");
  return res.data.data;
}

export async function updateProject(id: string, data: Partial<Project>) {
  const res = await apiClient.put<ApiResponse<Project>>(`/api/projects/${id}`, data);
  return res.data.data;
}

export async function deleteProject(id: string) {
  await apiClient.delete(`/api/projects/${id}`);
}

export async function generateOutline(projectId: string) {
  const res = await apiClient.post<ApiResponse<Project>>(
    `/api/projects/${projectId}/generate/outline`
  );
  return res.data.data;
}

export async function generateBackground(projectId: string) {
  const res = await apiClient.post<ApiResponse<Project>>(
    `/api/projects/${projectId}/generate/background`
  );
  return res.data.data;
}

export async function generateImages(projectId: string, pageIds?: string[]) {
  const res = await apiClient.post<ApiResponse<{ task_id: string }>>(
    `/api/projects/${projectId}/generate/images`,
    { page_ids: pageIds }
  );
  return res.data.data;
}

export async function getTaskStatus(projectId: string, taskId: string) {
  const res = await apiClient.get<ApiResponse<TaskInfo>>(
    `/api/projects/${projectId}/tasks/${taskId}`
  );
  return res.data.data;
}

// ── Pages ──

export async function listPages(projectId: string) {
  const res = await apiClient.get<ApiResponse<Page[]>>(
    `/api/projects/${projectId}/pages`
  );
  return res.data.data;
}

export async function createPage(projectId: string, data: Partial<Page>) {
  const res = await apiClient.post<ApiResponse<Page>>(
    `/api/projects/${projectId}/pages`,
    data
  );
  return res.data.data;
}

export async function updatePage(projectId: string, pageId: string, data: Partial<Page>) {
  const res = await apiClient.put<ApiResponse<Page>>(
    `/api/projects/${projectId}/pages/${pageId}`,
    data
  );
  return res.data.data;
}

export async function deletePage(projectId: string, pageId: string) {
  await apiClient.delete(`/api/projects/${projectId}/pages/${pageId}`);
}

export async function regeneratePageImage(
  projectId: string,
  pageId: string,
  layer: "all" | "visual" | "text" = "all"
) {
  const res = await apiClient.post<ApiResponse<Page>>(
    `/api/projects/${projectId}/pages/${pageId}/regenerate`,
    { layer }
  );
  return res.data.data;
}

export async function replaceText(
  projectId: string,
  pageId: string,
  oldText: string,
  newText: string,
  extraPrompt?: string
) {
  const res = await apiClient.post<ApiResponse<Page>>(
    `/api/projects/${projectId}/pages/${pageId}/replace-text`,
    { old_text: oldText, new_text: newText, extra_prompt: extraPrompt || "" }
  );
  return res.data.data;
}

export async function maskEdit(
  projectId: string,
  pageId: string,
  region: { x: number; y: number; width: number; height: number },
  prompt: string
) {
  const res = await apiClient.post<ApiResponse<Page>>(
    `/api/projects/${projectId}/pages/${pageId}/mask-edit`,
    { region, prompt }
  );
  return res.data.data;
}

export async function renderHtml(projectId: string, pageId: string, htmlContent: string) {
  const res = await apiClient.post<ApiResponse<Page>>(
    `/api/projects/${projectId}/pages/${pageId}/render-html`,
    { html_content: htmlContent }
  );
  return res.data.data;
}

export async function reorderPages(projectId: string, order: string[]) {
  const res = await apiClient.put<ApiResponse<Page[]>>(
    `/api/projects/${projectId}/pages/reorder`,
    { order }
  );
  return res.data.data;
}

// ── Files ──

export async function uploadFile(file: File, projectId?: string, silent = false) {
  const form = new FormData();
  form.append("file", file);
  if (projectId) form.append("project_id", projectId);
  const res = await apiClient.post<ApiResponse<ReferenceFile>>("/api/files/upload", form, {
    _silentError: silent,
  } as Record<string, unknown>);
  return res.data.data;
}

export async function analyzeFile(refId: string, silent = false) {
  const res = await apiClient.post<ApiResponse<ReferenceFile>>(
    `/api/files/${refId}/analyze`,
    {},
    { _silentError: silent } as Record<string, unknown>,
  );
  return res.data.data;
}

export async function listFiles(projectId?: string) {
  const params = projectId ? { project_id: projectId } : {};
  const res = await apiClient.get<ApiResponse<ReferenceFile[]>>("/api/files", { params });
  return res.data.data;
}

// ── Export ──

export async function exportPdf(projectId: string) {
  const res = await apiClient.post(`/api/projects/${projectId}/export/pdf`, {}, {
    responseType: "blob",
  });
  return res.data as Blob;
}

export async function exportImagesZip(projectId: string) {
  const res = await apiClient.post(`/api/projects/${projectId}/export/images`, {}, {
    responseType: "blob",
  });
  return res.data as Blob;
}
