"use client";

import AppShell, { LoadingSkeleton } from "@/components/AppShell";
import { authenticatedFetch } from "@/lib/supabase";
import { useCallback, useEffect, useState, type FormEvent } from "react";

type Page = { id: number; name: string; is_active: boolean };
type Job = {
  id: number; page_id: number; source_url: string; title: string; status: string;
  queue_position: number | null; reference_video_id: number | null; error_message: string | null;
  views_count: number | null; reactions_count: number | null; shares_count: number | null;
  comments_count: number | null; created_at: string; started_at: string | null; completed_at: string | null;
};
type Queue = { jobs: Job[]; queued_count: number; processing_count: number };
type Video = {
  id: number; page_id: number | null; title: string; source_url: string | null;
  original_filename: string; file_size: number; views_count: number | null;
  reactions_count: number | null; shares_count: number | null; comments_count: number | null;
  manual_comments: string[]; analysis_status: string; analysis_result: Record<string, any>;
  analyzed_at: string | null; created_at: string;
};

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await authenticatedFetch(`${API}${path}`, {
    ...init,
    headers: { ...(init?.body ? { "Content-Type": "application/json" } : {}), ...init?.headers },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail ?? `Request failed (${response.status})`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return response.json();
}

function dateLabel(value: string | null) {
  return value ? new Date(value).toLocaleString() : "Not available";
}

function metric(value: number | null) {
  return value == null ? "—" : value.toLocaleString();
}

export default function ReferencesPage() {
  const [pages, setPages] = useState<Page[]>([]);
  const [pageId, setPageId] = useState<number | "">("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [queuedCount, setQueuedCount] = useState(0);
  const [processingCount, setProcessingCount] = useState(0);
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [views, setViews] = useState("");
  const [reactions, setReactions] = useState("");
  const [shares, setShares] = useState("");
  const [commentsCount, setCommentsCount] = useState("");
  const [commentsText, setCommentsText] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    if (pageId === "") return;
    const [queue, analyzed] = await Promise.all([
      api<Queue>(`/pages/${pageId}/reference-videos/queue`),
      api<Video[]>(`/pages/${pageId}/reference-videos`),
    ]);
    setJobs(queue.jobs);
    setQueuedCount(queue.queued_count);
    setProcessingCount(queue.processing_count);
    setVideos(analyzed);
  }, [pageId]);

  useEffect(() => {
    void (async () => {
      setLoading(true);
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
    if (pageId === "") { setJobs([]); setVideos([]); return; }
    setError("");
    void refresh().catch(e => setError(e instanceof Error ? e.message : "Could not load the analysis queue."));
    const timer = window.setInterval(() => {
      void refresh().catch(e => setError(e instanceof Error ? e.message : "Queue refresh failed."));
    }, 5000);
    return () => window.clearInterval(timer);
  }, [pageId, refresh]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pageId === "") return;
    setSubmitting(true); setError(""); setNotice("");
    try {
      const payload = {
        source_url: url.trim(),
        title: title.trim() || "Reference video",
        views_count: views === "" ? null : Number(views),
        reactions_count: reactions === "" ? null : Number(reactions),
        shares_count: shares === "" ? null : Number(shares),
        comments_count: commentsCount === "" ? null : Number(commentsCount),
        manual_comments: commentsText.split("\n").map(x => x.trim()).filter(Boolean),
        engagement_notes: notes.trim(),
      };
      const job = await api<Job>(`/pages/${pageId}/reference-videos/queue`, {
        method: "POST", body: JSON.stringify(payload),
      });
      setUrl(""); setTitle(""); setViews(""); setReactions(""); setShares("");
      setCommentsCount(""); setCommentsText(""); setNotes("");
      await refresh();
      setNotice(`Video added to the FIFO queue. Queue position: ${job.queue_position ?? "calculating"}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not add this video to the queue.");
    } finally {
      setSubmitting(false);
    }
  }

  async function uploadFallback(jobId: number, file: File) {
    if (pageId === "") return;
    setSubmitting(true); setError(""); setNotice("");
    try {
      const form = new FormData();
      form.append("file", file);
      const response = await authenticatedFetch(`${API}/pages/${pageId}/reference-videos/queue/${jobId}/upload`, {
        method: "POST",
        body: form,
        cache: "no-store",
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        const detail = body?.detail ?? `Upload failed (${response.status})`;
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      await refresh();
      setNotice("Video uploaded successfully. It has returned to the FIFO analysis queue.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not upload the replacement video.");
    } finally {
      setSubmitting(false);
    }
  }

  async function openVideo(videoId: number) {
    try {
      const result = await api<{ url: string }>(`/pages/${pageId}/reference-videos/${videoId}/file`);
      window.open(result.url, "_blank", "noopener,noreferrer");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open stored video.");
    }
  }

  return (
    <AppShell active="references">
      <main className="min-h-screen text-slate-100">
        <div className="mx-auto max-w-7xl px-5 py-8 md:px-10 md:py-12">
          <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold tracking-[0.28em] text-cyan-400">CONTENT INTELLIGENCE · VIDEO ANALYSIS</p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">Reference Intelligence</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">Submit a public Facebook video, add the engagement context you observed, and let the FIFO worker download and analyze it automatically.</p>
            </div>
            <span className="rounded-full border border-cyan-400/20 bg-cyan-400/5 px-3 py-2 text-[11px] text-cyan-200">AUTOMATED VIDEO ANALYSIS</span>
          </header>

          {error && <div role="alert" className="mb-5 rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
          {notice && <div role="status" className="mb-5 rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200">{notice}</div>}

          <section className="mb-6 rounded-2xl border border-white/10 bg-white/[0.035] p-5 md:p-6">
            <label htmlFor="page-workspace" className="mb-2 block text-xs font-medium text-slate-400">Analyze for Page workspace</label>
            {loading ? <LoadingSkeleton rows={2} /> : pages.length === 0 ? (
              <p className="text-sm text-amber-200">Create a Page workspace first.</p>
            ) : (
              <select id="page-workspace" value={pageId} onChange={e => setPageId(Number(e.target.value))} className="field max-w-lg">
                {pages.map(page => <option key={page.id} value={page.id}>{page.name}{page.is_active ? "" : " · Paused"}</option>)}
              </select>
            )}
          </section>

          {pageId !== "" && (
            <>
              <section className="mb-8 rounded-2xl border border-cyan-300/15 bg-white/[0.035] p-5 md:p-7">
                <div className="mb-5">
                  <p className="text-xs font-semibold tracking-widest text-cyan-300">NEW ANALYSIS</p>
                  <h2 className="mt-2 text-xl font-semibold">Submit a Facebook video / Reel</h2>
                  <p className="mt-1 text-sm leading-6 text-slate-400">The video is added to the queue immediately. If Facebook requires login, you can upload a video file you are authorized to use and resume the same analysis job.</p>
                </div>
                <form onSubmit={submit} className="space-y-5">
                  <label className="block text-sm text-slate-300">Public Facebook video URL
                    <input required type="url" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://www.facebook.com/reel/..." className="field mt-2" />
                  </label>
                  <label className="block text-sm text-slate-300">Video title <span className="text-xs text-slate-500">(optional)</span>
                    <input maxLength={200} value={title} onChange={e => setTitle(e.target.value)} placeholder="Auto-detected if left blank" className="field mt-2" />
                  </label>

                  <div className="border-t border-white/10 pt-5">
                    <h3 className="font-semibold">Manual engagement metrics</h3>
                    <p className="mt-1 text-xs leading-5 text-slate-500">Enter figures you observed. Unknown values can stay blank. We keep these separate from verified platform data.</p>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                      <label className="text-xs text-slate-400">Views<input type="number" min="0" value={views} onChange={e => setViews(e.target.value)} className="field mt-2" /></label>
                      <label className="text-xs text-slate-400">Reactions<input type="number" min="0" value={reactions} onChange={e => setReactions(e.target.value)} className="field mt-2" /></label>
                      <label className="text-xs text-slate-400">Shares<input type="number" min="0" value={shares} onChange={e => setShares(e.target.value)} className="field mt-2" /></label>
                      <label className="text-xs text-slate-400">Total comments<input type="number" min="0" value={commentsCount} onChange={e => setCommentsCount(e.target.value)} className="field mt-2" /></label>
                    </div>
                  </div>

                  <label className="block text-sm text-slate-300">Comment samples <span className="text-xs text-slate-500">(one comment per line)</span>
                    <textarea value={commentsText} onChange={e => setCommentsText(e.target.value)} rows={4} placeholder="This is so interesting!&#10;Please make another video about this." className="field mt-2" />
                  </label>
                  <label className="block text-sm text-slate-300">Notes / source of metrics
                    <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2} placeholder="e.g. observed on 9 Nov; counts may change over time" className="field mt-2" />
                  </label>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-xs text-slate-500">If Facebook requires login, the job will pause and offer a manual MP4/video upload instead.</p>
                    <button disabled={submitting} className="rounded-xl bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50">{submitting ? "Adding to queue…" : "Add to analysis queue →"}</button>
                  </div>
                </form>
              </section>

              <section className="mb-9">
                <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
                  <div><p className="text-xs font-semibold tracking-widest text-cyan-300">PROCESSING PIPELINE</p><h2 className="mt-2 text-xl font-semibold">Analysis queue</h2><p className="mt-1 text-sm text-slate-500">First submitted, first processed. Queue refreshes automatically.</p></div>
                  <div className="flex gap-2 text-xs"><span className="rounded-lg border border-amber-300/20 px-3 py-2 text-amber-200">{queuedCount} waiting</span><span className="rounded-lg border border-cyan-300/20 px-3 py-2 text-cyan-200">{processingCount} processing</span></div>
                </div>
                {jobs.length === 0 ? <div className="rounded-2xl border border-dashed border-white/10 p-8 text-center text-sm text-slate-500">No submissions yet. Add a video above to start the queue.</div> : (
                  <div className="space-y-3">
                    {jobs.map(job => <article key={job.id} className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="min-w-0"><p className="truncate text-sm font-semibold">{job.title}</p><a href={job.source_url} target="_blank" rel="noreferrer" className="mt-1 block truncate text-xs text-cyan-300">{job.source_url}</a><p className="mt-1 text-[11px] text-slate-500">Submitted {dateLabel(job.created_at)}</p></div>
                        <span className={`rounded-lg border px-3 py-1.5 text-xs ${job.status === "completed" ? "border-emerald-300/20 text-emerald-200" : job.status === "failed" ? "border-rose-300/20 text-rose-200" : job.status === "processing" ? "border-cyan-300/20 text-cyan-200" : "border-amber-300/20 text-amber-200"}`}>{job.status === "queued" && job.queue_position ? `Queued #${job.queue_position}` : job.status}</span>
                      </div>
                      {job.error_message && <p className="mt-3 text-xs text-rose-200">{job.error_message}</p>}
                      {job.status === "needs_upload" && (
                        <div className="mt-3 rounded-xl border border-amber-300/20 bg-amber-300/5 p-3">
                          <p className="text-xs leading-5 text-amber-100">Facebook requires login for this video. Upload a video file you have permission to use; the original URL and engagement details will be kept.</p>
                          <label className="mt-3 inline-flex cursor-pointer items-center rounded-lg bg-cyan-300 px-3 py-2 text-xs font-semibold text-slate-950">
                            Upload video to continue
                            <input type="file" accept="video/mp4,video/webm,video/quicktime,video/x-matroska" className="sr-only" disabled={submitting} onChange={event => {
                              const selected = event.currentTarget.files?.[0];
                              if (selected) void uploadFallback(job.id, selected);
                              event.currentTarget.value = "";
                            }} />
                          </label>
                          <p className="mt-2 text-[11px] text-slate-500">MP4, WebM, MOV or MKV · maximum 300 MB</p>
                        </div>
                      )}
                      {job.completed_at && <p className="mt-2 text-xs text-emerald-300">Completed {dateLabel(job.completed_at)}</p>}
                    </article>)}
                  </div>
                )}
              </section>

              <section>
                <div className="mb-4 flex items-end justify-between gap-3"><div><p className="text-xs font-semibold tracking-widest text-emerald-300">COMPLETED ANALYSES</p><h2 className="mt-2 text-xl font-semibold">Analyzed videos</h2></div><span className="text-xs text-slate-500">{videos.length} analyzed</span></div>
                {videos.length === 0 ? <div className="rounded-2xl border border-dashed border-white/10 p-8 text-center text-sm text-slate-500">Completed video analyses will appear here.</div> : (
                  <div className="grid gap-4 lg:grid-cols-2">
                    {videos.map(video => <article key={video.id} className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
                      <div className="flex items-start justify-between gap-3"><div className="min-w-0"><h3 className="font-semibold">{video.title}</h3><p className="mt-1 text-xs text-slate-500">{video.original_filename} · {(video.file_size / 1024 / 1024).toFixed(1)} MB</p></div><span className="rounded-lg border border-emerald-300/20 px-2 py-1 text-xs text-emerald-200">Analyzed</span></div>
                      <p className="mt-3 text-xs text-emerald-300">Analysis completed: {dateLabel(video.analyzed_at)}</p>
                      <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-slate-400"><span>Views: {metric(video.views_count)}</span><span>Reactions: {metric(video.reactions_count)}</span><span>Shares: {metric(video.shares_count)}</span><span>Comments: {metric(video.comments_count)}</span></div>
                      <p className="mt-3 text-sm leading-6 text-slate-300">{video.analysis_result?.summary ?? "Analysis summary unavailable."}</p>
                      {video.analysis_result?.hook?.description && <p className="mt-2 text-xs text-slate-400"><strong className="text-slate-200">Hook:</strong> {video.analysis_result.hook.description}</p>}
                      {Array.isArray(video.analysis_result?.reusable_patterns) && <div className="mt-3"><p className="text-xs font-semibold text-slate-200">Reusable patterns</p><ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-400">{video.analysis_result.reusable_patterns.slice(0, 3).map((item: any, index: number) => <li key={index}>{item.pattern} — {item.adaptation_idea}</li>)}</ul></div>}
                      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-4"><span className="text-[11px] text-slate-500">{video.manual_comments.length} comment samples</span><button onClick={() => void openVideo(video.id)} className="text-sm font-semibold text-cyan-300">Open stored video ↗</button></div>
                    </article>)}
                  </div>
                )}
              </section>
            </>
          )}
        </div>
      </main>
    </AppShell>
  );
}
