"use client";

import AppShell, { GenerationOverlay } from "@/components/AppShell";
import { authenticatedFetch } from "@/lib/supabase";
import BatchStudio from "@/components/BatchStudio";
import { useCallback, useEffect, useMemo, useState } from "react";

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
    edited_by_human?: boolean;
    batch_id?: number;
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
type EditorState = { title: string; hook: string; narration: string; caption: string; hashtags: string };

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
const emptyEditor: EditorState = { title: "", hook: "", narration: "", caption: "", hashtags: "" };

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

function words(value: string) {
  return value.trim() ? value.trim().split(/\s+/).length : 0;
}

function editorFrom(script: ContentScript): EditorState {
  const latest = [...script.versions].sort((a, b) => b.version_number - a.version_number)[0];
  return latest ? {
    title: latest.script_data?.title ?? script.title,
    hook: latest.hook,
    narration: latest.narration,
    caption: latest.caption,
    hashtags: (latest.hashtags ?? []).join(" "),
  } : { ...emptyEditor };
}

function statusStyle(status: string) {
  if (status === "approved") return "border-emerald-400/25 bg-emerald-400/10 text-emerald-200";
  if (status === "rejected") return "border-rose-400/25 bg-rose-400/10 text-rose-200";
  return "border-amber-300/20 bg-amber-300/10 text-amber-100";
}

export default function ScriptsPage() {
  const [pages, setPages] = useState<Page[]>([]);
  const [pageId, setPageId] = useState<number | "">("");
  const [scripts, setScripts] = useState<ContentScript[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [editor, setEditor] = useState<EditorState>(emptyEditor);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [decisionBusy, setDecisionBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [brief, setBrief] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [generating, setGenerating] = useState(false);

  const selected = scripts.find((script) => script.id === selectedId) ?? scripts[0] ?? null;
  const latest = useMemo(() => selected ? [...selected.versions].sort((a, b) => b.version_number - a.version_number)[0] : null, [selected]);
  const narrationWords = words(editor.narration);
  const estimatedSeconds = Math.round((narrationWords / 145) * 60);
  const isDirty = Boolean(selected && latest && (
    editor.title !== (latest.script_data?.title ?? selected.title) ||
    editor.hook !== latest.hook ||
    editor.narration !== latest.narration ||
    editor.caption !== latest.caption ||
    editor.hashtags !== (latest.hashtags ?? []).join(" ")
  ));

  const loadScripts = useCallback(async (id: number, preferredId?: number) => {
    const result = await api<ContentScript[]>(`/pages/${id}/scripts`);
    setScripts(result);
    const next = result.find((script) => script.id === preferredId) ?? result[0] ?? null;
    setSelectedId(next?.id ?? null);
    setEditor(next ? editorFrom(next) : { ...emptyEditor });
  }, []);

  useEffect(() => {
    let active = true;
    api<Page[]>("/pages")
      .then((result) => {
        if (!active) return;
        setPages(result);
        if (result.length) setPageId(result[0].id);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load Pages."))
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (pageId === "") {
      setScripts([]);
      setSelectedId(null);
      setEditor({ ...emptyEditor });
      return;
    }
    setLoading(true);
    setError("");
    loadScripts(pageId)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load scripts."))
      .finally(() => setLoading(false));
  }, [pageId, loadScripts]);

  async function generateScript() {
    if (pageId === "" || brief.trim().length < 20) { setError("Choose a Page and enter a brief with at least 20 characters."); return; }
    setGenerating(true); setError(""); setNotice("");
    try {
      const created = await api<ContentScript>("/pages/" + pageId + "/scripts/generate", { method: "POST", body: JSON.stringify({ brief: brief.trim(), source_url: sourceUrl.trim() || null }) });
      setBrief(""); setSourceUrl(""); await loadScripts(pageId, created.id); setNotice("Your script has been generated. Review and edit it before approval.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not generate your script."); }
    finally { setGenerating(false); }
  }

  function chooseScript(script: ContentScript) {
    setSelectedId(script.id);
    setEditor(editorFrom(script));
    setError("");
    setNotice("");
  }

  function updateField<K extends keyof EditorState>(key: K, value: EditorState[K]) {
    setEditor((current) => ({ ...current, [key]: value }));
  }

  async function saveDraft() {
    if (!selected) return;
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const saved = await api<ScriptVersion>(
        `/pages/${selected.page_id}/scripts/${selected.id}/versions`,
        {
          method: "POST",
          body: JSON.stringify({
            title: editor.title.trim(),
            hook: editor.hook.trim(),
            narration: editor.narration.trim(),
            caption: editor.caption.trim(),
            hashtags: editor.hashtags.split(/\s+/).map((tag) => tag.trim()).filter(Boolean).slice(0, 20),
          }),
        },
      );
      await loadScripts(selected.page_id, selected.id);
      setNotice(`Your edits are saved as version ${saved.version_number}. Review it before approval.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save your edits.");
    } finally {
      setSaving(false);
    }
  }

  async function decide(decision: "approved" | "rejected") {
    if (!selected || !latest) return;
    if (isDirty) {
      setError("Save your edits before making an approval decision.");
      return;
    }
    setDecisionBusy(true);
    setError("");
    setNotice("");
    try {
      await api<ContentScript>(
        `/pages/${selected.page_id}/scripts/${selected.id}/versions/${latest.id}/decision`,
        { method: "POST", body: JSON.stringify({ decision, comments: "" }) },
      );
      await loadScripts(selected.page_id, selected.id);
      setNotice(decision === "approved" ? "Script approved. This exact version is ready for production." : "Script rejected. You can edit it and save a new version.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the review decision.");
    } finally {
      setDecisionBusy(false);
    }
  }

  const evaluation = latest?.script_data?.evaluation;
  const refreshScripts = useCallback(() => {
    if (pageId === "") return;
    void api<ContentScript[]>(`/pages/${pageId}/scripts`).then(setScripts).catch((e) => setError(e instanceof Error ? e.message : "Could not refresh generated scripts."));
  }, [pageId]);

  return (
    <AppShell active="scripts">
      {generating && <GenerationOverlay />}
      <main className="min-h-screen text-slate-100">
        <div className="mx-auto max-w-[1440px] px-4 py-7 sm:px-6 lg:px-10 lg:py-10">
          <header className="mb-8 flex flex-col justify-between gap-5 border-b border-white/[0.08] pb-7 lg:flex-row lg:items-end">
            <div>
              <div className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.25em] text-cyan-300"><span className="h-1.5 w-1.5 rounded-full bg-cyan-300 shadow-[0_0_12px_#55dff2]" /> Editorial workspace</div>
              <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Script studio</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">Generate one script or a full batch. Review, edit and approve each exact version before production.</p>
            </div>
            <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.025] px-4 py-3">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-cyan-300/10 text-lg text-cyan-200">✎</span>
              <div><p className="text-xs font-semibold text-slate-200">Human approval required</p><p className="mt-0.5 text-[11px] text-slate-500">AI output is always a draft</p></div>
            </div>
          </header>

          {error && <div role="alert" className="mb-5 rounded-xl border border-rose-400/25 bg-rose-400/[0.08] px-4 py-3 text-sm text-rose-200">{error}</div>}
          {notice && <div role="status" className="mb-5 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.07] px-4 py-3 text-sm text-emerald-200">{notice}</div>}

          <section className="mb-6 flex flex-col gap-4 rounded-2xl border border-white/10 bg-[#0d1521]/80 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
            <div className="min-w-0">
              <label htmlFor="page-select" className="mb-2 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Working on Page</label>
              <select id="page-select" value={pageId} onChange={(event) => setPageId(event.target.value ? Number(event.target.value) : "")} className="w-full min-w-0 rounded-xl border border-white/10 bg-[#080f19] px-4 py-3 text-sm text-slate-100 outline-none focus:border-cyan-300/50 sm:min-w-[280px]">
                {pages.map((page) => <option key={page.id} value={page.id}>{page.name}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-4 text-xs text-slate-500"><span>{scripts.length} script{scripts.length === 1 ? "" : "s"} in this Page</span><button onClick={() => pageId !== "" && void loadScripts(pageId)} disabled={loading || pageId === ""} className="rounded-lg border border-white/10 px-3 py-2 text-slate-300 hover:bg-white/5 disabled:opacity-40">Refresh ↻</button></div>
          </section>

          <section className="mb-6 rounded-2xl border border-cyan-300/20 bg-[#0d1825] p-5 sm:p-7"><p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-cyan-300">Create directly</p><h2 className="mt-2 text-xl font-semibold text-white">What should this Reel be about?</h2><p className="mt-1 text-sm leading-6 text-slate-400">Describe the topic, angle, key points or story. The AI uses this brief with the selected Page profile and active strategy.</p><textarea value={brief} onChange={(e) => setBrief(e.target.value)} rows={5} maxLength={5000} placeholder="Example: Explain how octopuses change colour to camouflage themselves. Keep it fascinating and accessible, explain the science simply, and finish with an interesting question..." className="mt-4 w-full resize-y rounded-xl border border-white/10 bg-[#080f19] p-4 text-sm leading-7 text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-300/40" /><div className="mt-3 flex flex-col gap-3 sm:flex-row"><input type="url" value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} placeholder="Optional source URL for fact-checking" className="min-w-0 flex-1 rounded-xl border border-white/10 bg-[#080f19] px-4 py-3 text-xs text-slate-300 outline-none focus:border-cyan-300/40" /><button onClick={() => void generateScript()} disabled={generating || loading || pageId === "" || brief.trim().length < 20} className="rounded-xl bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 disabled:opacity-40">{generating ? "Generating..." : "Generate final script ↗"}</button></div><p className="mt-2 text-[10px] text-slate-500">{brief.length}/5000 characters · Minimum 20. Source URL is saved for review and is not automatically fetched.</p></section>

          <BatchStudio pageId={pageId} onScriptsChanged={refreshScripts} />

          {loading ? (
            <div className="grid gap-5 lg:grid-cols-[280px_1fr]"><div className="skeleton-card h-64" /><div className="skeleton-card h-[620px]" /></div>
          ) : !selected ? (
            <section className="rounded-3xl border border-dashed border-white/15 bg-white/[0.015] px-6 py-16 text-center">
              <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl border border-cyan-300/20 bg-cyan-300/[0.06] text-2xl text-cyan-200">✦</div>
              <h2 className="mt-5 text-xl font-semibold">Your next script starts with an idea</h2>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-400">Write a topic or creative brief above and generate your first script directly from this workspace.</p>
              
            </section>
          ) : latest ? (
            <div className="grid items-start gap-5 xl:grid-cols-[270px_minmax(0,1fr)]">
              <aside className="space-y-3">
                <div className="rounded-2xl border border-white/10 bg-[#0d1521]/80 p-4">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Your scripts</p>
                  <div className="mt-3 space-y-2">
                    {scripts.map((script) => {
                      const current = [...script.versions].sort((a, b) => b.version_number - a.version_number)[0];
                      return <button key={script.id} onClick={() => chooseScript(script)} className={`w-full rounded-xl border p-3 text-left transition ${script.id === selected.id ? "border-cyan-300/30 bg-cyan-300/[0.07]" : "border-white/[0.07] bg-white/[0.015] hover:bg-white/[0.04]"}`}>
                        <div className="flex items-center justify-between gap-2"><span className="text-[10px] uppercase tracking-wider text-slate-500">Script #{script.id}{current?.script_data?.batch_id ? ` · Batch #${current.script_data.batch_id}` : ""}</span><span className={`rounded-full border px-2 py-0.5 text-[9px] capitalize ${statusStyle(script.status)}`}>{script.status}</span></div>
                        <p className="mt-2 line-clamp-2 text-sm font-medium leading-5 text-slate-200">{script.title}</p>
                        <p className="mt-2 text-[10px] text-slate-500">Version {current?.version_number ?? 0}</p>
                      </button>;
                    })}
                  </div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-[#0d1521]/80 p-4">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Writing check</p>
                  <div className="mt-4 flex items-end justify-between"><span className="text-sm text-slate-400">Narration length</span><strong className={`text-lg tabular-nums ${narrationWords >= 130 && narrationWords <= 210 ? "text-emerald-300" : "text-amber-200"}`}>{narrationWords}<span className="ml-1 text-xs font-normal text-slate-500">words</span></strong></div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10"><div className={`h-full rounded-full ${narrationWords >= 130 && narrationWords <= 210 ? "bg-emerald-300" : "bg-amber-300"}`} style={{ width: `${Math.min(100, narrationWords / 210 * 100)}%` }} /></div>
                  <div className="mt-4 flex justify-between text-xs"><span className="text-slate-500">Estimated duration</span><span className="font-medium text-slate-300">~{estimatedSeconds}s</span></div>
                  <p className="mt-3 text-[10px] leading-5 text-slate-600">Target: 150–200 narration words (hard range: 130–210) for an approximately 60–90 second Reel.</p>
                </div>
              </aside>

              <section className="overflow-hidden rounded-2xl border border-white/10 bg-[#0d1521]/85">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.08] px-5 py-4 sm:px-7">
                  <div><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-300">Final script draft · v{latest.version_number}</p><p className="mt-1 text-xs text-slate-500">Created {new Date(latest.created_at).toLocaleString()}</p></div>
                  <div className="flex items-center gap-2"><span className={`rounded-full border px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider ${statusStyle(selected.status)}`}>{selected.status}</span>{isDirty && <span className="text-[10px] text-amber-200">Unsaved changes</span>}</div>
                </div>

                <div className="grid gap-0 2xl:grid-cols-[minmax(0,1fr)_260px]">
                  <div className="space-y-5 p-5 sm:p-7">
                    <div><label className="mb-2 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Script title</label><input value={editor.title} onChange={(e) => updateField("title", e.target.value)} className="w-full border-0 border-b border-white/10 bg-transparent px-0 py-2 text-2xl font-semibold tracking-tight text-white outline-none placeholder:text-slate-600 focus:border-cyan-300/50" placeholder="Give this Reel a clear title" /></div>
                    <div className="rounded-xl border border-cyan-300/15 bg-cyan-300/[0.035] p-4"><label className="mb-2 block text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-200">Opening hook</label><textarea value={editor.hook} onChange={(e) => updateField("hook", e.target.value)} rows={2} className="w-full resize-y bg-transparent text-base font-medium leading-7 text-slate-100 outline-none placeholder:text-slate-600" placeholder="The first line that stops the scroll..." /></div>
                    <div><div className="mb-2 flex items-center justify-between gap-3"><label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Voice-over narration</label><span className="text-[10px] text-slate-500">Editable text</span></div><textarea value={editor.narration} onChange={(e) => updateField("narration", e.target.value)} rows={13} className="w-full resize-y rounded-xl border border-white/[0.08] bg-[#080f19] p-4 text-sm leading-7 text-slate-200 outline-none focus:border-cyan-300/35" placeholder="Your complete voice-over script..." /></div>
                    <div><label className="mb-2 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Social caption</label><textarea value={editor.caption} onChange={(e) => updateField("caption", e.target.value)} rows={3} className="w-full resize-y rounded-xl border border-white/[0.08] bg-[#080f19] p-4 text-sm leading-6 text-slate-300 outline-none focus:border-cyan-300/35" placeholder="Write the caption that accompanies this Reel..." /></div>
                    <div><label className="mb-2 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Hashtags</label><input value={editor.hashtags} onChange={(e) => updateField("hashtags", e.target.value)} className="w-full rounded-xl border border-white/[0.08] bg-[#080f19] px-4 py-3 text-sm text-cyan-200 outline-none focus:border-cyan-300/35" placeholder="#science #facts #learn" /><p className="mt-2 text-[10px] text-slate-600">Separate hashtags with spaces. Up to 20 tags are saved.</p></div>
                    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.08] pt-5"><p className="text-[10px] leading-5 text-slate-500">Edits create a new immutable version, so your previous draft remains available in the version history.</p><button onClick={() => void saveDraft()} disabled={saving || !isDirty || !editor.title.trim() || !editor.hook.trim() || !editor.narration.trim()} className="rounded-xl border border-cyan-300/30 bg-cyan-300/10 px-5 py-3 text-xs font-semibold text-cyan-100 hover:bg-cyan-300/15 disabled:cursor-not-allowed disabled:opacity-40">{saving ? "Saving..." : "Save as new version"}</button></div>
                  </div>

                  <aside className="border-t border-white/[0.08] bg-[#0a111b]/65 p-5 sm:p-6 2xl:border-l 2xl:border-t-0">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">AI editorial notes</p>
                    {evaluation ? <><div className="mt-4 space-y-3">{[["Hook", evaluation.hook_score],["Story", evaluation.storytelling_score],["Originality", evaluation.originality_score],["Visual fit", evaluation.visual_suitability_score]].map(([label, score]) => <div key={String(label)}><div className="mb-1 flex justify-between text-xs"><span className="text-slate-400">{label}</span><span className="tabular-nums text-slate-200">{score ?? "—"}/10</span></div><div className="h-1 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-cyan-300" style={{ width: `${Math.max(0, Math.min(10, Number(score) || 0)) * 10}%` }} /></div></div>)}</div>{evaluation.strengths && <p className="mt-5 rounded-xl border border-white/[0.07] bg-white/[0.025] p-3 text-xs leading-5 text-slate-400">{evaluation.strengths}</p>}{evaluation.fact_check_notes && <div className="mt-4 rounded-xl border border-amber-300/15 bg-amber-300/[0.045] p-3"><p className="text-[10px] font-semibold uppercase tracking-wider text-amber-200">Fact-check before approval</p><p className="mt-2 text-xs leading-5 text-amber-100/80">{evaluation.fact_check_notes}</p></div>}</> : <p className="mt-4 text-xs leading-5 text-slate-500">No editorial evaluation was returned for this script.</p>}
                    {latest.script_data?.source_url && <a href={latest.script_data.source_url} target="_blank" rel="noreferrer" className="mt-5 block break-all text-xs text-cyan-300 hover:text-cyan-200">Open original source ↗</a>}
                    <div className="mt-7 border-t border-white/[0.08] pt-5"><p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Final decision</p><p className="mt-2 text-xs leading-5 text-slate-500">Approve only after reviewing the wording and verifying factual claims. Approval applies to the current saved version.</p><button onClick={() => void decide("approved")} disabled={decisionBusy || isDirty || selected.status === "approved"} className="mt-4 w-full rounded-xl bg-emerald-300 px-4 py-3 text-sm font-semibold text-emerald-950 hover:bg-emerald-200 disabled:cursor-not-allowed disabled:opacity-40">{decisionBusy ? "Saving decision..." : selected.status === "approved" ? "✓ Approved" : "Approve final script"}</button><button onClick={() => void decide("rejected")} disabled={decisionBusy || isDirty || selected.status === "rejected"} className="mt-2 w-full rounded-xl border border-rose-300/20 px-4 py-3 text-xs font-semibold text-rose-200 hover:bg-rose-300/[0.06] disabled:cursor-not-allowed disabled:opacity-40">{selected.status === "rejected" ? "Rejected" : "Reject script"}</button>{isDirty && <p className="mt-3 text-[10px] leading-5 text-amber-200">Save your changes as a new version before approving.</p>}</div>
                  </aside>
                </div>
                <div className="border-t border-white/[0.08] bg-white/[0.015] px-5 py-3 text-[10px] text-slate-600 sm:px-7">AI-generated draft · Verify claims against the original source. Approval does not publish the Reel.</div>
              </section>
            </div>
          ) : null}
        </div>
      </main>
    </AppShell>
  );
}
