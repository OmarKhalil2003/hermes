"use client";

import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";

export interface TrainingJob {
  id: string;
  user_id: string;
  model_name: string;
  base_model: string;
  dataset_path: string;
  hyperparameters: {
    epochs?: number;
    batch_size?: number;
    learning_rate?: number;
    lora_r?: number;
    lora_alpha?: number;
    max_steps?: number;
  };
  status: "pending" | "running" | "completed" | "failed";
  mlflow_run_id: string | null;
  error_message: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Evaluation {
  id: string;
  training_job_id: string | null;
  model_name: string;
  dataset_name: string;
  metrics: {
    rouge1: number;
    rouge2: number;
    rougeL: number;
    bleu: number;
    bertscore_f1: number;
  };
  created_at: string;
}

export interface Deployment {
  name: string;
  id: string;
  path: string;
  is_active: boolean;
}

export default function DeploymentConsole() {
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  
  // Job creation form state
  const [baseModel, setBaseModel] = useState("Qwen/Qwen2.5-3B-Instruct");
  const [datasetPath, setDatasetPath] = useState("finetuning/dataset.jsonl");
  const [epochs, setEpochs] = useState(3);
  const [batchSize, setBatchSize] = useState(1);
  const [lr, setLr] = useState(0.0002);
  const [loraR, setLoraR] = useState(8);
  const [loraAlpha, setLoraAlpha] = useState(16);
  const [maxSteps, setMaxSteps] = useState(-1);
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const fetchData = async () => {
    try {
      const [jobsRes, evalsRes, deploysRes] = await Promise.all([
        apiFetch("/api/v1/jobs"),
        apiFetch("/api/v1/jobs/evaluations"),
        apiFetch("/api/v1/jobs/deployments"),
      ]);

      if (jobsRes.ok) setJobs(await jobsRes.json());
      if (evalsRes.ok) setEvaluations(await evalsRes.json());
      if (deploysRes.ok) setDeployments(await deploysRes.json());
    } catch (err) {
      console.error("Failed to load deployment/job data:", err);
    }
  };

  useEffect(() => {
    fetchData();
    // Poll data every 5 seconds to track training job progress
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleStartTraining = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage("");
    setSuccessMessage("");

    try {
      const response = await apiFetch("/api/v1/jobs", {
        method: "POST",
        body: JSON.stringify({
          base_model: baseModel,
          dataset_path: datasetPath,
          hyperparameters: {
            epochs,
            batch_size: batchSize,
            learning_rate: lr,
            lora_r: loraR,
            lora_alpha: loraAlpha,
            max_steps: maxSteps,
          },
        }),
      });

      if (response.ok) {
        setSuccessMessage("Fine-tuning training job queued successfully!");
        fetchData();
      } else {
        const errData = await response.json();
        setErrorMessage(errData.detail || "Failed to start training job.");
      }
    } catch (err) {
      setErrorMessage("Network error: failed to submit training job.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleActivateDeployment = async (modelPath: string) => {
    try {
      const response = await apiFetch("/api/v1/jobs/deployments/active", {
        method: "POST",
        body: JSON.stringify({ model_name: modelPath }),
      });

      if (response.ok) {
        fetchData();
      } else {
        const errData = await response.json();
        alert(errData.detail || "Failed to activate model deployment.");
      }
    } catch (err) {
      alert("Network error: failed to update active deployment.");
    }
  };

  return (
    <div className="space-y-12 animate-fade-in">
      {/* Top Section Grid: Start Job & Active Router */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Left Side: Submit Training Form */}
        <div className="lg:col-span-2 rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6 backdrop-blur-sm relative overflow-hidden space-y-6">
          <div className="absolute top-0 right-0 h-32 w-32 bg-indigo-500/5 rounded-full blur-2xl pointer-events-none"></div>
          <div>
            <h3 className="text-lg font-bold text-white">Trigger Fine-Tuning Job</h3>
            <p className="text-xs text-zinc-400 mt-1">Configure QLoRA hyperparameters to compile and train a custom model adapter.</p>
          </div>

          <form onSubmit={handleStartTraining} className="space-y-4 text-sm">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Base Model</label>
                <input
                  type="text"
                  value={baseModel}
                  onChange={(e) => setBaseModel(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-200 focus:outline-none focus:border-indigo-500 transition-all font-mono"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Dataset Path</label>
                <input
                  type="text"
                  value={datasetPath}
                  onChange={(e) => setDatasetPath(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-200 focus:outline-none focus:border-indigo-500 transition-all font-mono"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Epochs</label>
                <input
                  type="number"
                  value={epochs}
                  onChange={(e) => setEpochs(Number(e.target.value))}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-1.5 text-zinc-200 font-mono focus:outline-none"
                  min="1"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Batch Size</label>
                <input
                  type="number"
                  value={batchSize}
                  onChange={(e) => setBatchSize(Number(e.target.value))}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-1.5 text-zinc-200 font-mono focus:outline-none"
                  min="1"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Learn Rate</label>
                <input
                  type="number"
                  value={lr}
                  onChange={(e) => setLr(Number(e.target.value))}
                  step="0.00001"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-1.5 text-zinc-200 font-mono focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Lora R</label>
                <input
                  type="number"
                  value={loraR}
                  onChange={(e) => setLoraR(Number(e.target.value))}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-1.5 text-zinc-200 font-mono focus:outline-none"
                  min="1"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Lora Alpha</label>
                <input
                  type="number"
                  value={loraAlpha}
                  onChange={(e) => setLoraAlpha(Number(e.target.value))}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-1.5 text-zinc-200 font-mono focus:outline-none"
                  min="1"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">Max Steps</label>
                <input
                  type="number"
                  value={maxSteps}
                  onChange={(e) => setMaxSteps(Number(e.target.value))}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-1.5 text-zinc-200 font-mono focus:outline-none"
                />
              </div>
            </div>

            {errorMessage && (
              <div className="p-3 bg-red-950/40 border border-red-900/50 rounded-lg text-xs text-red-400 font-mono">
                {errorMessage}
              </div>
            )}

            {successMessage && (
              <div className="p-3 bg-emerald-950/40 border border-emerald-900/50 rounded-lg text-xs text-emerald-400 font-mono">
                {successMessage}
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 text-white rounded-lg font-semibold tracking-wide transition-all shadow-[0_0_15px_rgba(99,102,241,0.2)] focus:outline-none flex items-center gap-2 cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Initializing...
                </>
              ) : (
                "Queue Fine-Tuning Job"
              )}
            </button>
          </form>
        </div>

        {/* Right Side: Deployment Controller */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6 backdrop-blur-sm relative overflow-hidden space-y-6">
          <div className="absolute top-0 right-0 h-32 w-32 bg-emerald-500/5 rounded-full blur-2xl pointer-events-none"></div>
          <div>
            <h3 className="text-lg font-bold text-white">Active Deployment Router</h3>
            <p className="text-xs text-zinc-400 mt-1">Route conversational agent traffic instantly to different active model adapters.</p>
          </div>

          <div className="space-y-3">
            {deployments.map((dep) => (
              <div
                key={dep.id}
                className={`p-4 rounded-xl border transition-all flex flex-col justify-between gap-3 ${
                  dep.is_active
                    ? "bg-indigo-950/20 border-indigo-500/40 shadow-[0_0_15px_rgba(99,102,241,0.05)]"
                    : "bg-zinc-950/40 border-zinc-800 hover:border-zinc-700"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <span className="font-semibold text-sm text-zinc-100 block">{dep.name}</span>
                    <span className="text-[10px] text-zinc-500 font-mono block break-all">{dep.path}</span>
                  </div>
                  {dep.is_active && (
                    <span className="px-2 py-0.5 rounded-full text-[9px] bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 font-bold uppercase tracking-wider animate-pulse">
                      Active
                    </span>
                  )}
                </div>

                {!dep.is_active && (
                  <button
                    onClick={() => handleActivateDeployment(dep.path)}
                    className="self-end px-3 py-1 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-zinc-800 hover:border-zinc-700 text-xs font-semibold rounded-lg transition-all focus:outline-none cursor-pointer"
                  >
                    Activate Routing
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Progress Monitoring Dashboard Card */}
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6 backdrop-blur-sm space-y-6">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-500">Fine-Tuning Jobs Progress Monitoring</h3>

        {jobs.length === 0 ? (
          <div className="flex h-24 items-center justify-center rounded-xl border border-zinc-900 bg-zinc-900/10 text-zinc-500 text-sm font-sans">
            No historical fine-tuning jobs recorded.
          </div>
        ) : (
          <div className="space-y-4">
            {jobs.map((job) => (
              <div key={job.id} className="p-4 rounded-xl border border-zinc-800/80 bg-zinc-950/30 space-y-3 font-sans">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs">
                  <div className="space-y-0.5">
                    <span className="font-mono text-zinc-500">JOB ID: {job.id}</span>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-zinc-200">Target Adapter: {job.model_name}</span>
                      <span className="text-zinc-500">| Base: {job.base_model}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-zinc-500">Created: {new Date(job.created_at).toLocaleString()}</span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border uppercase tracking-wider ${
                        job.status === "completed"
                          ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                          : job.status === "running"
                          ? "bg-indigo-500/10 border-indigo-500/20 text-indigo-400 animate-pulse"
                          : job.status === "failed"
                          ? "bg-red-500/10 border-red-500/20 text-red-400"
                          : "bg-zinc-500/10 border-zinc-500/20 text-zinc-400"
                      }`}
                    >
                      {job.status}
                    </span>
                  </div>
                </div>

                {/* Progress bar container */}
                <div className="w-full bg-zinc-900 h-2 rounded-full overflow-hidden border border-zinc-800/50">
                  <div
                    className={`h-full transition-all duration-1000 ${
                      job.status === "completed"
                        ? "bg-gradient-to-r from-emerald-500 to-teal-500 w-full"
                        : job.status === "running"
                        ? "bg-gradient-to-r from-indigo-500 to-purple-500 w-1/2 animate-pulse"
                        : job.status === "failed"
                        ? "bg-gradient-to-r from-red-600 to-rose-600 w-full"
                        : "bg-zinc-800 w-[10%]"
                    }`}
                  ></div>
                </div>

                {/* Error log details */}
                {job.status === "failed" && job.error_message && (
                  <div className="p-3 bg-red-950/20 border border-red-900/30 rounded-lg text-xs text-red-400 font-mono break-words">
                    <strong>Error Log:</strong> {job.error_message}
                  </div>
                )}

                {/* Hyperparameters summary */}
                <div className="flex flex-wrap gap-x-6 gap-y-1 text-[11px] font-mono text-zinc-400 bg-zinc-950/50 px-3 py-2 rounded-lg border border-zinc-900">
                  <span>Epochs: {job.hyperparameters?.epochs ?? "N/A"}</span>
                  <span>Batch: {job.hyperparameters?.batch_size ?? "N/A"}</span>
                  <span>LR: {job.hyperparameters?.learning_rate ?? "N/A"}</span>
                  <span>LoRA R: {job.hyperparameters?.lora_r ?? "N/A"}</span>
                  <span>LoRA Alpha: {job.hyperparameters?.lora_alpha ?? "N/A"}</span>
                  {job.mlflow_run_id && (
                    <span className="text-zinc-500">MLflow Run ID: {job.mlflow_run_id}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Model Comparative Metrics Card */}
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6 backdrop-blur-sm space-y-6">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-500">Model Comparative Evaluations</h3>
          <p className="text-xs text-zinc-400 mt-1">Cross-compare text similarity (ROUGE, BLEU, BERTScore) evaluations of fine-tuned runs vs default baseline model.</p>
        </div>

        {evaluations.length === 0 ? (
          <div className="flex h-24 items-center justify-center rounded-xl border border-zinc-900 bg-zinc-900/10 text-zinc-500 text-sm font-sans">
            No model evaluations recorded. Complete a training run to generate benchmark results.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-zinc-850">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-zinc-900 border-b border-zinc-800 text-zinc-400 font-mono uppercase tracking-wider">
                  <th className="p-4 font-semibold">Model Target</th>
                  <th className="p-4 font-semibold text-center">Dataset</th>
                  <th className="p-4 font-semibold text-center text-indigo-400">ROUGE-1</th>
                  <th className="p-4 font-semibold text-center text-indigo-400">ROUGE-2</th>
                  <th className="p-4 font-semibold text-center text-indigo-400">ROUGE-L</th>
                  <th className="p-4 font-semibold text-center text-purple-400">BLEU</th>
                  <th className="p-4 font-semibold text-center text-teal-400">BERTScore F1</th>
                  <th className="p-4 font-semibold text-right">Evaluation Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-900 text-zinc-300 font-mono">
                {/* Default mock base model metrics for visual comparison */}
                <tr className="hover:bg-zinc-900/10 transition-colors">
                  <td className="p-4 font-sans font-semibold text-zinc-400">Base Baseline Model (gpt-4o-mini)</td>
                  <td className="p-4 text-center text-zinc-500">Hermes-QA-Bench</td>
                  <td className="p-4 text-center text-zinc-400">0.582</td>
                  <td className="p-4 text-center text-zinc-400">0.421</td>
                  <td className="p-4 text-center text-zinc-400">0.540</td>
                  <td className="p-4 text-center text-zinc-400">0.380</td>
                  <td className="p-4 text-center text-zinc-400">0.824</td>
                  <td className="p-4 text-right text-zinc-500 font-sans">Baseline</td>
                </tr>

                {evaluations.map((ev) => (
                  <tr key={ev.id} className="hover:bg-zinc-900/20 transition-colors">
                    <td className="p-4 font-sans font-semibold text-indigo-300">{ev.model_name}</td>
                    <td className="p-4 text-center text-zinc-400">{ev.dataset_name}</td>
                    <td className="p-4 text-center text-indigo-400 font-bold">{(ev.metrics.rouge1 || 0).toFixed(3)}</td>
                    <td className="p-4 text-center text-indigo-400 font-bold">{(ev.metrics.rouge2 || 0).toFixed(3)}</td>
                    <td className="p-4 text-center text-indigo-400 font-bold">{(ev.metrics.rougeL || 0).toFixed(3)}</td>
                    <td className="p-4 text-center text-purple-400 font-bold">{(ev.metrics.bleu || 0).toFixed(3)}</td>
                    <td className="p-4 text-center text-teal-400 font-bold">{(ev.metrics.bertscore_f1 || 0).toFixed(3)}</td>
                    <td className="p-4 text-right text-zinc-400 font-sans">{new Date(ev.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
