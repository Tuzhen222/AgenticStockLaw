"use client";

import { Copy, RotateCcw, ThumbsUp, ThumbsDown, MoreHorizontal } from "lucide-react";
import type { Message } from "@/types";

interface ChatMessageProps {
    message: Message;
}

// Loading indicator component
function TypingIndicator() {
    return (
        <div className="flex gap-1 items-center p-2">
            <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
        </div>
    );
}

// Markdown renderer using react-markdown library
import ReactMarkdown from 'react-markdown';

function SimpleMarkdown({ content }: { content: string }) {
    // Pre-process: Handle escaped newlines and ensure proper line breaks
    const processedContent = content
        .replace(/\\n/g, '\n')
        // Convert Unicode bullet points to markdown-compatible dashes
        .replace(/•/g, '-')
        // Insert newlines before headers that appear inline
        .replace(/([^\n])(##\s)/g, '$1\n\n$2')
        // Insert newlines before bullet points
        .replace(/([^\n])([-*+]\s)/g, '$1\n$2')
        // Insert newlines before numbered lists
        .replace(/([^\n])(\d+\.\s)/g, '$1\n$2')
        // Ensure paragraphs are separated (single newline -> double for markdown)
        .replace(/([^.\n])\n([A-Z])/g, '$1\n\n$2');

    return (
        <div className="space-y-2 prose prose-blue max-w-none">
            <ReactMarkdown
                components={{
                    h2: ({ children }) => (
                        <h2 className="text-lg font-semibold text-blue-900 mt-4 mb-2 first:mt-0">
                            {children}
                        </h2>
                    ),
                    h3: ({ children }) => (
                        <h3 className="text-md font-semibold text-gray-800 mt-3 mb-1">
                            {children}
                        </h3>
                    ),
                    p: ({ children }) => (
                        <p className="text-gray-700 leading-relaxed">{children}</p>
                    ),
                    strong: ({ children }) => (
                        <strong className="font-semibold text-gray-900">{children}</strong>
                    ),
                    ul: ({ children }) => (
                        <ul className="ml-4 list-disc text-gray-700">{children}</ul>
                    ),
                    ol: ({ children }) => (
                        <ol className="ml-4 list-decimal text-gray-700">{children}</ol>
                    ),
                    li: ({ children }) => (
                        <li className="text-gray-700">{children}</li>
                    ),
                    a: ({ href, children }) => (
                        <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                            {children}
                        </a>
                    ),
                    hr: () => <hr className="my-4 border-gray-200" />,
                }}
            >
                {processedContent}
            </ReactMarkdown>
        </div>
    );
}

export function ChatMessage({ message }: ChatMessageProps) {
    const isAssistant = message.type === "assistant";

    // Get user initial from localStorage
    const getUserInitial = () => {
        if (typeof window !== "undefined") {
            const email = localStorage.getItem("user_email");
            if (email) return email.charAt(0).toUpperCase();
        }
        return "U";
    };

    return (
        <div className={`flex gap-3 ${isAssistant ? "" : "justify-end"}`}>
            {isAssistant && (
                <div className="w-8 h-8 bg-gradient-to-br from-blue-900 to-blue-700 rounded-lg flex items-center justify-center flex-shrink-0">
                    <span className="text-white text-sm">⚖️</span>
                </div>
            )}

            <div className={isAssistant ? "flex-1" : "max-w-[70%]"}>
                <div
                    className={`p-4 rounded-2xl ${isAssistant
                        ? "bg-white border border-gray-200"
                        : "bg-blue-700 text-white"
                        }`}
                >
                    {isAssistant ? (
                        // Show typing indicator if content is empty (waiting for first token)
                        message.content ? (
                            <SimpleMarkdown content={message.content} />
                        ) : (
                            <TypingIndicator />
                        )
                    ) : (
                        <p className="text-white">{message.content}</p>
                    )}
                </div>

                {/* Timestamp below message */}
                {isAssistant && message.timestamp && (
                    <div className="text-gray-400 text-xs mt-2 ml-1">
                        {message.timestamp}
                    </div>
                )}
            </div>

            {/* User avatar with initial */}
            {!isAssistant && (
                <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-white text-sm font-medium">{getUserInitial()}</span>
                </div>
            )}
        </div>
    );
}

// Export loading message component
export function LoadingMessage() {
    return (
        <div className="flex gap-4">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-900 to-blue-700 rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-white text-sm">⚖️</span>
            </div>
            <div className="flex-1 max-w-3xl">
                <div className="p-4 rounded-2xl bg-white border border-gray-200">
                    <TypingIndicator />
                </div>
            </div>
        </div>
    );
}
