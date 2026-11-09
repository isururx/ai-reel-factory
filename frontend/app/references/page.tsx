"use client";

import AppShell, { LoadingSkeleton } from "@/components/AppShell";
import { authenticatedFetch } from "@/lib/supabase";
import { useCallback, useEffect, useState, type FormEvent } from "react";

type Page = { id: number; name: string; is_active: boolean };
type ReferencePage = {
  id: number;
  page_id: number;
  platform: "facebook";
  source_url: string;
  normalized_url: string;
  display_name: string | null;
  notes: string;
  status: "active" | "paused";
  created_at: string;
  updated_at: string;
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
  if (response.status === 204) return undefined as T;
  return response.json();
}

export default function ReferencesPage() {
  const [pages, setPages] = useState<Page[]>([]);
  const [pageId, setPageId] = useState<number | "">("");
  const [references, setReferences] = useState<ReferencePage[]>([]);
  const [url, setUrl] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadPages = useCallback(async () => {
    const result = await api<Page[]>("/pages");
    setPages(result);
    if (result.length && pageId === "") setPageId(result[0].id);
  }, [pageId]);

  const loadReferences = useCallback(async (id: number) => {
    setReferences(await api<ReferencePage[]>(`/pages/${id}/references`));
  }, []);

  useEffect(() => {
    void (async () => {
      setLoading(true);
      try { await loadPages(); }
      catch (e) { setError(e instanceof Error ? e.message : "Could not load Page workspaces."); }
      finally { setLoading(false); }
    })();
  }, [loadPages]);

  useEffect(() => {
    if (pageId === "") { setReferences([]); return; }
    setError("");
    void loadReferences(pageId).catch((e) => setError(e instanceof Error ? e.message : "Could not load reference Pages."));
  }, [pageId, loadReferences]);

  async function addReference(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pageId === "") return;
    setSaving(true); setError(""); setNotice("");
    try {
      await api<ReferencePage>(`/pages/${pageId}/references`, {
        method: "POST",
        body: JSON.stringify({
          source_url: url.trim(),
          display_name: displayName.trim() || null,
          notes: notes.trim(),
        }),
      });
      setUrl(""); setDisplayName(""); setNotes("");
      await loadReferences(pageId);
      setNotice("Reference Page saved to this workspace.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save this reference Page.");
    } finally { setSaving(false); }
  }

  async function toggleStatus(item: ReferencePage) {
    if (pageId === "") return;
    setBusyId(item.id); setError(""); setNotice("");
    try {
      await api<ReferencePage>(`/pages/${pageId}/references/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: item.status === "active" ? "paused" : "active" }),
      });
      await loadReferences(pageId);
      setNotice(item.status === "active" ? "Reference paused." : "Reference activated.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not update this reference."); }
    finally { setBusyId(null); }
  }

  async function deleteReference(item: ReferencePage) {
    if (pageId === "" || !window.confirm(`Remove "${item.display_name || item.normalized_url}" from this workspace?`)) return;
    setBusyId(item.id); setError(""); setNotice("");
    try {
      await api<void>(`/pages/${pageId}/references/${item.id}`, { method: "DELETE" });
      await loadReferences(pageId);
      setNotice("Reference Page removed.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not remove this reference."); }
    finally { setBusyId(null); }
  }

  return (
    <AppShell active="references">
      <main className="min-h-screen bg-transparent text-slate-100">
        <div className="mx-auto max-w-7xl px-5 py-8 md:px-10 md:py-12">
          <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold tracking-[0.28em] text-cyan-400">CONTENT INTELLIGENCE · R1</p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">Reference Intelligence</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">Build a separate reference library for each of your content brands by saving public Facebook Page links.</p>
            </div>
            <span className="rounded-full border border-cyan-400/20 bg-cyan-400/5 px-3 py-2 text-[11px] text-cyan-200">SOURCE REGISTRY</span>
          </header>

          {error && <div role="alert" className="mb-5 rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
          {notice && <div role="status" className="mb-5 rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200">{notice}</div>}

          <section className="mb-6 rounded-2xl border border-white/10 bg-white/[0.035] p-5 md:p-6">
            <label htmlFor="reference-page-workspace" className="mb-2 block text-xs font-medium text-slate-400">Save references under your Page workspace</label>
            {loading ? <LoadingSkeleton rows={2} /> : pages.length === 0 ? (
              <p className="text-sm text-amber-200">Create a Page workspace first, then add its reference Pages.</p>
            ) : (
              <select id="reference-page-workspace" value={pageId} onChange={(e) => setPageId(Number(e.target.value))} className="field max-w-lg">
                {pages.map((page) => <option key={page.id} value={page.id}>{page.name}{page.is_active ? "" : " · Paused"}</option>)}
              </select>
            )}
          </section>

          {pageId !== "" && (
            <>
              <section className="mb-6 rounded-2xl border border-white/10 bg-white/[0.035] p-5 md:p-6">
                <div className="mb-5">
                  <p className="text-xs font-semibold tracking-widest text-cyan-300">ADD A REFERENCE SOURCE</p>
                  <h2 className="mt-2 text-xl font-semibold">Add a public Facebook Page</h2>
                  <p className="mt-1 text-sm leading-6 text-slate-400">Paste the Page's main URL, not an individual Reel, post, group or video link.</p>
                </div>
                <form onSubmit={addReference} className="space-y-3">
                  <input required type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://www.facebook.com/NASA" className="field" />
                  <div className="grid gap-3 md:grid-cols-2">
                    <input maxLength={160} value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Display name (optional)" className="field" />
                    <input maxLength={2000} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Why is this Page relevant? (optional)" className="field" />
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                    <span className="text-xs text-slate-500">One reference list per workspace · duplicates are blocked</span>
                    <button disabled={saving} className="rounded-xl bg-cyan-300 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:opacity-50">{saving ? "Saving..." : "Save reference +"}</button>
                  </div>
                </form>
              </section>

              <section>
                <div className="mb-4 flex items-end justify-between gap-3">
                  <div><h2 className="text-xl font-semibold">Saved reference Pages</h2><p className="mt-1 text-sm text-slate-500">These sources are kept separate for the selected workspace.</p></div>
                  <span className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-400">{references.length} saved</span>
                </div>
                {references.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-white/10 p-10 text-center">
                    <p className="font-medium">No reference Pages yet</p>
                    <p className="mt-2 text-sm text-slate-500">Add a public Facebook Page above to start building this brand's reference library.</p>
                  </div>
                ) : (
                  <div className="grid gap-4 lg:grid-cols-2">
                    {references.map((item) => (
                      <article key={item.id} className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="mb-2 flex items-center gap-2">
                              <span className={`h-2 w-2 rounded-full ${item.status === "active" ? "bg-emerald-400" : "bg-slate-500"}`} />
                              <span className={`text-xs ${item.status === "active" ? "text-emerald-300" : "text-slate-500"}`}>{item.status}</span>
                              <span className="text-xs text-slate-600">· Facebook</span>
                            </div>
                            <h3 className="truncate text-lg font-semibold">{item.display_name || "Unnamed reference Page"}</h3>
                            <a href={item.normalized_url} target="_blank" rel="noreferrer" className="mt-1 block break-all text-xs text-cyan-300 hover:text-cyan-200">{item.normalized_url} ↗</a>
                          </div>
                          <span className="shrink-0 rounded-lg border border-white/10 px-2.5 py-1.5 text-xs text-slate-500">#{item.id}</span>
                        </div>
                        {item.notes && <p className="mt-4 rounded-xl border border-white/5 bg-[#0b1220] px-3 py-2.5 text-xs leading-5 text-slate-400">{item.notes}</p>}
                        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-4">
                          <span className="text-[11px] text-slate-600">Added {new Date(item.created_at).toLocaleDateString()}</span>
                          <div className="flex gap-2">
                            <button disabled={busyId === item.id} onClick={() => void toggleStatus(item)} className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 hover:bg-white/5 disabled:opacity-50">{item.status === "active" ? "Pause" : "Activate"}</button>
                            <button disabled={busyId === item.id} onClick={() => void deleteReference(item)} className="rounded-lg px-3 py-2 text-xs text-rose-300 hover:bg-rose-400/10 disabled:opacity-50">Remove</button>
                          </div>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </>
          )}

          <section className="mt-8 rounded-2xl border border-amber-400/15 bg-amber-400/[0.04] p-5">
            <p className="text-xs font-semibold tracking-widest text-amber-200">IMPORTANT · THIS IS R1 ONLY</p>
            <p className="mt-2 text-sm leading-6 text-slate-400">At this stage, AI Reel Factory only stores and organizes the links you provide. It does not access Facebook, collect posts, download videos, or read engagement metrics. Meta API access and permission review can be connected in a later stage.</p>
          </section>
          <footer className="mt-12 border-t border-white/10 pt-5 text-xs text-slate-600">AI Reel Factory · Reference sources are organized per Page workspace and are not yet analyzed.</footer>
        </div>
      </main>
    </AppShell>
  );
}
