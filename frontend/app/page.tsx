"use client";

import { authenticatedFetch } from "@/lib/supabase";
import AppShell, { LoadingSkeleton } from "@/components/AppShell";

import { FormEvent, useCallback, useEffect, useState } from "react";

type Page = {
  id: number;
  name: string;
  platform: string;
  external_page_id: string | null;
  is_active: boolean;
  created_at: string;
};

type Profile = {
  id?: number;
  page_id?: number;
  niche: string;
  target_audience: string;
  language: string;
  tone: Record<string, string>;
  preferred_formats: string[];
  restricted_topics: string[];
  fact_check_level: string;
};

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
const emptyProfile: Profile = {
  niche: "",
  target_audience: "",
  language: "English",
  tone: { style: "conversational", energy: "engaging" },
  preferred_formats: ["storytelling", "educational"],
  restricted_topics: [],
  fact_check_level: "standard",
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await authenticatedFetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body?.detail ?? `Request failed (${response.status})`;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export default function Home() {
  const [pages, setPages] = useState<Page[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [newName, setNewName] = useState("");
  const [newExternalId, setNewExternalId] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");
  const [profilePageId, setProfilePageId] = useState<number | null>(null);
  const [profile, setProfile] = useState<Profile>(emptyProfile);
  const [profileLoading, setProfileLoading] = useState(false);

  const loadPages = useCallback(async () => {
    setError("");
    try {
      setPages(await request<Page[]>("/pages"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load Pages.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadPages(); }, [loadPages]);

  async function createPage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newName.trim()) return;
    setSaving(true); setError(""); setNotice("");
    try {
      await request<Page>("/pages", {
        method: "POST",
        body: JSON.stringify({
          name: newName.trim(),
          platform: "facebook",
          external_page_id: newExternalId.trim() || null,
        }),
      });
      setNewName(""); setNewExternalId("");
      setNotice("Page created successfully.");
      await loadPages();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create Page.");
    } finally { setSaving(false); }
  }

  async function saveName(id: number) {
    if (!editingName.trim()) return;
    setSaving(true); setError("");
    try {
      await request<Page>(`/pages/${id}`, {
        method: "PATCH", body: JSON.stringify({ name: editingName.trim() }),
      });
      setEditingId(null); setNotice("Page updated."); await loadPages();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update Page.");
    } finally { setSaving(false); }
  }

  async function toggleActive(page: Page) {
    setError(""); setNotice("");
    try {
      await request<Page>(`/pages/${page.id}`, {
        method: "PATCH", body: JSON.stringify({ is_active: !page.is_active }),
      });
      setNotice(page.is_active ? "Page paused." : "Page activated.");
      await loadPages();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update Page status.");
    }
  }

  async function deletePage(page: Page) {
    if (!window.confirm(`Delete "${page.name}" and all its associated profiles and strategies? This cannot be undone.`)) return;
    setError(""); setNotice("");
    try {
      await request<void>(`/pages/${page.id}`, { method: "DELETE" });
      if (profilePageId === page.id) setProfilePageId(null);
      setNotice("Page deleted."); await loadPages();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete Page.");
    }
  }

  async function openProfile(page: Page) {
    setProfilePageId(page.id); setProfileLoading(true); setError("");
    try {
      const saved = await request<Profile>(`/pages/${page.id}/profile`);
      setProfile(saved);
    } catch (err) {
      if (err instanceof Error && err.message === "Page profile not found.") {
        setProfile(emptyProfile);
      } else {
        setError(err instanceof Error ? err.message : "Could not load profile.");
      }
    } finally { setProfileLoading(false); }
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profilePageId) return;
    setSaving(true); setError(""); setNotice("");
    try {
      await request<Profile>(`/pages/${profilePageId}/profile`, {
        method: "PUT", body: JSON.stringify(profile),
      });
      setNotice("Page profile saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile.");
    } finally { setSaving(false); }
  }

  const activeCount = pages.filter((page) => page.is_active).length;

  return (
    <AppShell active="overview">
    <main className="min-h-screen bg-transparent text-slate-100">
      <div className="mx-auto max-w-7xl px-5 py-8 md:px-10 md:py-12">
        <header className="mb-10 flex flex-wrap items-center justify-between gap-5">
          <div>
            <p className="text-xs font-semibold tracking-[0.28em] text-cyan-400">AI REEL FACTORY</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">Page workspace</h1>
            <p className="mt-2 text-sm text-slate-400">Manage your content brands from one place.</p>
          </div>
          <span className="rounded-full border border-cyan-400/20 bg-cyan-400/5 px-3 py-2 text-[11px] text-cyan-200">CONTENT OPERATIONS</span>
        </header>

        <section className="mb-8 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Stat label="Total Pages" value={pages.length} />
          <Stat label="Active Pages" value={activeCount} />
          <Stat label="Paused Pages" value={pages.length - activeCount} />
          <Stat label="Meta linked" value={pages.filter((page) => Boolean(page.external_page_id)).length} />
        </section>

        {error && <div role="alert" className="mb-5 rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
        {notice && <div role="status" className="mb-5 rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200">{notice}</div>}

        <section className="mb-8 rounded-2xl border border-white/10 bg-white/[0.035] p-5 md:p-7">
          <div className="mb-5">
            <p className="text-xs font-semibold tracking-widest text-cyan-300">ADD A CONTENT BRAND</p>
            <h2 className="mt-2 text-xl font-semibold">Connect a Facebook Page workspace</h2>
            <p className="mt-1 text-sm text-slate-400">Create the workspace now. Actual Meta account connection will be added in a later milestone.</p>
          </div>
          <form onSubmit={createPage} className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
            <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Page name · e.g. Curious Science" maxLength={120} required className="rounded-xl border border-white/10 bg-[#0b1220] px-4 py-3 text-sm outline-none transition focus:border-cyan-400/60" />
            <input value={newExternalId} onChange={(e) => setNewExternalId(e.target.value)} placeholder="Facebook Page ID (optional)" maxLength={128} className="rounded-xl border border-white/10 bg-[#0b1220] px-4 py-3 text-sm outline-none transition focus:border-cyan-400/60" />
            <button disabled={saving} className="rounded-xl bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:opacity-50">{saving ? "Saving..." : "Create Page +"}</button>
          </form>
        </section>

        <section>
          <div className="mb-4 flex items-end justify-between">
            <div><h2 className="text-xl font-semibold">Your Pages</h2><p className="mt-1 text-sm text-slate-500">Each Page has its own profile and content strategy.</p></div>
            <button onClick={() => { setLoading(true); void loadPages(); }} className="text-xs text-cyan-300 hover:text-cyan-200">Refresh ↻</button>
          </div>
          {loading ? <div className="grid gap-3 md:grid-cols-2"><div className="skeleton-card"><div className="skeleton-line w-1/3" /><div className="skeleton-line mt-5 h-8 w-1/2" /></div><div className="skeleton-card"><div className="skeleton-line w-1/3" /><div className="skeleton-line mt-5 h-8 w-1/2" /></div></div><div className="mt-4"><LoadingSkeleton rows={3} /></div> :
            pages.length === 0 ? <div className="rounded-2xl border border-dashed border-white/15 p-10 text-center"><p className="font-medium">No Pages yet</p><p className="mt-2 text-sm text-slate-500">Create your first content brand above.</p></div> :
            <div className="grid gap-4 lg:grid-cols-2">
              {pages.map((page) => (
                <article key={page.id} className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="mb-2 flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${page.is_active ? "bg-emerald-400" : "bg-slate-500"}`} /><span className={`text-xs ${page.is_active ? "text-emerald-300" : "text-slate-500"}`}>{page.is_active ? "Active" : "Paused"}</span><span className="text-xs text-slate-600">· Facebook · #{page.id}</span></div>
                      {editingId === page.id ? <div className="flex gap-2"><input autoFocus value={editingName} onChange={(e) => setEditingName(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void saveName(page.id); }} className="min-w-0 flex-1 rounded-lg border border-white/10 bg-[#0b1220] px-3 py-2 text-sm" /><button onClick={() => void saveName(page.id)} className="text-xs text-cyan-300">Save</button><button onClick={() => setEditingId(null)} className="text-xs text-slate-500">Cancel</button></div> : <h3 className="truncate text-lg font-semibold">{page.name}</h3>}
                      <p className="mt-1 text-xs text-slate-500">{page.external_page_id ? `Meta ID: ${page.external_page_id}` : "Not connected to Meta yet"}</p>
                    </div>
                    <span className="rounded-lg border border-white/10 px-2.5 py-1.5 text-xs text-slate-400">ID {page.id}</span>
                  </div>
                  <div className="mt-5 flex flex-wrap gap-2 border-t border-white/10 pt-4">
                    <button onClick={() => void openProfile(page)} className="rounded-lg bg-cyan-400/10 px-3 py-2 text-xs font-medium text-cyan-200 hover:bg-cyan-400/20">Edit profile</button>
                    <button onClick={() => { setEditingId(page.id); setEditingName(page.name); }} className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 hover:bg-white/5">Rename</button>
                    <button onClick={() => void toggleActive(page)} className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 hover:bg-white/5">{page.is_active ? "Pause" : "Activate"}</button>
                    <button onClick={() => void deletePage(page)} className="ml-auto rounded-lg px-3 py-2 text-xs text-rose-300 hover:bg-rose-400/10">Delete</button>
                  </div>
                </article>
              ))}
            </div>
          }
        </section>

        {profilePageId !== null && (
          <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-0 backdrop-blur-sm md:items-center md:p-5" onMouseDown={(e) => { if (e.target === e.currentTarget) setProfilePageId(null); }}>
            <section className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-t-2xl border border-white/10 bg-[#0d1524] p-5 shadow-2xl md:rounded-2xl md:p-7">
              <div className="mb-6 flex items-start justify-between"><div><p className="text-xs font-semibold tracking-widest text-cyan-300">PAGE CONFIGURATION</p><h2 className="mt-2 text-xl font-semibold">Content profile</h2><p className="mt-1 text-sm text-slate-400">These settings guide future content generation for this Page.</p></div><button onClick={() => setProfilePageId(null)} className="rounded-lg px-3 py-1 text-slate-400 hover:bg-white/5">✕</button></div>
              {profileLoading ? <p className="py-10 text-center text-sm text-slate-400">Loading profile...</p> :
                <form onSubmit={saveProfile} className="space-y-4">
                  <Field label="Niche"><input required value={profile.niche} onChange={(e) => setProfile({ ...profile, niche: e.target.value })} placeholder="e.g. Science, parenting, history" className="field" /></Field>
                  <Field label="Target audience"><textarea value={profile.target_audience} onChange={(e) => setProfile({ ...profile, target_audience: e.target.value })} placeholder="Who should this Page reach?" rows={3} className="field" /></Field>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field label="Language"><input value={profile.language} onChange={(e) => setProfile({ ...profile, language: e.target.value })} className="field" /></Field>
                    <Field label="Fact-check level"><select value={profile.fact_check_level} onChange={(e) => setProfile({ ...profile, fact_check_level: e.target.value })} className="field"><option value="standard">Standard</option><option value="strict">Strict</option><option value="high">High</option></select></Field>
                  </div>
                  <Field label="Tone / style"><input value={profile.tone.style ?? ""} onChange={(e) => setProfile({ ...profile, tone: { ...profile.tone, style: e.target.value } })} placeholder="conversational, dramatic, humorous..." className="field" /></Field>
                  <Field label="Preferred formats (comma separated)"><input value={profile.preferred_formats.join(", ")} onChange={(e) => setProfile({ ...profile, preferred_formats: e.target.value.split(",").map((v) => v.trim()).filter(Boolean) })} placeholder="storytelling, educational, listicle" className="field" /></Field>
                  <Field label="Restricted topics (comma separated)"><input value={profile.restricted_topics.join(", ")} onChange={(e) => setProfile({ ...profile, restricted_topics: e.target.value.split(",").map((v) => v.trim()).filter(Boolean) })} placeholder="Topics this Page should avoid" className="field" /></Field>
                  <div className="flex justify-end gap-3 border-t border-white/10 pt-5"><button type="button" onClick={() => setProfilePageId(null)} className="rounded-xl border border-white/10 px-4 py-2.5 text-sm text-slate-300">Cancel</button><button disabled={saving} className="rounded-xl bg-cyan-300 px-5 py-2.5 text-sm font-semibold text-slate-950 disabled:opacity-50">{saving ? "Saving..." : "Save profile"}</button></div>
                </form>}
            </section>
          </div>
        )}
        <footer className="mt-14 border-t border-white/10 pt-5 text-xs text-slate-600">AI Reel Factory · Page workspaces are configuration records; Meta OAuth connection is a later step.</footer>
      </div>
    </main>
    </AppShell>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4"><p className="text-xs text-slate-500">{label}</p><p className="mt-2 text-2xl font-semibold">{value.toString().padStart(2, "0")}</p></div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="mb-2 block text-xs font-medium text-slate-400">{label}</span>{children}</label>;
}
