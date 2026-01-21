"use client";

import { useState, useEffect, type FormEvent, type KeyboardEvent } from "react";
import { X, Edit3 } from "lucide-react";
import { MAX_NAME_LENGTH } from "@/constants";

interface RenameChatModalProps {
    isOpen: boolean;
    onClose: () => void;
    currentName: string;
    onRename: (newName: string) => void;
}

export function RenameChatModal({
    isOpen,
    onClose,
    currentName,
    onRename,
}: RenameChatModalProps) {
    const [name, setName] = useState(currentName);

    useEffect(() => {
        setName(currentName);
    }, [currentName, isOpen]);

    if (!isOpen) return null;

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        if (name.trim()) {
            onRename(name.trim());
            onClose();
        }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
            onClose();
        }
    };

    return (
        <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
            onClick={(e) => {
                if (e.target === e.currentTarget) onClose();
            }}
        >
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-100">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center">
                            <Edit3 className="w-5 h-5 text-blue-700" />
                        </div>
                        <h2 className="text-xl text-gray-900">Đổi tên hội thoại</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-all duration-200"
                        title="Đóng"
                    >
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6">
                    <div className="space-y-2 mb-6">
                        <label className="block text-sm text-gray-700">
                            Tên hội thoại <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            onKeyDown={handleKeyDown}
                            autoFocus
                            className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all duration-200 bg-gray-50 hover:bg-white"
                            placeholder="Nhập tên mới cho hội thoại"
                            maxLength={MAX_NAME_LENGTH}
                        />
                        <p className="text-xs text-gray-500">
                            {name.length}/{MAX_NAME_LENGTH} ký tự
                        </p>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 px-4 py-2.5 border-2 border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 hover:border-gray-400 transition-all duration-200"
                        >
                            Hủy
                        </button>
                        <button
                            type="submit"
                            disabled={!name.trim()}
                            className="flex-1 px-4 py-2.5 bg-gradient-to-r from-blue-700 to-blue-800 text-white rounded-xl hover:from-blue-800 hover:to-blue-900 transition-all duration-200 disabled:opacity-50"
                        >
                            Lưu
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
