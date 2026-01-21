"use client";

import { type RefObject } from "react";
import { Settings, LogOut, ChevronDown } from "lucide-react";

interface SidebarUserMenuProps {
    userEmail: string;
    isMenuOpen: boolean;
    onToggleMenu: () => void;
    onOpenSettings: () => void;
    onLogout: () => void;
    menuRef: RefObject<HTMLDivElement | null>;
}

export function SidebarUserMenu({
    userEmail,
    isMenuOpen,
    onToggleMenu,
    onOpenSettings,
    onLogout,
    menuRef,
}: SidebarUserMenuProps) {
    return (
        <div className="mt-auto border-t border-slate-700 p-3" ref={menuRef}>
            <button
                onClick={onToggleMenu}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-800 transition-colors"
            >
                <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
                    {userEmail.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 text-left">
                    <p className="text-sm text-slate-200 truncate">{userEmail}</p>
                </div>
                <ChevronDown
                    className={`w-4 h-4 text-slate-400 transition-transform ${isMenuOpen ? "rotate-180" : ""
                        }`}
                />
            </button>

            {/* Dropdown Menu */}
            {isMenuOpen && (
                <div className="mt-2 bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
                    <button
                        onClick={() => {
                            onOpenSettings();
                            onToggleMenu();
                        }}
                        className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                    >
                        <Settings className="w-4 h-4" />
                        Cài đặt
                    </button>
                    <button
                        onClick={onLogout}
                        className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:bg-slate-700 transition-colors"
                    >
                        <LogOut className="w-4 h-4" />
                        Đăng xuất
                    </button>
                </div>
            )}
        </div>
    );
}
