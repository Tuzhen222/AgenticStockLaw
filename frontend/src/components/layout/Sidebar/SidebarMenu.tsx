"use client";

import { MessageSquarePlus, BookOpen } from "lucide-react";
import type { ViewType } from "@/types";

interface SidebarMenuProps {
    currentView: ViewType;
    onViewChange: (view: ViewType) => void;
    onNewChat: () => void;
}

export function SidebarMenu({
    currentView,
    onViewChange,
    onNewChat,
}: SidebarMenuProps) {
    const menuItems = [
        { icon: MessageSquarePlus, label: "Chat mới", view: "chat" as const },
        { icon: BookOpen, label: "Cơ sở tri thức", view: "knowledge" as const },
    ];

    const handleClick = (view: ViewType) => {
        if (view === "chat") {
            onNewChat();
        } else {
            onViewChange(view);
        }
    };

    return (
        <nav className="p-3 space-y-1">
            {menuItems.map((item) => (
                <button
                    key={item.view}
                    onClick={() => handleClick(item.view)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg menu-item ${currentView === item.view
                        ? "bg-blue-600 text-white"
                        : "text-slate-300 hover:bg-slate-800"
                        }`}
                >
                    <item.icon className="w-5 h-5" />
                    <span>{item.label}</span>
                </button>
            ))}
        </nav>
    );
}
