"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Menu, PanelLeftClose } from "lucide-react";
import { ChatMessage, LoadingMessage } from "./ChatMessage";
import { useMessages } from "@/hooks/use-messages";
import type { Chat } from "@/types";

interface ChatViewProps {
  isSidebarCollapsed: boolean;
  onToggleSidebar: () => void;
  selectedChatId: string | null;
  chats: Chat[];
  onSessionCreated?: (sessionId: number, title: string) => void;
}

export function ChatView({
  isSidebarCollapsed,
  onToggleSidebar,
  selectedChatId,
  chats,
  onSessionCreated,
}: ChatViewProps) {
  const [inputValue, setInputValue] = useState("");
  const { messages, sendMessage, isLoading } = useMessages(selectedChatId);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    // Reset height to auto to get the correct scrollHeight
    e.target.style.height = "auto";
    // Set height to scrollHeight, but max at 150px
    e.target.style.height = Math.min(e.target.scrollHeight, 150) + "px";
  };

  // Get current chat name
  const currentChat = chats.find((chat) => chat.id === selectedChatId);
  const chatTitle = currentChat ? currentChat.name : "Chat mới";

  const handleSend = () => {
    if (!inputValue.trim()) return;
    sendMessage(inputValue, onSessionCreated);
    setInputValue("");
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter to send, Shift+Enter for new line
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Empty state - show centered input
  if (messages.length === 0) {
    return (
      <div className="flex flex-col h-full bg-gradient-to-br from-blue-50 via-indigo-50 to-slate-50">
        {/* Header */}
        <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 px-6 py-3 flex items-center justify-between">
          <button
            onClick={onToggleSidebar}
            className="p-2 hover:bg-gray-100 rounded transition-colors"
            title={isSidebarCollapsed ? "Mở sidebar" : "Đóng sidebar"}
          >
            {isSidebarCollapsed ? (
              <Menu className="w-5 h-5" />
            ) : (
              <PanelLeftClose className="w-5 h-5" />
            )}
          </button>
          <h2 className="absolute left-1/2 -translate-x-1/2">Chat mới</h2>
        </header>

        {/* Centered Content */}
        <div className="flex-1 flex flex-col items-center justify-center px-6">
          <div className="w-full max-w-2xl">
            <h1 className="text-4xl text-blue-900 text-center mb-12">
              Chào bạn, tôi là trợ lý pháp lý AI
            </h1>

            {/* Input Box */}
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg p-4">
              <div className="flex items-end gap-3">
                <textarea
                  ref={textareaRef}
                  value={inputValue}
                  onChange={handleInputChange}
                  onKeyDown={handleKeyDown}
                  placeholder="Hỏi về vấn đề pháp lý hoặc @mention"
                  className="flex-1 outline-none bg-transparent text-lg resize-none min-h-[28px] max-h-[150px]"
                  rows={1}
                  autoFocus
                />
                <button
                  onClick={handleSend}
                  disabled={isLoading || !inputValue.trim()}
                  className="bg-blue-700 hover:bg-blue-800 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-full p-2.5 transition-colors flex-shrink-0"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Chat view with messages
  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <button
          onClick={onToggleSidebar}
          className="p-2 hover:bg-gray-100 rounded transition-colors"
          title={isSidebarCollapsed ? "Mở sidebar" : "Đóng sidebar"}
        >
          {isSidebarCollapsed ? (
            <Menu className="w-5 h-5" />
          ) : (
            <PanelLeftClose className="w-5 h-5" />
          )}
        </button>
        <h2 className="absolute left-1/2 -translate-x-1/2">{chatTitle}</h2>
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
          {/* Scroll anchor for auto-scroll */}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="px-6 pb-6 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-end gap-3">
              <textarea
                ref={textareaRef}
                value={inputValue}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="Hỏi bất cứ điều gì hoặc @mention"
                className="flex-1 outline-none bg-transparent resize-none min-h-[24px] max-h-[150px]"
                rows={1}
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !inputValue.trim()}
                className="bg-blue-700 hover:bg-blue-800 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-full p-2.5 transition-colors flex-shrink-0"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
