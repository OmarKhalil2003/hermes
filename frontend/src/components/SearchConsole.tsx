"use client";

import React, { useState, FormEvent } from "react";
import { apiFetch } from "@/lib/api";
import { DocumentInfo } from "./FilesTable";

interface SearchResult {
  chunk_id: string;
  document_id: string;
  filename: string;
  content: string;
  score: number;
}

interface SearchConsoleProps {
  files: DocumentInfo[];
}

export default function SearchConsole({ files }: SearchConsoleProps) {
  const [query, setQuery] = useState("");
  const [targetDocId, setTargetDocId] = useState("");
  const [limit, setLimit] = useState(5);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setErrorMessage("");
    setResults(null);

    try {
      const params = new URLSearchParams();
      params.append("query", query);
      params.append("limit", limit.toString());

      if (targetDocId) {
        params.append("document_id", targetDocId);
      }
      if (startDate) {
        params.append("start_date", new Date(startDate).toISOString());
      }
      if (endDate) {
        params.append("end_date", new Date(endDate).toISOString());
      }

      const response = await apiFetch(`/api/v1/documents/search?${params.toString()}`);
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Search operation failed.");
      }

      const data: SearchResult[] = await response.json();
      setResults(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "An unexpected error occurred during search.";
      setErrorMessage(message);
    } finally {
      setIsSearching(false);
    }
  };

  const getScoreBadge = (score: number) => {
    // Cross encoder score ranges from highly negative to positive, but if it has been normalized
    // let's show relevance based on score scale
    let percentage = 0;
    if (score > 1) {
      percentage = 100;
    } else if (score < 0) {
      percentage = Math.max(0, Math.round((score + 10) * 10)); // approximate scale
    } else {
      percentage = Math.round(score * 100);
    }

    let badgeClass = "bg-rose-500/10 text-rose-400 border border-rose-500/20";
    if (percentage >= 80) {
      badgeClass = "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-[0_0_12px_rgba(16,185,129,0.1)]";
    } else if (percentage >= 50) {
      badgeClass = "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20";
    }

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold font-mono ${badgeClass}`}>
        {percentage}% Match
      </span>
    );
  };

  const highlightMatch = (text: string, searchQuery: string) => {
    if (!searchQuery.trim()) return <span>{text}</span>;
    
    // Split into words, cleaning punctuation, length > 2
    const words = searchQuery
      .toLowerCase()
      .split(/[^a-zA-Z0-9]+/)
      .filter((w) => w.length > 2);
      
    if (words.length === 0) return <span>{text}</span>;
    
    const escapedWords = words.map((w) => w.replace(/[-\/\\^$*+?.()|[\]{}]/g, "\\$&"));
    const regex = new RegExp(`\\b(${escapedWords.join("|")})\\b`, "gi");
    const parts = text.split(regex);
    
    return (
      <>
        {parts.map((part, idx) =>
          regex.test(part) ? (
            <mark
              key={idx}
              className="bg-indigo-500/25 text-indigo-300 font-semibold px-0.5 rounded border border-indigo-500/30"
            >
              {part}
            </mark>
          ) : (
            <span key={idx}>{part}</span>
          )
        )}
      </>
    );
  };

  return (
    <div className="w-full space-y-8">
      {/* Console form panel */}
      <form onSubmit={handleSearch} className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6 backdrop-blur-sm shadow-xl">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <svg className="h-5 w-5 text-indigo-400 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          Semantic RAG Console
        </h3>

        {/* Input Bar */}
        <div className="flex flex-col md:flex-row gap-3 mb-6">
          <div className="flex-1 relative">
            <input
              type="text"
              placeholder="Ask Hermes: 'What are the main findings regarding artificial neural network scales?'"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full h-12 pl-4 pr-4 bg-zinc-950/80 hover:bg-zinc-950 focus:bg-zinc-950 text-white placeholder-zinc-500 rounded-xl border border-zinc-850 hover:border-zinc-700 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-medium transition-all text-sm"
              disabled={isSearching}
            />
          </div>
          <button
            type="submit"
            disabled={isSearching || !query.trim()}
            className={`h-12 px-6 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all shadow-lg ${
              isSearching || !query.trim()
                ? "bg-zinc-800 text-zinc-500 border border-zinc-750 cursor-not-allowed"
                : "bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer hover:shadow-indigo-500/10"
            }`}
          >
            {isSearching ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Reranking...
              </>
            ) : (
              <>
                Query Hermes
              </>
            )}
          </button>
        </div>

        {/* Filters grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          {/* Target Document */}
          <div className="flex flex-col gap-1.5">
            <label className="text-zinc-400 font-semibold uppercase tracking-wider text-[10px]">Filter by Document</label>
            <select
              value={targetDocId}
              onChange={(e) => setTargetDocId(e.target.value)}
              className="h-9 px-3 bg-zinc-950 rounded-lg border border-zinc-800 text-zinc-300 focus:border-indigo-500 focus:outline-none transition-colors"
            >
              <option value="">All Uploaded Files</option>
              {files
                .filter((f) => f.status === "processed")
                .map((file) => (
                  <option key={file.id} value={file.id}>
                    {file.filename}
                  </option>
                ))}
            </select>
          </div>

          {/* Search result count limit */}
          <div className="flex flex-col gap-1.5">
            <label className="text-zinc-400 font-semibold uppercase tracking-wider text-[10px]">Top-K Limit</label>
            <select
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value))}
              className="h-9 px-3 bg-zinc-950 rounded-lg border border-zinc-800 text-zinc-300 focus:border-indigo-500 focus:outline-none transition-colors"
            >
              <option value={3}>Retrieve 3 Chunks</option>
              <option value={5}>Retrieve 5 Chunks</option>
              <option value={10}>Retrieve 10 Chunks</option>
              <option value={20}>Retrieve 20 Chunks</option>
            </select>
          </div>

          {/* Start Date */}
          <div className="flex flex-col gap-1.5">
            <label className="text-zinc-400 font-semibold uppercase tracking-wider text-[10px]">Ingested From</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="h-9 px-3 bg-zinc-950 rounded-lg border border-zinc-800 text-zinc-300 focus:border-indigo-500 focus:outline-none transition-colors"
            />
          </div>

          {/* End Date */}
          <div className="flex flex-col gap-1.5">
            <label className="text-zinc-400 font-semibold uppercase tracking-wider text-[10px]">Ingested Until</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="h-9 px-3 bg-zinc-950 rounded-lg border border-zinc-800 text-zinc-300 focus:border-indigo-500 focus:outline-none transition-colors"
            />
          </div>
        </div>
      </form>

      {/* Error alert */}
      {errorMessage && (
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-400 flex items-center gap-3">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Results grid */}
      <div>
        {isSearching && (
          <div className="grid grid-cols-1 gap-4">
            {[...Array(limit)].map((_, idx) => (
              <div key={idx} className="rounded-2xl border border-zinc-900 bg-zinc-900/10 p-6 space-y-4 animate-pulse">
                <div className="flex items-center justify-between">
                  <div className="h-4 w-32 bg-zinc-800 rounded"></div>
                  <div className="h-5 w-20 bg-zinc-800 rounded-full"></div>
                </div>
                <div className="space-y-2">
                  <div className="h-3 w-full bg-zinc-800 rounded"></div>
                  <div className="h-3 w-5/6 bg-zinc-800 rounded"></div>
                  <div className="h-3 w-4/5 bg-zinc-800 rounded"></div>
                </div>
              </div>
            ))}
          </div>
        )}

        {!isSearching && results !== null && (
          <div className="space-y-4">
            <h4 className="text-sm font-semibold uppercase tracking-wider text-zinc-500 mb-2">
              Found {results.length} relevant context fragments
            </h4>

            {results.length === 0 ? (
              <div className="text-center py-12 rounded-2xl border border-zinc-900 bg-zinc-900/5 text-zinc-500">
                No matching passages found. Try broadening your query keywords or uploading more files.
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {results.map((result) => (
                  <div
                    key={result.chunk_id}
                    className="rounded-2xl border border-zinc-800 bg-zinc-900/10 p-6 hover:border-zinc-700 hover:bg-zinc-900/20 transition-all shadow-md group relative overflow-hidden"
                  >
                    {/* Left glow accent */}
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-indigo-500/20 group-hover:bg-indigo-500 transition-colors"></div>

                    {/* Metadata Header */}
                    <div className="flex items-center justify-between gap-4 mb-3 text-xs">
                      <div className="flex items-center gap-2 text-zinc-400">
                        <svg className="h-3.5 w-3.5 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <span className="font-medium hover:text-white transition-colors truncate max-w-xs" title={result.filename}>
                          {result.filename}
                        </span>
                      </div>
                      {getScoreBadge(result.score)}
                    </div>

                    {/* Snippet text */}
                    <p className="text-zinc-300 text-sm leading-relaxed font-normal whitespace-pre-wrap">
                      {highlightMatch(result.content, query)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
