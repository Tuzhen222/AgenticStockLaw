// UI Messages and Labels
export const MESSAGES = {
    DELETE_CHAT_TITLE: "Xóa hội thoại",
    DELETE_CHAT_CONFIRM: (name: string) =>
        `Bạn có chắc chắn muốn xóa hội thoại "${name}"? Hành động này không thể hoàn tác.`,
    DELETE_KB_TITLE: "Xóa cơ sở tri thức",
    DELETE_KB_CONFIRM: (name: string) =>
        `Bạn có chắc chắn muốn xóa cơ sở tri thức "${name}"? Hành động này không thể hoàn tác.`,
    DELETE_DOC_TITLE: "Xóa tài liệu",
    DELETE_DOC_CONFIRM: (name: string) =>
        `Bạn có chắc chắn muốn xóa tài liệu "${name}"? Hành động này không thể hoàn tác.`,
} as const;

// Placeholder messages
export const PLACEHOLDERS = {
    CHAT_INPUT: "Hỏi về vấn đề pháp lý hoặc @mention",
    SEARCH_KB: "Tìm kiếm cơ sở tri thức...",
    EMAIL: "Nhập email",
    PASSWORD: "Nhập mật khẩu",
} as const;

// Error messages
export const ERRORS = {
    LOGIN_FAILED: "Email hoặc mật khẩu không đúng",
    PASSWORD_TOO_SHORT: "Mật khẩu mới phải có ít nhất 6 ký tự",
    PASSWORD_MISMATCH: "Mật khẩu xác nhận không khớp",
    CURRENT_PASSWORD_REQUIRED: "Vui lòng nhập mật khẩu hiện tại",
} as const;
