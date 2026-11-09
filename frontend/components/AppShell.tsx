"use client";

import type { ReactNode } from "react";
import AuthActions from "@/components/AuthActions";

type AppSection = "overview" | "trends" | "strategies" | "scripts";

const links: { id: AppSection; label: string; href: string; icon: string }[] = [
  { id: "overview", label: "Overview", href: "/", icon: "◫" },
  { id: "trends", label: "Discover", href: "/trends", icon: "⌁" },
  { id: "strategies", label: "Strategies", href: "/strategies", icon: "◈" },
  { id: "scripts", label: "Script studio", href: "/scripts", icon: "▤" },
];

export function LoadingSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3" aria-label="Loading content" role="status">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="skeleton-row">
          <span className="skeleton-block h-10 w-10 shrink-0 rounded-xl" />
          <span className="min-w-0 flex-1 space-y-2">
            <span className="skeleton-block block h-3 w-2/5 rounded-full" />
            <span className="skeleton-block block h-3 w-4/5 rounded-full" />
          </span>
          <span className="skeleton-block hidden h-7 w-20 rounded-lg sm:block" />
        </div>
      ))}
      <span className="sr-only">Loading data…</span>
    </div>
  );
}

export function GenerationOverlay() {
  return (
    <div className="generation-overlay" role="status" aria-live="polite">
      <div className="generation-card">
        <div className="generation-orbit"><span /><span /><span /></div>
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-300">AI script engine</p>
        <h2 className="mt-2 text-xl font-semibold text-white">Crafting your scripts</h2>
        <p className="mt-2 max-w-sm text-sm leading-6 text-slate-400">Reading the selected trend, matching your Page strategy and creating three original variations.</p>
        <div className="generation-progress"><span /></div>
        <p className="mt-3 text-xs text-slate-500">This can take a little while. Keep this tab open.</p>
      </div>
    </div>
  );
}

export default function AppShell({ active, children }: { active: AppSection; children: ReactNode }) {
  return (
    <div className="app-shell">
      <div className="app-ambient" />
      <header className="app-topbar">
        <a href="/" className="brand-lockup">
          <span className="brand-mark">✦</span>
          <span><strong>AI REEL</strong><small>FACTORY</small></span>
        </a>
        <nav className="app-nav" aria-label="Main navigation">
          {links.map((link) => (
            <a key={link.id} href={link.href} className={active === link.id ? "app-nav-link active" : "app-nav-link"}>
              <span className="nav-icon">{link.icon}</span>{link.label}
            </a>
          ))}
        </nav>
        <div className="app-account"><span className="hidden text-[11px] text-slate-500 sm:inline">WORKSPACE</span><AuthActions /></div>
      </header>
      <div className="app-mobile-nav">
        {links.map((link) => <a key={link.id} href={link.href} className={active === link.id ? "active" : ""}>{link.icon}<span>{link.label}</span></a>)}
      </div>
      <div className="app-content">{children}</div>
      <footer className="app-global-footer"><span>AI REEL FACTORY</span><span>Content operations workspace · v0.6</span></footer>
    </div>
  );
}
