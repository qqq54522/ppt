import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Plus, Trash2, GripVertical, Loader2 } from "lucide-react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useProjectStore } from "../store/useProjectStore";
import { updatePage, deletePage, createPage } from "../api/endpoints";
import { RELATIONSHIP_LABELS, type RelationshipType, type Page } from "../types";

function SortableCard({
  page,
  onUpdate,
  onDelete,
}: {
  page: Page;
  onUpdate: (page: Page, data: Partial<Page>) => void;
  onDelete: (id: string) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: page.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 50 : "auto" as const,
  };

  return (
    <div ref={setNodeRef} style={style} className="bg-white rounded-xl border border-slate-200 p-5 relative group">
      <div
        {...attributes}
        {...listeners}
        className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-300 cursor-grab active:cursor-grabbing opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <GripVertical size={16} />
      </div>

      <span className="absolute top-3 right-3 text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 cursor-pointer">
        <select
          value={page.relationship_type}
          onChange={(e) => onUpdate(page, { relationship_type: e.target.value as RelationshipType })}
          className="bg-transparent text-xs focus:outline-none cursor-pointer"
        >
          {Object.entries(RELATIONSHIP_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </span>

      <div className="pl-5">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs text-slate-400 font-mono">#{page.page_number}</span>
          <input
            value={page.title}
            onChange={(e) => onUpdate(page, { title: e.target.value })}
            className="text-base font-semibold text-slate-800 bg-transparent border-none focus:outline-none focus:ring-0 flex-1"
            placeholder="页面标题"
          />
          <button
            onClick={() => onDelete(page.id)}
            className="text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <Trash2 size={14} />
          </button>
        </div>
        <textarea
          value={page.content}
          onChange={(e) => onUpdate(page, { content: e.target.value })}
          rows={3}
          className="w-full text-sm text-slate-600 bg-slate-50 rounded-lg px-3 py-2 resize-none border-none focus:outline-none focus:ring-1 focus:ring-primary-300"
          placeholder="页面内容要点..."
        />
      </div>
    </div>
  );
}

export default function OutlineEditor() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { currentProject, syncProject, generateOutline, isLoading, updatePageLocal, reorderPages } = useProjectStore();
  const [refineText, setRefineText] = useState("");

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  useEffect(() => {
    if (projectId) syncProject(projectId);
  }, [projectId, syncProject]);

  const pages = currentProject?.pages || [];

  async function handleUpdatePage(page: Page, data: Partial<Page>) {
    if (!projectId) return;
    updatePageLocal(page.id, data);
    await updatePage(projectId, page.id, data);
  }

  async function handleDeletePage(pageId: string) {
    if (!projectId) return;
    await deletePage(projectId, pageId);
    await syncProject(projectId);
  }

  async function handleAddPage() {
    if (!projectId) return;
    await createPage(projectId, { title: "新页面", content: "", relationship_type: "none" });
    await syncProject(projectId);
  }

  async function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = pages.findIndex((p) => p.id === active.id);
    const newIndex = pages.findIndex((p) => p.id === over.id);
    if (oldIndex === -1 || newIndex === -1) return;

    const reordered = [...pages];
    const [moved] = reordered.splice(oldIndex, 1);
    reordered.splice(newIndex, 0, moved);

    const newOrder = reordered.map((p) => p.id);
    await reorderPages(newOrder);
  }

  async function handleRefine() {
    if (!refineText.trim()) return;
    await useProjectStore.getState().updateProject({
      idea_prompt: `${currentProject?.idea_prompt || ""}\n[修改要求] ${refineText}`,
    });
    await generateOutline();
    setRefineText("");
  }

  function handleGenerate() {
    navigate(`/project/${projectId}/preview`);
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(`/style/${projectId}`)} className="text-slate-500 hover:text-slate-700">
            <ArrowLeft size={18} />
          </button>
          <h1 className="text-lg font-bold text-slate-800">
            {currentProject?.title || "大纲编辑"}
          </h1>
        </div>
        <button
          onClick={handleGenerate}
          disabled={pages.length === 0}
          className="px-5 py-2 rounded-lg font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-40 transition-colors"
        >
          生成页面
        </button>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <div className="w-80 border-r border-slate-200 bg-white p-5 overflow-y-auto">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">原始内容</h3>
          <div className="text-sm text-slate-600 whitespace-pre-wrap bg-slate-50 rounded-lg p-3 mb-4 max-h-60 overflow-y-auto">
            {currentProject?.idea_prompt || currentProject?.outline_text || "（无内容）"}
          </div>

          <h3 className="text-sm font-semibold text-slate-700 mb-2">AI 优化大纲</h3>
          <div className="flex gap-2">
            <input
              value={refineText}
              onChange={(e) => setRefineText(e.target.value)}
              placeholder="例如：把第三页拆成两页"
              className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              onKeyDown={(e) => e.key === "Enter" && handleRefine()}
            />
            <button
              onClick={handleRefine}
              disabled={isLoading}
              className="px-3 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-40"
            >
              {isLoading ? <Loader2 className="animate-spin" size={14} /> : "优化"}
            </button>
          </div>
        </div>

        <div className="flex-1 p-6 overflow-y-auto">
          {isLoading && pages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="animate-spin text-primary-500" size={32} />
              <span className="ml-3 text-slate-500">正在生成大纲...</span>
            </div>
          ) : (
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={pages.map((p) => p.id)} strategy={verticalListSortingStrategy}>
                <div className="space-y-4 max-w-3xl mx-auto">
                  {pages.map((page) => (
                    <SortableCard
                      key={page.id}
                      page={page}
                      onUpdate={handleUpdatePage}
                      onDelete={handleDeletePage}
                    />
                  ))}

                  <button
                    onClick={handleAddPage}
                    className="w-full py-3 border-2 border-dashed border-slate-300 rounded-xl text-slate-400 hover:text-primary-500 hover:border-primary-400 flex items-center justify-center gap-2 transition-colors"
                  >
                    <Plus size={16} /> 添加页面
                  </button>
                </div>
              </SortableContext>
            </DndContext>
          )}
        </div>
      </div>
    </div>
  );
}
