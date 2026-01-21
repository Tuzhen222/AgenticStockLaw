/**
 * Chat data utilities
 * Data will be loaded from API based on authenticated user
 */

import type { Message } from "@/types";

// Empty messages - will be populated from API
export const MOCK_MESSAGES: Record<string, Message[]> = {};

/**
 * Get mock AI response based on user input
 * TODO: Replace with actual API call to backend AI service
 */
export function getMockAIResponse(userMessage: string): string {
    return `Xin chào! Tôi là trợ lý pháp lý AI, sẵn sàng hỗ trợ bạn về các vấn đề pháp luật. Bạn đã hỏi: "${userMessage.slice(0, 50)}..."`;
}
