"use client";

import { useState, useRef, useEffect, type MouseEvent } from "react";
import {
    MessageSquarePlus,
    BookOpen,
    Settings,
    LogOut,
    ChevronDown,
    MoreHorizontal,
    Edit3,
    Trash2,
} from "lucide-react";
import { SidebarMenu } from "./SidebarMenu";
import { SidebarChatList } from "./SidebarChatList";
import { SidebarUserMenu } from "./SidebarUserMenu";
import { RenameChatModal } from "@/components/features/chat/RenameChatModal";
import { DeleteConfirmModal } from "@/components/common/DeleteConfirmModal";
import { NEW_CHAT_ID, MESSAGES } from "@/constants";
import type { Chat, ViewType } from "@/types";

interface SidebarProps {
    currentView: ViewType;
    onViewChange: (view: ViewType) => void;
    isCollapsed: boolean;
    onToggleCollapse: () => void;
    onLogout: () => void;
    onOpenSettings: () => void;
    userEmail: string;
    selectedChatId: string | null;
    onSelectChat: (chatId: string) => void;
    chats: Chat[];
    onRenameChat: (chatId: string, newName: string) => void;
    onDeleteChat: (chatId: string) => void;
}

export function Sidebar({
    currentView,
    onViewChange,
    isCollapsed,
    onLogout,
    onOpenSettings,
    userEmail,
    selectedChatId,
    onSelectChat,
    chats,
    onRenameChat,
    onDeleteChat,
}: SidebarProps) {
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [chatMenuOpenId, setChatMenuOpenId] = useState<string | null>(null);
    const [isRenameModalOpen, setIsRenameModalOpen] = useState(false);
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    const [chatToEdit, setChatToEdit] = useState<Chat | null>(null);
    const menuRef = useRef<HTMLDivElement>(null);

    // Close menu when clicking outside
    useEffect(() => {
        function handleClickOutside(event: globalThis.MouseEvent) {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setIsMenuOpen(false);
            }
        }

        if (isMenuOpen) {
            document.addEventListener("mousedown", handleClickOutside);
            return () => document.removeEventListener("mousedown", handleClickOutside);
        }
    }, [isMenuOpen]);

    const handleChatClick = (chatId: string) => {
        onSelectChat(chatId);
        if (currentView !== "chat") {
            onViewChange("chat");
        }
    };

    const handleNewChat = () => {
        onSelectChat(NEW_CHAT_ID);
        if (currentView !== "chat") {
            onViewChange("chat");
        }
    };

    const handleOpenRename = (chat: Chat) => {
        setChatToEdit(chat);
        setIsRenameModalOpen(true);
        setChatMenuOpenId(null);
    };

    const handleOpenDelete = (chat: Chat) => {
        setChatToEdit(chat);
        setIsDeleteModalOpen(true);
        setChatMenuOpenId(null);
    };

    const handleRename = (newName: string) => {
        if (chatToEdit) {
            onRenameChat(chatToEdit.id, newName);
        }
    };

    const handleDelete = () => {
        if (chatToEdit) {
            onDeleteChat(chatToEdit.id);
        }
    };

    if (isCollapsed) {
        return null;
    }

    return (
        <aside className="w-64 bg-slate-900 text-white flex flex-col h-full sidebar-transition">
            {/* Logo */}
            <div className="p-4 border-b border-slate-700">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl flex items-center justify-center">
                        <span className="text-xl">⚖️</span>
                    </div>
                    <div>
                        <h1 className="font-semibold text-lg">Luật Gia AI</h1>
                        <span className="text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded">
                            BETA
                        </span>
                    </div>
                </div>
            </div>

            {/* Navigation Menu */}
            <SidebarMenu
                currentView={currentView}
                onViewChange={onViewChange}
                onNewChat={handleNewChat}
            />

            {/* Chat List - Always visible */}
            <SidebarChatList
                chats={chats}
                selectedChatId={selectedChatId}
                onChatClick={handleChatClick}
                onOpenRename={handleOpenRename}
                onOpenDelete={handleOpenDelete}
                chatMenuOpenId={chatMenuOpenId}
                onToggleChatMenu={(id) =>
                    setChatMenuOpenId(chatMenuOpenId === id ? null : id)
                }
            />

            {/* User Menu */}
            <SidebarUserMenu
                userEmail={userEmail}
                isMenuOpen={isMenuOpen}
                onToggleMenu={() => setIsMenuOpen(!isMenuOpen)}
                onOpenSettings={onOpenSettings}
                onLogout={onLogout}
                menuRef={menuRef}
            />

            {/* Modals */}
            <RenameChatModal
                isOpen={isRenameModalOpen}
                onClose={() => setIsRenameModalOpen(false)}
                currentName={chatToEdit?.name || ""}
                onRename={handleRename}
            />

            <DeleteConfirmModal
                isOpen={isDeleteModalOpen}
                onClose={() => setIsDeleteModalOpen(false)}
                onConfirm={handleDelete}
                title={MESSAGES.DELETE_CHAT_TITLE}
                message={MESSAGES.DELETE_CHAT_CONFIRM(chatToEdit?.name || "")}
            />
        </aside>
    );
}
