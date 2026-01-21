"use client";

import { useState, useCallback, useEffect } from "react";
import type { KnowledgeBase, KnowledgeDocument } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export function useKnowledgeBase() {
    const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Fetch knowledge bases from Qdrant via API
    const fetchKnowledgeBases = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await fetch(`${API_URL}/knowledge-bases`);
            if (!response.ok) {
                throw new Error(`Failed to fetch: ${response.statusText}`);
            }
            const data = await response.json();
            setKnowledgeBases(data.knowledge_bases || []);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to fetch knowledge bases");
            console.error("Error fetching knowledge bases:", err);
        } finally {
            setLoading(false);
        }
    }, []);

    // Fetch documents for a specific knowledge base
    const fetchDocuments = useCallback(async (kbId: string) => {
        // Mark as loading
        setKnowledgeBases((prev) =>
            prev.map((kb) =>
                kb.id === kbId ? { ...kb, loadingDocs: true } : kb
            )
        );

        try {
            const response = await fetch(`${API_URL}/knowledge-bases/documents`);
            if (!response.ok) {
                throw new Error(`Failed to fetch documents: ${response.statusText}`);
            }
            const data = await response.json();

            // Map API response to our document format
            const documents: KnowledgeDocument[] = (data.documents || []).map((doc: {
                id: string;
                name: string;
                size: number;
                last_modified?: string;
            }) => ({
                id: doc.id,
                name: doc.name,
                size: doc.size,
                lastModified: doc.last_modified,
            }));

            // Update the knowledge base with documents
            setKnowledgeBases((prev) =>
                prev.map((kb) =>
                    kb.id === kbId
                        ? { ...kb, documents, loadingDocs: false, files: documents.length }
                        : kb
                )
            );
        } catch (err) {
            console.error("Error fetching documents:", err);
            setKnowledgeBases((prev) =>
                prev.map((kb) =>
                    kb.id === kbId ? { ...kb, loadingDocs: false } : kb
                )
            );
        }
    }, []);

    // Get download URL for a document (now returns direct URL to backend endpoint)
    const getDownloadUrl = useCallback((docName: string): string => {
        // The backend now streams the file directly, so we just return the endpoint URL
        return `${API_URL}/knowledge-bases/documents/${encodeURIComponent(docName)}/download`;
    }, []);

    // Fetch on mount
    useEffect(() => {
        fetchKnowledgeBases();
    }, [fetchKnowledgeBases]);

    const toggleExpanded = useCallback((id: string) => {
        setKnowledgeBases((prev) =>
            prev.map((kb) => {
                if (kb.id === id) {
                    const newExpanded = !kb.expanded;
                    // Fetch documents when expanding if not already loaded
                    if (newExpanded && !kb.documents) {
                        fetchDocuments(id);
                    }
                    return { ...kb, expanded: newExpanded };
                }
                return kb;
            })
        );
    }, [fetchDocuments]);

    const expandAll = useCallback(() => {
        setKnowledgeBases((prev) =>
            prev.map((kb) => {
                // Fetch documents if not already loaded
                if (!kb.documents) {
                    fetchDocuments(kb.id);
                }
                return { ...kb, expanded: true };
            })
        );
    }, [fetchDocuments]);

    const collapseAll = useCallback(() => {
        setKnowledgeBases((prev) => prev.map((kb) => ({ ...kb, expanded: false })));
    }, []);

    const toggleFavorite = useCallback((id: string) => {
        setKnowledgeBases((prev) =>
            prev.map((kb) => (kb.id === id ? { ...kb, favorite: !kb.favorite } : kb))
        );
    }, []);

    const renameKnowledgeBase = useCallback((id: string, newName: string) => {
        setKnowledgeBases((prev) =>
            prev.map((kb) => (kb.id === id ? { ...kb, name: newName } : kb))
        );
    }, []);

    const deleteKnowledgeBase = useCallback((id: string) => {
        setKnowledgeBases((prev) => prev.filter((kb) => kb.id !== id));
    }, []);

    const deleteDocument = useCallback((kbId: string, docId: string) => {
        setKnowledgeBases((prev) =>
            prev.map((kb) => {
                if (kb.id === kbId && kb.documents) {
                    const newDocuments = kb.documents.filter((doc) => doc.id !== docId);
                    return {
                        ...kb,
                        documents: newDocuments,
                        files: newDocuments.length,
                    };
                }
                return kb;
            })
        );
    }, []);

    const allExpanded = knowledgeBases.every((kb) => kb.expanded);

    return {
        knowledgeBases,
        loading,
        error,
        allExpanded,
        toggleExpanded,
        expandAll,
        collapseAll,
        toggleFavorite,
        renameKnowledgeBase,
        deleteKnowledgeBase,
        deleteDocument,
        refetch: fetchKnowledgeBases,
        getDownloadUrl,
    };
}
