"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { apiFetch } from "@/lib/api";

export interface UserProfile {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, isSuperuser?: boolean) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const defaultProfile: UserProfile = {
    id: "00000000-0000-0000-0000-000000000000",
    email: "admin@hermes.ai",
    is_active: true,
    is_superuser: true,
    created_at: new Date().toISOString(),
  };

  const [user, setUser] = useState<UserProfile | null>(defaultProfile);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Fetch current user details from `/api/v1/protected`
  const fetchUserProfile = async (): Promise<UserProfile | null> => {
    try {
      const response = await apiFetch("/api/v1/protected");
      if (response.ok) {
        const data: UserProfile = await response.json();
        setUser(data);
        return data;
      }
    } catch (error) {
      console.error("Failed to load user profile:", error);
    }
    return null;
  };

  // Run on mount to sync with backend user profile if possible
  useEffect(() => {
    fetchUserProfile();
  }, []);

  const login = async (_email: string, _password: string) => {
    // No-op for authentication bypass
  };

  const register = async (
    _email: string,
    _password: string,
    _isSuperuser: boolean = false
  ) => {
    // No-op for authentication bypass
  };

  const logout = () => {
    // No-op for authentication bypass
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: true,
        isLoading,
        login,
        register,
        logout,
        refreshProfile: async () => {
          await fetchUserProfile();
        },
      }}
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
