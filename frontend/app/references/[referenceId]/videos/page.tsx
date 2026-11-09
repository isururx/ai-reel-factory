"use client";

import AppShell from "@/components/AppShell";
import { authenticatedFetch } from "@/lib/supabase";
import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";

type Video = {
  id: number; title: string; source_url: string | null; original_filename: string;
  content_type: string; file_size: number; views_count: number | null;
  reactions_count: number | null; shares_count: number | null; comments_count: number | null;
  manual_comments: string[]; analysis_status: string;
  created_at: string; analysis_result: Record<string, any>;
};
const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await authenticatedFetch(`${API}${path}`, { ...init, cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return response.json();
}

export default function ReferenceVideosPage() {
  const params = useParams<{ referenceId: string }>();
  const search = useSearchParams();
  const referenceId = Number(params.referenceId);
  const pageId = Number(search.get("pageId"));
  const [videos, setVideos] = useState<Video[]>([]);
  const [mode, setMode] = useState<"upload" | "facebook">("upload");
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [views, setViews] = useState("");
  const [reactions, setReactions] = useState("");
  const [shares, setShares] = useState("");
  const [commentsCount, setCommentsCount] = useState("");
  const [commentsText, setCommentsText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [analyzingId, setAnalyzingId] = useState<number | null>(null);

  const base = `/pages/${pageId}/references/${referenceId}/videos`;
  const load = useCallback(async () => {
    if (!pageId || !referenceId) return;
    setVideos(await request<Video[]>(base));
  }, [base, pageId, referenceId]);

  useEffect(() => { void load().catch(e => setError(e.message)); }, [load]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    const form = new FormData();
    form.set("title", title || "Reference video");
    if (views !== "") form.set("views_count", views);
    if (reactions !== "") form.set("reactions_count", reactions);
    if (shares !== "") form.set("shares_count", shares);
    if (commentsCount !== "") form.set("comments_count", commentsCount);
    form.set("manual_comments_json", JSON.stringify(commentsText.split("\n").map(x => x.trim()).filter(Boolean)));
    try {
      if (mode === "upload") {
        if (!file) throw new Error("Choose a video file first.");
        form.set("file", file);
        await request<Video>(base, { method: "POST", body: form });
      } else {
        if (!url.trim()) throw new Error("Enter a public Facebook video URL.");
        form.set("url", url.trim());
        await request<Video>(`${base}/import-facebook`, { method: "POST", body: form });
      }
      setFile(null); setUrl(""); setTitle(""); setViews(""); setReactions(""); setShares(""); setCommentsCount(""); setCommentsText("");
      await load();
      setNotice("Video saved to this reference workspace.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save the video."); }
    finally { setBusy(false); }
  }

  async function analyzeVideo(id: number) {
    setAnalyzingId(id); setError(""); setNotice("");
    try {
      await request<Video>(`${base}/${id}/analyze`, { method: "POST" });
      await load();
      setNotice("AI analysis completed. Review the findings before using them as creative guidance.");
    } catch (e) { setError(e instanceof Error ? e.message : "Video analysis failed."); await load(); }
    finally { setAnalyzingId(null); }
  }

  async function openVideo(id: number) {
    try {
      const result = await request<{url: string}>(`${base}/${id}/file`);
      window.open(result.url, "_blank", "noopener,noreferrer");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not open video."); }
  }

  return (
    <AppShell active="references">
      <main className="min-h-screen text-slate-100">
        <div className="mx-auto max-w-6xl px-5 py-8 md:px-10 md:py-12">
          <a href={`/references/${referenceId}?pageId=${pageId}`} className="text-sm text-cyan-300">← Back to reference posts</a>
          <header className="my-6">
            <p className="text-xs font-semibold tracking-[0.25em] text-cyan-400">REFERENCE INTELLIGENCE · VIDEO INGESTION</p>
            <h1 className="mt-3 text-3xl font-semibold">Reference video library</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">Upload a video you are permitted to use, or import a publicly accessible Facebook video. Store engagement figures and audience comments manually.</p>
          </header>
          {error && <div role="alert" className="mb-4 rounded-xl border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-200">{error}</div>}
          {notice && <div role="status" className="mb-4 rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-3 text-sm text-emerald-200">{notice}</div>}

          <form onSubmit={submit} className="space-y-5 rounded-2xl border border-white/10 bg-white/[0.035] p-5 md:p-7">
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={() => setMode("upload")} className={mode === "upload" ? "rounded-lg bg-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950" : "rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-300"}>Upload a file</button>
              <button type="button" onClick={() => setMode("facebook")} className={mode === "facebook" ? "rounded-lg bg-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950" : "rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-300"}>Import public Facebook video</button>
            </div>
            {mode === "upload" ? <label className="block text-sm text-slate-300">Video file (MP4, WebM, MOV or MKV; maximum 300 MB)<input key="upload-file" required type="file" accept="video/mp4,video/webm,video/quicktime,video/x-matroska" onChange={e => setFile(e.target.files?.[0] ?? null)} className="mt-2 block w-full rounded-xl border border-white/10 bg-slate-950 p-3 text-sm" /></label> : <label className="block text-sm text-slate-300">Public Facebook video / Reel URL<input key="facebook-url" required type="url" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://www.facebook.com/..." className="field mt-2" /></label>}
            <label className="block text-sm text-slate-300">Display title<input value={title} onChange={e => setTitle(e.target.value)} placeholder="Optional video title" className="field mt-2" /></label>

            <section className="border-t border-white/10 pt-5">
              <h2 className="font-semibold">Manual engagement data</h2>
              <p className="mt-1 text-xs leading-5 text-slate-500">Enter values from your own observation or permitted sources. These values are not fetched or verified by the system. Leave unknown fields blank.</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {[[views,setViews,"Views"],[reactions,setReactions,"Reactions"],[shares,setShares,"Shares"],[commentsCount,setCommentsCount,"Comment count"]].map(([value,setter,label]) => <label key={label as string} className="text-xs text-slate-400">{label as string}<input type="number" min="0" value={value as string} onChange={e => (setter as (v:string)=>void)(e.target.value)} className="field mt-2" /></label>)}
              </div>
            </section>
            <label className="block text-sm text-slate-300">Manually entered audience comments <span className="text-xs text-slate-500">(one comment per line)</span><textarea value={commentsText} onChange={e => setCommentsText(e.target.value)} rows={5} placeholder="This is so interesting!&#10;Can you explain how this works?" className="field mt-2" /></label>
            <button disabled={busy} className="rounded-xl bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50">{busy ? "Saving video…" : mode === "upload" ? "Upload to reference library" : "Download and save to reference library"}</button>
          </form>

          <section className="mt-9">
            <div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-semibold">Saved videos</h2><span className="text-xs text-slate-500">{videos.length} videos</span></div>
            {videos.length === 0 ? <div className="rounded-2xl border border-dashed border-white/10 p-10 text-center text-sm text-slate-500">No reference videos uploaded yet.</div> : <div className="grid gap-3 md:grid-cols-2">{videos.map(video => <article key={video.id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-5"><div className="flex items-start justify-between gap-3"><div><h3 className="font-semibold">{video.title}</h3><p className="mt-1 text-xs text-slate-500">{video.original_filename} · {(video.file_size / 1024 / 1024).toFixed(1)} MB</p></div><span className="rounded-lg border border-amber-300/20 px-2 py-1 text-xs text-amber-200">Analysis: {video.analysis_status}</span></div><div className="mt-4 grid grid-cols-2 gap-2 text-xs text-slate-400"><span>Views: {video.views_count ?? "—"}</span><span>Reactions: {video.reactions_count ?? "—"}</span><span>Shares: {video.shares_count ?? "—"}</span><span>Comments: {video.comments_count ?? "—"}</span></div><p className="mt-3 text-xs text-slate-500">{video.manual_comments.length} manually entered comments</p><div className="mt-4 flex flex-wrap gap-4"><button disabled={analyzingId === video.id} onClick={() => void analyzeVideo(video.id)} className="text-sm font-semibold text-cyan-300 disabled:opacity-50">{analyzingId === video.id ? "Analyzing video…" : video.analysis_status === "completed" ? "Re-analyze video" : "Run AI analysis"}</button><button onClick={() => void openVideo(video.id)} className="text-sm font-semibold text-slate-300">Open stored video ↗</button></div>{video.analysis_status === "completed" && video.analysis_result && <div className="mt-4 space-y-3 rounded-xl border border-cyan-300/15 bg-cyan-300/[0.04] p-4"><div><p className="text-xs font-semibold uppercase tracking-wider text-cyan-300">AI creative analysis</p><p className="mt-1 text-sm text-slate-200">{video.analysis_result.summary}</p></div>{video.analysis_result.hook && <p className="text-xs text-slate-400"><strong className="text-slate-200">Hook:</strong> {video.analysis_result.hook.description} · {video.analysis_result.hook.strength}</p>}{Array.isArray(video.analysis_result.reusable_patterns) && <div><p className="text-xs font-semibold text-slate-200">Reusable creative patterns</p><ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-400">{video.analysis_result.reusable_patterns.slice(0,3).map((item: any, index: number) => <li key={index}>{item.pattern} — {item.adaptation_idea}</li>)}</ul></div>}<p className="text-[11px] text-amber-200">Saved as Page-specific insights pending human review. These are AI interpretations, not verified performance claims.</p></div>}</article>)}</div>}
          </section>
        </div>
      </main>
    </AppShell>
  );
}
