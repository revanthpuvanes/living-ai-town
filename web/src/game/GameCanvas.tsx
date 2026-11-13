"use client";

import { useEffect, useRef, useState } from "react";
import type { TownWorld } from "./TownCharacters";
import TownLiveChat from "./TownLiveChat";

type SelectedCharacter = {
  id: string;
  name: string;
  profession: string;
  location: string;
  activity: string;
};

type TownEvent = {
  id: number;
  tick: number;
  actor: string;
  type: string;
  payload: {
    message?: string;
    character_id?: string;
    visitor_event_id?: number;
  };
  depends_on: number[];
};

export default function GameCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const latestWorldRef = useRef<TownWorld | null>(null);
  const [tick, setTick] = useState<number | null>(null);
  const [clock, setClock] = useState("");
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const updateClock = () => {
      setClock(new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      }));
    };

    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);
  const [selected, setSelected] = useState<SelectedCharacter | null>(null);
  const [recentEvents, setRecentEvents] = useState<TownEvent[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let game: import("phaser").Game | undefined;
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | undefined;
    let currentWorld: TownWorld | null = null;

    async function start() {
      const Phaser = (await import("phaser")).default;
      const { TownScene } = await import("./TownScene");
      const { TownCharacters } = await import("./TownCharacters");
      const { TownSpeech } = await import("./TownSpeech");

      if (cancelled || !containerRef.current) return;

      let characters: InstanceType<typeof TownCharacters> | undefined;
      let speech: InstanceType<typeof TownSpeech> | undefined;
      let lastEventId: number | null = null;

      class LiveTownScene extends TownScene {
        create() {
          super.create();
          characters = new TownCharacters(this);
          speech = new TownSpeech(this);
          if (currentWorld) characters.update(currentWorld);
        }

        shutdown() {
          speech?.destroy();
          characters?.destroy();
        }
      }

      game = new Phaser.Game({
        type: Phaser.AUTO,
        width: 960,
        height: 640,
        parent: containerRef.current,
        backgroundColor: "#78a65c",
        audio: { noAudio: true },
        render: { pixelArt: true, antialias: false },
        scale: {
          mode: Phaser.Scale.FIT,
          autoCenter: Phaser.Scale.CENTER_BOTH,
        },
        scene: [LiveTownScene],
      });

      game.events.on("character-selected", (id: string) => {
        const character = currentWorld?.state.characters[id];

        if (character) {
          setSelected({
            id,
            name: character.name,
            profession: character.profession,
            location: character.location,
            activity: character.activity,
          });
          setMessage("");
          setNotice("");
        }
      });

      async function refresh() {
        try {
          const response = await fetch("/api/world", {
            cache: "no-store",
          });

          if (!response.ok) throw new Error("API unavailable");

          const world: TownWorld = await response.json();
          if (cancelled) return;

          currentWorld = world;
          latestWorldRef.current = world;
          setTick(world.tick);
          setConnected(true);
          setError("");

          setSelected((previous) => {
            if (!previous) return null;

            const character = world.state.characters[previous.id];
            if (!character) return null;

            return {
              ...previous,
              location: character.location,
              activity: character.activity,
            };
          });

          characters?.update(world);

          const eventsResponse = await fetch("/api/events?limit=100", {
            cache: "no-store",
          });

          if (!eventsResponse.ok) {
            throw new Error("Events API unavailable");
          }

          const eventData = await eventsResponse.json();
          if (cancelled) return;

          const events: TownEvent[] = eventData.events;
          setRecentEvents(events);

          const newestId = Math.max(
            0,
            ...events.map((event) => event.id),
          );

          if (lastEventId !== null) {
            for (const event of [...events].reverse()) {
              if (
                event.id > lastEventId &&
                (event.type === "CONVERSATION_SPOKEN" ||
                  event.type === "VISITOR_REPLY") &&
                typeof event.payload.message === "string"
              ) {
                const character =
                  characters?.getCharacterContainer(event.actor);

                if (character) {
                  speech?.show(
                    event.actor,
                    event.payload.message,
                    character,
                  );
                }
              }
            }
          }

          lastEventId = Math.max(lastEventId ?? 0, newestId);
        } catch {
          if (!cancelled) {
            setConnected(false);
            setError("Unable to load town state.");
          }
        }
      }

      await refresh();
      if (!cancelled) {
        timer = setInterval(() => void refresh(), 3000);
      }
    }

    void start();

    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
      game?.destroy(true);
    };
  }, []);

  async function sendMessage() {
    if (!selected || !message.trim() || sending) return;

    setSending(true);
    setNotice("");

    try {
      const response = await fetch("/api/visitor-message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          character_id: selected.id,
          message: message.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || "Send failed");
      }

      setMessage("");
      setNotice(
        `Message #${data.event_id} saved. ${selected.name} will reply on the next town cycle.`,
      );
    } catch (err) {
      setNotice(
        err instanceof Error ? err.message : "Unable to send message",
      );
    } finally {
      setSending(false);
    }
  }

  const characterEvents = selected
    ? recentEvents
        .filter(
          (event) =>
            event.actor === selected.id ||
            (event.type === "VISITOR_MESSAGE" &&
              event.payload.character_id === selected.id),
        )
        .slice(0, 8)
    : [];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm">
        <div className="flex flex-wrap items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="relative flex h-2.5 w-2.5">
              {connected && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-60" />
              )}
              <span
                className={`relative inline-flex h-2.5 w-2.5 rounded-full ${
                  connected ? "bg-green-400" : "bg-slate-500"
                }`}
              />
            </span>
            <span
              className={connected ? "text-green-400" : "text-slate-400"}
            >
              {connected ? "LIVE" : "OFFLINE"}
            </span>
          </span>
          <span className="font-mono tabular-nums text-slate-300">
            {clock || "--:--:--"}
          </span>
        </div>
        <span>Tick: {tick ?? "Loading..."}</span>
      </div>

      {error && <p className="text-sm text-red-300">{error}</p>}

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(280px,1fr)] xl:grid-cols-[minmax(0,2.8fr)_minmax(240px,1fr)_minmax(240px,1fr)]">
        <div className="min-w-0">
          <div
            ref={containerRef}
            className="aspect-[3/2] w-full overflow-hidden rounded-xl border-4 border-[#344b37]"
          />
          <p className="mt-2 text-center text-xs text-slate-400">
            Click a character to inspect them and send a message.
          </p>
        </div>

        <aside className="min-w-0 rounded-xl border border-emerald-500/20 bg-[#1d3028] p-4 text-white">
          <div className="mb-4 flex flex-wrap gap-2">
            {(["emma", "noah", "sophia"] as const).map((id) => (
              <button
                key={id}
                type="button"
                onClick={() => {
                  const character = latestWorldRef.current?.state.characters[id];
                  if (!character) return;

                  setSelected({
                    id,
                    name: character.name,
                    profession: character.profession,
                    location: character.location,
                    activity: character.activity,
                  });
                  setMessage("");
                  setNotice("");
                }}
                className={`rounded-lg border px-3 py-2 text-sm capitalize transition-colors ${
                  selected?.id === id
                    ? "border-emerald-400 bg-emerald-500/20 text-emerald-200"
                    : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
                }`}
              >
                {id}
              </button>
            ))}
          </div>
          {!selected ? (
            <div className="flex min-h-56 flex-col items-center justify-center gap-3 text-center">
              <span className="text-3xl">🏘️</span>
              <h2 className="text-lg font-semibold">
                Character inspector
              </h2>
              <p className="max-w-xs text-sm text-slate-300">
                Select Emma, Noah, or Sophia on the map to see
                their activity and send a visitor message.
              </p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-xl font-bold">{selected.name}</h2>
                <button
                  onClick={() => {
                    setSelected(null);
                    setMessage("");
                    setNotice("");
                  }}
                  className="text-sm text-slate-400 hover:text-white"
                >
                  Close
                </button>
              </div>

              <p className="mt-2 text-sm capitalize text-emerald-300">
                {selected.profession}
              </p>

              <p className="mt-1 text-sm text-slate-300">
                Location: {selected.location} · Activity: {selected.activity}
              </p>

              <div className="mt-5">
                <label
                  htmlFor="visitor-message"
                  className="text-sm font-semibold text-emerald-200"
                >
                  Send a message
                </label>

                <textarea
                  id="visitor-message"
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  maxLength={300}
                  rows={3}
                  placeholder={`Say something to ${selected.name}...`}
                  className="mt-2 w-full resize-none rounded-lg border border-emerald-500/20 bg-black/25 p-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-emerald-400"
                />

                <div className="mt-2 flex items-center justify-between">
                  <span className="text-xs text-slate-400">
                    {message.length}/300
                  </span>
                  <button
                    onClick={() => void sendMessage()}
                    disabled={sending || !message.trim()}
                    className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-[#10241a] hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {sending ? "Sending..." : "Send message"}
                  </button>
                </div>

                {notice && (
                  <p
                    role="status"
                    className="mt-3 text-sm text-emerald-200"
                  >
                    {notice}
                  </p>
                )}
              </div>

              <h3 className="mt-5 text-sm font-semibold text-emerald-200">
                Recent activity
              </h3>

              <div className="mt-2 max-h-[360px] space-y-2 overflow-y-auto pr-1">
                {characterEvents.map((event) => (
                  <div
                    key={event.id}
                    className="rounded-lg bg-black/20 px-3 py-2 text-sm"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-slate-400">
                        Tick {event.tick}
                      </span>
                      <span className="text-white">
                        {event.type.replaceAll("_", " ")}
                      </span>
                      <span className="text-xs text-slate-500">
                        #{event.id}
                      </span>
                    </div>

                    {typeof event.payload?.message === "string" && (
                      <p className="mt-1 break-words text-emerald-200">
                        {event.payload.message.replace(/\s*[—–]\s*/g, ", ")}
                      </p>
                    )}

                    {event.depends_on?.length > 0 && (
                      <p className="mt-1 text-xs text-sky-300">
                        ↳ In response to event #
                        {event.depends_on.join(", #")}
                      </p>
                    )}
                  </div>
                ))}

                {characterEvents.length === 0 && (
                  <p className="text-sm text-slate-400">
                    No recent activity recorded.
                  </p>
                )}
              </div>
            </>
          )}
        </aside>

        <TownLiveChat events={recentEvents} connected={connected} />
      </div>
    </div>
  );
}
