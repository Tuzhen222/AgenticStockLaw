"use client";

import { useState, type FormEvent } from "react";
import { Lock, Mail, User } from "lucide-react";
import { authService } from "@/services/auth.service";

interface RegisterFormProps {
    onSuccess: () => void;
}

export function RegisterForm({ onSuccess }: RegisterFormProps) {
    const [email, setEmail] = useState("");
    const [username, setUsername] = useState("");
    const [fullName, setFullName] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError("");

        // Validate
        if (password.length < 6) {
            setError("Mật khẩu phải có ít nhất 6 ký tự");
            return;
        }

        if (password !== confirmPassword) {
            setError("Mật khẩu xác nhận không khớp");
            return;
        }

        setIsLoading(true);

        try {
            await authService.register({
                email,
                username,
                password,
                full_name: fullName || undefined,
            });
            onSuccess();
        } catch (err) {
            const message = err instanceof Error ? err.message : "Đăng ký thất bại";
            setError(message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <div>
                <label className="block text-sm text-gray-700 mb-2">
                    Email <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                        type="email"
                        value={email}
                        onChange={(e) => {
                            setEmail(e.target.value);
                            setError("");
                        }}
                        placeholder="Nhập email"
                        className="w-full pl-11 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        autoFocus
                        required
                        disabled={isLoading}
                    />
                </div>
            </div>

            {/* Username */}
            <div>
                <label className="block text-sm text-gray-700 mb-2">
                    Tên đăng nhập <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                        type="text"
                        value={username}
                        onChange={(e) => {
                            setUsername(e.target.value);
                            setError("");
                        }}
                        placeholder="Nhập tên đăng nhập"
                        className="w-full pl-11 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        required
                        disabled={isLoading}
                    />
                </div>
            </div>

            {/* Full Name */}
            <div>
                <label className="block text-sm text-gray-700 mb-2">
                    Họ và tên
                </label>
                <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                        type="text"
                        value={fullName}
                        onChange={(e) => {
                            setFullName(e.target.value);
                            setError("");
                        }}
                        placeholder="Nhập họ và tên (không bắt buộc)"
                        className="w-full pl-11 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        disabled={isLoading}
                    />
                </div>
            </div>

            {/* Password */}
            <div>
                <label className="block text-sm text-gray-700 mb-2">
                    Mật khẩu <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => {
                            setPassword(e.target.value);
                            setError("");
                        }}
                        placeholder="Nhập mật khẩu (ít nhất 6 ký tự)"
                        className="w-full pl-11 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        required
                        disabled={isLoading}
                    />
                </div>
            </div>

            {/* Confirm Password */}
            <div>
                <label className="block text-sm text-gray-700 mb-2">
                    Xác nhận mật khẩu <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => {
                            setConfirmPassword(e.target.value);
                            setError("");
                        }}
                        placeholder="Nhập lại mật khẩu"
                        className="w-full pl-11 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        required
                        disabled={isLoading}
                    />
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm">
                    {error}
                </div>
            )}

            {/* Submit Button */}
            <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-blue-700 hover:bg-blue-800 disabled:bg-blue-400 text-white py-3 rounded-lg transition-colors"
            >
                {isLoading ? "Đang đăng ký..." : "Đăng ký"}
            </button>
        </form>
    );
}
