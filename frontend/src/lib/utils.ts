/**
 * Utility functions for the application
 */

/**
 * Format a date to a relative time string
 */
export function formatRelativeTime(date: Date | string): string {
    const now = new Date();
    const targetDate = typeof date === "string" ? new Date(date) : date;
    const diffInSeconds = Math.floor(
        (now.getTime() - targetDate.getTime()) / 1000
    );

    if (diffInSeconds < 60) return "Vừa xong";
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} phút trước`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} giờ trước`;
    if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} ngày trước`;

    return targetDate.toLocaleDateString("vi-VN");
}

/**
 * Generate a unique ID
 */
export function generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text: string, maxLength: number): string {
    if (text.length <= maxLength) return text;
    return `${text.slice(0, maxLength)}...`;
}

/**
 * Debounce function
 */
export function debounce<T extends (...args: Parameters<T>) => void>(
    func: T,
    wait: number
): (...args: Parameters<T>) => void {
    let timeout: NodeJS.Timeout | null = null;

    return (...args: Parameters<T>) => {
        if (timeout) clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    };
}

/**
 * Check if a string is empty or only whitespace
 */
export function isEmpty(value: string | null | undefined): boolean {
    return !value || value.trim().length === 0;
}

/**
 * Capitalize first letter of a string
 */
export function capitalize(text: string): string {
    if (!text) return "";
    return text.charAt(0).toUpperCase() + text.slice(1);
}
