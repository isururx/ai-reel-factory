"use client";

import AppShell, { LoadingSkeleton } from "@/components/AppShell";
import { authenticatedFetch } from "@/lib/supabase";
import { useCallback, useEffect, useMemo, useState } from "react";

type Page = { id: number; name: string; is_active: boolean };
type Pattern = {
  id: number; page_id: number; category: string; name: string; description: string;
  reusable_construction: string; occurrence_count: number; supporting_video_count: number;
  confidence_score: number | null; status: "emerging" | "active" | "archived";
  last_observed_at: string | null;
};
type Summary = { patterns_count: number; elements_count: number; active_patterns_count: number };
type Evidence = {
  id: number; pattern_id: number; reference_video_id: number; evidence_description: string;
  timestamp_start: number | null; timestamp_end: number | null;
  performance_context: Record<string, unknown>;
};

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
const categories = ["all", "hook", "storytelling", "retention", "editing", "visual", "audio", "emotional", "information_delivery", "cta", "ending", "other"];

async function api<T>(path: string): Promise<T> {
  const response = await authenticatedFetch(`${API}${path}`, { cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return response.json();
}

function seconds(value: number | null) {
  if (value == null) return "Timestamp unavailable";
  const minutes = Math.floor(value / 60);
  const remainder = (value % 60).toFixed(1).padStart(4, "0");
  return `${minutes}:${remainder}`;
}

export default function CreativeIntelligencePage() {
  const [pages, setPages] = useState<Page[]>([]);
  const [pageId, setPageId] = useState<number | "">("");
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [category, setCategory] = useState("all");
  const [selected, setSelected] = useState<Pattern | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    if (pageId === "") return;
    const suffix = category === "all" ? "" : `?category=${encodeURIComponent(category)}`;
    const [patternRows, totals] = await Promise.all([
      api<Pattern[]>(`/pages/${pageId}/creative-intelligence/patterns${suffix}`),
      api<Summary>(`/pages/${pageId}/creative-intelligence/summary`),
    ]);
    setPatterns(patternRows);
    setSummary(totals);
  }, [pageId, category]);

  useEffect(() => {
    void (async () => {
      try {
        const result = await api<Page[]>("/pages");
        setPages(result);
        if (result.length) setPageId(result[0].id);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not load Page workspaces.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    if (pageId === "") return;
    setError("");
    void refresh().catch(e => setError(e instanceof Error ? e.message : "Could not load creative intelligence."));
  }, [pageId, refresh]);

  async function openPattern(pattern: Pattern) {
    setSelected(pattern);
    setEvidence([]);
    try {
      const rows = await api<Evidence[]>(`/pages/${pageId}/creative-intelligence/patterns/${pattern.id}/evidence`);
      setEvidence(rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load pattern evidence.");
    }
  }

  const grouped = useMemo(() => patterns.length, [patterns]);

  return (
    <AppShell active="intelligence">
      <main className="min-h-screen text-slate-100">
        <div className="mx-auto max-w-7xl px-5 py-8 md:px-10 md:py-12">
          <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold tracking-[0.28em] text-cyan-400">PAGE-SPECIFIC LEARNING</p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">Creative Intelligence</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">Reusable hooks, storytelling techniques, retention devices and editing patterns extracted automatically from your selected reference videos.</p>
            </div>
            <a href="/references" className="rounded-xl border border-cyan-300/20 px-4 py-2.5 text-sm font-semibold text-cyan-200 hover:bg-cyan-300/10">Submit reference video ↗</a>
          </header>

          {error && <div role="alert" className="mb-5 rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
          <section className="mb-6 rounded-2xl border border-white/10 bg-white/[0.035] p-5">
            <label htmlFor="intelligence-page" className="mb-2 block text-xs font-medium text-slate-400">Page intelligence workspace</label>
            {loading ? <LoadingSkeleton rows={2} /> : pages.length === 0 ? (
              <p className="text-sm text-amber-200">Create a Page workspace first.</p>
            ) : (
              <select id="intelligence-page" value={pageId} onChange={e => { setPageId(Number(e.target.value)); setSelected(null); }} className="field max-w-lg">
                {pages.map(page => <option key={page.id} value={page.id}>{page.name}{page.is_active ? "" : " · Paused"}</option>)}
              </select>
            )}
          </section>

          {pageId !== "" && (
            <>
              <section className="mb-7 grid gap-3 sm:grid-cols-3">
                {[
                  ["Reusable patterns", summary?.patterns_count ?? 0],
                  ["Extracted elements", summary?.elements_count ?? 0],
                  ["Repeated patterns", summary?.active_patterns_count ?? 0],
                ].map(([label, value]) => (
                  <div key={String(label)} className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
                    <p className="text-xs text-slate-400">{label}</p><p className="mt-2 text-3xl font-semibold tabular-nums">{value}</p>
                  </div>
                ))}
              </section>

              <section className="grid gap-5 lg:grid-cols-[1.15fr_.85fr]">
                <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
                  <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                    <div><h2 className="text-lg font-semibold">Pattern library</h2><p className="mt-1 text-xs text-slate-500">{grouped} matching techniques · automatically updated after analysis</p></div>
                    <button onClick={() => void refresh()} className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 hover:bg-white/5">Refresh</button>
                  </div>
                  <div className="mb-4 flex flex-wrap gap-2">
                    {categories.map(item => <button key={item} onClick={() => setCategory(item)} className={category === item ? "rounded-full bg-cyan-300 px-3 py-1.5 text-xs font-semibold text-slate-950" : "rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:border-cyan-300/30"}>{item.replaceAll("_", " ")}</button>)}
                  </div>
                  {patterns.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-white/10 p-8 text-center"><p className="text-sm text-slate-300">No patterns extracted yet.</p><p className="mt-2 text-xs text-slate-500">Submit reference videos and the analysis worker will build this Page's library automatically.</p></div>
                  ) : (
                    <div className="space-y-3">
                      {patterns.map(pattern => <button key={pattern.id} onClick={() => void openPattern(pattern)} className={selected?.id === pattern.id ? "w-full rounded-xl border border-cyan-300/40 bg-cyan-300/[0.07] p-4 text-left" : "w-full rounded-xl border border-white/10 bg-white/[0.02] p-4 text-left hover:border-white/20"}>
                        <div className="flex flex-wrap items-center justify-between gap-2"><span className="text-sm font-semibold">{pattern.name}</span><span className={pattern.status === "active" ? "rounded-full border border-emerald-300/20 px-2 py-1 text-[10px] text-emerald-200" : "rounded-full border border-amber-300/20 px-2 py-1 text-[10px] text-amber-200"}>{pattern.status}</span></div>
                        <p className="mt-2 text-xs leading-5 text-slate-400">{pattern.description}</p>
                        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500"><span>{pattern.category.replaceAll("_", " ")}</span><span>{pattern.supporting_video_count} supporting videos</span><span>{pattern.occurrence_count} observations</span><span>{pattern.confidence_score == null ? "Confidence unavailable" : `${Math.round(pattern.confidence_score * 100)}% extraction confidence`}</span></div>
                      </button>)}
                    </div>
                  )}
                </div>

                <aside className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
                  <h2 className="text-lg font-semibold">Pattern evidence</h2>
                  {!selected ? <p className="mt-3 text-sm leading-6 text-slate-500">Select a pattern to inspect the source videos, timestamps and manually supplied performance context supporting it.</p> : (
                    <>
                      <p className="mt-2 text-sm font-medium text-cyan-200">{selected.name}</p>
                      <p className="mt-2 text-sm leading-6 text-slate-400">{selected.reusable_construction || selected.description}</p>
                      <div className="mt-4 space-y-3">
                        {evidence.length === 0 ? <p className="text-xs text-slate-500">No evidence records returned.</p> : evidence.map(item => <div key={item.id} className="rounded-xl border border-white/10 p-3">
                          <p className="text-xs font-semibold text-slate-200">Reference video #{item.reference_video_id}</p>
                          <p className="mt-1 text-xs text-slate-400">{item.evidence_description}</p>
                          <p className="mt-2 text-[11px] text-cyan-300">{seconds(item.timestamp_start)} – {seconds(item.timestamp_end)}</p>
                          <p className="mt-2 text-[10px] text-slate-500">Manual metrics: {Object.entries(item.performance_context).filter(([key]) => key !== "provenance").map(([key, value]) => `${key}: ${value ?? "—"}`).join(" · ")}</p>
                        </div>)}
                      </div>
                    </>
                  )}
                  <p className="mt-5 border-t border-white/10 pt-4 text-[11px] leading-5 text-slate-500">Repeated observations indicate that a technique appears across multiple references. They do not prove that the technique caused high performance.</p>
                </aside>
              </section>
            </>
          )}
        </div>
      </main>
    </AppShell>
  );
}
