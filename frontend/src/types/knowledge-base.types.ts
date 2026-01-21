// Knowledge Base related types
export interface KnowledgeDocument {
    id: string;
    name: string;
    size: number;
    lastModified?: string;
    downloadUrl?: string;
}

export interface KnowledgeBase {
    id: string;
    name: string;
    type: string;
    files: number;
    chunks: number;
    expanded?: boolean;
    favorite?: boolean;
    documents?: KnowledgeDocument[];
    loadingDocs?: boolean;
}

export interface ModalState {
    isOpen: boolean;
    id: string;
    name: string;
    type: "knowledge-base" | "document";
}
