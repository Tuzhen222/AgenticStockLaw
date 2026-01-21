"use client";

import { X, AlertTriangle } from "lucide-react";
import type { KeyboardEvent } from "react";

interface DeleteConfirmModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => void;
    title: string;
    message: string;
}

export function DeleteConfirmModal({
    isOpen,
    onClose,
    onConfirm,
    title,
    message,
}: DeleteConfirmModalProps) {
    if (!isOpen) return null;

    const handleConfirm = () => {
        onConfirm();
        onClose();
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
            onKeyDown={handleKeyDown}
        >
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-100">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-red-100 rounded-xl flex items-center justify-center">
                            <AlertTriangle className="w-5 h-5 text-red-700" />
                        </div>
                        <h2 className="text-xl text-gray-900">{title}</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-all duration-200 cursor-pointer hover:scale-105 active:scale-95"
                        title="Đóng"
                    >
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6">
                    <p className="text-gray-700 leading-relaxed">{message}</p>
                </div>

                {/* Actions */}
                <div className="flex gap-3 p-6 pt-0">
                    <button
                        type="button"
                        onClick={onClose}
                        className="flex-1 px-4 py-2.5 border-2 border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 hover:border-gray-400 transition-all duration-200 cursor-pointer"
                    >
                        Hủy
                    </button>
                    <button
                        type="button"
                        onClick={handleConfirm}
                        className="flex-1 px-4 py-2.5 bg-gradient-to-r from-red-600 to-red-700 text-white rounded-xl hover:from-red-700 hover:to-red-800 transition-all duration-200 cursor-pointer"
                    >
                        Xóa
                    </button>
                </div>
            </div>
        </div>
    );
}
