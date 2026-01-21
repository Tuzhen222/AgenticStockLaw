/**
 * useMessages hook - manages chat messages state and actions
 * Uses SSE streaming for real-time AI responses
 * Supports both anonymous and authenticated modes
 */

import { useState, useEffect, useCallback, useRef } from "react";
import type { Message } from "@/types";
import { NEW_CHAT_ID } from "@/constants";
import { chatService } from "@/services/chat.service";

interface UseMessagesReturn {
    messages: Message[];
    isLoading: boolean;
    status: string;
    sendMessage: (content: string, onSessionCreated?: (sessionId: number, title: string) => void) => void;
    clearMessages: () => void;
}

// Check if user is authenticated
function isAuthenticated(): boolean {
    if (typeof window !== "undefined") {
        return !!localStorage.getItem("access_token");
    }
    return false;
}

export function useMessages(chatId: string | null): UseMessagesReturn {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [status, setStatus] = useState("");
    const streamingMessageRef = useRef<string>("");
    const previousChatIdRef = useRef<string | null>(null);

    // Load messages when chatId changes
    useEffect(() => {
        async function loadMessages() {
            const prevChatId = previousChatIdRef.current;
            previousChatIdRef.current = chatId;

            // If transitioning from NEW_CHAT_ID or null to a numeric ID, keep current messages
            // This preserves the streaming response when a new session is created
            if ((prevChatId === NEW_CHAT_ID || prevChatId === null) && chatId && !isNaN(Number(chatId))) {
                console.log('[useMessages] Keeping messages after session creation');
                return;
            }

            if (chatId && chatId !== NEW_CHAT_ID && !isNaN(Number(chatId))) {
                // Load from API for numeric session IDs
                const msgs = await chatService.getMessages(chatId);
                setMessages(msgs);
            } else {
                setMessages([]);
            }
        }
        loadMessages();
    }, [chatId]);

    // Send a message with SSE streaming
    const sendMessage = useCallback(async (
        content: string,
        onSessionCreated?: (sessionId: number, title: string) => void
    ) => {
        if (!content.trim()) return;

        // Add user message
        const userMessage: Message = {
            id: Date.now().toString(),
            type: "user",
            content: content.trim(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setIsLoading(true);
        setStatus("Đang xử lý...");
        streamingMessageRef.current = "";

        // Add placeholder streaming message
        const streamingMsgId = (Date.now() + 1).toString();
        const streamingMessage: Message = {
            id: streamingMsgId,
            type: "assistant",
            content: "",
            timestamp: "Đang trả lời...",
        };
        setMessages((prev) => [...prev, streamingMessage]);

        // Use authenticated endpoint if logged in
        if (isAuthenticated()) {
            const sessionId = chatId && chatId !== NEW_CHAT_ID ? Number(chatId) : null;

            await chatService.streamResponseAuth(
                sessionId,
                content.trim(),
                // onToken
                (token: string) => {
                    streamingMessageRef.current += token;
                    setMessages((prev) =>
                        prev.map((msg) =>
                            msg.id === streamingMsgId
                                ? { ...msg, content: streamingMessageRef.current }
                                : msg
                        )
                    );
                },
                // onSession - called when new session is created
                (newSessionId: number) => {
                    console.log(`[useMessages] Session created: ${newSessionId}`);
                    // Notify parent about new session so it can update sidebar
                    const title = content.trim().substring(0, 30) + (content.length > 30 ? "..." : "");
                    onSessionCreated?.(newSessionId, title);
                },
                // onStatus
                (newStatus: string) => {
                    setStatus(newStatus);
                },
                // onDone
                () => {
                    setStatus("");
                    setMessages((prev) =>
                        prev.map((msg) =>
                            msg.id === streamingMsgId
                                ? { ...msg, timestamp: "Vừa xong" }
                                : msg
                        )
                    );
                    setIsLoading(false);
                },
                // onError
                (error: string) => {
                    setStatus("");
                    setMessages((prev) =>
                        prev.map((msg) =>
                            msg.id === streamingMsgId
                                ? { ...msg, content: `❌ Lỗi: ${error}`, timestamp: "Lỗi" }
                                : msg
                        )
                    );
                    setIsLoading(false);
                }
            );
        } else {
            // Anonymous mode - no session saving
            await chatService.streamResponse(
                content.trim(),
                // onToken
                (token: string) => {
                    streamingMessageRef.current += token;
                    setMessages((prev) =>
                        prev.map((msg) =>
                            msg.id === streamingMsgId
                                ? { ...msg, content: streamingMessageRef.current }
                                : msg
                        )
                    );
                },
                // onStatus
                (newStatus: string) => {
                    setStatus(newStatus);
                },
                // onDone
                () => {
                    setStatus("");
                    setMessages((prev) =>
                        prev.map((msg) =>
                            msg.id === streamingMsgId
                                ? { ...msg, timestamp: "Vừa xong" }
                                : msg
                        )
                    );
                    setIsLoading(false);
                },
                // onError
                (error: string) => {
                    setStatus("");
                    setMessages((prev) =>
                        prev.map((msg) =>
                            msg.id === streamingMsgId
                                ? { ...msg, content: `❌ Lỗi: ${error}`, timestamp: "Lỗi" }
                                : msg
                        )
                    );
                    setIsLoading(false);
                }
            );
        }
    }, [chatId]);

    // Clear all messages
    const clearMessages = useCallback(() => {
        setMessages([]);
    }, []);

    return {
        messages,
        isLoading,
        status,
        sendMessage,
        clearMessages,
    };
}
