import { create } from "zustand";
import type { Project, Page, TaskInfo, StyleConfig } from "../types";
import * as api from "../api/endpoints";

interface ProjectState {
  currentProject: Project | null;
  isLoading: boolean;
  error: string;
  taskProgress: number;
  currentTaskId: string;

  createProject: (type: string, content: string) => Promise<Project>;
  syncProject: (id?: string) => Promise<void>;
  updateProject: (data: Partial<Project>) => Promise<void>;
  setStyleConfig: (config: StyleConfig) => Promise<void>;
  generateOutline: () => Promise<void>;
  generateImages: (pageIds?: string[]) => Promise<string>;
  pollTask: (taskId: string) => Promise<TaskInfo>;
  updatePageLocal: (pageId: string, data: Partial<Page>) => void;
  reorderPages: (order: string[]) => Promise<void>;
  setError: (msg: string) => void;
  clearError: () => void;
  reset: () => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  currentProject: null,
  isLoading: false,
  error: "",
  taskProgress: 0,
  currentTaskId: "",

  createProject: async (type, content) => {
    set({ isLoading: true, error: "" });
    try {
      const payload: Record<string, unknown> = { creation_type: type };
      if (type === "idea") payload.idea_prompt = content;
      else if (type === "outline") payload.outline_text = content;
      const project = await api.createProject(payload as Partial<Project>);
      set({ currentProject: project, isLoading: false });
      localStorage.setItem("currentProjectId", project.id);
      return project;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "创建项目失败";
      set({ error: msg, isLoading: false });
      throw e;
    }
  },

  syncProject: async (id?: string) => {
    const pid = id || get().currentProject?.id || localStorage.getItem("currentProjectId");
    if (!pid) return;
    try {
      const project = await api.getProject(pid);
      set({ currentProject: project });
    } catch {
      set({ currentProject: null });
      localStorage.removeItem("currentProjectId");
    }
  },

  updateProject: async (data) => {
    const p = get().currentProject;
    if (!p) return;
    try {
      const updated = await api.updateProject(p.id, data);
      set({ currentProject: updated });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "更新失败";
      set({ error: msg });
    }
  },

  setStyleConfig: async (config) => {
    const p = get().currentProject;
    if (!p) return;
    const updated = await api.updateProject(p.id, { style_config: config } as Partial<Project>);
    set({ currentProject: updated });
  },

  generateOutline: async () => {
    const p = get().currentProject;
    if (!p) return;
    set({ isLoading: true, error: "" });
    try {
      const updated = await api.generateOutline(p.id);
      set({ currentProject: updated, isLoading: false });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "生成大纲失败";
      set({ error: msg, isLoading: false });
    }
  },

  generateImages: async (pageIds) => {
    const p = get().currentProject;
    if (!p) throw new Error("No project");
    set({ isLoading: true, error: "", taskProgress: 0 });
    const { task_id } = await api.generateImages(p.id, pageIds);
    set({ currentTaskId: task_id });
    return task_id;
  },

  pollTask: async (taskId) => {
    const p = get().currentProject;
    if (!p) throw new Error("No project");
    const task = await api.getTaskStatus(p.id, taskId);
    set({ taskProgress: task.progress });
    if (task.status === "completed" || task.status === "failed") {
      set({ isLoading: false });
      if (task.status === "completed") {
        await get().syncProject();
      }
      if (task.status === "failed") {
        set({ error: task.error || "任务失败" });
      }
    }
    return task;
  },

  updatePageLocal: (pageId, data) => {
    const p = get().currentProject;
    if (!p) return;
    const pages = p.pages.map((pg) => (pg.id === pageId ? { ...pg, ...data } : pg));
    set({ currentProject: { ...p, pages } });
  },

  reorderPages: async (order) => {
    const p = get().currentProject;
    if (!p) return;
    const pages = await api.reorderPages(p.id, order);
    set({ currentProject: { ...p, pages } });
  },

  setError: (msg) => set({ error: msg }),
  clearError: () => set({ error: "" }),
  reset: () => set({ currentProject: null, isLoading: false, error: "", taskProgress: 0 }),
}));
