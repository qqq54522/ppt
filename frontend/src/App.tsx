import { Routes, Route, Navigate } from "react-router-dom";
import Home from "./pages/Home";
import StyleReference from "./pages/StyleReference";
import OutlineEditor from "./pages/OutlineEditor";
import SlidePreview from "./pages/SlidePreview";
import { useProjectStore } from "./store/useProjectStore";
import { useEffect } from "react";

export default function App() {
  const error = useProjectStore((s) => s.error);
  const clearError = useProjectStore((s) => s.clearError);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(clearError, 5000);
      return () => clearTimeout(timer);
    }
  }, [error, clearError]);

  return (
    <div className="min-h-screen bg-slate-50">
      {error && (
        <div className="fixed top-4 right-4 z-50 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg shadow-lg max-w-md">
          <p className="text-sm">{error}</p>
          <button onClick={clearError} className="absolute top-1 right-2 text-red-400 hover:text-red-600">&times;</button>
        </div>
      )}
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/style/:projectId" element={<StyleReference />} />
        <Route path="/project/:projectId/outline" element={<OutlineEditor />} />
        <Route path="/project/:projectId/preview" element={<SlidePreview />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
