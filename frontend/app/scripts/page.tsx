"use client";

import AppShell from "@/components/AppShell";
import { authenticatedFetch } from "@/lib/supabase";
import { useCallback, useEffect, useState } from "react";

type Page = { id: number; name: string; is_active: boolean };
type ScriptVersion = {
  id: number;
  version_number: number;
  hook: string;
  narration: string;
  caption: string;
  hashtags: string[];
  script_data: {
    title?: string;
    variation?: number;
    estimated_duration_seconds?: number;
    evaluation?: {
      hook_score?: number;
      storytelling_score?: number;
      originality_score?: number;
      visual_suitability_score?: number;
      fact_check_notes?: string;
      strengths?: string;
    };
    source_url?: string;
  };
  created_at: string;
};
type ContentScript = {
  id: number;
  page_id: number;
  title: string;
  status: string;
  created_at: string;
  versions: ScriptVersion[];
};

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

export default function ScriptsPage() {
  const [pages, setPages] = useState<Page[]>([]);
  const [pageId, setPageId] = useState<number | "">("");
  const [scripts, setScripts] = useState<ContentScript[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyVersion, setBusyVersion] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadScripts = useCallback(async (id: number) => {
    const result = await api<ContentScript[]>(`/pages/${id}/scripts`);
    setScripts(result);
  }, []);

  useEffect(() => {
    let alive = true;
    api<Page[]>("/pages")
      .then((result) => {
        if (!alive) return;
        setPages(result);
        if (result.length) setPageId(result[0].id);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load Pages."))
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (pageId === "") {
      setScripts([]);
      return;
    }
    setLoading(true);
    setError("");
    loadScripts(pageId)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load scripts."))
      .finally(() => setLoading(false));
  }, [pageId, loadScripts]);

  async function decide(script: ContentScript, version: ScriptVersion, decision: "approved" | "rejected") {
    setBusyVersion(version.id);
    setError("");
    setNotice("");
    try {
      await api<ContentScript>(
        `/pages/${script.page_id}/scripts/${script.id}/versions/${version.id}/decision`,
        { method: "POST", body: JSON.stringify({ decision, comments: "" }) },
      );
      setNotice(`Version ${version.version_number} ${decision}.`);
      await loadScripts(script.page_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the review decision.");
    } finally {
      setBusyVersion(null);
    }
  }

  return (
    <AppShell active="scripts">
    <main className="min-h-screen bg-transparent text-slate-100">
      <div className="mx-auto max-w-7xl px-5 py-8 md:px-10 md:py-12">
        <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold tracking-[0.28em] text-cyan-400">CONTENT WORKFLOW</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight">Script studio</h1>
            <p className="mt-2 text-sm text-slate-400">Review generated variations, inspect their evaluations, and approve the exact version you want to produce.</p>
          </div>
          <span className="rounded-full border border-cyan-400/20 bg-cyan-400/5 px-3 py-2 text-[11px] text-cyan-200">HUMAN REVIEW REQUIRED</span>
        </header>

        {error && <div role="alert" className="mb-5 rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
        {notice && <div role="status" className="mb-5 rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200">{notice}</div>}

        <section className="mb-7 flex flex-wrap items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.035] p-5">
          <label className="text-sm text-slate-400" htmlFor="page-select">Content Page</label>
          <select id="page-select" value={pageId} onChange={(e) => setPageId(e.target.value ? Number(e.target.value) : "")} className="min-w-64 rounded-xl border border-white/10 bg-[#0b1220] px-4 py-3 text-sm outline-none focus:border-cyan-400/60">
            {pages.map((page) => <option key={page.id} value={page.id}>{page.name}</option>)}
          </select>
          <button onClick={() => { if (pageId !== "") void loadScripts(pageId); }} disabled={pageId === "" || loading} className="rounded-xl border border-white/10 px-4 py-3 text-sm text-cyan-200 hover:bg-white/5 disabled:opacity-50">Refresh ↻</button>
          <span className="text-xs text-slate-500">{scripts.length} script group(s)</span>
        </section>

        {loading ? (
          <div className="grid gap-4 lg:grid-cols-3">{[1,2,3].map((item) => <div key={item} className="skeleton-card space-y-4"><div className="skeleton-line w-1/3" /><div className="skeleton-line h-5 w-3/4" /><div className="skeleton-line h-3 w-full" /><div className="skeleton-line h-3 w-5/6" /><div className="skeleton-line h-3 w-full" /><div className="skeleton-line h-24 w-full rounded-xl" /></div>)}</div>
        ) : scripts.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/15 p-12 text-center">
            <h2 className="text-lg font-semibold">No generated scripts yet</h2>
            <p className="mt-2 text-sm text-slate-400">Select a trend in Trend discovery and choose Generate 3 scripts.</p>
            <a href="/trends" className="mt-5 inline-flex rounded-xl bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-200">Explore selected trends ↗</a>
          </div>
        ) : (
          <div className="space-y-6">
            {scripts.map((script) => (
              <section key={script.id} className="rounded-2xl border border-white/10 bg-white/[0.025] p-5 md:p-7">
                <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-cyan-300">Script #{script.id}</p>
                    <h2 className="mt-2 text-xl font-semibold">{script.title}</h2>
                    <p className="mt-1 text-xs text-slate-500">Created {new Date(script.created_at).toLocaleString()}</p>
                  </div>
                  <span className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-300">{script.status}</span>
                </div>
                <div className="grid gap-4 lg:grid-cols-3">
                  {script.versions.slice().sort((a, b) => a.version_number - b.version_number).map((version) => {
                    const evaluation = version.script_data?.evaluation;
                    const title = version.script_data?.title ?? `Variation ${version.script_data?.variation ?? version.version_number}`;
                    return (
                      <article key={version.id} className="flex flex-col rounded-xl border border-white/10 bg-[#0b1220] p-4">
                        <div className="mb-3 flex items-center justify-between gap-2">
                          <div>
                            <p className="text-xs font-semibold text-cyan-300">VERSION {version.version_number}</p>
                            <h3 className="mt-1 font-semibold">{title}</h3>
                          </div>
                          <span className="text-xs text-slate-500">{version.script_data?.estimated_duration_seconds ?? "—"} sec</span>
                        </div>
                        <div className="space-y-3 text-sm">
                          <div><p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">Hook</p><p className="text-slate-100">{version.hook}</p></div>
                          <div><p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">Narration</p><p className="whitespace-pre-wrap leading-6 text-slate-300">{version.narration}</p></div>
                          <div><p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">Caption</p><p className="text-slate-300">{version.caption}</p></div>
                          <p className="break-words text-xs text-cyan-200">{(version.hashtags ?? []).join(" ")}</p>
                        </div>
                        {evaluation && (
                          <div className="mt-4 rounded-lg border border-white/10 bg-white/[0.025] p-3">
                            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">AI evaluation · preliminary</p>
                            <div className="grid grid-cols-2 gap-2 text-xs text-slate-300">
                              <span>Hook: {evaluation.hook_score ?? "—"}/10</span>
                              <span>Story: {evaluation.storytelling_score ?? "—"}/10</span>
                              <span>Originality: {evaluation.originality_score ?? "—"}/10</span>
                              <span>Visuals: {evaluation.visual_suitability_score ?? "—"}/10</span>
                            </div>
                            {evaluation.fact_check_notes && <p className="mt-3 text-xs leading-5 text-amber-200">Fact-check: {evaluation.fact_check_notes}</p>}
                            {evaluation.strengths && <p className="mt-2 text-xs leading-5 text-slate-400">{evaluation.strengths}</p>}
                          </div>
                        )}
                        <div className="mt-auto flex flex-wrap gap-2 border-t border-white/10 pt-4 mt-4">
                          <button disabled={busyVersion === version.id} onClick={() => void decide(script, version, "approved")} className="rounded-lg bg-emerald-400/15 px-3 py-2 text-xs font-semibold text-emerald-200 hover:bg-emerald-400/25 disabled:opacity-50">Approve version</button>
                          <button disabled={busyVersion === version.id} onClick={() => void decide(script, version, "rejected")} className="rounded-lg border border-rose-400/20 px-3 py-2 text-xs text-rose-200 hover:bg-rose-400/10 disabled:opacity-50">Reject</button>
                        </div>
                      </article>
                    );
                  })}
                </div>
                <p className="mt-4 text-xs text-amber-200/80">AI evaluations are suggestions only. Verify factual claims and sources before approving a script.</p>
              </section>
            ))}
          </div>
        )}
        <footer className="mt-14 border-t border-white/10 pt-5 text-xs text-slate-600">AI Reel Factory · Script approval applies to the exact version reviewed.</footer>
      </div>
    </main>
    </AppShell>
  );
}
