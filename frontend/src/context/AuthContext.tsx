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
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

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
    setUser(null);
    return null;
  };

  // Run on mount to check for existing credentials
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem("access_token");
      if (token) {
        await fetchUserProfile();
      }
      setIsLoading(false);
    };
    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      params.append("username", email);
      params.append("password", password);

      const response = await apiFetch("/api/v1/auth/login", {
        method: "POST",
        useFormUrlEncoded: true,
        body: params.toString(),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Authentication failed. Check credentials.");
      }

      const tokenData = await response.json();
      localStorage.setItem("access_token", tokenData.access_token);
      localStorage.setItem("refresh_token", tokenData.refresh_token);

      const profile = await fetchUserProfile();
      if (!profile) {
        throw new Error("Unable to retrieve user profile after login.");
      }
    } catch (error) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      setUser(null);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string, isSuperuser: boolean = false) => {
    setIsLoading(true);
    try {
      const response = await apiFetch("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
          is_superuser: isSuperuser,
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Account registration failed.");
      }

      // Auto login after registration
      await login(email, password);
    } catch (error) {
      setIsLoading(false);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
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
