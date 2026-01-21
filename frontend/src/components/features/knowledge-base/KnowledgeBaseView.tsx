"use client";

import { useState } from "react";
import {
  Search,
  ChevronRight,
  ChevronDown,
  FileText,
  Star,
  Edit,
  Trash2,
  Menu,
  PanelLeftClose,
  Loader2,
  AlertCircle,
  Download,
} from "lucide-react";
import { DeleteConfirmModal } from "@/components/common/DeleteConfirmModal";
import { EditKnowledgeBaseModal } from "./EditKnowledgeBaseModal";
import { useKnowledgeBase } from "@/hooks/use-knowledge-base";
import { MESSAGES } from "@/constants";
import type { ModalState } from "@/types";

interface KnowledgeBaseViewProps {
  isSidebarCollapsed: boolean;
  onToggleSidebar: () => void;
}

// Helper function to format file size
function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

export function KnowledgeBaseView({
  isSidebarCollapsed,
  onToggleSidebar,
}: KnowledgeBaseViewProps) {
  const {
    knowledgeBases,
    loading,
    error,
    allExpanded,
    toggleExpanded,
    expandAll,
    collapseAll,
    toggleFavorite,
    renameKnowledgeBase,
    deleteKnowledgeBase,
    deleteDocument,
    refetch,
    getDownloadUrl,
  } = useKnowledgeBase();

  const [selectedTab, setSelectedTab] = useState<"all" | "favorites">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [deleteModal, setDeleteModal] = useState<ModalState>({
    isOpen: false,
    id: "",
    name: "",
    type: "knowledge-base",
  });
  const [editModal, setEditModal] = useState<ModalState>({
    isOpen: false,
    id: "",
    name: "",
    type: "knowledge-base",
  });
  const [downloadingDoc, setDownloadingDoc] = useState<string | null>(null);

  const handleEdit = (id: string, name: string) => {
    setEditModal({ isOpen: true, id, name, type: "knowledge-base" });
  };

  const handleDelete = (
    id: string,
    name: string,
    type: "knowledge-base" | "document" = "knowledge-base"
  ) => {
    setDeleteModal({ isOpen: true, id, name, type });
  };

  const confirmEdit = (newName: string) => {
    renameKnowledgeBase(editModal.id, newName);
  };

  const confirmDelete = () => {
    if (deleteModal.type === "knowledge-base") {
      deleteKnowledgeBase(deleteModal.id);
    } else {
      // For documents, we need to find the parent KB
      const kbId = deleteModal.id.split("-")[0]; // Assuming format like "kbId-docId"
      const docId = deleteModal.id.split("-")[1];
      deleteDocument(kbId, docId);
    }
  };

  const handleDownload = (docName: string) => {
    setDownloadingDoc(docName);
    try {
      const url = getDownloadUrl(docName);
      // Open download URL in new tab
      window.open(url, "_blank");
    } catch (err) {
      console.error("Download error:", err);
    } finally {
      setDownloadingDoc(null);
    }
  };

  const getDeleteMessage = () => {
    if (deleteModal.type === "knowledge-base") {
      return MESSAGES.DELETE_KB_CONFIRM(deleteModal.name);
    }
    return MESSAGES.DELETE_DOC_CONFIRM(deleteModal.name);
  };

  const getDeleteTitle = () => {
    if (deleteModal.type === "knowledge-base") {
      return MESSAGES.DELETE_KB_TITLE;
    }
    return MESSAGES.DELETE_DOC_TITLE;
  };

  // Filter knowledge bases based on search and tab
  const filteredKBs = knowledgeBases.filter((kb) => {
    const matchesSearch = kb.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTab = selectedTab === "all" || (selectedTab === "favorites" && kb.favorite);
    return matchesSearch && matchesTab;
  });

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="border-b border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <button
            onClick={onToggleSidebar}
            className="p-2 hover:bg-gray-100 rounded transition-colors"
            title={isSidebarCollapsed ? "Mở sidebar" : "Đóng sidebar"}
          >
            {isSidebarCollapsed ? (
              <Menu className="w-5 h-5" />
            ) : (
              <PanelLeftClose className="w-5 h-5" />
            )}
          </button>
          <h1 className="text-2xl flex-1">Cơ sở tri thức pháp luật</h1>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => setSelectedTab("all")}
            className={`px-4 py-2 rounded-lg transition-colors ${selectedTab === "all"
              ? "bg-blue-100 text-blue-700"
              : "text-gray-600 hover:bg-gray-100"
              }`}
          >
            Tất cả
          </button>
          <button
            onClick={() => setSelectedTab("favorites")}
            className={`px-4 py-2 rounded-lg transition-colors ${selectedTab === "favorites"
              ? "bg-blue-100 text-blue-700"
              : "text-gray-600 hover:bg-gray-100"
              }`}
          >
            Yêu thích
          </button>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-2 flex-1">
          <button
            onClick={allExpanded ? collapseAll : expandAll}
            className="px-3 py-2 border border-gray-300 rounded-lg flex items-center gap-2 text-sm hover:bg-gray-50 transition-colors"
          >
            {allExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
            {allExpanded ? "Thu gọn tất cả" : "Mở rộng tất cả"}
          </button>
          <div className="text-sm text-blue-700">
            {filteredKBs.length} Cơ sở tri thức
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm kiếm cơ sở tri thức..."
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg outline-none focus:border-blue-700 transition-colors"
            />
          </div>
        </div>
      </div>

      {/* Knowledge Base List */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-blue-700" />
            <span className="ml-3 text-gray-600">Đang tải...</span>
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center py-12 text-red-600">
            <AlertCircle className="w-6 h-6 mr-2" />
            <span>{error}</span>
            <button
              onClick={refetch}
              className="ml-4 px-3 py-1 bg-red-100 hover:bg-red-200 rounded text-sm"
            >
              Thử lại
            </button>
          </div>
        )}

        {!loading && !error && filteredKBs.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <FileText className="w-12 h-12 mb-3 text-gray-300" />
            <p>Chưa có cơ sở tri thức nào</p>
            <p className="text-sm mt-1">Tạo collection trong Qdrant để hiển thị ở đây</p>
          </div>
        )}
        <div className="max-w-7xl mx-auto space-y-4">
          {filteredKBs.map((kb) => (
            <div
              key={kb.id}
              className="border border-gray-200 rounded-lg overflow-hidden"
            >
              {/* Knowledge Base Header */}
              <div className="bg-blue-50 p-4 flex items-center justify-between">
                <div className="flex items-center gap-3 flex-1">
                  <button
                    onClick={() => toggleExpanded(kb.id)}
                    className="p-1 hover:bg-blue-100 rounded transition-colors"
                  >
                    {kb.expanded ? (
                      <ChevronDown className="w-5 h-5 text-gray-600" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-gray-600" />
                    )}
                  </button>

                  <div className="w-10 h-10 bg-blue-200 rounded-lg flex items-center justify-center">
                    <FileText className="w-6 h-6 text-blue-700" />
                  </div>

                  <div className="flex-1">
                    <h3 className="text-gray-900">{kb.name}</h3>
                    <div className="flex items-center gap-4 text-sm text-gray-500 mt-1">
                      <span className="flex items-center gap-1">
                        <FileText className="w-4 h-4" />
                        {kb.files} docs
                      </span>
                      <span className="flex items-center gap-1">
                        <svg
                          className="w-4 h-4"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                        >
                          <rect
                            x="3"
                            y="3"
                            width="7"
                            height="7"
                            strokeWidth="2"
                          />
                          <rect
                            x="14"
                            y="3"
                            width="7"
                            height="7"
                            strokeWidth="2"
                          />
                          <rect
                            x="14"
                            y="14"
                            width="7"
                            height="7"
                            strokeWidth="2"
                          />
                          <rect
                            x="3"
                            y="14"
                            width="7"
                            height="7"
                            strokeWidth="2"
                          />
                        </svg>
                        {kb.chunks} chunks
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toggleFavorite(kb.id)}
                    className={`px-3 py-1.5 border rounded-lg text-sm transition-colors flex items-center gap-1 ${kb.favorite
                      ? "border-amber-400 bg-amber-50 text-amber-700"
                      : "border-gray-300 hover:bg-white"
                      }`}
                  >
                    <Star
                      className={`w-4 h-4 ${kb.favorite ? "fill-amber-400 text-amber-400" : ""}`}
                    />
                    {kb.favorite ? "Đã đánh dấu" : "Đánh dấu"}
                  </button>
                  <button
                    onClick={() => {
                      // Handle edit
                      handleEdit(kb.id, kb.name);
                    }}
                    className="p-2 hover:bg-blue-100 rounded transition-colors"
                    title="Chỉnh sửa"
                  >
                    <Edit className="w-4 h-4 text-gray-600" />
                  </button>
                  <button
                    onClick={() => handleDelete(kb.id, kb.name)}
                    className="p-2 hover:bg-blue-100 rounded transition-colors"
                    title="Xóa"
                  >
                    <Trash2 className="w-4 h-4 text-gray-600" />
                  </button>
                </div>
              </div>

              {/* Documents List */}
              {kb.expanded && (
                <div className="p-4 bg-white">
                  {kb.loadingDocs ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-blue-700" />
                      <span className="ml-2 text-gray-600">Đang tải tài liệu...</span>
                    </div>
                  ) : kb.documents && kb.documents.length > 0 ? (
                    <div className="max-h-96 overflow-y-auto space-y-2 pr-2">
                      {kb.documents.map((doc) => (
                        <div
                          key={doc.id}
                          className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3 flex-1 min-w-0">
                              <div className="w-10 h-10 bg-blue-100 rounded flex items-center justify-center flex-shrink-0">
                                <FileText className="w-5 h-5 text-blue-700" />
                              </div>

                              <div className="flex-1 min-w-0">
                                <h4 className="text-gray-900 truncate" title={doc.name}>
                                  {doc.name}
                                </h4>
                                <div className="flex items-center gap-4 text-sm text-gray-500 mt-1">
                                  <span>{formatFileSize(doc.size)}</span>
                                  {doc.lastModified && (
                                    <span>
                                      {new Date(doc.lastModified).toLocaleDateString("vi-VN")}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>

                            <button
                              onClick={() => handleDownload(doc.name)}
                              disabled={downloadingDoc === doc.name}
                              className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2 disabled:opacity-50"
                              title="Tải xuống"
                            >
                              {downloadingDoc === doc.name ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <Download className="w-4 h-4" />
                              )}
                              Tải xuống
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <FileText className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                      <p>Chưa có tài liệu nào</p>
                      <p className="text-sm mt-1">Upload tài liệu vào MinIO để hiển thị ở đây</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Modals */}

      <DeleteConfirmModal
        isOpen={deleteModal.isOpen}
        onClose={() => setDeleteModal({ ...deleteModal, isOpen: false })}
        onConfirm={confirmDelete}
        title={getDeleteTitle()}
        message={getDeleteMessage()}
      />

      <EditKnowledgeBaseModal
        isOpen={editModal.isOpen}
        onClose={() => setEditModal({ ...editModal, isOpen: false })}
        currentName={editModal.name}
        onSave={confirmEdit}
      />
    </div>
  );
}