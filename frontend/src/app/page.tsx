"use client";

import { useState } from "react";
import LoginPage from "./(auth)/login/page";
import { Sidebar } from "@/components/layout/Sidebar";
import { ChatView } from "@/components/features/chat";
import { KnowledgeBaseView } from "@/components/features/knowledge-base";
import { SettingsModal } from "@/components/features/settings";
import { useChats } from "@/hooks/use-chats";
import { useAuth } from "@/contexts/AuthContext";
import { NEW_CHAT_ID } from "@/constants";
import type { ViewType, SettingsData } from "@/types";

export default function Home() {
  const { isAuthenticated, isLoading, user, logout, updateUser } = useAuth();
  const [currentView, setCurrentView] = useState<ViewType>("chat");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const { chats, selectedChatId, selectChat, renameChat, deleteChat, addChatFromSession } =
    useChats();

  const handleLogout = () => {
    logout();
  };

  const handleSettingsSave = (data: SettingsData) => {
    updateUser(data);
  };

  const handleViewChange = (view: ViewType) => {
    setCurrentView(view);
    if (view === "knowledge") {
      selectChat(NEW_CHAT_ID);
    }
  };

  // Show loading spinner while checking auth
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-white/10 backdrop-blur-sm rounded-2xl mb-4 animate-pulse">
            <span className="text-4xl">⚖️</span>
          </div>
          <p className="text-blue-200">Đang tải...</p>
        </div>
      </div>
    );
  }

  // Show login page if not authenticated
  if (!isAuthenticated) {
    return <LoginPage />;
  }

  // Show main app after login
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar
        currentView={currentView}
        onViewChange={handleViewChange}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        onLogout={handleLogout}
        onOpenSettings={() => setIsSettingsOpen(true)}
        userEmail={user?.email || ""}
        selectedChatId={selectedChatId}
        onSelectChat={selectChat}
        chats={chats}
        onRenameChat={renameChat}
        onDeleteChat={deleteChat}
      />
      <main className="flex-1 overflow-hidden">
        {currentView === "chat" ? (
          <ChatView
            isSidebarCollapsed={isSidebarCollapsed}
            onToggleSidebar={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            selectedChatId={selectedChatId}
            chats={chats}
            onSessionCreated={addChatFromSession}
          />
        ) : (
          <KnowledgeBaseView
            isSidebarCollapsed={isSidebarCollapsed}
            onToggleSidebar={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          />
        )}
      </main>

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        currentEmail={user?.email || ""}
        onSave={handleSettingsSave}
      />
    </div>
  );
}
