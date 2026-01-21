"use client";

import { useState, useRef, type KeyboardEvent } from "react";
import { Send } from "lucide-react";
import { PLACEHOLDERS } from "@/constants";

interface ChatInputProps {
    onSend: (message: string) => void;
    placeholder?: string;
    autoFocus?: boolean;
}

export function ChatInput({
    onSend,
    placeholder = PLACEHOLDERS.CHAT_INPUT,
    autoFocus = false,
}: ChatInputProps) {
    const [value, setValue] = useState("");
    const inputRef = useRef<HTMLInputElement>(null);

    const handleSend = () => {
        if (!value.trim()) return;
        onSend(value.trim());
        setValue("");
    };

    const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex items-center gap-3">
            <input
                type="text"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder={placeholder}
                className="flex-1 outline-none bg-transparent text-lg"
                autoFocus={autoFocus}
                ref={inputRef}
            />
            <button
                onClick={handleSend}
                disabled={!value.trim()}
                className="bg-blue-700 hover:bg-blue-800 text-white rounded-full p-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
                <Send className="w-5 h-5" />
            </button>
        </div>
    );
}
