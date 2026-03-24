export interface Project {
  id: string;
  title: string;
  creation_type: "upload" | "idea" | "outline";
  idea_prompt: string;
  outline_text: string;
  document_analysis: Record<string, unknown>;
  style_config: StyleConfig;
  status: string;
  created_at: string;
  updated_at: string;
  pages: Page[];
}

export interface Page {
  id: string;
  project_id: string;
  page_number: number;
  title: string;
  content: string;
  relationship_type: RelationshipType;
  html_content: string;
  /** 方案C视觉层：AI 生成的每页独立视觉背景图（背景+装饰+配图，不含文字） */
  visual_image_path: string;
  /** 最终合成图（视觉层+文字层） */
  image_path: string;
  image_versions: string[];
  status: string;
}

export type RelationshipType =
  | "none"
  | "parallel"
  | "progressive"
  | "hierarchical"
  | "causal"
  | "comparison"
  | "data"
  | "process";

export interface StyleConfig {
  reference_images?: string[];
  style_description?: string;
  preset?: string;
  aspect_ratio?: "16:9" | "4:3";
  /** AI 生成的全局风格锚定提示词，首次出图时自动生成并缓存 */
  global_style_prompt?: string;
  /** AI 生成的统一底图模板路径（相对 uploads），所有页面共用 */
  background_template?: string;
}

export interface TaskInfo {
  id: string;
  project_id: string;
  task_type: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  result: Record<string, unknown>;
  error: string;
}

export interface ReferenceFile {
  id: string;
  project_id: string | null;
  filename: string;
  file_path: string;
  file_type: string;
  analysis_result: Record<string, unknown>;
  status: string;
}

export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

export const RELATIONSHIP_LABELS: Record<RelationshipType, string> = {
  none: "无",
  parallel: "并列",
  progressive: "递进",
  hierarchical: "总分",
  causal: "因果",
  comparison: "对比",
  data: "数据",
  process: "流程",
};
