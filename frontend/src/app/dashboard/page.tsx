"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import UploadZone from "@/components/UploadZone";
import FilesTable, { DocumentInfo } from "@/components/FilesTable";
import SearchConsole from "@/components/SearchConsole";
import AgentChatPanel from "@/components/AgentChatPanel";
import ReportsLibrary from "@/components/ReportsLibrary";
import DeploymentConsole from "@/components/DeploymentConsole";
import { apiFetch } from "@/lib/api";

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const [files, setFiles] = useState<DocumentInfo[]>([]);
  const [isLoadingFiles, setIsLoadingFiles] = useState(true);
  const [activeTab, setActiveTab] = useState<"files" | "search" | "chat" | "reports" | "deploy">("files");

  const fetchDocuments = async () => {
    try {
      const response = await apiFetch("/api/v1/documents");
      if (response.ok) {
        const data: DocumentInfo[] = await response.json();
        setFiles(data);
      }
    } catch (error) {
      console.error("Failed to load documents:", error);
    } finally {
      setIsLoadingFiles(false);
    }
  };

  // Initial fetch on mount
  useEffect(() => {
    Promise.resolve().then(() => {
      fetchDocuments();
    });
  }, []);

  // Poll status updates every 4 seconds if there are pending or processing files
  useEffect(() => {
    const hasActiveJobs = files.some(
      (file) => file.status === "pending" || file.status === "processing"
    );

    if (hasActiveJobs) {
      const interval = setInterval(() => {
        fetchDocuments();
      }, 4000);
      return () => clearInterval(interval);
    }
  }, [files]);

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans flex flex-col">
        {/* Navigation Bar */}
        <header className="border-b border-zinc-900 bg-zinc-900/40 backdrop-blur-md sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 items-center justify-center flex rounded-lg bg-indigo-600/20 border border-indigo-500/30 shadow-[0_0_15px_rgba(99,102,241,0.15)]">
                <svg className="h-5 w-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <span className="font-bold tracking-tight text-white">Hermes AI Workspace</span>
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
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-zinc-800 hover:border-zinc-700 transition-all focus:outline-none cursor-pointer"
              >
                <svg className="h-4 w-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                Logout
              </button>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
          {/* Header text */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight text-white bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
                Document Intelligence Workspace
              </h1>
              <p className="text-sm text-zinc-400 mt-1">Manage and query your repository files using semantic hybrid RAG pipelines.</p>
            </div>
            
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-emerald-400 text-xs font-semibold font-mono">Hermes-V1 Ingestion Engine Online</span>
            </div>
          </div>

          {/* Tab Navigation Menu */}
          <div className="flex border-b border-zinc-900 pb-px gap-6">
            <button
              onClick={() => setActiveTab("files")}
              className={`pb-3 text-xs uppercase tracking-wider font-bold border-b-2 transition-all cursor-pointer ${
                activeTab === "files"
                  ? "text-indigo-400 border-indigo-500"
                  : "text-zinc-500 border-transparent hover:text-zinc-300"
              }`}
            >
              Knowledge Library
            </button>
            <button
              onClick={() => setActiveTab("search")}
              className={`pb-3 text-xs uppercase tracking-wider font-bold border-b-2 transition-all cursor-pointer ${
                activeTab === "search"
                  ? "text-indigo-400 border-indigo-500"
                  : "text-zinc-500 border-transparent hover:text-zinc-300"
              }`}
            >
              Semantic Search
            </button>
            <button
              onClick={() => setActiveTab("chat")}
              className={`pb-3 text-xs uppercase tracking-wider font-bold border-b-2 transition-all cursor-pointer ${
                activeTab === "chat"
                  ? "text-indigo-400 border-indigo-500"
                  : "text-zinc-500 border-transparent hover:text-zinc-300"
              }`}
            >
              Agent Workspace
            </button>
            <button
              onClick={() => setActiveTab("reports")}
              className={`pb-3 text-xs uppercase tracking-wider font-bold border-b-2 transition-all cursor-pointer ${
                activeTab === "reports"
                  ? "text-indigo-400 border-indigo-500"
                  : "text-zinc-500 border-transparent hover:text-zinc-300"
              }`}
            >
              Generated Reports
            </button>
            <button
              onClick={() => setActiveTab("deploy")}
              className={`pb-3 text-xs uppercase tracking-wider font-bold border-b-2 transition-all cursor-pointer ${
                activeTab === "deploy"
                  ? "text-indigo-400 border-indigo-500"
                  : "text-zinc-500 border-transparent hover:text-zinc-300"
              }`}
            >
              Model Management
            </button>
          </div>

          {/* Dynamic Render Tab Views */}
          <div className="pt-2">
            {activeTab === "files" && (
              <div className="space-y-12">
                {/* Upload and Workspace Summary Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
                  {/* Left side: Upload card */}
                  <div className="lg:col-span-2 space-y-4">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-500">Upload Research Files</h3>
                    <UploadZone onUploadSuccess={fetchDocuments} />
                  </div>

                  {/* Right side: Session Profile Stats */}
                  <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6 backdrop-blur-sm relative overflow-hidden space-y-4">
                    <div className="absolute top-0 right-0 h-24 w-24 bg-indigo-500/5 rounded-full blur-xl pointer-events-none"></div>
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-500">Secure Session Details</h3>
                    <div className="space-y-4 text-xs font-mono">
                      <div>
                        <span className="text-zinc-500 block uppercase tracking-wider text-[10px]">Account ID</span>
                        <span className="text-zinc-300 break-all">{user?.id}</span>
                      </div>
                      <div>
                        <span className="text-zinc-500 block uppercase tracking-wider text-[10px]">Email Address</span>
                        <span className="text-zinc-300">{user?.email}</span>
                      </div>
                      <div>
                        <span className="text-zinc-500 block uppercase tracking-wider text-[10px]">Account Created At</span>
                        <span className="text-zinc-300" suppressHydrationWarning>
                          {user ? new Date(user.created_at).toLocaleString() : "Loading..."}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Files Table Section */}
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-500 flex items-center justify-between">
                    <span>Knowledge Collection</span>
                    <span className="text-xs text-zinc-400 font-normal font-sans">
                      {files.length} {files.length === 1 ? "document" : "documents"} indexed
                    </span>
                  </h3>
                  
                  {isLoadingFiles ? (
                    <div className="flex h-32 items-center justify-center rounded-2xl border border-zinc-900 bg-zinc-900/5 text-zinc-400">
                      <svg className="animate-spin h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Loading files...
                    </div>
                  ) : (
                    <FilesTable files={files} onDeleteSuccess={fetchDocuments} />
                  )}
                </div>
              </div>
            )}

            {activeTab === "search" && (
              <SearchConsole files={files} />
            )}

            {activeTab === "chat" && (
              <AgentChatPanel />
            )}

            {activeTab === "reports" && (
              <ReportsLibrary />
            )}

            {activeTab === "deploy" && (
              <DeploymentConsole />
            )}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
