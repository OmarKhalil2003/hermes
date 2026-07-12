"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  // If already authenticated, redirect straight to dashboard
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-100">
        <div className="relative flex h-12 w-12 items-center justify-center">
          <div className="absolute h-full w-full rounded-full border-4 border-solid border-indigo-500/20"></div>
          <div className="absolute h-full w-full animate-spin rounded-full border-4 border-solid border-indigo-500 border-t-transparent"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-between overflow-hidden bg-zinc-950 px-4 font-sans text-zinc-100">
      {/* Background glowing gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-[600px] h-[600px] rounded-full bg-indigo-500/5 blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[600px] h-[600px] rounded-full bg-violet-500/5 blur-[120px] pointer-events-none"></div>

      {/* Header navbar */}
      <header className="w-full max-w-7xl mx-auto h-20 flex items-center justify-between z-10 shrink-0">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 items-center justify-center flex rounded-lg bg-indigo-600/20 border border-indigo-500/30">
            <svg className="h-5 w-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <span className="font-bold tracking-tight text-white">Hermes AI</span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/login" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">
            Sign In
          </Link>
          <Link href="/register" className="text-sm font-semibold text-white bg-zinc-800 hover:bg-zinc-700 px-4 py-2 border border-zinc-700 rounded-lg transition-colors">
            Register
          </Link>
        </div>
      </header>

      {/* Main hero section */}
      <main className="flex-1 flex flex-col justify-center items-center text-center max-w-4xl mx-auto z-10 py-16">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-xs font-semibold text-indigo-400 mb-6">
          <span className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse"></span>
          Now Live: Interactive RAG Workspace
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight mb-6">
          Enterprise Document <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-violet-400 to-fuchsia-400">
            Intelligence Platform
          </span>
        </h1>

        <p className="max-w-2xl text-lg text-zinc-400 leading-relaxed mb-10">
          Unlock insights from your corporate manuals, PDFs, and databases. Empower your workflow with production-grade Retrieval-Augmented Generation (RAG) models.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto px-4 justify-center">
          <Link
            href="/register"
            className="flex h-12 items-center justify-center px-8 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 transition-colors shadow-[0_4px_20px_rgba(99,102,241,0.3)]"
          >
            Get Started Free
          </Link>
          <Link
            href="/login"
            className="flex h-12 items-center justify-center px-8 rounded-xl text-sm font-semibold text-zinc-300 bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 transition-colors"
          >
            Sign In to Account
          </Link>
        </div>
      </main>

      {/* Footer info */}
      <footer className="w-full max-w-7xl mx-auto h-16 flex items-center justify-center z-10 shrink-0 border-t border-zinc-900/60 text-xs text-zinc-600">
        &copy; {new Date().getFullYear()} Hermes AI Platform. All rights reserved.
      </footer>
    </div>
  );
}
