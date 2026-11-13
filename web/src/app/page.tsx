"use client";

import dynamic from "next/dynamic";

const GameCanvas = dynamic(
  () => import("@/game/GameCanvas"),
  { ssr: false },
);

export default function Home() {
  return (
    <main className="min-h-screen bg-[#101b19] px-3 py-6 text-white md:px-8">
      <div className="mx-auto max-w-[1600px]">
        <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.3em] text-emerald-400">
              Persistent Agent Simulation
            </p>
            <h1 className="mt-2 text-3xl font-black md:text-5xl">
              Living AI Town
            </h1>
          </div>
          <span className="rounded-xl border border-emerald-500/30 bg-emerald-900/30 px-4 py-2 text-sm text-emerald-200">
            2D Game World
          </span>
        </header>

        <GameCanvas />

        <p className="mt-4 text-center text-sm text-slate-400">
          A persistent world where autonomous AI characters live, move, and interact.
        </p>
      </div>
    </main>
  );
}
