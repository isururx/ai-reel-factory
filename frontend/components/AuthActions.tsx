"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

export default function AuthActions() {
  const [email, setEmail] = useState<string | null>(null);
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setEmail(data.session?.user.email ?? null));
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setEmail(session?.user.email ?? null);
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  async function signOut() {
    await supabase.auth.signOut();
    window.location.assign("/login");
  }

  return email ? (
    <button onClick={() => void signOut()} className="rounded-full border border-white/10 px-4 py-2 text-xs text-slate-300 hover:bg-white/5">
      Sign out · {email}
    </button>
  ) : (
    <a href="/login" className="rounded-full border border-cyan-400/30 px-4 py-2 text-xs text-cyan-200 hover:bg-cyan-400/10">Sign in</a>
  );
}
