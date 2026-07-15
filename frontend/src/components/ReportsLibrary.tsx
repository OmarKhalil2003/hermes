"use client";

import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";

interface ReportFile {
  filename: string;
  size_bytes: number;
  created_at: string;
}

export default function ReportsLibrary() {
  const [reports, setReports] = useState<ReportFile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  const fetchReports = async () => {
    setIsLoading(true);
    setErrorMsg("");
    try {
      const response = await apiFetch("/api/v1/documents/reports");
      if (response.ok) {
        const data = await response.json();
        setReports(data);
      } else {
        throw new Error("Failed to load reports list.");
      }
    } catch (err: unknown) {
      const errMsg =
        err instanceof Error ? err.message : "Could not retrieve generated reports.";
      setErrorMsg(errMsg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    Promise.resolve().then(() => {
      fetchReports();
    });
  }, []);

  const downloadReport = async (filename: string) => {
    try {
      const response = await apiFetch(`/api/v1/documents/reports/download/${filename}`);
      if (!response.ok) {
        throw new Error("Download failed.");
      }
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(link);
    } catch (err) {
      console.error("Failed to download file:", err);
      alert("Failed to download file. Please check server logs.");
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="w-full space-y-6">
      {/* Header and Refresh triggers */}
      <div className="flex items-center justify-between border-b border-zinc-900 pb-4">
        <div>
          <h3 className="text-md font-bold text-white">Generated Reports Archive</h3>
          <p className="text-xs text-zinc-500">Download compiled PDF analyses and PowerPoint pitch slide decks.</p>
        </div>
        <button
          onClick={fetchReports}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-zinc-800 hover:border-zinc-700 transition-all cursor-pointer"
        >
          <svg
            className={`h-3.5 w-3.5 text-zinc-400 ${isLoading ? "animate-spin" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M9 11l3-3m0 0l3 3m-3-3v12" />
          </svg>
          Refresh Archive
        </button>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl border border-rose-500/20 bg-rose-500/10 text-rose-400 text-xs">
          {errorMsg}
        </div>
      )}

      {isLoading ? (
        <div className="flex h-32 items-center justify-center rounded-2xl border border-zinc-900 bg-zinc-900/5 text-zinc-400 text-xs">
          <svg className="animate-spin h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Loading reports archive...
        </div>
      ) : reports.length === 0 ? (
        <div className="text-center py-16 rounded-2xl border border-zinc-900 bg-zinc-900/5 text-zinc-500 text-xs">
          No reports found. Ask the Multi-Agent Researcher to generate a report, and it will appear here.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {reports.map((report) => {
            const isPdf = report.filename.toLowerCase().endsWith(".pdf");
            return (
              <div
                key={report.filename}
                className="rounded-2xl border border-zinc-800 bg-zinc-900/10 p-5 hover:border-zinc-700 hover:bg-zinc-900/20 transition-all flex items-center justify-between group shadow-sm"
              >
                {/* File Details */}
                <div className="flex items-center gap-4">
                  <div
                    className={`h-10 w-10 rounded-xl flex items-center justify-center border shadow-sm ${
                      isPdf
                        ? "bg-rose-500/10 border-rose-500/20 text-rose-400"
                        : "bg-amber-500/10 border-amber-500/20 text-amber-400"
                    }`}
                  >
                    {isPdf ? (
                      <span className="text-[10px] font-bold font-mono">PDF</span>
                    ) : (
                      <span className="text-[10px] font-bold font-mono">PPT</span>
                    )}
                  </div>
                  <div className="flex flex-col gap-0.5 max-w-[200px] sm:max-w-[300px]">
                    <span className="text-sm font-semibold text-white truncate group-hover:text-indigo-400 transition-colors" title={report.filename}>
                      {report.filename}
                    </span>
                    <span className="text-[10px] text-zinc-500 font-mono" suppressHydrationWarning>
                      {formatBytes(report.size_bytes)}  |  {new Date(report.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>

                {/* Download trigger */}
                <button
                  onClick={() => downloadReport(report.filename)}
                  className="p-2.5 rounded-xl border border-zinc-800 bg-zinc-950 hover:bg-zinc-900 text-zinc-300 hover:text-white transition-all cursor-pointer shadow-sm hover:border-zinc-750"
                  title="Download File"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
