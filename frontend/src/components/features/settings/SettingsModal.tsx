"use client";

import { useState, type FormEvent } from "react";
import { X, User, Mail, Lock, Save, Eye, EyeOff, Shield } from "lucide-react";

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    currentEmail: string;
    onSave: (data: { name: string; email: string; password?: string }) => void;
}

export function SettingsModal({
    isOpen,
    onClose,
    currentEmail,
    onSave,
}: SettingsModalProps) {
    const [name, setName] = useState("Luật Sư");
    const [email, setEmail] = useState(currentEmail);
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [showCurrentPassword, setShowCurrentPassword] = useState(false);
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    if (!isOpen) return null;

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        setError("");

        // Validate new password if changing
        if (newPassword) {
            if (newPassword.length < 6) {
                setError("Mật khẩu mới phải có ít nhất 6 ký tự");
                return;
            }
            if (newPassword !== confirmPassword) {
                setError("Mật khẩu xác nhận không khớp");
                return;
            }
            if (!currentPassword) {
                setError("Vui lòng nhập mật khẩu hiện tại");
                return;
            }
        }

        onSave({
            name,
            email,
            password: newPassword || undefined,
        });

        onClose();
    };

    return (
        <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
            onClick={(e) => {
                if (e.target === e.currentTarget) onClose();
            }}
        >
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="sticky top-0 bg-white border-b border-gray-100 px-8 py-6 rounded-t-2xl z-10">
                    <div className="flex items-start justify-between">
                        <div>
                            <h2 className="text-2xl text-gray-900 flex items-center gap-3">
                                <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center">
                                    <Shield className="w-5 h-5 text-blue-700" />
                                </div>
                                Cài đặt tài khoản
                            </h2>
                            <p className="text-sm text-gray-500 mt-2 ml-[52px]">
                                Quản lý thông tin cá nhân và bảo mật tài khoản của bạn
                            </p>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-gray-100 rounded-lg transition-all duration-200 cursor-pointer hover:scale-105 active:scale-95"
                            title="Đóng"
                        >
                            <X className="w-5 h-5 text-gray-500" />
                        </button>
                    </div>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-8">
                    {/* Personal Information Section */}
                    <div className="space-y-6 mb-8">
                        <div className="flex items-center gap-2 mb-4">
                            <div className="h-px bg-gray-200 flex-1"></div>
                            <span className="text-xs uppercase tracking-wider text-gray-500 px-3">
                                Thông tin cá nhân
                            </span>
                            <div className="h-px bg-gray-200 flex-1"></div>
                        </div>

                        {/* Name */}
                        <div className="space-y-2">
                            <label className="block text-sm text-gray-700">
                                Họ và tên <span className="text-red-500">*</span>
                            </label>
                            <div className="relative group">
                                <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-blue-600 transition-colors" />
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    required
                                    className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all duration-200 bg-gray-50 hover:bg-white cursor-text"
                                    placeholder="Nhập họ và tên của bạn"
                                />
                            </div>
                        </div>

                        {/* Email */}
                        <div className="space-y-2">
                            <label className="block text-sm text-gray-700">
                                Địa chỉ Email <span className="text-red-500">*</span>
                            </label>
                            <div className="relative group">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-blue-600 transition-colors" />
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                    className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all duration-200 bg-gray-50 hover:bg-white cursor-text"
                                    placeholder="example@email.com"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Password Section */}
                    <div className="space-y-6 mb-8">
                        <div className="flex items-center gap-2 mb-4">
                            <div className="h-px bg-gray-200 flex-1"></div>
                            <span className="text-xs uppercase tracking-wider text-gray-500 px-3">
                                Đổi mật khẩu
                            </span>
                            <div className="h-px bg-gray-200 flex-1"></div>
                        </div>

                        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 mb-6">
                            <p className="text-sm text-blue-800 flex items-start gap-2">
                                <Lock className="w-4 h-4 mt-0.5 flex-shrink-0" />
                                <span>
                                    Để thay đổi mật khẩu, vui lòng điền đầy đủ 3 trường bên dưới.
                                    Bỏ trống nếu không muốn đổi mật khẩu.
                                </span>
                            </p>
                        </div>

                        {/* Current Password */}
                        <div className="space-y-2">
                            <label className="block text-sm text-gray-700">
                                Mật khẩu hiện tại
                            </label>
                            <div className="relative group">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-blue-600 transition-colors" />
                                <input
                                    type={showCurrentPassword ? "text" : "password"}
                                    value={currentPassword}
                                    onChange={(e) => {
                                        setCurrentPassword(e.target.value);
                                        setError("");
                                    }}
                                    className="w-full pl-12 pr-12 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all duration-200 bg-gray-50 hover:bg-white cursor-text"
                                    placeholder="••••••••"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                                    className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors cursor-pointer"
                                    title={showCurrentPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                                >
                                    {showCurrentPassword ? (
                                        <EyeOff className="w-5 h-5" />
                                    ) : (
                                        <Eye className="w-5 h-5" />
                                    )}
                                </button>
                            </div>
                        </div>

                        {/* New Password */}
                        <div className="space-y-2">
                            <label className="block text-sm text-gray-700">
                                Mật khẩu mới
                            </label>
                            <div className="relative group">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-blue-600 transition-colors" />
                                <input
                                    type={showNewPassword ? "text" : "password"}
                                    value={newPassword}
                                    onChange={(e) => {
                                        setNewPassword(e.target.value);
                                        setError("");
                                    }}
                                    className="w-full pl-12 pr-12 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all duration-200 bg-gray-50 hover:bg-white cursor-text"
                                    placeholder="••••••••"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowNewPassword(!showNewPassword)}
                                    className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors cursor-pointer"
                                    title={showNewPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                                >
                                    {showNewPassword ? (
                                        <EyeOff className="w-5 h-5" />
                                    ) : (
                                        <Eye className="w-5 h-5" />
                                    )}
                                </button>
                            </div>
                            {newPassword && (
                                <p
                                    className={`text-xs ${newPassword.length >= 6 ? "text-green-600" : "text-gray-500"}`}
                                >
                                    {newPassword.length >= 6
                                        ? "✓ Mật khẩu hợp lệ"
                                        : `Tối thiểu 6 ký tự (${newPassword.length}/6)`}
                                </p>
                            )}
                        </div>

                        {/* Confirm Password */}
                        <div className="space-y-2">
                            <label className="block text-sm text-gray-700">
                                Xác nhận mật khẩu mới
                            </label>
                            <div className="relative group">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-blue-600 transition-colors" />
                                <input
                                    type={showConfirmPassword ? "text" : "password"}
                                    value={confirmPassword}
                                    onChange={(e) => {
                                        setConfirmPassword(e.target.value);
                                        setError("");
                                    }}
                                    className="w-full pl-12 pr-12 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all duration-200 bg-gray-50 hover:bg-white cursor-text"
                                    placeholder="••••••••"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                    className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors cursor-pointer"
                                    title={showConfirmPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                                >
                                    {showConfirmPassword ? (
                                        <EyeOff className="w-5 h-5" />
                                    ) : (
                                        <Eye className="w-5 h-5" />
                                    )}
                                </button>
                            </div>
                            {confirmPassword && (
                                <p
                                    className={`text-xs ${confirmPassword === newPassword ? "text-green-600" : "text-red-500"}`}
                                >
                                    {confirmPassword === newPassword
                                        ? "✓ Mật khẩu khớp"
                                        : "✗ Mật khẩu không khớp"}
                                </p>
                            )}
                        </div>
                    </div>

                    {/* Error Message */}
                    {error && (
                        <div className="bg-red-50 border border-red-200 text-red-700 px-5 py-4 rounded-xl text-sm mb-6 flex items-start gap-3">
                            <span className="text-red-500 text-lg leading-none">⚠</span>
                            <span>{error}</span>
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-4 pt-6 border-t border-gray-100">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 hover:border-gray-400 transition-all duration-200 cursor-pointer hover:shadow-sm active:scale-98"
                        >
                            Hủy bỏ
                        </button>
                        <button
                            type="submit"
                            className="flex-1 px-6 py-3 bg-gradient-to-r from-blue-700 to-blue-800 text-white rounded-xl hover:from-blue-800 hover:to-blue-900 transition-all duration-200 flex items-center justify-center gap-2 shadow-lg shadow-blue-700/30 hover:shadow-xl hover:shadow-blue-800/40 cursor-pointer hover:scale-105 active:scale-95"
                        >
                            <Save className="w-5 h-5" />
                            Lưu thay đổi
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
