// Chat related types
export interface Chat {
    id: string;
    name: string;
    createdAt?: string;
    updatedAt?: string;
}

export interface Message {
    id: string;
    type: "user" | "assistant";
    content: string;
    timestamp?: string;
}

export type ViewType = "chat" | "knowledge";
