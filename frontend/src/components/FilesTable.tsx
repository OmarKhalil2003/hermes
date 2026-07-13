"use client";

import React, { useState } from "react";
import { apiFetch } from "@/lib/api";

export interface DocumentInfo {
  id: string;
  filename: string;
  mime_type: string;
  file_size: number;
  status: "pending" | "processing" | "processed" | "failed" | "duplicate";
  created_at: string | null;
  chunks_count: number;
}

interface FilesTableProps {
  files: DocumentInfo[];
  onDeleteSuccess: () => void;
}

export default function FilesTable({ files, onDeleteSuccess }: FilesTableProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const formatSize = (bytes: number): string => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return "N/A";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  const handleDelete = async (id: string, filename: string) => {
    if (!confirm(`Are you sure you want to permanently delete "${filename}" and all its vector chunks?`)) {
      return;
    }

    setDeletingId(id);
    try {
      const response = await apiFetch(`/api/v1/documents/${id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Delete operation failed.");
      }

      onDeleteSuccess();
    } catch (error) {
      console.error("Deletion failed:", error);
      alert(error instanceof Error ? error.message : "Deletion failed");
    } finally {
      setDeletingId(null);
    }
  };

  const getFileIcon = (filename: string) => {
    const ext = filename.substring(filename.lastIndexOf(".")).toLowerCase();
    if (ext === ".pdf") {
      return (
        <span className="p-2 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded-lg">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        </span>
      );
    } else if (ext === ".csv") {
      return (
        <span className="p-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </span>
      );
    } else if (ext === ".doc" || ext === ".docx") {
      return (
        <span className="p-2 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-lg">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </span>
      );
    } else {
      return (
        <span className="p-2 bg-zinc-500/10 text-zinc-400 border border-zinc-500/20 rounded-lg">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </span>
      );
    }
  };

  const getStatusPill = (status: DocumentInfo["status"]) => {
    switch (status) {
      case "pending":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 animate-pulse">
            <span className="h-1.5 w-1.5 rounded-full bg-yellow-400"></span>
            Queued
          </span>
        );
      case "processing":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-ping"></span>
            Parsing
          </span>
        );
      case "processed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
            Processed
          </span>
        );
      case "duplicate":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400"></span>
            Duplicate
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-400"></span>
            Failed
          </span>
        );
    }
  };

  if (files.length === 0) {
    return (
      <div className="text-center py-12 rounded-2xl border border-zinc-800 bg-zinc-900/10 p-8">
        <svg className="mx-auto h-12 w-12 text-zinc-600 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
        </svg>
        <p className="text-sm font-semibold text-zinc-300">No documents found</p>
        <p className="text-xs text-zinc-500 mt-1">Upload a research file to build your knowledge collection.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-zinc-800 bg-zinc-900/10 backdrop-blur-sm shadow-xl">
      <table className="min-w-full divide-y divide-zinc-800 text-left text-sm text-zinc-300">
        <thead className="bg-zinc-900/30 text-xs font-semibold uppercase tracking-wider text-zinc-400">
          <tr>
            <th className="px-6 py-4">Filename</th>
            <th className="px-6 py-4">Status</th>
            <th className="px-6 py-4">Size</th>
            <th className="px-6 py-4">Chunks</th>
            <th className="px-6 py-4">Parsing Date</th>
            <th className="px-6 py-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800/50 bg-transparent">
          {files.map((file) => (
            <tr key={file.id} className="hover:bg-zinc-900/30 transition-colors">
              <td className="whitespace-nowrap px-6 py-4 font-medium text-white">
                <div className="flex items-center gap-3">
                  {getFileIcon(file.filename)}
                  <span className="truncate max-w-[200px] sm:max-w-xs md:max-w-md block" title={file.filename}>
                    {file.filename}
                  </span>
                </div>
              </td>
              <td className="whitespace-nowrap px-6 py-4">
                {getStatusPill(file.status)}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-xs font-mono">
                {formatSize(file.file_size)}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-xs font-mono text-zinc-400">
                {file.status === "processed" ? (
                  <span className="text-indigo-400 font-semibold">{file.chunks_count}</span>
                ) : (
                  <span className="text-zinc-600">—</span>
                )}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-xs text-zinc-400">
                {formatDate(file.created_at)}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-right">
                <button
                  disabled={deletingId === file.id}
                  onClick={() => handleDelete(file.id, file.filename)}
                  className={`inline-flex items-center justify-center p-1.5 rounded-lg border border-zinc-800 bg-zinc-900/50 hover:bg-rose-500/10 hover:border-rose-500/30 text-zinc-400 hover:text-rose-400 transition-colors ${
                    deletingId === file.id ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
                  }`}
                  title="Delete document and index chunks"
                >
                  {deletingId === file.id ? (
                    <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  ) : (
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  )}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
