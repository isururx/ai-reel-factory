"use client";

import AppShell from "@/components/AppShell";
import { authenticatedFetch } from "@/lib/supabase";
import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

type Metric = { reactions_count: number | null; comments_count: number | null; shares_count: number | null; captured_at: string; available_fields: string[] };
type Post = { id: number; external_post_id: string; message: string; permalink_url: string | null; media_type: string | null; created_time: string | null; latest_metrics: Metric | null; interaction_count: number | null; performance_score: number | null };
type CollectResult = { reference_page_id: number; status: string; collected_posts: number; updated_posts: number; message: string };

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await authenticatedFetch(`${API}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers }, cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail ?? `Request failed (${response.status})`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return response.json();
}

export default function ReferencePostsPage() {
  const params = useParams<{ referenceId: string }>();
  const search = useSearchParams();
  const referenceId = Number(params.referenceId);
  const pageId = Number(search.get("pageId"));
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadPosts = useCallback(async () => {
    if (!Number.isInteger(pageId) || !Number.isInteger(referenceId)) return;
    setPosts(await api<Post[]>(`/pages/${pageId}/references/${referenceId}/posts`));
  }, [pageId, referenceId]);

  useEffect(() => {
    void loadPosts().catch((e) => setError(e instanceof Error ? e.message : "Could not load posts.")).finally(() => setLoading(false));
  }, [loadPosts]);

  async function collect() {
    setCollecting(true); setError(""); setNotice("");
    try {
      const result = await api<CollectResult>(`/pages/${pageId}/references/${referenceId}/collect?limit=25`, { method: "POST" });
      await loadPosts();
      setNotice(`Collection complete: ${result.collected_posts} new posts, ${result.updated_posts} updated.`);
    } catch (e) { setError(e instanceof Error ? e.message : "Collection failed."); }
    finally { setCollecting(false); }
  }

  const totalInteractions = posts.reduce((sum, post) => sum + (post.interaction_count ?? 0), 0);

  return (
    <AppShell active="references">
      <main className="min-h-screen bg-transparent text-slate-100">
        <div className="mx-auto max-w-7xl px-5 py-8 md:px-10 md:py-12">
          <a href="/references" className="text-sm text-cyan-300 hover:text-cyan-200">← Back to references</a>
          <header className="mt-5 mb-8 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs font-semibold tracking-[0.28em] text-cyan-400">CONTENT INTELLIGENCE · R2</p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">Reference posts</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">Collect permitted public post metadata and available interaction counts. No third-party video files are downloaded.</p>
              <a href={`/references/${referenceId}/videos?pageId=${pageId}`} className="mt-3 inline-flex rounded-lg border border-cyan-300/20 px-3 py-2 text-xs font-semibold text-cyan-200 hover:bg-cyan-300/10">Open video library →</a>
            </div>
            <button onClick={() => void collect()} disabled={collecting || !pageId || !referenceId} className="rounded-xl bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-200 disabled:opacity-50">{collecting ? "Collecting…" : "Collect latest posts"}</button>
          </header>

          {error && <div role="alert" className="mb-5 rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
          {notice && <div role="status" className="mb-5 rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200">{notice}</div>}

          <div className="mb-7 grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5"><p className="text-xs text-slate-500">Collected posts</p><p className="mt-2 text-3xl font-semibold">{posts.length}</p></div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5"><p className="text-xs text-slate-500">Known interactions</p><p className="mt-2 text-3xl font-semibold">{totalInteractions.toLocaleString()}</p></div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5"><p className="text-xs text-slate-500">Ranking method</p><p className="mt-2 text-lg font-semibold">Page median index</p></div>
          </div>

          <div className="mb-6 rounded-xl border border-amber-400/15 bg-amber-400/[0.04] p-4 text-xs leading-5 text-amber-100/80">
            Performance index compares available reactions + comments + shares with the median of this reference Page's collected posts. It is not an engagement rate: competitor reach, impressions and watch time are not assumed to be available.
          </div>

          {loading ? <p className="py-12 text-center text-sm text-slate-500">Loading reference posts…</p> : posts.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 p-12 text-center"><p className="font-medium">No posts collected yet</p><p className="mt-2 text-sm text-slate-500">Connect approved Meta access on the backend, then collect posts from this reference.</p></div>
          ) : (
            <div className="space-y-3">
              {posts.map((post) => (
                <article key={post.id} className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-xs text-slate-500"><span>{post.media_type || "Post"}</span><span>·</span><span>{post.created_time ? new Date(post.created_time).toLocaleString() : "Date unavailable"}</span></div>
                    <span className="rounded-lg border border-cyan-300/20 px-3 py-1.5 text-xs text-cyan-200">{post.performance_score == null ? "Not ranked" : `${post.performance_score} index`}</span>
                  </div>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-200">{post.message || "No caption returned by Meta."}</p>
                  <div className="mt-4 flex flex-wrap gap-4 text-xs text-slate-400">
                    <span>Reactions: {post.latest_metrics?.reactions_count ?? "—"}</span>
                    <span>Comments: {post.latest_metrics?.comments_count ?? "—"}</span>
                    <span>Shares: {post.latest_metrics?.shares_count ?? "—"}</span>
                    <span className="font-semibold text-slate-200">Known interactions: {post.interaction_count ?? "—"}</span>
                  </div>
                  <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-3 text-xs text-slate-600">
                    <span>Snapshot: {post.latest_metrics ? new Date(post.latest_metrics.captured_at).toLocaleString() : "None"}</span>
                    {post.permalink_url && <a href={post.permalink_url} target="_blank" rel="noreferrer" className="text-cyan-300 hover:text-cyan-200">Open original post ↗</a>}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </main>
    </AppShell>
  );
}
