"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Lock, Mail } from "lucide-react";
import { ERRORS } from "@/constants";
import { useAuth } from "@/contexts/AuthContext";

export function LoginForm() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const { login } = useAuth();
    const router = useRouter();

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError("");
        setIsLoading(true);

        try {
            await login(email, password);
            // Navigate to home page after successful login
            router.push('/');
        } catch (err) {
            const message = err instanceof Error ? err.message : ERRORS.LOGIN_FAILED;
            setError(message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-3">
            {/* Email */}
            <div>
                <label className="block text-xs text-gray-700 mb-1">
                    Email
                </label>
                <div className="relative">
                    <Mail className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                        type="email"
                        value={email}
                        onChange={(e) => {
                            setEmail(e.target.value);
                            setError("");
                        }}
                        placeholder="Nhập email"
                        className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        autoFocus
                        disabled={isLoading}
                    />
                </div>
            </div>

            {/* Password */}
            <div>
                <label className="block text-xs text-gray-700 mb-1">
                    Mật khẩu
                </label>
                <div className="relative">
                    <Lock className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => {
                            setPassword(e.target.value);
                            setError("");
                        }}
                        placeholder="Nhập mật khẩu"
                        className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        disabled={isLoading}
                    />
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <div className="bg-red-50 border border-red-200 text-red-600 px-3 py-2 rounded-md text-xs">
                    {error}
                </div>
            )}

            {/* Submit Button */}
            <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-blue-700 hover:bg-blue-800 disabled:bg-blue-400 text-white py-2 text-sm rounded-md transition-colors"
            >
                {isLoading ? "Đang đăng nhập..." : "Đăng nhập"}
            </button>
        </form>
    );
}
