"use client";

import { useState } from "react";
import AppShell from "@/components/AppShell";
import { authenticatedFetch } from "@/lib/supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export default function DownloaderPage() {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function handleDownload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await authenticatedFetch(`${API_BASE}/downloads/facebook`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Download failed. Check the link and try again.");
      }
      const blob = await response.blob();
      const disposition = response.headers.get("content-disposition") || "";
      const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || "facebook-video.mp4";
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(objectUrl);
      setMessage("Download completed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell active={"downloader" as never}>
      <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-300">Utilities</p>
          <h1 className="mt-3 text-3xl font-semibold text-white">Facebook video downloader</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
            Download publicly accessible Facebook videos for educational testing. No Facebook login,
            cookies, or private-video access is supported.
          </p>
        </div>
        <form onSubmit={handleDownload} className="rounded-2xl border border-white/10 bg-slate-900/70 p-5 shadow-xl sm:p-7">
          <label htmlFor="facebook-url" className="mb-2 block text-sm font-medium text-slate-200">Facebook video or Reel URL</label>
          <input id="facebook-url" type="url" required value={url} onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.facebook.com/reel/..." className="w-full rounded-xl border border-white/10 bg-slate-950 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400" />
          <button type="submit" disabled={busy || !url.trim()} className="mt-4 w-full rounded-xl bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50">
            {busy ? "Downloading video…" : "Download MP4"}
          </button>
          {error && <p role="alert" className="mt-4 rounded-lg border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">{error}</p>}
          {message && <p role="status" className="mt-4 rounded-lg border border-emerald-400/20 bg-emerald-400/10 p-3 text-sm text-emerald-200">{message}</p>}
        </form>
        <div className="mt-5 rounded-xl border border-white/10 bg-white/[0.03] p-4 text-xs leading-5 text-slate-400">
          Prototype limits: public videos only, up to 15 minutes and 300 MB. Availability depends on Facebook's
          current access rules and the video owner’s settings. Only download content you have permission to use.
        </div>
      </main>
    </AppShell>
  );
}
