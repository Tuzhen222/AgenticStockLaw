"use client";

import { useState, useRef, useEffect } from "react";
import { MoreHorizontal, Edit3, Trash2 } from "lucide-react";
import type { Chat } from "@/types";

interface SidebarChatListProps {
    chats: Chat[];
    selectedChatId: string | null;
    onChatClick: (chatId: string) => void;
    onOpenRename: (chat: Chat) => void;
    onOpenDelete: (chat: Chat) => void;
    chatMenuOpenId: string | null;
    onToggleChatMenu: (chatId: string) => void;
}

export function SidebarChatList({
    chats,
    selectedChatId,
    onChatClick,
    onOpenRename,
    onOpenDelete,
    chatMenuOpenId,
    onToggleChatMenu,
}: SidebarChatListProps) {
    const chatMenuRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});

    // Close chat menu when clicking outside
    useEffect(() => {
        function handleClickOutside(event: globalThis.MouseEvent) {
            if (chatMenuOpenId) {
                const chatMenuRef = chatMenuRefs.current[chatMenuOpenId];
                if (chatMenuRef && !chatMenuRef.contains(event.target as Node)) {
                    onToggleChatMenu(chatMenuOpenId);
                }
            }
        }

        if (chatMenuOpenId) {
            document.addEventListener("mousedown", handleClickOutside);
            return () => document.removeEventListener("mousedown", handleClickOutside);
        }
    }, [chatMenuOpenId, onToggleChatMenu]);

    return (
        <div className="flex-1 overflow-y-auto custom-scroll">
            <div className="px-3 py-2 text-xs text-slate-400 uppercase tracking-wider">
                Lịch sử chat
            </div>
            <div className="px-2 space-y-1">
                {chats.map((chat) => (
                    <div
                        key={chat.id}
                        className={`group relative flex items-center rounded-lg transition-colors ${selectedChatId === chat.id
                                ? "bg-slate-700"
                                : "hover:bg-slate-800"
                            }`}
                    >
                        <button
                            onClick={() => onChatClick(chat.id)}
                            className="flex-1 text-left px-3 py-2 text-sm text-slate-300 truncate"
                        >
                            {chat.name}
                        </button>

                        {/* Chat Menu Button */}
                        <div
                            ref={(el) => {
                                chatMenuRefs.current[chat.id] = el;
                            }}
                            className="relative"
                        >
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onToggleChatMenu(chat.id);
                                }}
                                className="p-1.5 opacity-0 group-hover:opacity-100 hover:bg-slate-600 rounded transition-all"
                            >
                                <MoreHorizontal className="w-4 h-4 text-slate-400" />
                            </button>

                            {/* Dropdown Menu */}
                            {chatMenuOpenId === chat.id && (
                                <div className="absolute right-0 top-full mt-1 w-40 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50">
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onOpenRename(chat);
                                        }}
                                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                                    >
                                        <Edit3 className="w-4 h-4" />
                                        Đổi tên
                                    </button>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onOpenDelete(chat);
                                        }}
                                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-slate-700 transition-colors"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                        Xóa
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
