"use client";

import React, { useState, useRef, DragEvent, ChangeEvent } from "react";
import { apiFetch } from "@/lib/api";

interface UploadZoneProps {
  onUploadSuccess: () => void;
}

const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".doc", ".pptx", ".ppt", ".csv", ".txt"];
const MAX_FILE_SIZE_MB = 20;

export default function UploadZone({ onUploadSuccess }: UploadZoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [fileName, setFileName] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true);
    } else if (e.type === "dragleave") {
      setIsDragActive(false);
    }
  };

  const validateFile = (file: File): boolean => {
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setErrorMessage(`Unsupported format. Allowed formats: ${ALLOWED_EXTENSIONS.join(", ")}`);
      setUploadStatus("error");
      return false;
    }
    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      setErrorMessage(`File exceeds the maximum limit of ${MAX_FILE_SIZE_MB}MB.`);
      setUploadStatus("error");
      return false;
    }
    return true;
  };

  const uploadFile = async (file: File) => {
    setUploadStatus("uploading");
    setFileName(file.name);
    setErrorMessage("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await apiFetch("/api/v1/documents/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Upload failed. Please try again.");
      }

      setUploadStatus("success");
      onUploadSuccess();

      // Reset to idle state after 3 seconds
      setTimeout(() => {
        setUploadStatus("idle");
        setFileName("");
      }, 3000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "An unexpected error occurred";
      setErrorMessage(message);
      setUploadStatus("error");
    }
  };

  const handleDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (validateFile(file)) {
        await uploadFile(file);
      }
    }
  };

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (validateFile(file)) {
        await uploadFile(file);
      }
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="w-full max-w-xl mx-auto">
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={triggerFileInput}
        className={`relative overflow-hidden rounded-2xl border-2 border-dashed p-8 text-center transition-all cursor-pointer flex flex-col items-center justify-center min-h-[220px] ${
          isDragActive
            ? "border-indigo-500 bg-indigo-500/5 shadow-[0_0_20px_rgba(99,102,241,0.15)]"
            : "border-zinc-800 bg-zinc-900/10 hover:border-zinc-700 hover:bg-zinc-900/20"
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          className="hidden"
          accept={ALLOWED_EXTENSIONS.join(",")}
          onChange={handleFileChange}
        />

        {uploadStatus === "idle" && (
          <div className="flex flex-col items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:scale-105 transition-transform">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Drag & drop your research file here</p>
              <p className="text-xs text-zinc-500 mt-1">or click to browse local storage</p>
            </div>
            <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-500 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800">
              PDF, DOCX, CSV, TXT up to {MAX_FILE_SIZE_MB}MB
            </span>
          </div>
        )}

        {uploadStatus === "uploading" && (
          <div className="flex flex-col items-center gap-4 w-full px-4">
            <div className="relative flex h-10 w-10 items-center justify-center">
              <div className="absolute h-full w-full rounded-full border-2 border-solid border-indigo-500/20"></div>
              <div className="absolute h-full w-full animate-spin rounded-full border-2 border-solid border-indigo-400 border-t-transparent shadow-[0_0_10px_rgba(99,102,241,0.3)]"></div>
            </div>
            <div className="text-center w-full">
              <p className="text-sm font-medium text-indigo-400 animate-pulse">Uploading file...</p>
              <p className="text-xs font-mono text-zinc-400 mt-1 truncate max-w-xs mx-auto">{fileName}</p>
            </div>
            {/* Elegant Glow Progress Bar */}
            <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden relative">
              <div className="bg-indigo-500 h-full animate-[loading_1.5s_infinite_linear] rounded-full shadow-[0_0_8px_#6366f1] w-[50%]"></div>
            </div>
          </div>
        )}

        {uploadStatus === "success" && (
          <div className="flex flex-col items-center gap-3 text-center">
            <div className="h-10 w-10 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.2)]">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-emerald-400">File uploaded successfully</p>
              <p className="text-xs text-zinc-400 mt-1">Ingestion queued on Celery workers</p>
            </div>
          </div>
        )}

        {uploadStatus === "error" && (
          <div className="flex flex-col items-center gap-3 text-center px-4" onClick={(e) => e.stopPropagation()}>
            <div className="h-10 w-10 rounded-full bg-rose-500/20 border border-rose-500/30 flex items-center justify-center text-rose-400 shadow-[0_0_15px_rgba(244,63,94,0.2)]">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-rose-400">Upload failed</p>
              <p className="text-xs text-zinc-400 mt-1">{errorMessage}</p>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setUploadStatus("idle");
              }}
              className="mt-2 px-3 py-1 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded border border-zinc-700 transition-colors"
            >
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
