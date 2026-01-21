"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { SettingsModal } from "@/components/features/settings";
import { useChats } from "@/hooks/use-chats";
import { DEFAULT_USER_EMAIL, NEW_CHAT_ID } from "@/constants";
import type { ViewType, SettingsData } from "@/types";

interface MainLayoutProps {
    children: ReactNode;
}

export default function MainLayout({ children }: MainLayoutProps) {
    const [currentView, setCurrentView] = useState<ViewType>("chat");
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [userEmail, setUserEmail] = useState(DEFAULT_USER_EMAIL);

    const { chats, selectedChatId, selectChat, renameChat, deleteChat } =
        useChats();

    const handleLogout = () => {
        // Redirect to login page
        window.location.href = "/login";
    };

    const handleSettingsSave = (data: SettingsData) => {
        setUserEmail(data.email);
    };

    const handleViewChange = (view: ViewType) => {
        setCurrentView(view);
        if (view === "knowledge") {
            selectChat(NEW_CHAT_ID);
        }
    };

    return (
        <div className="flex h-screen bg-gray-50">
            <Sidebar
                currentView={currentView}
                onViewChange={handleViewChange}
                isCollapsed={isSidebarCollapsed}
                onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
                onLogout={handleLogout}
                onOpenSettings={() => setIsSettingsOpen(true)}
                userEmail={userEmail}
                selectedChatId={selectedChatId}
                onSelectChat={selectChat}
                chats={chats}
                onRenameChat={renameChat}
                onDeleteChat={deleteChat}
            />
            <main className="flex-1 overflow-hidden">{children}</main>

            <SettingsModal
                isOpen={isSettingsOpen}
                onClose={() => setIsSettingsOpen(false)}
                currentEmail={userEmail}
                onSave={handleSettingsSave}
            />
        </div>
    );
}
