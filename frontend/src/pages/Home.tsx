import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, Sparkles, List, FileText, Loader2, AlertCircle } from "lucide-react";
import { useProjectStore } from "../store/useProjectStore";
import { uploadFile, analyzeFile } from "../api/endpoints";

type TabKey = "upload" | "idea" | "outline";

export default function Home() {
  const [tab, setTab] = useState<TabKey>("upload");
  const [ideaText, setIdeaText] = useState("");
  const [outlineText, setOutlineText] = useState("");
  const [uploadedFile, setUploadedFile] = useState<{ id: string; name: string } | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { createProject, updateProject, isLoading } = useProjectStore();

  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: "upload", label: "上传分析", icon: <Upload size={18} /> },
    { key: "idea", label: "一句话生成", icon: <Sparkles size={18} /> },
    { key: "outline", label: "大纲生成", icon: <List size={18} /> },
  ];

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setAnalyzing(true);
    setUploadError("");
    setUploadedFile(null);
    try {
      const ref = await uploadFile(file, undefined, true);
      const analyzed = await analyzeFile(ref.id, true);
      setUploadedFile({ id: analyzed.id, name: file.name });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { message?: string } }; message?: string };
      const detail = axiosErr?.response?.data?.message || axiosErr?.message || "";
      setUploadError(
        detail
          ? `分析失败：${detail}`
          : "文档上传或分析失败，请检查后端服务是否运行，然后重试"
      );
    } finally {
      setAnalyzing(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function handleNext() {
    let project;
    if (tab === "upload" && uploadedFile) {
      project = await createProject("upload", "");
      await updateProject({ document_analysis: { ref_file_id: uploadedFile.id } });
    } else if (tab === "idea" && ideaText.trim()) {
      project = await createProject("idea", ideaText.trim());
    } else if (tab === "outline" && outlineText.trim()) {
      project = await createProject("outline", outlineText.trim());
    }
    if (project) {
      navigate(`/style/${project.id}`);
    }
  }

  const canProceed =
    (tab === "upload" && uploadedFile) ||
    (tab === "idea" && ideaText.trim().length > 0) ||
    (tab === "outline" && outlineText.trim().length > 0);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      {/* Header */}
      <div className="mb-10 text-center">
        <h1 className="text-4xl font-bold text-primary-600 tracking-tight">AI-PPT</h1>
        <p className="mt-2 text-slate-500">AI 驱动的智能演示文稿生成</p>
      </div>

      {/* Card */}
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden">
        {/* Tabs */}
        <div className="flex border-b border-slate-200">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex-1 flex items-center justify-center gap-2 py-4 text-sm font-medium transition-colors ${
                tab === t.key
                  ? "text-primary-600 border-b-2 border-primary-600 bg-primary-50/50"
                  : "text-slate-500 hover:text-slate-700 hover:bg-slate-50"
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-6">
          {tab === "upload" && (
            <div>
              <div
                onClick={() => !analyzing && fileRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors ${
                  uploadError
                    ? "border-red-300 bg-red-50/30"
                    : analyzing
                      ? "border-primary-300 bg-primary-50/30 cursor-wait"
                      : "border-slate-300 cursor-pointer hover:border-primary-400 hover:bg-primary-50/30"
                }`}
              >
                {analyzing ? (
                  <div className="flex flex-col items-center gap-2">
                    <Loader2 className="animate-spin text-primary-500" size={32} />
                    <p className="text-slate-500">AI 正在分析文档...</p>
                    <p className="text-xs text-slate-400">大文件可能需要较长时间，请耐心等待</p>
                  </div>
                ) : uploadError ? (
                  <div className="flex flex-col items-center gap-2">
                    <AlertCircle className="text-red-400" size={32} />
                    <p className="text-sm text-red-600">{uploadError}</p>
                    <p className="text-xs text-slate-400 mt-1">点击重新上传</p>
                  </div>
                ) : uploadedFile ? (
                  <div className="flex flex-col items-center gap-2">
                    <FileText className="text-green-500" size={32} />
                    <p className="font-medium text-slate-700">{uploadedFile.name}</p>
                    <p className="text-xs text-green-600">分析完成，点击更换文件</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2">
                    <Upload className="text-slate-400" size={32} />
                    <p className="text-slate-500">点击或拖拽上传文档</p>
                    <p className="text-xs text-slate-400">支持 PDF / DOCX / TXT / MD</p>
                  </div>
                )}
              </div>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.docx,.doc,.txt,.md"
                className="hidden"
                onChange={handleFileUpload}
              />
            </div>
          )}

          {tab === "idea" && (
            <div>
              <input
                type="text"
                value={ideaText}
                onChange={(e) => setIdeaText(e.target.value)}
                placeholder="例如：人工智能在教育领域的应用"
                className="w-full px-4 py-3 border border-slate-300 rounded-xl text-base focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
              <p className="mt-2 text-xs text-slate-400">输入一个主题，AI 将自动生成完整的 PPT</p>
            </div>
          )}

          {tab === "outline" && (
            <div>
              <textarea
                value={outlineText}
                onChange={(e) => setOutlineText(e.target.value)}
                rows={8}
                placeholder={"# 标题\n## 第一章 引言\n- 要点1\n- 要点2\n## 第二章 核心内容\n- 要点1"}
                className="w-full px-4 py-3 border border-slate-300 rounded-xl text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
              <p className="mt-2 text-xs text-slate-400">使用 Markdown 格式输入大纲</p>
            </div>
          )}

          {/* Next button */}
          <button
            onClick={handleNext}
            disabled={!canProceed || isLoading}
            className="mt-6 w-full py-3 rounded-xl font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {isLoading ? <Loader2 className="animate-spin" size={18} /> : null}
            下一步：设置风格
          </button>
        </div>
      </div>
    </div>
  );
}
