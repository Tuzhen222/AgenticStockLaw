"use client";

import { LoginForm } from "@/components/features/auth";
import { APP_NAME, APP_DESCRIPTION } from "@/constants";

export default function LoginPage() {
    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 flex items-center justify-center px-4">
            <div className="w-full max-w-xs">
                {/* Logo & Title */}
                <div className="text-center mb-5">
                    <div className="inline-flex items-center justify-center w-14 h-14 bg-white/10 backdrop-blur-sm rounded-xl mb-3">
                        <span className="text-3xl">⚖️</span>
                    </div>
                    <h1 className="text-2xl text-white mb-1">{APP_NAME}</h1>
                    <p className="text-blue-200 text-sm">{APP_DESCRIPTION}</p>
                </div>

                {/* Login Form */}
                <div className="bg-white rounded-xl shadow-2xl p-5">
                    <div className="mb-3">
                        <h2 className="text-lg text-gray-800 mb-1">Đăng nhập</h2>
                        <p className="text-gray-500 text-xs">Vui lòng đăng nhập để tiếp tục</p>
                    </div>

                    <LoginForm />

                    {/* Register Link */}
                    <div className="mt-4 pt-4 border-t border-gray-200 text-center">
                        <p className="text-xs text-gray-600">
                            Chưa có tài khoản?{" "}
                            <a
                                href="/register"
                                className="text-blue-600 hover:text-blue-800 font-medium"
                            >
                                Đăng ký ngay
                            </a>
                        </p>
                    </div>

                    {/* Demo Credentials */}
                    <div className="mt-3 pt-3 border-t border-gray-200">
                        <p className="text-xs text-gray-500 text-center mb-1">
                            Demo Account:
                        </p>
                        <div className="bg-amber-50 border border-amber-200 rounded-md p-2 text-xs">
                            <p className="text-gray-700">
                                <span className="text-gray-500">Email:</span>{" "}
                                <span className="font-mono">user001@example.com</span>
                            </p>
                            <p className="text-gray-700">
                                <span className="text-gray-500">Password:</span>{" "}
                                <span className="font-mono">user123456</span>
                            </p>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <p className="text-center text-blue-200 text-xs mt-4">
                    © 2024 {APP_NAME}. All rights reserved.
                </p>
            </div>
        </div>
    );
}
