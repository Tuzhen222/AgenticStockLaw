/**
 * Chat Service - API calls for chat functionality
 * Connects to Backend API which calls AI Gateway
 */

import type { Message } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// Helper to get auth token
function getAuthToken(): string | null {
    if (typeof window !== "undefined") {
        return localStorage.getItem("access_token");
    }
    return null;
}

// Helper for authenticated requests
async function authFetch(url: string, options: RequestInit = {}) {
    const token = getAuthToken();
    const headers: HeadersInit = {
        "Content-Type": "application/json",
        ...(options.headers || {}),
    };
    if (token) {
        (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
    }
    return fetch(url, { ...options, headers });
}

export interface ChatSession {
    id: number;
    title: string;
    created_at: string;
    updated_at: string;
}

export interface ChatMessageApi {
    id: number;
    role: string;
    content: string;
    extra_data?: Record<string, unknown>;
    created_at: string;
}

export interface SendMessageRequest {
    chatId: string;
    content: string;
}

export interface SendMessageResponse {
    message: Message;
}

export interface ChatApiResponse {
    answer: string;
    sources: Array<{
        title: string;
        content: string;
        score?: number;
        metadata?: Record<string, unknown>;
    }>;
    session_id?: string;
    metadata?: Record<string, unknown>;
}

export const chatService = {
    // ============ Session Management ============

    /**
     * Get all chat sessions for current user (requires auth)
     */
    async getSessions(): Promise<ChatSession[]> {
        try {
            const response = await authFetch(`${API_URL}/chat/sessions`);
            if (!response.ok) {
                if (response.status === 401) return []; // Not logged in
                throw new Error(`API error: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error("[ChatService] getSessions error:", error);
            return [];
        }
    },

    /**
     * Create a new chat session (requires auth)
     */
    async createSession(title: string = "New Chat"): Promise<ChatSession | null> {
        try {
            const response = await authFetch(`${API_URL}/chat/sessions`, {
                method: "POST",
                body: JSON.stringify({ title }),
            });
            if (!response.ok) return null;
            return await response.json();
        } catch (error) {
            console.error("[ChatService] createSession error:", error);
            return null;
        }
    },

    /**
     * Get messages for a session (requires auth)
     */
    async getSessionMessages(sessionId: number): Promise<Message[]> {
        try {
            const response = await authFetch(`${API_URL}/chat/sessions/${sessionId}/messages`);
            if (!response.ok) return [];
            const messages: ChatMessageApi[] = await response.json();
            return messages.map((m) => ({
                id: m.id.toString(),
                type: m.role as "user" | "assistant",
                content: m.content,
                timestamp: m.created_at,
            }));
        } catch (error) {
            console.error("[ChatService] getSessionMessages error:", error);
            return [];
        }
    },

    /**
     * Delete a chat session (requires auth)
     */
    async deleteSession(sessionId: number): Promise<boolean> {
        try {
            const response = await authFetch(`${API_URL}/chat/sessions/${sessionId}`, {
                method: "DELETE",
            });
            return response.ok;
        } catch (error) {
            console.error("[ChatService] deleteSession error:", error);
            return false;
        }
    },

    // ============ Existing Methods ============

    /**
     * Get messages for a specific chat
     */
    async getMessages(chatId: string): Promise<Message[]> {
        console.log(`[ChatService] Getting messages for chat: ${chatId}`);
        // Use session API if chatId is numeric
        if (!isNaN(Number(chatId))) {
            return this.getSessionMessages(Number(chatId));
        }
        return [];
    },

    /**
     * Send a message to chat
     */
    async sendMessage(chatId: string, content: string): Promise<Message> {
        console.log(`[ChatService] Sending message to chat: ${chatId}`);

        const message: Message = {
            id: Date.now().toString(),
            type: "user",
            content,
        };

        return message;
    },

    /**
     * Get AI response from Backend API
     */
    async getAIResponse(chatId: string, userMessage: string): Promise<Message> {
        console.log(`[ChatService] Calling API for: ${userMessage}`);

        try {
            const response = await fetch(`${API_URL}/chat/anonymous`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    query: userMessage,
                    session_id: chatId,
                    knowledge_base: "stock_law_chunks",
                }),
            });

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            const data: ChatApiResponse = await response.json();

            const aiMessage: Message = {
                id: Date.now().toString(),
                type: "assistant",
                content: data.answer || "Không có phản hồi từ hệ thống.",
                timestamp: "Vừa xong",
                sources: data.sources,
            };

            return aiMessage;
        } catch (error) {
            console.error("[ChatService] API error:", error);

            // Return error message
            return {
                id: Date.now().toString(),
                type: "assistant",
                content: `❌ Lỗi kết nối: ${error instanceof Error ? error.message : "Unknown error"}`,
                timestamp: "Vừa xong",
            };
        }
    },

    /**
     * Stream AI response using SSE
     * @param userMessage - User's message
     * @param onToken - Callback for each token
     * @param onStatus - Callback for status updates
     * @param onDone - Callback when complete
     * @param onError - Callback for errors
     */
    async streamResponse(
        userMessage: string,
        onToken: (token: string) => void,
        onStatus?: (status: string) => void,
        onDone?: (metadata: { trace_id: string; routed_to: string }) => void,
        onError?: (error: string) => void
    ): Promise<void> {
        console.log(`[ChatService] Streaming for: ${userMessage}`);

        try {
            const response = await fetch(`${API_URL}/chat/stream`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    query: userMessage,
                    session_id: "stream-session",
                    knowledge_base: "stock_law_chunks",
                }),
            });

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            await this.processSSEStream(response, onToken, onStatus, onDone, onError);
        } catch (error) {
            console.error("[ChatService] Stream error:", error);
            onError?.(error instanceof Error ? error.message : "Unknown error");
        }
    },

    /**
     * Stream AI response with authentication - saves messages to database
     * @param sessionId - DB session ID (null to create new session)
     * @param userMessage - User's message
     * @param onToken - Callback for each token
     * @param onSession - Callback when session is created/confirmed
     * @param onStatus - Callback for status updates
     * @param onDone - Callback when complete
     * @param onError - Callback for errors
     */
    async streamResponseAuth(
        sessionId: number | null,
        userMessage: string,
        onToken: (token: string) => void,
        onSession?: (sessionId: number) => void,
        onStatus?: (status: string) => void,
        onDone?: (metadata: { trace_id: string; routed_to: string }) => void,
        onError?: (error: string) => void
    ): Promise<void> {
        console.log(`[ChatService] Auth streaming for session: ${sessionId}`);

        try {
            const response = await authFetch(`${API_URL}/chat/stream/auth`, {
                method: "POST",
                body: JSON.stringify({
                    query: userMessage,
                    session_id: sessionId,
                    knowledge_base: "stock_law_chunks",
                }),
            });

            if (!response.ok) {
                if (response.status === 401) {
                    onError?.("Please login to save chat history");
                    return;
                }
                throw new Error(`API error: ${response.status}`);
            }

            await this.processSSEStream(response, onToken, onStatus, onDone, onError, onSession);
        } catch (error) {
            console.error("[ChatService] Auth stream error:", error);
            onError?.(error instanceof Error ? error.message : "Unknown error");
        }
    },

    /**
     * Process SSE stream response
     */
    async processSSEStream(
        response: Response,
        onToken: (token: string) => void,
        onStatus?: (status: string) => void,
        onDone?: (metadata: { trace_id: string; routed_to: string }) => void,
        onError?: (error: string) => void,
        onSession?: (sessionId: number) => void
    ): Promise<void> {
        const reader = response.body?.getReader();
        if (!reader) {
            throw new Error("No response body");
        }

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    try {
                        const data = JSON.parse(line.slice(6));

                        switch (data.type) {
                            case "token":
                                onToken(data.content);
                                break;
                            case "status":
                                onStatus?.(data.content);
                                break;
                            case "done":
                                onDone?.({
                                    trace_id: data.trace_id,
                                    routed_to: data.routed_to
                                });
                                break;
                            case "error":
                                onError?.(data.content);
                                break;
                            case "session":
                                onSession?.(data.session_id);
                                break;
                        }
                    } catch (e) {
                        console.warn("[ChatService] Failed to parse SSE:", line);
                    }
                }
            }
        }
    },
};
