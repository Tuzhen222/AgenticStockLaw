/**
 * Knowledge Base Service - API calls for knowledge base functionality
 * Currently using mock data, will be replaced with API calls
 */

import type { KnowledgeBase } from "@/types";

export interface CreateKnowledgeBaseRequest {
    name: string;
    type: string;
    description?: string;
}

export const knowledgeBaseService = {
    /**
     * Get all knowledge bases
     * TODO: Replace with actual API call
     */
    async getAll(): Promise<KnowledgeBase[]> {
        console.log("[KnowledgeBaseService] Getting all knowledge bases");
        return [];
    },

    /**
     * Get a single knowledge base by ID
     * TODO: Replace with actual API call
     */
    async getById(id: string): Promise<KnowledgeBase | null> {
        console.log(`[KnowledgeBaseService] Getting knowledge base: ${id}`);
        return null;
    },

    /**
     * Create a new knowledge base
     * TODO: Replace with actual API call
     */
    async create(data: CreateKnowledgeBaseRequest): Promise<KnowledgeBase> {
        console.log("[KnowledgeBaseService] Creating knowledge base:", data);

        const newKB: KnowledgeBase = {
            id: Date.now().toString(),
            name: data.name,
            type: data.type,
            files: 0,
            chunks: 0,
            expanded: false,
            favorite: false,
            documents: [],
        };

        return newKB;
    },

    /**
     * Update a knowledge base
     * TODO: Replace with actual API call
     */
    async update(
        id: string,
        data: Partial<KnowledgeBase>
    ): Promise<KnowledgeBase> {
        console.log(`[KnowledgeBaseService] Updating knowledge base: ${id}`, data);
        return { id, ...data } as KnowledgeBase;
    },

    /**
     * Delete a knowledge base
     * TODO: Replace with actual API call
     */
    async delete(id: string): Promise<void> {
        console.log(`[KnowledgeBaseService] Deleting knowledge base: ${id}`);
    },

    /**
     * Upload document to knowledge base
     * TODO: Replace with actual API call
     */
    async uploadDocument(kbId: string, file: File): Promise<void> {
        console.log(`[KnowledgeBaseService] Uploading to ${kbId}:`, file.name);
    },
};
