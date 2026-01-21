"use client";

import { useState, type FormEvent } from "react";
import { X, FolderPlus } from "lucide-react";

interface CreateKnowledgeBaseModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (data: { name: string; type: string; description: string }) => void;
}

export function CreateKnowledgeBaseModal({
    isOpen,
    onClose,
    onSave,
}: CreateKnowledgeBaseModalProps) {
    const [name, setName] = useState("");
    const [type, setType] = useState("Pipedrive");
    const [description, setDescription] = useState("");

    if (!isOpen) return null;

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        if (!name.trim()) return;

        onSave({ name, type, description });

        // Reset form
        setName("");
        setType("Pipedrive");
        setDescription("");
        onClose();
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                            <FolderPlus className="w-5 h-5 text-blue-700" />
                        </div>
                        <h2 className="text-xl text-gray-900">Tạo cơ sở tri thức mới</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    <div>
                        <label className="block text-sm text-gray-700 mb-2">
                            Tên cơ sở tri thức <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Nhập tên cơ sở tri thức"
                            autoFocus
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm text-gray-700 mb-2">Loại</label>
                        <select
                            value={type}
                            onChange={(e) => setType(e.target.value)}
                            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                            <option value="Pipedrive">Pipedrive</option>
                            <option value="Salesforce">Salesforce</option>
                            <option value="HubSpot">HubSpot</option>
                            <option value="Custom">Custom</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm text-gray-700 mb-2">Mô tả</label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                            placeholder="Nhập mô tả (tùy chọn)"
                            rows={3}
                        />
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 pt-4">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                        >
                            Hủy
                        </button>
                        <button
                            type="submit"
                            className="flex-1 px-4 py-2.5 bg-blue-700 text-white rounded-lg hover:bg-blue-800 transition-colors"
                        >
                            Tạo mới
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
