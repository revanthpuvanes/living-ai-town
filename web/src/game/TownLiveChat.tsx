"use client";

import { useEffect, useRef } from "react";

type ChatEvent = {
  id: number;
  tick: number;
  actor: string;
  type: string;
  payload: {
    message?: string;
  };
};

type Props = {
  events: ChatEvent[];
  connected: boolean;
};

const characters: Record<string, {
  name: string;
  emoji: string;
  color: string;
}> = {
  emma: {
    name: "Emma",
    emoji: "🥐",
    color: "text-emerald-300",
  },
  noah: {
    name: "Noah",
    emoji: "📚",
    color: "text-sky-300",
  },
  sophia: {
    name: "Sophia",
    emoji: "🛍️",
    color: "text-pink-300",
  },
};

export default function TownLiveChat({ events, connected }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const followLatestRef = useRef(true);

  const messages = events
    .filter(
      (event) =>
        (event.type === "CONVERSATION_SPOKEN" ||
          event.type === "VISITOR_REPLY") &&
        typeof event.payload?.message === "string" &&
        Boolean(characters[event.actor]),
    )
    .sort((a, b) => a.id - b.id);

  const newestId = messages.at(-1)?.id;

  useEffect(() => {
    if (followLatestRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [newestId]);

  return (
    <aside className="flex min-h-[420px] min-w-0 flex-col rounded-xl border border-emerald-500/20 bg-[#1d3028] p-4 text-white lg:h-[640px]">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-bold">Town Live Chat</h2>
          <p className="mt-1 text-xs text-slate-400">
            Conversations across the town
          </p>
        </div>
        <span className={`flex items-center gap-1.5 text-xs ${
          connected ? "text-emerald-300" : "text-slate-400"
        }`}>
          <span className={`h-2 w-2 rounded-full ${
            connected ? "bg-emerald-400" : "bg-slate-500"
          }`} />
          {connected ? "LIVE" : "OFFLINE"}
        </span>
      </div>

      <div className="my-4 border-t border-white/10" />

      <div
        ref={scrollRef}
        onScroll={(event) => {
          const element = event.currentTarget;
          const distance =
            element.scrollHeight -
            element.scrollTop -
            element.clientHeight;
          followLatestRef.current = distance < 60;
        }}
        className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-2"
      >
        {messages.length === 0 ? (
          <p className="text-sm text-slate-400">
            Waiting for the town's next conversation...
          </p>
        ) : (
          messages.map((event) => {
            const character = characters[event.actor];

            return (
              <div key={event.id} className="text-sm">
                <div className="flex items-center gap-2">
                  <span className={`font-semibold ${character.color}`}>
                    {character.emoji} {character.name}
                  </span>
                  <span className="text-xs text-slate-500">
                    Tick {event.tick}
                  </span>
                </div>
                <p className="mt-1 break-words leading-relaxed text-slate-200">
                  {event.payload.message?.replace(/\s*[—–]\s*/g, ", ")}
                </p>
              </div>
            );
          })
        )}
      </div>

      <div className="mt-4 border-t border-white/10 pt-3 text-center text-xs text-slate-400">
        Autonomous conversations · Live updates
      </div>
    </aside>
  );
}
