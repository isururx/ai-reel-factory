"use client";

import { useState, type FormEvent } from "react";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError(""); setMessage("");
    try {
      if (mode === "signup") {
        const { data, error: authError } = await supabase.auth.signUp({ email, password });
        if (authError) throw authError;
        if (!data.session) {
          setMessage("Account created. Check your email to confirm it, then sign in.");
        } else {
          window.location.assign("/");
        }
      } else {
        const { error: authError } = await supabase.auth.signInWithPassword({ email, password });
        if (authError) throw authError;
        window.location.assign("/");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Authentication failed.");
    } finally { setBusy(false); }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#080d18] px-5 py-10 text-slate-100">
      <section className="w-full max-w-md rounded-2xl border border-white/10 bg-white/[0.035] p-7 shadow-2xl">
        <p className="text-xs font-semibold tracking-[0.28em] text-cyan-400">AI REEL FACTORY</p>
        <h1 className="mt-4 text-2xl font-semibold">{mode === "signin" ? "Welcome back" : "Create your account"}</h1>
        <p className="mt-2 text-sm text-slate-400">Sign in to manage your private Page workspaces.</p>
        {error && <p role="alert" className="mt-5 rounded-xl border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-200">{error}</p>}
        {message && <p role="status" className="mt-5 rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-3 text-sm text-emerald-200">{message}</p>}
        <form onSubmit={submit} className="mt-6 space-y-4">
          <label className="block"><span className="mb-2 block text-xs text-slate-400">Email</span><input required type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} className="field" /></label>
          <label className="block"><span className="mb-2 block text-xs text-slate-400">Password</span><input required type="password" minLength={8} autoComplete={mode === "signin" ? "current-password" : "new-password"} value={password} onChange={(e) => setPassword(e.target.value)} className="field" /></label>
          <button disabled={busy} className="w-full rounded-xl bg-cyan-300 px-4 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50">{busy ? "Please wait..." : mode === "signin" ? "Sign in" : "Create account"}</button>
        </form>
        <button onClick={() => { setMode(mode === "signin" ? "signup" : "signin"); setError(""); setMessage(""); }} className="mt-5 w-full text-center text-sm text-cyan-300 hover:text-cyan-200">{mode === "signin" ? "New here? Create an account" : "Already registered? Sign in"}</button>
        <p className="mt-6 text-center text-xs text-slate-600">Authentication powered by Supabase Auth.</p>
      </section>
    </main>
  );
}
