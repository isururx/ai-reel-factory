"use client";

import { authenticatedFetch } from "@/lib/supabase";
import AppShell, { LoadingSkeleton } from "@/components/AppShell";

import { useCallback, useEffect, useState, type FormEvent } from "react";

type Page = { id: number; name: string; is_active: boolean };
type Strategy = {
  id: number;
  page_id: number;
  name: string;
  description: string;
  status: "draft" | "active" | "paused" | "archived";
  created_at: string;
};
type StrategyVersion = {
  id: number;
  version_number: number;
  configuration: Record<string, unknown>;
  status: string;
  created_at: string;
};

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
const starterConfiguration = {
  content_pillars: ["Core topic explainers", "Surprising facts", "Real-world examples"],
  posting_frequency_per_week: 5,
  target_duration_seconds: { min: 60, max: 90 },
  hook_styles: ["Curiosity question", "Unexpected fact"],
  storytelling: "Hook → context → key insight → payoff → CTA",
  visual_direction: "Fast-paced, relevant visuals, readable captions",
  call_to_action: "Ask one relevant question",
  guardrails: ["Use reliable sources", "Do not present speculation as fact"],
};

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

export default function StrategiesPage() {
  const [pages, setPages] = useState<Page[]>([]);
  const [pageId, setPageId] = useState<number | "">("");
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [versions, setVersions] = useState<StrategyVersion[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [versionJson, setVersionJson] = useState(JSON.stringify(starterConfiguration, null, 2));
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadPages = useCallback(async () => {
    const result = await api<Page[]>("/pages");
    setPages(result);
    if (result.length && pageId === "") setPageId(result[0].id);
  }, [pageId]);

  const loadStrategies = useCallback(async (id: number) => {
    const result = await api<Strategy[]>(`/pages/${id}/strategies`);
    setStrategies(result);
    if (selectedId !== null && !result.some((item) => item.id === selectedId)) {
      setSelectedId(null);
      setVersions([]);
    }
  }, [selectedId]);

  const loadVersions = useCallback(async (id: number, strategyId: number) => {
    const result = await api<StrategyVersion[]>(`/pages/${id}/strategies/${strategyId}/versions`);
    setVersions(result);
    if (result.length) setVersionJson(JSON.stringify(result[result.length - 1].configuration, null, 2));
  }, []);

  useEffect(() => {
    void (async () => {
      setLoading(true);
      try { await loadPages(); }
      catch (e) { setError(e instanceof Error ? e.message : "Could not load Pages."); }
      finally { setLoading(false); }
    })();
  }, [loadPages]);

  useEffect(() => {
    if (pageId === "") { setStrategies([]); setSelectedId(null); setVersions([]); return; }
    void loadStrategies(pageId).catch((e) => setError(e instanceof Error ? e.message : "Could not load strategies."));
  }, [pageId, loadStrategies]);

  async function selectStrategy(item: Strategy) {
    setSelectedId(item.id);
    setName(item.name);
    setDescription(item.description);
    setError("");
    try { await loadVersions(item.page_id, item.id); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not load strategy versions."); }
  }

  async function createStrategy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pageId === "") return;
    setBusy(true); setError(""); setNotice("");
    try {
      const created = await api<Strategy>(`/pages/${pageId}/strategies`, {
        method: "POST",
        body: JSON.stringify({ name: newName.trim(), description: newDescription.trim(), configuration: starterConfiguration }),
      });
      setNewName(""); setNewDescription("");
      await loadStrategies(pageId);
      await selectStrategy(created);
      setNotice("Strategy created with its first immutable version.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not create strategy."); }
    finally { setBusy(false); }
  }

  async function saveMetadata(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pageId === "" || selectedId === null) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await api<Strategy>(`/pages/${pageId}/strategies/${selectedId}`, {
        method: "PATCH", body: JSON.stringify({ name: name.trim(), description }),
      });
      await loadStrategies(pageId);
      setNotice("Strategy details saved.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save strategy."); }
    finally { setBusy(false); }
  }

  async function setStatus(status: Strategy["status"]) {
    if (pageId === "" || selectedId === null) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await api<Strategy>(`/pages/${pageId}/strategies/${selectedId}`, {
        method: "PATCH", body: JSON.stringify({ status }),
      });
      await loadStrategies(pageId);
      setNotice(`Strategy marked ${status}.`);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not update status."); }
    finally { setBusy(false); }
  }

  async function createVersion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pageId === "" || selectedId === null) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const configuration = JSON.parse(versionJson) as Record<string, unknown>;
      if (!configuration || Array.isArray(configuration) || typeof configuration !== "object") {
        throw new Error("The configuration must be a JSON object.");
      }
      await api<StrategyVersion>(`/pages/${pageId}/strategies/${selectedId}/versions`, {
        method: "POST", body: JSON.stringify({ configuration }),
      });
      await loadVersions(pageId, selectedId);
      setNotice("New draft version saved. Previous versions were preserved.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save version."); }
    finally { setBusy(false); }
  }

  const selected = strategies.find((item) => item.id === selectedId) ?? null;

  return (
    <AppShell active="strategies">
    <main className="min-h-screen bg-transparent text-slate-100">
      <div className="mx-auto max-w-7xl px-5 py-8 md:px-10 md:py-12">
        <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold tracking-[0.28em] text-cyan-400">AI REEL FACTORY · M3</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">Content strategies</h1>
            <p className="mt-2 text-sm text-slate-400">Build a distinct, versioned content playbook for every Page.</p>
          </div>
          <span className="rounded-full border border-cyan-400/20 bg-cyan-400/5 px-3 py-2 text-[11px] text-cyan-200">PAGE PLAYBOOKS</span>
        </header>

        {error && <div role="alert" className="mb-5 rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
        {notice && <div role="status" className="mb-5 rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200">{notice}</div>}

        <section className="mb-6 rounded-2xl border border-white/10 bg-white/[0.035] p-5">
          <label className="mb-2 block text-xs font-medium text-slate-400" htmlFor="page-select">Choose a Page workspace</label>
          {loading ? <LoadingSkeleton rows={2} /> : pages.length === 0 ? <p className="text-sm text-slate-400">Create a Page workspace first.</p> :
            <select id="page-select" value={pageId} onChange={(e) => { setPageId(Number(e.target.value)); setSelectedId(null); setVersions([]); }} className="field max-w-md">
              {pages.map((page) => <option key={page.id} value={page.id}>{page.name}{page.is_active ? "" : " · Paused"}</option>)}
            </select>}
        </section>

        {pageId !== "" && <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
          <div className="space-y-5">
            <section className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
              <h2 className="text-lg font-semibold">Create a strategy</h2>
              <p className="mt-1 text-xs text-slate-500">Start with a baseline playbook. Refine it through new versions.</p>
              <form onSubmit={createStrategy} className="mt-4 space-y-3">
                <input required maxLength={120} value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="e.g. Science explainers" className="field" />
                <textarea maxLength={1000} rows={3} value={newDescription} onChange={(e) => setNewDescription(e.target.value)} placeholder="What is this strategy designed to achieve?" className="field" />
                <button disabled={busy} className="rounded-xl bg-cyan-300 px-4 py-2.5 text-sm font-semibold text-slate-950 disabled:opacity-50">{busy ? "Saving..." : "Create strategy +"}</button>
              </form>
            </section>

            <section className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
              <div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-semibold">Strategies</h2><span className="text-xs text-slate-500">{strategies.length} total</span></div>
              {strategies.length === 0 ? <p className="rounded-xl border border-dashed border-white/10 p-5 text-center text-sm text-slate-500">No strategies for this Page yet.</p> :
                <div className="space-y-2">{strategies.map((item) => <button key={item.id} onClick={() => void selectStrategy(item)} className={`w-full rounded-xl border p-4 text-left transition ${selectedId === item.id ? "border-cyan-400/40 bg-cyan-400/10" : "border-white/10 bg-[#0b1220] hover:border-white/20"}`}>
                  <div className="flex items-center justify-between gap-3"><span className="font-medium">{item.name}</span><span className={`rounded-full px-2 py-1 text-[10px] uppercase tracking-wide ${item.status === "active" ? "bg-emerald-400/10 text-emerald-300" : "bg-white/5 text-slate-400"}`}>{item.status}</span></div>
                  <p className="mt-1 line-clamp-2 text-xs text-slate-500">{item.description || "No description yet."}</p>
                </button>)}</div>}
            </section>
          </div>

          <div className="space-y-5">
            {!selected ? <section className="flex min-h-64 items-center justify-center rounded-2xl border border-dashed border-white/10 p-8 text-center"><div><p className="font-medium">Select a strategy</p><p className="mt-2 text-sm text-slate-500">Its settings, version history and controls will appear here.</p></div></section> :
              <>
                <section className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
                  <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-semibold tracking-widest text-cyan-300">STRATEGY SETTINGS</p><h2 className="mt-1 text-lg font-semibold">{selected.name}</h2></div><div className="flex flex-wrap gap-2">
                    <button disabled={busy} onClick={() => void setStatus("active")} className="rounded-lg border border-emerald-400/20 px-3 py-2 text-xs text-emerald-300 hover:bg-emerald-400/10">Activate</button>
                    <button disabled={busy} onClick={() => void setStatus("paused")} className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 hover:bg-white/5">Pause</button>
                    <button disabled={busy} onClick={() => void setStatus("archived")} className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-400 hover:bg-white/5">Archive</button>
                  </div></div>
                  <form onSubmit={saveMetadata} className="space-y-3">
                    <label className="block"><span className="mb-2 block text-xs text-slate-400">Name</span><input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} className="field" /></label>
                    <label className="block"><span className="mb-2 block text-xs text-slate-400">Description</span><textarea rows={3} maxLength={1000} value={description} onChange={(e) => setDescription(e.target.value)} className="field" /></label>
                    <button disabled={busy} className="rounded-lg border border-cyan-400/30 px-4 py-2 text-xs text-cyan-200 hover:bg-cyan-400/10">Save details</button>
                  </form>
                </section>

                <section className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
                  <div className="mb-3"><p className="text-xs font-semibold tracking-widest text-cyan-300">IMMUTABLE CONFIGURATION</p><h2 className="mt-1 text-lg font-semibold">Create a new version</h2><p className="mt-1 text-xs text-slate-500">Edit the JSON and save. Existing versions remain unchanged.</p></div>
                  <form onSubmit={createVersion} className="space-y-3">
                    <textarea spellCheck={false} value={versionJson} onChange={(e) => setVersionJson(e.target.value)} rows={18} className="w-full rounded-xl border border-white/10 bg-[#080d18] p-4 font-mono text-xs leading-6 text-cyan-100 outline-none focus:border-cyan-400/50" />
                    <div className="flex flex-wrap items-center justify-between gap-3"><span className="text-xs text-slate-500">Next version: v{(versions[versions.length - 1]?.version_number ?? 0) + 1}</span><button disabled={busy} className="rounded-xl bg-cyan-300 px-4 py-2.5 text-sm font-semibold text-slate-950 disabled:opacity-50">Save new version</button></div>
                  </form>
                </section>

                <section className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
                  <h2 className="mb-3 text-lg font-semibold">Version history</h2>
                  {versions.length === 0 ? <p className="text-sm text-slate-500">No versions found.</p> : <div className="space-y-2">{[...versions].reverse().map((version) => <div key={version.id} className="flex items-center justify-between rounded-xl border border-white/10 bg-[#0b1220] px-4 py-3"><div><p className="text-sm font-medium">Version {version.version_number}</p><p className="mt-1 text-xs text-slate-500">{new Date(version.created_at).toLocaleString()}</p></div><span className="rounded-full bg-amber-400/10 px-2 py-1 text-[10px] uppercase text-amber-300">{version.status}</span></div>)}</div>}
                </section>
              </>}
          </div>
        </div>}
        <footer className="mt-12 border-t border-white/10 pt-5 text-xs text-slate-600">AI Reel Factory · Each Page owns its own strategy and immutable configuration history.</footer>
      </div>
    </main>
    </AppShell>
  );
}
