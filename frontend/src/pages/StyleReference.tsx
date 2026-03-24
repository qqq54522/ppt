import { useState, useRef, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ImagePlus, X, Loader2, ArrowLeft, Sparkles, Upload, Trash2 } from "lucide-react";
import { useProjectStore } from "../store/useProjectStore";
import { uploadFile, generateBackground } from "../api/endpoints";
import { getImageUrl } from "../api/client";

const PRESETS = [
  { id: "business", label: "商务", desc: "简洁专业，深蓝配色" },
  { id: "academic", label: "学术", desc: "严谨规范，白底黑字" },
  { id: "tech", label: "科技", desc: "渐变背景，未来感" },
  { id: "minimal", label: "简约", desc: "大留白，极简风格" },
  { id: "creative", label: "创意", desc: "色彩丰富，自由排版" },
  { id: "education", label: "教育", desc: "温暖色调，清晰易读" },
];

export default function StyleReference() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { currentProject, syncProject, setStyleConfig, generateOutline, isLoading } = useProjectStore();
  const fileRef = useRef<HTMLInputElement>(null);
  const bgFileRef = useRef<HTMLInputElement>(null);

  const [refImages, setRefImages] = useState<string[]>([]);
  const [styleDesc, setStyleDesc] = useState("");
  const [selectedPreset, setSelectedPreset] = useState("");
  const [aspectRatio, setAspectRatio] = useState<"16:9" | "4:3">("16:9");
  const [globalStylePrompt, setGlobalStylePrompt] = useState("");
  const [showGlobalStyle, setShowGlobalStyle] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [bgTemplate, setBgTemplate] = useState("");
  const [bgGenerating, setBgGenerating] = useState(false);
  const [bgUploading, setBgUploading] = useState(false);

  useEffect(() => {
    if (projectId && (!currentProject || currentProject.id !== projectId)) {
      syncProject(projectId);
    }
  }, [projectId, currentProject, syncProject]);

  useEffect(() => {
    if (!currentProject?.style_config) return;
    const sc = currentProject.style_config;
    if (sc.reference_images?.length) setRefImages(sc.reference_images);
    if (sc.style_description) setStyleDesc(sc.style_description);
    if (sc.preset) setSelectedPreset(sc.preset);
    if (sc.aspect_ratio) setAspectRatio(sc.aspect_ratio);
    if (sc.global_style_prompt) {
      setGlobalStylePrompt(sc.global_style_prompt);
      setShowGlobalStyle(true);
    }
    if (sc.background_template) setBgTemplate(sc.background_template);
  }, [currentProject?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !projectId) return;
    setUploading(true);
    try {
      const ref = await uploadFile(file, projectId);
      setRefImages((prev) => [...prev, ref.file_path]);
    } finally {
      setUploading(false);
    }
  }

  function removeImage(idx: number) {
    setRefImages((prev) => prev.filter((_, i) => i !== idx));
  }

  async function handleGenerateBackground() {
    if (!projectId) return;
    setBgGenerating(true);
    try {
      await setStyleConfig({
        reference_images: refImages,
        style_description: styleDesc,
        preset: selectedPreset,
        aspect_ratio: aspectRatio,
        ...(globalStylePrompt ? { global_style_prompt: globalStylePrompt } : {}),
      });
      const updated = await generateBackground(projectId);
      if (updated.style_config?.background_template) {
        setBgTemplate(updated.style_config.background_template);
      }
      await syncProject(projectId);
    } finally {
      setBgGenerating(false);
    }
  }

  async function handleBgUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !projectId) return;
    setBgUploading(true);
    try {
      const ref = await uploadFile(file, projectId);
      setBgTemplate(ref.file_path);
      await setStyleConfig({
        reference_images: refImages,
        style_description: styleDesc,
        preset: selectedPreset,
        aspect_ratio: aspectRatio,
        background_template: ref.file_path,
        ...(globalStylePrompt ? { global_style_prompt: globalStylePrompt } : {}),
      });
    } finally {
      setBgUploading(false);
      if (bgFileRef.current) bgFileRef.current.value = "";
    }
  }

  function handleRemoveBg() {
    setBgTemplate("");
  }

  async function handleStart() {
    await setStyleConfig({
      reference_images: refImages,
      style_description: styleDesc,
      preset: selectedPreset,
      aspect_ratio: aspectRatio,
      background_template: bgTemplate || undefined,
      ...(globalStylePrompt ? { global_style_prompt: globalStylePrompt } : {}),
    });
    await generateOutline();
    navigate(`/project/${projectId}/outline`);
  }

  return (
    <div className="min-h-screen flex flex-col items-center py-10 px-4">
      <div className="w-full max-w-2xl">
        <button onClick={() => navigate("/")} className="flex items-center gap-1 text-slate-500 hover:text-slate-700 mb-6">
          <ArrowLeft size={16} /> 返回
        </button>

        <h2 className="text-2xl font-bold text-slate-800 mb-1">风格参考</h2>
        <p className="text-slate-500 text-sm mb-8">上传参考图或描述你想要的 PPT 风格</p>

        {/* Reference images */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">参考图片（可选）</h3>
          <div className="flex gap-3 flex-wrap">
            {refImages.map((img, i) => (
              <div key={i} className="relative w-24 h-24 rounded-lg overflow-hidden border border-slate-200">
                <img src={`/uploads/${img}`} alt="" className="w-full h-full object-cover" />
                <button onClick={() => removeImage(i)} className="absolute top-0.5 right-0.5 bg-black/50 rounded-full p-0.5">
                  <X size={12} className="text-white" />
                </button>
              </div>
            ))}
            {refImages.length < 3 && (
              <button
                onClick={() => fileRef.current?.click()}
                className="w-24 h-24 border-2 border-dashed border-slate-300 rounded-lg flex flex-col items-center justify-center text-slate-400 hover:border-primary-400 hover:text-primary-500 transition-colors"
              >
                {uploading ? <Loader2 className="animate-spin" size={20} /> : <ImagePlus size={20} />}
                <span className="text-xs mt-1">上传</span>
              </button>
            )}
          </div>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
        </div>

        {/* Style description */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">风格描述（可选）</h3>
          <textarea
            value={styleDesc}
            onChange={(e) => setStyleDesc(e.target.value)}
            rows={3}
            placeholder="例如：简约商务风格，深蓝和白色为主色调，扁平化图标"
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {/* Presets */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">预设风格</h3>
          <div className="grid grid-cols-3 gap-3">
            {PRESETS.map((p) => (
              <button
                key={p.id}
                onClick={() => setSelectedPreset(p.id === selectedPreset ? "" : p.id)}
                className={`p-3 rounded-lg border text-left transition-colors ${
                  selectedPreset === p.id
                    ? "border-primary-500 bg-primary-50 text-primary-700"
                    : "border-slate-200 hover:border-slate-300"
                }`}
              >
                <p className="text-sm font-medium">{p.label}</p>
                <p className="text-xs text-slate-400 mt-0.5">{p.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Aspect ratio */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">画面比例</h3>
          <div className="flex gap-3">
            {(["16:9", "4:3"] as const).map((r) => (
              <button
                key={r}
                onClick={() => setAspectRatio(r)}
                className={`px-6 py-2 rounded-lg border text-sm font-medium transition-colors ${
                  aspectRatio === r
                    ? "border-primary-500 bg-primary-50 text-primary-700"
                    : "border-slate-200 text-slate-600 hover:border-slate-300"
                }`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>

        {/* Background template */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-sm font-semibold text-slate-700">统一底图模板</h3>
            {bgTemplate && (
              <button onClick={handleRemoveBg} className="text-xs text-slate-400 hover:text-red-500 flex items-center gap-1">
                <Trash2 size={12} /> 移除底图
              </button>
            )}
          </div>
          <p className="text-xs text-slate-400 mb-4">
            所有页面将共用同一张背景底图，AI 在底图上排版文字和图表，确保风格完全统一。
          </p>

          {bgTemplate ? (
            <div className="relative rounded-lg overflow-hidden border border-slate-200 bg-slate-50">
              <img
                src={getImageUrl(bgTemplate)}
                alt="底图模板"
                className="w-full aspect-video object-contain"
              />
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/50 to-transparent p-3">
                <p className="text-xs text-white/90">当前底图模板（生成页面时将自动使用）</p>
              </div>
            </div>
          ) : (
            <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center">
              <p className="text-sm text-slate-400 mb-4">还没有底图模板</p>
              <div className="flex gap-3 justify-center">
                <button
                  onClick={handleGenerateBackground}
                  disabled={bgGenerating}
                  className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-40 flex items-center gap-1.5 transition-colors"
                >
                  {bgGenerating ? <Loader2 className="animate-spin" size={14} /> : <Sparkles size={14} />}
                  AI 生成底图
                </button>
                <button
                  onClick={() => bgFileRef.current?.click()}
                  disabled={bgUploading}
                  className="px-4 py-2 rounded-lg text-sm font-medium border border-slate-300 text-slate-600 hover:bg-slate-50 flex items-center gap-1.5 transition-colors"
                >
                  {bgUploading ? <Loader2 className="animate-spin" size={14} /> : <Upload size={14} />}
                  上传底图
                </button>
              </div>
            </div>
          )}

          {bgTemplate && (
            <button
              onClick={handleGenerateBackground}
              disabled={bgGenerating}
              className="mt-3 w-full py-2 rounded-lg text-sm border border-slate-300 text-slate-600 hover:bg-slate-50 flex items-center justify-center gap-1.5 transition-colors"
            >
              {bgGenerating ? <Loader2 className="animate-spin" size={14} /> : <Sparkles size={14} />}
              重新生成底图
            </button>
          )}

          <input ref={bgFileRef} type="file" accept="image/*" className="hidden" onChange={handleBgUpload} />
        </div>

        {/* Global style prompt */}
        {showGlobalStyle && (
          <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-slate-700">全局风格提示词</h3>
              <button
                onClick={() => setGlobalStylePrompt("")}
                className="text-xs text-slate-400 hover:text-red-500"
              >
                清空（下次出图时自动重新生成）
              </button>
            </div>
            <p className="text-xs text-slate-400 mb-2">
              首次生成图片时 AI 会自动生成此段文字，后续每页都会携带以保持风格一致。你也可以手动修改。
            </p>
            <textarea
              value={globalStylePrompt}
              onChange={(e) => setGlobalStylePrompt(e.target.value)}
              rows={5}
              placeholder="AI 将在首次出图时自动生成…"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        )}

        {!showGlobalStyle && globalStylePrompt === "" && (
          <button
            onClick={() => setShowGlobalStyle(true)}
            className="text-xs text-primary-500 hover:underline mb-4"
          >
            高级：查看 / 编辑全局风格提示词
          </button>
        )}

        {/* Start */}
        <button
          onClick={handleStart}
          disabled={isLoading}
          className="w-full py-3 rounded-xl font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-40 transition-colors flex items-center justify-center gap-2"
        >
          {isLoading ? <Loader2 className="animate-spin" size={18} /> : null}
          开始生成大纲
        </button>
      </div>
    </div>
  );
}
