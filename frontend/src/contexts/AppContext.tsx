"use client";

import {
    createContext,
    useContext,
    useState,
    useCallback,
    type ReactNode,
} from "react";
import type { ViewType } from "@/types";

interface AppContextType {
    // Sidebar state
    isSidebarCollapsed: boolean;
    toggleSidebar: () => void;
    setSidebarCollapsed: (collapsed: boolean) => void;

    // View state
    currentView: ViewType;
    setCurrentView: (view: ViewType) => void;

    // Modal states
    isSettingsOpen: boolean;
    openSettings: () => void;
    closeSettings: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

interface AppProviderProps {
    children: ReactNode;
}

export function AppProvider({ children }: AppProviderProps) {
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
    const [currentView, setCurrentView] = useState<ViewType>("chat");
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

    const toggleSidebar = useCallback(() => {
        setIsSidebarCollapsed((prev) => !prev);
    }, []);

    const setSidebarCollapsed = useCallback((collapsed: boolean) => {
        setIsSidebarCollapsed(collapsed);
    }, []);

    const openSettings = useCallback(() => {
        setIsSettingsOpen(true);
    }, []);

    const closeSettings = useCallback(() => {
        setIsSettingsOpen(false);
    }, []);

    return (
        <AppContext.Provider
            value={{
                isSidebarCollapsed,
                toggleSidebar,
                setSidebarCollapsed,
                currentView,
                setCurrentView,
                isSettingsOpen,
                openSettings,
                closeSettings,
            }}
        >
            {children}
        </AppContext.Provider>
    );
}

export function useApp() {
    const context = useContext(AppContext);
    if (context === undefined) {
        throw new Error("useApp must be used within an AppProvider");
    }
    return context;
}
