// Auth related types
export interface User {
    id?: number;
    email: string;
    username?: string;
    name?: string;
    full_name?: string;
    role?: Role;
}

export interface Role {
    id: number;
    name: string;
    description?: string;
}

export interface LoginCredentials {
    username: string;
    password: string;
}

export interface SettingsData {
    name: string;
    email: string;
    password?: string;
}

export interface AuthResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
}
