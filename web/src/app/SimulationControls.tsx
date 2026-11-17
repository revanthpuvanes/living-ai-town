"use client";

import { useCallback, useEffect, useState } from "react";

type SimulationStatus = {
  active: boolean;
  remaining_seconds: number;
};

export default function SimulationControls() {
  const [status, setStatus] = useState<SimulationStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/simulation", {
        cache: "no-store",
      });

      if (!response.ok) throw new Error("Simulation unavailable");

      const data: SimulationStatus = await response.json();
      setStatus(data);
      setError("");
    } catch {
      setError("Unable to connect to the simulation.");
    }
  }, []);

  useEffect(() => {
    void refresh();

    const timer = setInterval(() => {
      void refresh();
    }, 1000);

    return () => clearInterval(timer);
  }, [refresh]);

  async function startSimulation() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/simulation/start", {
        method: "POST",
      });

      if (!response.ok) throw new Error("Unable to start");

      const data: SimulationStatus = await response.json();
      setStatus(data);
    } catch {
      setError("Could not start the simulation.");
    } finally {
      setLoading(false);
    }
  }

  async function stopSimulation() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/simulation/stop", {
        method: "POST",
      });

      if (!response.ok) throw new Error("Unable to stop");

      const data: SimulationStatus = await response.json();
      setStatus(data);
    } catch {
      setError("Could not stop the simulation.");
    } finally {
      setLoading(false);
    }
  }

  const active = status?.active ?? false;
  const remaining = status?.remaining_seconds ?? 0;
  const minutes = Math.floor(remaining / 60);
  const seconds = String(remaining % 60).padStart(2, "0");

  return (
    <div className="mb-5 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-emerald-500/20 bg-[#172923] p-4">
      <div>
        <p className="font-bold text-white">
          {active ? "🟢 Simulation running" : "💤 Simulation paused"}
        </p>
        <p className="mt-1 text-sm text-slate-300">
          {active
            ? "Three AI agents are moving and interacting."
            : "Start a 2-minute live AI agent simulation."}
        </p>
        {error && (
          <p className="mt-2 text-sm text-red-400">{error}</p>
        )}
      </div>

      {active ? (
        <div className="flex flex-wrap items-center gap-3">
          <div className="rounded-xl border border-emerald-400/30 px-5 py-3 text-lg font-bold text-emerald-300">
            ⏱ {minutes}:{seconds}
          </div>
          <button
            type="button"
            onClick={stopSimulation}
            disabled={loading}
            className="rounded-xl bg-red-500 px-6 py-3 font-bold text-white transition hover:bg-red-400 disabled:opacity-50"
          >
            {loading ? "Stopping..." : "■ Stop Simulation"}
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={startSimulation}
          disabled={loading || status === null}
          className="rounded-xl bg-emerald-500 px-6 py-3 font-bold text-[#101b19] transition hover:bg-emerald-400 disabled:opacity-50"
        >
          {loading ? "Starting..." : "▶ Start Simulation — 2 Minutes"}
        </button>
      )}
    </div>
  );
}
