"use client";

import AuthActions from "@/components/AuthActions";
import { authenticatedFetch } from "@/lib/supabase";
import { useCallback, useEffect, useState, type FormEvent } from "react";

type Page = { id: number; name: string; is_active: boolean };
type TrendItem = {
  id: number;
  source_name: string;
  source_url: string;
  title: string;
  summary: string;
  published_at: string | null;
  collected_at: string;
};
type Recommendation = {
  id: number;
  page_id: number;
  trend_id: number;
  score: number;
  rationale: string;
  status: "suggested" | "saved" | "dismissed" | "selected";
  created_at: string;
  trend: TrendItem;
};

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
type Filter = "suggested" | "saved" | "selected" | "dismissed";

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

function formatDate(value: string | null) {
  if (!value) return "Publication date unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Publication date unavailable" : date.toLocaleString();
}

function scoreTone(score: number) {
  if (score >= 70) return "text-emerald-300 border-emerald-400/20 bg-emerald-400/10";
  if (score >= 40) return "text-amber-200 border-amber-400/20 bg-amber-400/10";
  return "text-slate-300 border-white/10 bg-white/5";
}

export default function TrendsPage() {
  const [pages, setPages] = useState<Page[]>([]);
  const [pageId, setPageId] = useState<number | "">("");
  const [items, setItems] = useState<Recommendation[]>([]);
  const [filter, setFilter] = useState<Filter>("suggested");
  const [feedUrls, setFeedUrls] = useState("https://www.sciencedaily.com/rss/all.xml");
  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadPages = useCallback(async () => {
    const result = await api<Page[]>("/pages");
    setPages(result);
    if (result.length && pageId === "") setPageId(result[0].id);
  }, [pageId]);

  const loadRecommendations = useCallback(async (id: number, selectedFilter: Filter) => {
    const result = await api<Recommendation[]>(
      `/pages/${id}/trends?status_filter=${selectedFilter}&limit=100`
    );
    setItems(result);
  }, []);

  const refresh = useCallback(async () => {
    if (pageId === "") return;
    setError("");
    try {
      await loadRecommendations(pageId, filter);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load recommendations.");
    }
  }, [pageId, filter, loadRecommendations]);

  useEffect(() => {
    void (async () => {
      setLoading(true);
      setError("");
      try {
        await loadPages();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not load Pages.");
      } finally {
        setLoading(false);
      }
    })();
  }, [loadPages]);

  useEffect(() => {
    if (pageId === "") {
      setItems([]);
      return;
    }
    void loadRecommendations(pageId, filter).catch((e) =>
      setError(e instanceof Error ? e.message : "Could not load recommendations.")
    );
  }, [pageId, filter, loadRecommendations]);

  async function collect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const urls = [...new Set(feedUrls.split(/[\n,]+/).map((value) => value.trim()).filter(Boolean))];
    if (!urls.length) {
      setError("Add at least one RSS or Atom feed URL.");
      return;
    }
    setCollecting(true);
    setError("");
    setNotice("");
    try {
      const result = await api<{ created: number; updated: number; feeds_processed: number; errors: { feed_url: string; error: string }[] }>("/trends/collect", {
        method: "POST",
        body: JSON.stringify({ feed_urls: urls }),
      });
      const failures = result.errors?.length ?? 0;
      setNotice(`Collection finished: ${result.feeds_processed} feed(s) processed, ${result.created} new item(s), ${result.updated} updated.${failures ? ` ${failures} feed(s) failed.` : ""}`);
      if (pageId !== "") await loadRecommendations(pageId, filter);
      if (failures) setError(result.errors.map((item) => `${item.feed_url}: ${item.error}`).join(" · "));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not collect feeds.");
    } finally {
      setCollecting(false);
    }
  }

  async function generateScripts(item: Recommendation) {
    setBusyId(item.id); setError(""); setNotice("");
    try {
      await api(`/pages/${item.page_id}/trends/${item.id}/generate-scripts`, { method: "POST" });
      window.location.assign("/scripts");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not generate scripts."); }
    finally { setBusyId(null); }
  }

  async function updateStatus(item: Recommendation, status: Filter) {
    setBusyId(item.id);
    setError("");
    setNotice("");
    try {
      await api<Recommendation>(`/pages/${item.page_id}/trends/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setNotice(`Idea marked ${status}.`);
      await loadRecommendations(item.page_id, filter);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update this idea.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="min-h-screen bg-[#080d18] text-slate-100">
      <div className="mx-auto max-w-7xl px-5 py-8 md:px-10 md:py-12">
        <header className="mb-9 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold tracking-[0.28em] text-cyan-400">AI REEL FACTORY · M5</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">Trend discovery</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-400">Collect stories from RSS feeds and discover which ideas fit each content brand.</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <AuthActions />
            <a href="/" className="rounded-xl border border-white/10 px-4 py-2.5 text-sm text-slate-300 hover:bg-white/5">Pages</a>
            <a href="/strategies" className="rounded-xl border border-white/10 px-4 py-2.5 text-sm text-slate-300 hover:bg-white/5">Strategies</a>
            <a href="/scripts" className="rounded-xl border border-cyan-300/30 px-4 py-2.5 text-sm text-cyan-200 hover:bg-cyan-300/10">Script studio</a>
          </div>
        </header>

        {error && <div role="alert" className="mb-5 rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
        {notice && <div role="status" className="mb-5 rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200">{notice}</div>}

        <section className="mb-6 grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5 md:p-6">
            <div className="mb-4 flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-400/10 text-lg text-cyan-200">⌁</span>
              <div><p className="text-xs font-semibold tracking-widest text-cyan-300">SOURCE COLLECTION</p><h2 className="mt-1 text-lg font-semibold">Collect RSS / Atom feeds</h2></div>
            </div>
            <p className="mb-4 text-sm leading-6 text-slate-400">Add public feed URLs, one per line or separated by commas. New items are matched against every active Page with a configured profile.</p>
            <form onSubmit={collect} className="space-y-3">
              <textarea value={feedUrls} onChange={(e) => setFeedUrls(e.target.value)} rows={4} spellCheck={false} placeholder="https://example.com/feed.xml" className="field font-mono text-xs leading-6" />
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="text-xs text-slate-500">Maximum 20 feeds per collection</span>
                <button disabled={collecting} className="rounded-xl bg-cyan-300 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:opacity-50">{collecting ? "Collecting feeds..." : "Collect trends ↗"}</button>
              </div>
            </form>
          </div>

          <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-cyan-400/[0.09] to-white/[0.02] p-5 md:p-6">
            <p className="text-xs font-semibold tracking-widest text-cyan-300">HOW RANKING WORKS</p>
            <h2 className="mt-2 text-lg font-semibold">Page-specific relevance</h2>
            <div className="mt-5 space-y-4">
              <div><div className="mb-1 flex justify-between text-xs"><span className="text-slate-300">Niche & audience match</span><strong className="text-cyan-200">75%</strong></div><div className="h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full w-3/4 rounded-full bg-cyan-300" /></div></div>
              <div><div className="mb-1 flex justify-between text-xs"><span className="text-slate-300">Freshness</span><strong className="text-cyan-200">25%</strong></div><div className="h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full w-1/4 rounded-full bg-cyan-300" /></div></div>
            </div>
            <p className="mt-5 text-xs leading-5 text-slate-500">Scores are transparent triage signals—not predictions of virality. Review source material before turning an idea into content.</p>
          </div>
        </section>

        <section className="mb-5 rounded-2xl border border-white/10 bg-white/[0.035] p-4 md:p-5">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div className="min-w-0 flex-1">
              <label htmlFor="trend-page" className="mb-2 block text-xs font-medium text-slate-400">Recommendations for Page</label>
              {loading ? <p className="text-sm text-slate-400">Loading Pages...</p> : pages.length === 0 ? <p className="text-sm text-amber-200">Create a Page workspace before collecting recommendations.</p> :
                <select id="trend-page" value={pageId} onChange={(e) => setPageId(Number(e.target.value))} className="field max-w-lg">
                  {pages.map((page) => <option key={page.id} value={page.id}>{page.name}{page.is_active ? "" : " · Paused"}</option>)}
                </select>}
            </div>
            <div className="flex flex-wrap gap-2">
              {(["suggested", "saved", "selected", "dismissed"] as Filter[]).map((value) => (
                <button key={value} onClick={() => setFilter(value)} className={`rounded-lg border px-3 py-2 text-xs capitalize transition ${filter === value ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-100" : "border-white/10 text-slate-400 hover:bg-white/5"}`}>{value}</button>
              ))}
              <button onClick={() => void refresh()} className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 hover:bg-white/5">Refresh ↻</button>
            </div>
          </div>
        </section>

        <section>
          <div className="mb-4 flex items-center justify-between gap-3">
            <div><h2 className="text-xl font-semibold capitalize">{filter} ideas</h2><p className="mt-1 text-xs text-slate-500">Ranked for this Page's niche and target audience.</p></div>
            <span className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-400">{items.length} shown</span>
          </div>
          {pageId === "" ? <div className="rounded-2xl border border-dashed border-white/10 p-10 text-center text-sm text-slate-500">Create a Page workspace to get started.</div> :
            items.length === 0 ? <div className="rounded-2xl border border-dashed border-white/10 p-10 text-center"><p className="font-medium">No {filter} ideas yet</p><p className="mt-2 text-sm text-slate-500">Collect a few feeds above. Ideas will appear here when they match this Page's profile.</p></div> :
            <div className="grid gap-4 xl:grid-cols-2">
              {items.map((item) => (
                <article key={item.id} className="rounded-2xl border border-white/10 bg-white/[0.025] p-5 transition hover:border-cyan-400/25">
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <span className="text-[11px] font-medium uppercase tracking-wider text-slate-500">{item.trend.source_name} · {formatDate(item.trend.published_at)}</span>
                    <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold tabular-nums ${scoreTone(item.score)}`}>{Math.round(item.score)} / 100 match</span>
                  </div>
                  <h3 className="text-base font-semibold leading-6">{item.trend.title}</h3>
                  <p className="mt-2 line-clamp-3 text-sm leading-6 text-slate-400">{item.trend.summary || "No description was provided by the source."}</p>
                  <div className="mt-4 rounded-xl border border-white/5 bg-[#0b1220] px-3 py-2.5">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-cyan-300">Why it matches</p>
                    <p className="mt-1 text-xs leading-5 text-slate-400">{item.rationale}</p>
                  </div>
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-4">
                    <a href={item.trend.source_url} target="_blank" rel="noreferrer" className="text-xs text-cyan-300 hover:text-cyan-200">Read original source ↗</a>
                    <div className="flex flex-wrap gap-2">
                      {item.status !== "saved" && <button disabled={busyId === item.id} onClick={() => void updateStatus(item, "saved")} className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 hover:bg-white/5 disabled:opacity-50">Save</button>}
                      {item.status !== "selected" && <button disabled={busyId === item.id} onClick={() => void updateStatus(item, "selected")} className="rounded-lg bg-cyan-300 px-3 py-2 text-xs font-semibold text-slate-950 hover:bg-cyan-200 disabled:opacity-50">Select idea</button>}
                      {item.status === "selected" && <button disabled={busyId === item.id} onClick={() => void generateScripts(item)} className="rounded-lg bg-cyan-300 px-3 py-2 text-xs font-semibold text-slate-950 hover:bg-cyan-200 disabled:opacity-50">{busyId === item.id ? "Generating..." : "Generate 3 scripts ↗"}</button>}
                      {item.status !== "dismissed" && <button disabled={busyId === item.id} onClick={() => void updateStatus(item, "dismissed")} className="rounded-lg px-3 py-2 text-xs text-rose-300 hover:bg-rose-400/10 disabled:opacity-50">Dismiss</button>}
                    </div>
                  </div>
                </article>
              ))}
            </div>}
        </section>

        <footer className="mt-14 border-t border-white/10 pt-5 text-xs text-slate-600">AI Reel Factory · Trend scores are heuristic recommendations. Human review remains required.</footer>
      </div>
    </main>
  );
}
