"use client";

import { useState, useCallback, useEffect } from "react";
import type { Chat } from "@/types";
import { chatService, type ChatSession } from "@/services/chat.service";

// Check if user is authenticated
function getAuthToken(): string | null {
    if (typeof window !== "undefined") {
        return localStorage.getItem("access_token");
    }
    return null;
}

export function useChats() {
    const [chats, setChats] = useState<Chat[]>([]);
    const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [authToken, setAuthToken] = useState<string | null>(null);

    // Track auth token changes (for login/logout detection)
    useEffect(() => {
        const token = getAuthToken();
        setAuthToken(token);

        // Listen for storage changes (login/logout in other tabs)
        const handleStorage = () => {
            const newToken = getAuthToken();
            if (newToken !== authToken) {
                setAuthToken(newToken);
            }
        };

        window.addEventListener("storage", handleStorage);

        // Also check periodically for same-tab login
        const interval = setInterval(() => {
            const newToken = getAuthToken();
            if (newToken !== authToken) {
                setAuthToken(newToken);
            }
        }, 1000);

        return () => {
            window.removeEventListener("storage", handleStorage);
            clearInterval(interval);
        };
    }, [authToken]);

    // Fetch sessions from API when auth changes
    useEffect(() => {
        async function fetchSessions() {
            if (!authToken) {
                setChats([]);
                return;
            }

            setIsLoading(true);
            try {
                const sessions = await chatService.getSessions();
                const chatList: Chat[] = sessions.map((s: ChatSession) => ({
                    id: s.id.toString(),
                    name: s.title,
                }));
                setChats(chatList);
            } catch (error) {
                console.error("[useChats] Failed to fetch sessions:", error);
            } finally {
                setIsLoading(false);
            }
        }
        fetchSessions();
    }, [authToken]);

    const refreshChats = useCallback(async () => {
        try {
            const sessions = await chatService.getSessions();
            const chatList: Chat[] = sessions.map((s: ChatSession) => ({
                id: s.id.toString(),
                name: s.title,
            }));
            setChats(chatList);
        } catch (error) {
            console.error("[useChats] Failed to refresh sessions:", error);
        }
    }, []);

    const selectChat = useCallback((chatId: string) => {
        setSelectedChatId(chatId);
    }, []);

    const renameChat = useCallback((chatId: string, newName: string) => {
        setChats((prev) =>
            prev.map((chat) =>
                chat.id === chatId ? { ...chat, name: newName } : chat
            )
        );
        // TODO: Call API to rename session
    }, []);

    const deleteChat = useCallback(
        async (chatId: string) => {
            // Call API to delete
            const success = await chatService.deleteSession(Number(chatId));
            if (success) {
                setChats((prev) => prev.filter((chat) => chat.id !== chatId));
                if (selectedChatId === chatId) {
                    setSelectedChatId(null);
                }
            }
        },
        [selectedChatId]
    );

    const createNewChat = useCallback(() => {
        // Just select null to indicate new chat mode
        // Session will be created when first message is sent
        setSelectedChatId(null);
        return null;
    }, []);

    const addChatFromSession = useCallback((sessionId: number, title: string) => {
        const newChat: Chat = {
            id: sessionId.toString(),
            name: title,
        };
        setChats((prev) => {
            // Check if already exists
            if (prev.find(c => c.id === newChat.id)) {
                return prev;
            }
            return [newChat, ...prev];
        });
        setSelectedChatId(sessionId.toString());
    }, []);

    return {
        chats,
        selectedChatId,
        isLoading,
        selectChat,
        renameChat,
        deleteChat,
        createNewChat,
        refreshChats,
        addChatFromSession,
    };
}
