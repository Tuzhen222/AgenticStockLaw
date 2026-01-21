"use client";

import {
    createContext,
    useContext,
    useState,
    useEffect,
    useCallback,
    type ReactNode,
} from "react";
import { authService, type UserResponse } from "@/services/auth.service";
import type { SettingsData } from "@/types";

interface User {
    id?: number;
    email: string;
    username?: string;
    name?: string;
    full_name?: string;
    role?: {
        id: number;
        name: string;
    };
}

interface AuthContextType {
    isAuthenticated: boolean;
    isLoading: boolean;
    user: User | null;
    login: (email: string, password: string) => Promise<void>;
    logout: () => void;
    updateUser: (data: SettingsData) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
    children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [user, setUser] = useState<User | null>(null);

    // Check authentication status on mount
    useEffect(() => {
        const checkAuth = async () => {
            if (authService.isAuthenticated()) {
                try {
                    // Try to get current user with existing access token
                    const userData = await authService.getCurrentUser();
                    setUser({
                        id: userData.id,
                        email: userData.email,
                        username: userData.username,
                        name: userData.full_name || userData.username,
                        full_name: userData.full_name ?? undefined,
                        role: userData.role,
                    });
                    setIsAuthenticated(true);
                } catch {
                    // Access token invalid/expired, try to refresh
                    try {
                        await authService.refreshTokens();
                        // Retry getting user data with new access token
                        const userData = await authService.getCurrentUser();
                        setUser({
                            id: userData.id,
                            email: userData.email,
                            username: userData.username,
                            name: userData.full_name || userData.username,
                            full_name: userData.full_name ?? undefined,
                            role: userData.role,
                        });
                        setIsAuthenticated(true);
                    } catch {
                        // Both access and refresh tokens are invalid - user needs to login again
                        authService.clearTokens();
                    }
                }
            }
            setIsLoading(false);
        };

        checkAuth();
    }, []);

    const login = useCallback(async (email: string, password: string) => {
        const tokens = await authService.login(email, password);

        // Fetch user data after login
        const userData = await authService.getCurrentUser();
        setUser({
            id: userData.id,
            email: userData.email,
            username: userData.username,
            name: userData.full_name || userData.username,
            full_name: userData.full_name ?? undefined,
            role: userData.role,
        });
        setIsAuthenticated(true);
    }, []);

    const logout = useCallback(() => {
        authService.logout();
        setIsAuthenticated(false);
        setUser(null);
    }, []);

    const updateUser = useCallback((data: SettingsData) => {
        setUser((prev) => (prev ? { ...prev, ...data } : null));
    }, []);

    return (
        <AuthContext.Provider
            value={{ isAuthenticated, isLoading, user, login, logout, updateUser }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}
