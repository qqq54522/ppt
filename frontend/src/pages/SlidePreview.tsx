import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft, RefreshCw, Type, Scissors, Code2,
  ChevronLeft, ChevronRight, Loader2, FileDown, Image as ImageIcon,
  Layers, ImagePlus, FileText,
} from "lucide-react";
import { useProjectStore } from "../store/useProjectStore";
import {
  regeneratePageImage, replaceText, maskEdit, renderHtml,
  exportPdf, exportImagesZip,
} from "../api/endpoints";
import { getImageUrl } from "../api/client";
import { RELATIONSHIP_LABELS, type Page } from "../types";

/** 将容器内坐标（object-contain 留白）换算为图片原始像素坐标 */
function containerRegionToNatural(
  containerW: number,
  containerH: number,
  naturalW: number,
  naturalH: number,
  region: { x: number; y: number; width: number; height: number }
) {
  if (naturalW <= 0 || naturalH <= 0) {
    return { x: 0, y: 0, width: 0, height: 0 };
  }
  const scale = Math.min(containerW / naturalW, containerH / naturalH);
  const drawnW = naturalW * scale;
  const drawnH = naturalH * scale;
  const offsetX = (containerW - drawnW) / 2;
  const offsetY = (containerH - drawnH) / 2;

  let x = Math.round((region.x - offsetX) / scale);
  let y = Math.round((region.y - offsetY) / scale);
  let w = Math.round(region.width / scale);
  let h = Math.round(region.height / scale);

  x = Math.max(0, Math.min(x, naturalW - 1));
  y = Math.max(0, Math.min(y, naturalH - 1));
  w = Math.max(1, Math.min(w, naturalW - x));
  h = Math.max(1, Math.min(h, naturalH - y));
  return { x, y, width: w, height: h };
}

export default function SlidePreview() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { currentProject, syncProject, generateImages, pollTask, isLoading, taskProgress, currentTaskId, setError } = useProjectStore();

  const [currentIdx, setCurrentIdx] = useState(0);
  const [showReplace, setShowReplace] = useState(false);
  const [showMask, setShowMask] = useState(false);
  const [replaceOld, setReplaceOld] = useState("");
  const [replaceNew, setReplaceNew] = useState("");
  const [replacePrompt, setReplacePrompt] = useState("");
  const [maskPrompt, setMaskPrompt] = useState("");
  const [maskRegion, setMaskRegion] = useState({ x: 0, y: 0, width: 0, height: 0 });
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawStart, setDrawStart] = useState({ x: 0, y: 0 });
  const [pageLoading, setPageLoading] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [showRegenConfirm, setShowRegenConfirm] = useState(false);
  const [showHtmlEditor, setShowHtmlEditor] = useState(false);
  const [editingHtml, setEditingHtml] = useState("");
  const canvasRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  const pages = currentProject?.pages || [];
  const currentPage = pages[currentIdx];
  const hasAnyImage = pages.some((p) => p.image_path);

  useEffect(() => {
    if (projectId) syncProject(projectId);
  }, [projectId, syncProject]);

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  async function handleGenerateAll() {
    if (!projectId) return;
    const taskId = await generateImages();
    let polling = false;
    pollRef.current = setInterval(async () => {
      if (polling) return;
      polling = true;
      try {
        const task = await pollTask(taskId);
        if (task.status !== "completed" && task.status !== "failed") {
          await syncProject(projectId);
        }
        if (task.status === "completed" || task.status === "failed") {
          clearInterval(pollRef.current);
          await syncProject(projectId);
        }
      } finally {
        polling = false;
      }
    }, 2000);
  }

  async function handleRegenerate(page: Page, layer: "all" | "visual" | "text" = "all") {
    if (!projectId) return;
    setPageLoading(page.id);
    try {
      await regeneratePageImage(projectId, page.id, layer);
      await syncProject(projectId);
    } catch (err) {
      console.error("Regenerate failed:", err);
      const layerName = layer === "visual" ? "视觉层" : layer === "text" ? "文字层" : "页面";
      setError(`重新生成${layerName}失败，请重试`);
    } finally {
      setPageLoading(null);
    }
  }

  async function handleReplaceText() {
    if (!projectId || !currentPage) return;
    setPageLoading(currentPage.id);
    try {
      await replaceText(projectId, currentPage.id, replaceOld, replaceNew, replacePrompt);
      await syncProject(projectId);
      setShowReplace(false);
      setReplaceOld(""); setReplaceNew(""); setReplacePrompt("");
    } catch (err) {
      console.error("Replace text failed:", err);
      setError("文字替换失败，请重试");
    } finally {
      setPageLoading(null);
    }
  }

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (!showMask || !canvasRef.current) return;
    e.preventDefault();
    const rect = canvasRef.current.getBoundingClientRect();
    setDrawStart({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setMaskRegion({ x: 0, y: 0, width: 0, height: 0 });
    setIsDrawing(true);
  }, [showMask]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDrawing || !canvasRef.current) return;
    e.preventDefault();
    const rect = canvasRef.current.getBoundingClientRect();
    const curX = e.clientX - rect.left;
    const curY = e.clientY - rect.top;
    setMaskRegion({
      x: Math.min(drawStart.x, curX),
      y: Math.min(drawStart.y, curY),
      width: Math.abs(curX - drawStart.x),
      height: Math.abs(curY - drawStart.y),
    });
  }, [isDrawing, drawStart]);

  const handleMouseUp = useCallback(() => { setIsDrawing(false); }, []);

  async function handleMaskEdit() {
    if (!projectId || !currentPage || !imgRef.current || !canvasRef.current) return;
    setPageLoading(currentPage.id);
    try {
      const img = imgRef.current;
      const cw = canvasRef.current.clientWidth;
      const ch = canvasRef.current.clientHeight;
      const scaledRegion = containerRegionToNatural(
        cw,
        ch,
        img.naturalWidth,
        img.naturalHeight,
        maskRegion
      );
      await maskEdit(projectId, currentPage.id, scaledRegion, maskPrompt);
      await syncProject(projectId);
      setShowMask(false);
      setMaskPrompt("");
      setMaskRegion({ x: 0, y: 0, width: 0, height: 0 });
    } catch (err) {
      console.error("Mask edit failed:", err);
      setError("遮罩重绘失败，请重试");
    } finally {
      setPageLoading(null);
    }
  }

  function handleOpenHtmlEditor() {
    if (!currentPage) return;
    setEditingHtml(currentPage.html_content || "");
    setShowHtmlEditor(true);
    setShowReplace(false);
    setShowMask(false);
  }

  async function handleRenderHtml() {
    if (!projectId || !currentPage) return;
    setPageLoading(currentPage.id);
    try {
      await renderHtml(projectId, currentPage.id, editingHtml);
      await syncProject(projectId);
      setShowHtmlEditor(false);
    } catch (err) {
      console.error("Render HTML failed:", err);
      setError("HTML 渲染失败，请重试");
    } finally {
      setPageLoading(null);
    }
  }

  async function handleExport(type: "pdf" | "images") {
    if (!projectId) return;
    setExporting(true);
    try {
      const blob = type === "pdf" ? await exportPdf(projectId) : await exportImagesZip(projectId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = type === "pdf" ? `${currentProject?.title || "slides"}.pdf` : `${currentProject?.title || "slides"}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(`/project/${projectId}/outline`)} className="text-slate-500 hover:text-slate-700">
            <ArrowLeft size={18} />
          </button>
          <h1 className="text-lg font-bold text-slate-800">{currentProject?.title || "预览"}</h1>
          {isLoading && (
            <div className="flex items-center gap-2 text-sm text-primary-600">
              <Loader2 className="animate-spin" size={14} />
              生成中 {Math.round(taskProgress)}%
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!hasAnyImage && (
            <button onClick={handleGenerateAll} disabled={isLoading || pages.length === 0}
              className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-40 flex items-center gap-1">
              <RefreshCw size={14} /> 生成全部页面
            </button>
          )}
          {hasAnyImage && (
            <>
              <button
                onClick={() => setShowRegenConfirm(true)}
                disabled={isLoading}
                className="px-3 py-2 rounded-lg text-sm font-medium text-white bg-amber-500 hover:bg-amber-600 disabled:opacity-40 flex items-center gap-1"
              >
                <RefreshCw size={14} /> 全部重新生成
              </button>
              <button onClick={() => handleExport("pdf")} disabled={exporting}
                className="px-3 py-2 rounded-lg text-sm border border-slate-300 text-slate-600 hover:bg-slate-50 flex items-center gap-1">
                <FileDown size={14} /> PDF
              </button>
              <button onClick={() => handleExport("images")} disabled={exporting}
                className="px-3 py-2 rounded-lg text-sm border border-slate-300 text-slate-600 hover:bg-slate-50 flex items-center gap-1">
                <ImageIcon size={14} /> 图片
              </button>
            </>
          )}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar thumbnails */}
        <div className="w-48 border-r border-slate-200 bg-white overflow-y-auto p-3 space-y-2">
          {pages.map((page, idx) => (
            <div
              key={page.id}
              onClick={() => setCurrentIdx(idx)}
              className={`cursor-pointer rounded-lg border-2 p-1 transition-colors relative ${
                idx === currentIdx ? "border-primary-500" : "border-transparent hover:border-slate-300"
              }`}
            >
              {page.image_path ? (
                <img src={getImageUrl(page.image_path)} alt="" className="w-full rounded aspect-video object-cover" />
              ) : (
                <div className="w-full aspect-video bg-slate-100 rounded flex items-center justify-center text-slate-400 text-xs">
                  {pageLoading === page.id ? <Loader2 className="animate-spin" size={16} /> : `#${page.page_number}`}
                </div>
              )}
              {page.relationship_type !== "none" && (
                <span className="absolute top-2 right-2 text-[10px] px-1.5 py-0.5 rounded bg-blue-500 text-white">
                  {RELATIONSHIP_LABELS[page.relationship_type]}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Main preview */}
        <div className="flex-1 flex flex-col items-center justify-center p-6 bg-slate-100 relative">
          {currentPage ? (
            <>
              {/* Image */}
              <div
                ref={canvasRef}
                className={`relative bg-white shadow-xl rounded-lg overflow-hidden max-w-4xl w-full aspect-video select-none ${showMask ? "cursor-crosshair" : ""}`}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
              >
                {currentPage.image_path ? (
                  <img
                    ref={imgRef}
                    key={currentPage.image_path}
                    src={getImageUrl(currentPage.image_path)}
                    alt=""
                    draggable={false}
                    className="w-full h-full object-contain pointer-events-none"
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center text-slate-400">
                    <p className="font-medium">{currentPage.title}</p>
                    <p className="text-sm mt-1">尚未生成图片</p>
                  </div>
                )}

                {/* Mask selection rectangle */}
                {showMask && maskRegion.width > 0 && (
                  <div
                    className="absolute border-2 border-red-500 bg-red-500/10 pointer-events-none"
                    style={{
                      left: maskRegion.x, top: maskRegion.y,
                      width: maskRegion.width, height: maskRegion.height,
                    }}
                  />
                )}

                {/* Relationship badge */}
                {currentPage.relationship_type !== "none" && (
                  <span className="absolute top-3 left-3 text-xs px-2 py-1 rounded-md bg-blue-500/90 text-white font-medium">
                    {RELATIONSHIP_LABELS[currentPage.relationship_type]}
                  </span>
                )}

                {/* Regenerate button */}
                {currentPage.image_path && (
                  <button
                    onClick={() => handleRegenerate(currentPage)}
                    disabled={pageLoading === currentPage.id}
                    className="absolute top-3 right-3 p-2 rounded-lg bg-white/90 shadow hover:bg-white text-slate-600 transition-colors"
                    title="重新生成此页"
                  >
                    {pageLoading === currentPage.id ? <Loader2 className="animate-spin" size={16} /> : <RefreshCw size={16} />}
                  </button>
                )}
              </div>

              {/* Navigation */}
              <div className="flex items-center gap-4 mt-4">
                <button onClick={() => setCurrentIdx(Math.max(0, currentIdx - 1))} disabled={currentIdx === 0}
                  className="p-2 rounded-lg bg-white border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-30">
                  <ChevronLeft size={18} />
                </button>
                <span className="text-sm text-slate-500">{currentIdx + 1} / {pages.length}</span>
                <button onClick={() => setCurrentIdx(Math.min(pages.length - 1, currentIdx + 1))} disabled={currentIdx >= pages.length - 1}
                  className="p-2 rounded-lg bg-white border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-30">
                  <ChevronRight size={18} />
                </button>
              </div>

              {/* Layer info badge */}
              {currentPage.image_path && currentPage.visual_image_path && (
                <div className="flex items-center gap-2 mt-3">
                  <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-emerald-100 text-emerald-700">
                    <Layers size={12} /> 混合方案：视觉层 + 文字层
                  </span>
                </div>
              )}

              {/* Toolbar */}
              {currentPage.image_path && (
                <div className="flex flex-wrap items-center gap-2 mt-3">
                  <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-white border border-slate-200">
                    <span className="text-xs text-slate-400 mr-1">分层操作</span>
                    <button
                      onClick={() => handleRegenerate(currentPage, "visual")}
                      disabled={pageLoading === currentPage.id}
                      className="px-2.5 py-1.5 rounded-md text-xs font-medium text-purple-700 bg-purple-50 hover:bg-purple-100 disabled:opacity-40 flex items-center gap-1 transition-colors"
                      title="仅重新生成视觉层（背景+装饰+配图），保留现有文字"
                    >
                      <ImagePlus size={13} /> 换视觉
                    </button>
                    <button
                      onClick={() => handleRegenerate(currentPage, "text")}
                      disabled={pageLoading === currentPage.id}
                      className="px-2.5 py-1.5 rounded-md text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 disabled:opacity-40 flex items-center gap-1 transition-colors"
                      title="仅重新生成文字层排版，保留现有视觉背景"
                    >
                      <FileText size={13} /> 换文字
                    </button>
                  </div>
                  <div className="w-px h-6 bg-slate-200" />
                  <button onClick={handleOpenHtmlEditor}
                    className="px-3 py-2 rounded-lg text-sm border border-slate-300 text-slate-600 hover:bg-white flex items-center gap-1">
                    <Code2 size={14} /> 编辑排版
                  </button>
                  <button onClick={() => { setShowReplace(true); setShowMask(false); setShowHtmlEditor(false); }}
                    className="px-3 py-2 rounded-lg text-sm border border-slate-300 text-slate-600 hover:bg-white flex items-center gap-1">
                    <Type size={14} /> 替换文字
                  </button>
                  <button onClick={() => { setShowMask(true); setShowReplace(false); setShowHtmlEditor(false); }}
                    className="px-3 py-2 rounded-lg text-sm border border-slate-300 text-slate-600 hover:bg-white flex items-center gap-1">
                    <Scissors size={14} /> 遮罩重绘
                  </button>
                  <button onClick={() => handleRegenerate(currentPage)} disabled={pageLoading === currentPage.id}
                    className="px-3 py-2 rounded-lg text-sm border border-orange-300 text-orange-600 hover:bg-orange-50 flex items-center gap-1">
                    <RefreshCw size={14} /> 全部重做
                  </button>
                </div>
              )}
            </>
          ) : (
            <p className="text-slate-400">没有页面</p>
          )}
        </div>
      </div>

      {/* Replace text modal */}
      {showReplace && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowReplace(false)}>
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-slate-800 mb-4">替换文字</h3>
            <div className="space-y-3">
              <input value={replaceOld} onChange={(e) => setReplaceOld(e.target.value)} placeholder="原文字"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500" />
              <input value={replaceNew} onChange={(e) => setReplaceNew(e.target.value)} placeholder="替换为"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500" />
              <input value={replacePrompt} onChange={(e) => setReplacePrompt(e.target.value)} placeholder="额外提示（可选，如：同时调整字体颜色为红色）"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500" />
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setShowReplace(false)} className="px-4 py-2 rounded-lg text-sm border border-slate-300 text-slate-600">取消</button>
              <button onClick={handleReplaceText} disabled={!replaceOld || !replaceNew || pageLoading !== null}
                className="px-4 py-2 rounded-lg text-sm bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-40 flex items-center gap-1">
                {pageLoading ? <Loader2 className="animate-spin" size={14} /> : null} 替换
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mask edit modal */}
      {showMask && maskRegion.width > 10 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-white rounded-xl p-4 shadow-2xl border border-slate-200 w-full max-w-md z-50">
          <h3 className="text-sm font-bold text-slate-800 mb-2">遮罩区域已选择 - 输入新内容</h3>
          <input value={maskPrompt} onChange={(e) => setMaskPrompt(e.target.value)}
            placeholder="例如：将这行文字替换为 2024年度总结"
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500" />
          <div className="flex justify-end gap-2 mt-3">
            <button onClick={() => { setShowMask(false); setMaskRegion({ x: 0, y: 0, width: 0, height: 0 }); }}
              className="px-3 py-2 rounded-lg text-sm border border-slate-300 text-slate-600">取消</button>
            <button onClick={handleMaskEdit} disabled={!maskPrompt || pageLoading !== null}
              className="px-3 py-2 rounded-lg text-sm bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-40">重绘</button>
          </div>
        </div>
      )}

      {/* HTML Editor modal */}
      {showHtmlEditor && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowHtmlEditor(false)}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
              <h3 className="text-lg font-bold text-slate-800">编辑页面排版 (HTML)</h3>
              <span className="text-xs text-slate-400">修改后点击"重新渲染"即可预览效果</span>
            </div>
            <div className="flex-1 overflow-hidden p-4">
              <textarea
                value={editingHtml}
                onChange={(e) => setEditingHtml(e.target.value)}
                spellCheck={false}
                className="w-full h-full min-h-[400px] font-mono text-sm bg-slate-900 text-green-300 p-4 rounded-lg border-0 resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="HTML 内容..."
              />
            </div>
            <div className="flex justify-end gap-2 px-6 py-4 border-t border-slate-200">
              <button onClick={() => setShowHtmlEditor(false)}
                className="px-4 py-2 rounded-lg text-sm border border-slate-300 text-slate-600">
                取消
              </button>
              <button
                onClick={handleRenderHtml}
                disabled={!editingHtml.trim() || pageLoading !== null}
                className="px-4 py-2 rounded-lg text-sm bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-40 flex items-center gap-1"
              >
                {pageLoading ? <Loader2 className="animate-spin" size={14} /> : <RefreshCw size={14} />}
                重新渲染
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Regenerate all confirmation */}
      {showRegenConfirm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowRegenConfirm(false)}>
          <div className="bg-white rounded-xl p-6 w-full max-w-sm shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-slate-800 mb-2">全部重新生成</h3>
            <p className="text-sm text-slate-500 mb-5">
              将重新生成所有 {pages.length} 页的图片。当前图片会保存到历史版本，不会丢失。确定继续？
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowRegenConfirm(false)}
                className="px-4 py-2 rounded-lg text-sm border border-slate-300 text-slate-600">
                取消
              </button>
              <button
                onClick={() => { setShowRegenConfirm(false); handleGenerateAll(); }}
                className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-amber-500 hover:bg-amber-600 flex items-center gap-1"
              >
                <RefreshCw size={14} /> 确认重新生成
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
