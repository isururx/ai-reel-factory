const modules = [
  { name: "Content intelligence", detail: "Learn what works for each Page", status: "Coming in milestone 2" },
  { name: "Script studio", detail: "Generate, edit and approve scripts", status: "Coming in milestone 3" },
  { name: "Video production", detail: "Turn approved scripts into Reels", status: "Planned" },
  { name: "Publishing", detail: "Review and schedule approved videos", status: "Planned" },
];

export default function Home() {
  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-12 md:px-10">
      <div className="mb-12 flex items-center justify-between">
        <div>
          <p className="text-sm font-medium tracking-[0.22em] text-cyan-400">AI REEL FACTORY</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-5xl">Your content operation,</h1>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-400 md:text-5xl">with intelligence built in.</h2>
        </div>
        <span className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-300">MVP foundation</span>
      </div>

      <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 md:p-8">
        <p className="text-sm text-slate-400">PROJECT STATUS</p>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-2xl font-semibold">Foundation initialized</p>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">We are starting with one Page and a complete script approval workflow. The platform is designed to expand to multiple independent Pages after the first workflow is proven.</p>
          </div>
          <div className="text-right"><p className="text-3xl font-semibold text-cyan-300">01</p><p className="text-xs text-slate-500">of 06 phases</p></div>
        </div>
      </section>

      <section className="mt-10">
        <div className="mb-4 flex items-center justify-between"><h3 className="text-lg font-semibold">Platform modules</h3><span className="text-xs text-slate-500">Development roadmap</span></div>
        <div className="grid gap-4 sm:grid-cols-2">
          {modules.map((module, index) => (
            <article key={module.name} className="rounded-xl border border-white/10 bg-white/[0.025] p-5">
              <div className="flex items-center justify-between"><span className="text-xs text-slate-500">0{index + 1}</span><span className="text-xs text-cyan-300">{module.status}</span></div>
              <h4 className="mt-5 text-lg font-medium">{module.name}</h4>
              <p className="mt-1 text-sm text-slate-400">{module.detail}</p>
            </article>
          ))}
        </div>
      </section>
      <footer className="mt-14 border-t border-white/10 pt-5 text-xs text-slate-600">AI Reel Factory · Built around original content, human review and measurable improvement.</footer>
    </main>
  );
}
