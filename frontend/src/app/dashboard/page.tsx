"use client";

import React from "react";
import { useAuth } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";

export default function DashboardPage() {
  const { user, logout } = useAuth();

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans flex flex-col">
        {/* Navigation Bar */}
        <header className="border-b border-zinc-800 bg-zinc-900/50 backdrop-blur-md sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 items-center justify-center flex rounded-lg bg-indigo-600/20 border border-indigo-500/30">
                <svg className="h-5 w-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <span className="font-bold tracking-tight text-white">Hermes AI Dashboard</span>
            </div>

            <div className="flex items-center gap-4">
              <div className="hidden sm:flex flex-col items-end text-xs">
                <span className="font-medium text-zinc-300">{user?.email}</span>
                <span className="text-zinc-500 font-mono">
                  Role: {user?.is_superuser ? "Administrator" : "Research User"}
                </span>
              </div>
              <button
                onClick={logout}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 transition-colors focus:outline-none"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                Logout
              </button>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold tracking-tight text-white">Document Intelligence Workspace</h1>
            <p className="text-sm text-zinc-400 mt-1">Manage and query your repository files using semantic RAG pipelines.</p>
          </div>

          {/* Feature Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Session Info Card */}
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6 backdrop-blur-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 h-24 w-24 bg-indigo-500/5 rounded-full blur-xl pointer-events-none"></div>
              <h3 className="text-lg font-semibold text-white mb-4">Secure Profile Session</h3>
              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-zinc-500 block text-xs uppercase tracking-wider">Account ID</span>
                  <span className="font-mono text-zinc-300 break-all">{user?.id}</span>
                </div>
                <div>
                  <span className="text-zinc-500 block text-xs uppercase tracking-wider">Email Address</span>
                  <span className="text-zinc-300 font-medium">{user?.email}</span>
                </div>
                <div>
                  <span className="text-zinc-500 block text-xs uppercase tracking-wider">Account Created At</span>
                  <span className="text-zinc-300 font-medium">{user ? new Date(user.created_at).toLocaleString() : "Loading..."}</span>
                </div>
              </div>
            </div>

            {/* Document ingestion card placeholder */}
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6 backdrop-blur-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 h-24 w-24 bg-violet-500/5 rounded-full blur-xl pointer-events-none"></div>
              <h3 className="text-lg font-semibold text-white mb-4">Document Repository</h3>
              <p className="text-zinc-400 text-sm mb-4">Upload research papers, manuals, or database dumps to construct vector indexes.</p>
              <button className="px-4 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors shadow-lg shadow-indigo-500/20 cursor-not-allowed opacity-50">
                Upload Document (RAG)
              </button>
            </div>

            {/* Ingestion & Training jobs card placeholder */}
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6 backdrop-blur-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 h-24 w-24 bg-amber-500/5 rounded-full blur-xl pointer-events-none"></div>
              <h3 className="text-lg font-semibold text-white mb-4">AI Model Status</h3>
              <div className="flex items-center gap-2 mb-4">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span className="text-emerald-400 text-xs font-semibold font-mono">Hermes-V1 Online</span>
              </div>
              <p className="text-zinc-400 text-sm mb-4">Inspect ongoing embedding model training runs, weights, or fine-tuning evaluations.</p>
              <button className="px-4 py-2 text-xs font-semibold bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 rounded-lg transition-colors cursor-not-allowed opacity-50">
                Manage Jobs
              </button>
            </div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
