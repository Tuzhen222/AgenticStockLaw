"use client";

import { useState } from "react";
import { RegisterForm } from "@/components/features/auth";
import { APP_NAME, APP_DESCRIPTION } from "@/constants";
import { CheckCircle } from "lucide-react";

export default function RegisterPage() {
    const [isSuccess, setIsSuccess] = useState(false);

    if (isSuccess) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 flex items-center justify-center px-4">
                <div className="w-full max-w-md">
                    {/* Logo & Title */}
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-20 h-20 bg-white/10 backdrop-blur-sm rounded-2xl mb-4">
                            <span className="text-5xl">⚖️</span>
                        </div>
                        <h1 className="text-4xl text-white mb-2">{APP_NAME}</h1>
                        <p className="text-blue-200">{APP_DESCRIPTION}</p>
                    </div>

                    {/* Success Message */}
                    <div className="bg-white rounded-2xl shadow-2xl p-8 text-center">
                        <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
                            <CheckCircle className="w-8 h-8 text-green-600" />
                        </div>
                        <h2 className="text-2xl text-gray-800 mb-2">Đăng ký thành công!</h2>
                        <p className="text-gray-500 mb-6">
                            Tài khoản của bạn đã được tạo. Bạn có thể đăng nhập ngay bây giờ.
                        </p>
                        <a
                            href="/login"
                            className="inline-block w-full bg-blue-700 hover:bg-blue-800 text-white py-3 rounded-lg transition-colors text-center"
                        >
                            Đăng nhập ngay
                        </a>
                    </div>

                    {/* Footer */}
                    <p className="text-center text-blue-200 text-sm mt-6">
                        © 2024 {APP_NAME}. All rights reserved.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 flex items-center justify-center px-4">
            <div className="w-full max-w-md">
                {/* Logo & Title */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-20 h-20 bg-white/10 backdrop-blur-sm rounded-2xl mb-4">
                        <span className="text-5xl">⚖️</span>
                    </div>
                    <h1 className="text-4xl text-white mb-2">{APP_NAME}</h1>
                    <p className="text-blue-200">{APP_DESCRIPTION}</p>
                </div>

                {/* Register Form */}
                <div className="bg-white rounded-2xl shadow-2xl p-8">
                    <div className="mb-6">
                        <h2 className="text-2xl text-gray-800 mb-2">Đăng ký tài khoản</h2>
                        <p className="text-gray-500">Tạo tài khoản mới để sử dụng hệ thống</p>
                    </div>

                    <RegisterForm onSuccess={() => setIsSuccess(true)} />

                    {/* Login Link */}
                    <div className="mt-6 pt-6 border-t border-gray-200 text-center">
                        <p className="text-sm text-gray-600">
                            Đã có tài khoản?{" "}
                            <a
                                href="/login"
                                className="text-blue-600 hover:text-blue-800 font-medium"
                            >
                                Đăng nhập
                            </a>
                        </p>
                    </div>
                </div>

                {/* Footer */}
                <p className="text-center text-blue-200 text-sm mt-6">
                    © 2024 {APP_NAME}. All rights reserved.
                </p>
            </div>
        </div>
    );
}
