"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { authenticatedFetch } from "@/lib/supabase";

type Strategy = { id: number; name: string; description: string; status: string };
type StrategyVersion = { id: number; version_number: number; status: string; configuration: Record<string, unknown> };
type Pattern = { id: number; name: string; category: string; description: string; reusable_construction: string; status: string; supporting_video_count: number; occurrence_count: number; confidence_score: number | null };
type Batch = { id: number; page_id: number; strategy_id: number; strategy_version_id: number; mode: string; status: string; requested_count: number; completed_count: number; input_snapshot: Record<string, unknown>; created_at: string; started_at: string | null; completed_at: string | null; error_message: string | null };

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await authenticatedFetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail ?? `Request failed (${response.status})`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return response.json();
}

function badge(status: string) {
  if (status === "completed") return "border-emerald-400/25 bg-emerald-400/10 text-emerald-200";
  if (status === "failed" || status === "partially_failed") return "border-rose-400/25 bg-rose-400/10 text-rose-200";
  if (status === "processing") return "border-cyan-300/25 bg-cyan-300/10 text-cyan-100";
  return "border-amber-300/20 bg-amber-300/10 text-amber-100";
}

export default function BatchStudio({ pageId, onScriptsChanged }: { pageId: number | ""; onScriptsChanged: () => void }) {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [strategyId, setStrategyId] = useState<number | "">("");
  const [versions, setVersions] = useState<StrategyVersion[]>([]);
  const [versionId, setVersionId] = useState<number | "">("");
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [selectedPatterns, setSelectedPatterns] = useState<number[]>([]);
  const [mode, setMode] = useState<"automatic" | "manual">("automatic");
  const [patternMode, setPatternMode] = useState<"automatic" | "manual" | "hybrid">("automatic");
  const [brief, setBrief] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [count, setCount] = useState(3);
  const [fillSlots, setFillSlots] = useState(false);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadBatches = useCallback(async () => {
    if (pageId === "") { setBatches([]); return; }
    const result = await api<Batch[]>(`/pages/${pageId}/script-batches?limit=10`);
    setBatches(result);
    if (result.some((batch) => batch.status === "completed" || batch.status === "partially_failed" || batch.status === "failed")) onScriptsChanged();
  }, [pageId, onScriptsChanged]);

  useEffect(() => {
    let alive = true;
    if (pageId === "") {
      setStrategies([]); setPatterns([]); setBatches([]); setStrategyId(""); setVersionId("");
      return;
    }
    setLoading(true); setError("");
    Promise.all([
      api<Strategy[]>(`/pages/${pageId}/strategies`),
      api<Pattern[]>(`/pages/${pageId}/creative-intelligence/patterns`),
      api<Batch[]>(`/pages/${pageId}/script-batches?limit=10`),
    ]).then(([strategyRows, patternRows, batchRows]) => {
      if (!alive) return;
      const active = strategyRows.filter((item) => item.status === "active");
      setStrategies(active.length ? active : strategyRows);
      setStrategyId((current) => current !== "" && strategyRows.some((item) => item.id === current) ? current : (active[0]?.id ?? strategyRows[0]?.id ?? ""));
      setPatterns(patternRows.filter((item) => item.status !== "archived"));
      setBatches(batchRows);
    }).catch((e) => { if (alive) setError(e instanceof Error ? e.message : "Could not load batch settings."); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [pageId]);

  useEffect(() => {
    let alive = true;
    if (pageId === "" || strategyId === "") { setVersions([]); setVersionId(""); return; }
    api<StrategyVersion[]>(`/pages/${pageId}/strategies/${strategyId}/versions`)
      .then((rows) => {
        if (!alive) return;
        setVersions(rows);
        const active = rows.filter((row) => row.status === "active");
        setVersionId((current) => current !== "" && rows.some((row) => row.id === current) ? current : (active[0]?.id ?? rows[rows.length - 1]?.id ?? ""));
      })
      .catch((e) => { if (alive) setError(e instanceof Error ? e.message : "Could not load strategy versions."); });
    return () => { alive = false; };
  }, [pageId, strategyId]);

  const hasRunning = useMemo(() => batches.some((batch) => batch.status === "queued" || batch.status === "processing"), [batches]);
  useEffect(() => {
    if (!hasRunning) return;
    const timer = window.setInterval(() => { void loadBatches().catch((e) => setError(e instanceof Error ? e.message : "Could not refresh batch status.")); }, 4000);
    return () => window.clearInterval(timer);
  }, [hasRunning, loadBatches]);

  async function createBatch() {
    if (pageId === "" || strategyId === "" || versionId === "") {
      setError("Select a Page, strategy and strategy version first."); return;
    }
    if (mode === "manual" && brief.trim().length < 20) {
      setError("Manual mode requires a brief of at least 20 characters."); return;
    }
    if (patternMode === "manual" && selectedPatterns.length === 0) {
      setError("Select at least one pattern, or change the pattern selection mode."); return;
    }
    setSubmitting(true); setError(""); setNotice("");
    try {
      const created = await api<Batch>(`/pages/${pageId}/script-batches`, {
        method: "POST",
        body: JSON.stringify({
          strategy_id: strategyId,
          strategy_version_id: versionId,
          mode,
          brief: brief.trim() || null,
          source_url: sourceUrl.trim() || null,
          pattern_selection: patternMode,
          pattern_ids: selectedPatterns,
          script_count: fillSlots ? null : count,
          fill_remaining_daily_slots: fillSlots,
        }),
      });
      setNotice(`Batch #${created.id} queued: ${created.requested_count} script(s) requested.`);
      setBrief(""); setSourceUrl("");
      await loadBatches();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create the batch.");
    } finally { setSubmitting(false); }
  }

  function togglePattern(id: number) {
    setSelectedPatterns((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  return (
    <section className="mb-7 overflow-hidden rounded-2xl border border-cyan-300/20 bg-[#0d1825]">
      <div className="border-b border-white/[0.07] px-5 py-5 sm:px-7">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-cyan-300">Batch production</p>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
          <div><h2 className="text-xl font-semibold text-white">Generate a batch of scripts</h2><p className="mt-1 text-sm text-slate-400">Choose one strategy for this batch, then create several distinct drafts for this Page.</p></div>
          <span className="rounded-full border border-white/10 px-3 py-1.5 text-[10px] text-slate-400">One strategy · Page-scoped</span>
        </div>
      </div>

      {error && <div role="alert" className="mx-5 mt-4 rounded-xl border border-rose-400/25 bg-rose-400/[0.08] px-4 py-3 text-xs text-rose-200 sm:mx-7">{error}</div>}
      {notice && <div role="status" className="mx-5 mt-4 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.07] px-4 py-3 text-xs text-emerald-200 sm:mx-7">{notice}</div>}

      <div className="grid gap-5 p-5 sm:p-7">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Strategy
            <select value={strategyId} onChange={(e) => setStrategyId(e.target.value ? Number(e.target.value) : "")} disabled={loading || strategies.length === 0} className="mt-2 w-full rounded-xl border border-white/10 bg-[#080f19] px-3 py-3 text-sm font-normal normal-case text-slate-100 outline-none focus:border-cyan-300/40">
              {strategies.length === 0 && <option value="">No strategies available</option>}
              {strategies.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.status}</option>)}
            </select>
          </label>
          <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Strategy version
            <select value={versionId} onChange={(e) => setVersionId(e.target.value ? Number(e.target.value) : "")} disabled={versions.length === 0} className="mt-2 w-full rounded-xl border border-white/10 bg-[#080f19] px-3 py-3 text-sm font-normal normal-case text-slate-100 outline-none focus:border-cyan-300/40">
              {versions.length === 0 && <option value="">No versions available</option>}
              {versions.map((item) => <option key={item.id} value={item.id}>Version {item.version_number} · {item.status}</option>)}
            </select>
          </label>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div><p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Generation mode</p><div className="grid grid-cols-2 gap-2">
            <button type="button" onClick={() => setMode("automatic")} className={`rounded-xl border px-3 py-3 text-left text-xs ${mode === "automatic" ? "border-cyan-300/40 bg-cyan-300/[0.08] text-cyan-100" : "border-white/10 text-slate-400 hover:bg-white/[0.03]"}`}><strong className="block text-sm">Automatic</strong><span className="mt-1 block text-[10px] opacity-70">Build from Page profile and strategy</span></button>
            <button type="button" onClick={() => setMode("manual")} className={`rounded-xl border px-3 py-3 text-left text-xs ${mode === "manual" ? "border-cyan-300/40 bg-cyan-300/[0.08] text-cyan-100" : "border-white/10 text-slate-400 hover:bg-white/[0.03]"}`}><strong className="block text-sm">Manual brief</strong><span className="mt-1 block text-[10px] opacity-70">You provide the creative direction</span></button>
          </div></div>
          <div><p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Creative pattern selection</p><div className="grid grid-cols-3 gap-2">
            {(["automatic", "manual", "hybrid"] as const).map((value) => <button key={value} type="button" onClick={() => setPatternMode(value)} className={`rounded-xl border px-2 py-3 text-xs capitalize ${patternMode === value ? "border-cyan-300/40 bg-cyan-300/[0.08] text-cyan-100" : "border-white/10 text-slate-400 hover:bg-white/[0.03]"}`}>{value}</button>)}
          </div><p className="mt-2 text-[10px] text-slate-600">Automatic selects up to five mature Page patterns. Hybrid combines your choices with automatic suggestions.</p></div>
        </div>

        {mode === "manual" && <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Creative brief <span className="font-normal normal-case text-slate-600">· minimum 20 characters</span><textarea value={brief} onChange={(e) => setBrief(e.target.value)} rows={3} maxLength={5000} placeholder="Describe the topic, angle, key facts and storytelling direction for this batch..." className="mt-2 w-full rounded-xl border border-white/10 bg-[#080f19] p-4 text-sm leading-6 font-normal normal-case text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-300/40" /></label>}
        {mode === "automatic" && <p className="rounded-xl border border-white/[0.07] bg-white/[0.02] px-4 py-3 text-xs leading-5 text-slate-400">The system will create a brief using the Page profile and the selected strategy. You can still optionally add a specific creative direction below.</p>}
        {mode === "automatic" && <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Optional creative direction<textarea value={brief} onChange={(e) => setBrief(e.target.value)} rows={2} maxLength={5000} placeholder="Optional: focus on a particular subject, event or angle..." className="mt-2 w-full rounded-xl border border-white/10 bg-[#080f19] p-3 text-sm font-normal normal-case text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-300/40" /></label>}

        {patternMode !== "automatic" && <div className="rounded-xl border border-white/[0.08] bg-[#080f19]/70 p-4">
          <div className="mb-3 flex items-center justify-between gap-3"><div><p className="text-xs font-semibold text-slate-200">Choose creative patterns</p><p className="mt-1 text-[10px] text-slate-500">{selectedPatterns.length} selected · {patterns.length} available for this Page</p></div><button type="button" onClick={() => setSelectedPatterns([])} className="text-[10px] text-cyan-300 hover:text-cyan-200">Clear selection</button></div>
          {patterns.length === 0 ? <p className="text-xs text-slate-500">No patterns have been analysed for this Page yet. Automatic pattern selection can still run when patterns become available.</p> : <div className="grid gap-2 sm:grid-cols-2">
            {patterns.map((pattern) => <label key={pattern.id} className="flex cursor-pointer items-start gap-3 rounded-lg border border-white/[0.07] p-3 hover:bg-white/[0.025]"><input type="checkbox" checked={selectedPatterns.includes(pattern.id)} onChange={() => togglePattern(pattern.id)} className="mt-1 accent-cyan-300" /><span className="min-w-0"><span className="block text-xs font-medium text-slate-200">{pattern.name}</span><span className="mt-1 block text-[10px] leading-4 text-slate-500">{pattern.category} · {pattern.supporting_video_count} source videos</span><span className="mt-1 block text-[10px] leading-4 text-slate-600">{pattern.reusable_construction || pattern.description}</span></span></label>)}
          </div>}
        </div>}

        <div className="grid gap-4 md:grid-cols-[1fr_1fr]">
          <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Number of scripts
            <input type="number" min={1} max={20} value={count} onChange={(e) => setCount(Math.max(1, Math.min(20, Number(e.target.value) || 1)))} disabled={fillSlots} className="mt-2 w-full rounded-xl border border-white/10 bg-[#080f19] px-3 py-3 text-sm font-normal text-slate-100 outline-none disabled:opacity-40" />
          </label>
          <div className="flex items-end"><label className="flex w-full cursor-pointer items-center gap-3 rounded-xl border border-white/10 bg-[#080f19] px-4 py-3 text-xs text-slate-300"><input type="checkbox" checked={fillSlots} onChange={(e) => setFillSlots(e.target.checked)} className="accent-cyan-300" /><span><strong className="block">Fill remaining daily slots</strong><span className="mt-1 block text-[10px] text-slate-500">Uses this Page&apos;s publishing limit and timezone</span></span></label></div>
        </div>
        <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Optional source URL<input type="url" value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} placeholder="https://..." className="mt-2 w-full rounded-xl border border-white/10 bg-[#080f19] px-4 py-3 text-xs font-normal normal-case text-slate-300 outline-none focus:border-cyan-300/40" /></label>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.07] pt-5"><p className="max-w-xl text-[10px] leading-5 text-slate-500">Every generated script starts as a draft. Review, edit and approve each exact version individually before production.</p><button type="button" onClick={() => void createBatch()} disabled={submitting || loading || strategies.length === 0 || versionId === "" || (mode === "manual" && brief.trim().length < 20)} className="rounded-xl bg-cyan-300 px-6 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-40">{submitting ? "Queuing batch..." : "Generate script batch ↗"}</button></div>
      </div>

      <div className="border-t border-white/[0.07] bg-[#080f19]/55 p-5 sm:p-7">
        <div className="mb-4 flex items-center justify-between gap-3"><div><h3 className="text-sm font-semibold text-slate-200">Recent batches</h3><p className="mt-1 text-[10px] text-slate-500">Progress refreshes automatically while generation is running.</p></div><button type="button" onClick={() => void loadBatches().catch((e) => setError(e instanceof Error ? e.message : "Refresh failed."))} className="text-[10px] text-cyan-300 hover:text-cyan-200">Refresh ↻</button></div>
        {batches.length === 0 ? <p className="rounded-xl border border-dashed border-white/10 px-4 py-7 text-center text-xs text-slate-500">No script batches for this Page yet.</p> : <div className="space-y-3">
          {batches.map((batch) => <article key={batch.id} className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4">
            <div className="flex flex-wrap items-center justify-between gap-2"><div><p className="text-xs font-semibold text-slate-200">Batch #{batch.id}</p><p className="mt-1 text-[10px] text-slate-500">{batch.mode === "automatic" ? "Automatic" : "Manual"} · {new Date(batch.created_at).toLocaleString()}</p></div><span className={`rounded-full border px-2.5 py-1 text-[9px] font-semibold uppercase tracking-wider ${badge(batch.status)}`}>{batch.status.replace("_", " ")}</span></div>
            <div className="mt-3 flex items-center justify-between text-[10px] text-slate-400"><span>{batch.completed_count} / {batch.requested_count} scripts generated</span><span>{Math.round(batch.completed_count / Math.max(1, batch.requested_count) * 100)}%</span></div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-cyan-300 transition-all" style={{ width: `${Math.min(100, batch.completed_count / Math.max(1, batch.requested_count) * 100)}%` }} /></div>
            {batch.error_message && <p className="mt-2 text-[10px] text-rose-200">{batch.error_message}</p>}
          </article>)}
        </div>}
      </div>
    </section>
  );
}
