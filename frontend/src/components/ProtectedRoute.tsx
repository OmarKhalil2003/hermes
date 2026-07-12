"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-100">
        <div className="flex flex-col items-center gap-4 text-center">
          {/* Custom premium glowing spinner */}
          <div className="relative flex h-16 w-16 items-center justify-center">
            <div className="absolute h-full w-full rounded-full border-4 border-solid border-indigo-500/20"></div>
            <div className="absolute h-full w-full animate-spin rounded-full border-4 border-solid border-indigo-500 border-t-transparent shadow-[0_0_15px_rgba(99,102,241,0.5)]"></div>
          </div>
          <p className="mt-4 text-sm font-medium tracking-wide text-indigo-400 animate-pulse">
            Verifying secure credentials...
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Prevents flashing dashboard elements before redirect finishes
  }

  return <>{children}</>;
}
