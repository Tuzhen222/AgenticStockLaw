/**
 * Authentication service for API calls
 */

const AUTH_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const USER_EMAIL_KEY = "user_email";

// API URL - use relative path for same-origin, or env var
const API_URL = typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL || "/api")
    : "/api";

export interface AuthTokens {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export interface UserResponse {
    id: number;
    email: string;
    username: string;
    full_name: string | null;
    is_active: boolean;
    role: {
        id: number;
        name: string;
        description: string | null;
    };
    created_at: string;
    updated_at: string;
}

export interface RegisterData {
    email: string;
    username: string;
    password: string;
    full_name?: string;
}

class AuthService {
    /**
     * Login with email and password
     */
    async login(email: string, password: string): Promise<AuthTokens> {
        const formData = new URLSearchParams();
        formData.append("username", email); // OAuth2 spec uses 'username' field for credentials
        formData.append("password", password);

        const response = await fetch(`${API_URL}/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: formData,
        });

        if (!response.ok) {
            let message = "Login failed";
            try {
                const error = await response.json();
                message = error.detail || message;
            } catch {
                // Response was not JSON
            }
            throw new Error(message);
        }

        const tokens: AuthTokens = await response.json();
        this.setTokens(tokens);
        // Save email for avatar display
        this.setUserEmail(email);
        return tokens;
    }

    /**
     * Register a new user
     */
    async register(data: RegisterData): Promise<UserResponse> {
        const response = await fetch(`${API_URL}/auth/register`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            let message = "Registration failed";
            try {
                const error = await response.json();
                message = error.detail || message;
            } catch {
                // Response was not JSON
            }
            throw new Error(message);
        }

        return response.json();
    }

    /**
     * Get current user info
     */
    async getCurrentUser(): Promise<UserResponse> {
        const token = this.getAccessToken();
        if (!token) {
            throw new Error("No token found");
        }

        const response = await fetch(`${API_URL}/auth/me`, {
            method: "GET",
            headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
            },
        });

        if (!response.ok) {
            if (response.status === 401) {
                this.clearTokens();
            }
            throw new Error("Failed to get user info");
        }

        return response.json();
    }

    /**
     * Logout user
     */
    logout(): void {
        this.clearTokens();
    }

    /**
     * Refresh tokens using refresh token
     * Returns new tokens or throws if refresh token is invalid/expired
     */
    async refreshTokens(): Promise<AuthTokens> {
        const refreshToken = this.getRefreshToken();
        if (!refreshToken) {
            throw new Error("No refresh token found");
        }

        const response = await fetch(`${API_URL}/auth/refresh`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (!response.ok) {
            // Clear tokens if refresh fails
            this.clearTokens();
            throw new Error("Session expired. Please login again.");
        }

        const tokens: AuthTokens = await response.json();
        this.setTokens(tokens);
        return tokens;
    }

    /**
     * Store tokens in localStorage
     */
    setTokens(tokens: AuthTokens): void {
        if (typeof window !== "undefined") {
            localStorage.setItem(AUTH_TOKEN_KEY, tokens.access_token);
            localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
        }
    }

    /**
     * Get access token from localStorage
     */
    getAccessToken(): string | null {
        if (typeof window !== "undefined") {
            return localStorage.getItem(AUTH_TOKEN_KEY);
        }
        return null;
    }

    /**
     * Get refresh token from localStorage
     */
    getRefreshToken(): string | null {
        if (typeof window !== "undefined") {
            return localStorage.getItem(REFRESH_TOKEN_KEY);
        }
        return null;
    }

    /**
     * Clear tokens from localStorage
     */
    clearTokens(): void {
        if (typeof window !== "undefined") {
            localStorage.removeItem(AUTH_TOKEN_KEY);
            localStorage.removeItem(REFRESH_TOKEN_KEY);
            localStorage.removeItem(USER_EMAIL_KEY);
        }
    }

    /**
     * Store user email in localStorage
     */
    setUserEmail(email: string): void {
        if (typeof window !== "undefined") {
            localStorage.setItem(USER_EMAIL_KEY, email);
        }
    }

    /**
     * Get user email from localStorage
     */
    getUserEmail(): string | null {
        if (typeof window !== "undefined") {
            return localStorage.getItem(USER_EMAIL_KEY);
        }
        return null;
    }

    /**
     * Check if user is authenticated
     */
    isAuthenticated(): boolean {
        return !!this.getAccessToken();
    }
}

export const authService = new AuthService();
