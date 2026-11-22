"use client";

import { useState } from "react";
import { secondsToTime } from "@/lib/sensorState";

const DAY = 24 * 3600;
const W = 1440;

export interface TimelineSegment {
  start: number;
  end: number;
  label: string;
  color: string;
}

export interface TimelineMarker {
  t: number;
  tone: "high" | "medium" | "low";
  title: string;
}

const TONE = { high: "var(--danger)", medium: "var(--warning)", low: "#8a8a85" };

/** One day as a coloured band of activities, with alert markers and the current time. */
export function DayTimeline({
  segments,
  markers = [],
  now,
  onSeek,
}: {
  segments: TimelineSegment[];
  markers?: TimelineMarker[];
  now?: number;
  onSeek?: (second: number) => void;
}) {
  const x = (s: number) => (Math.max(0, Math.min(s, DAY)) / DAY) * W;
  const legend = [...new Map(segments.map((s) => [s.label, s.color])).entries()];
  // Hover readout instead of SVG <title> (which breaks server-rendered hydration).
  const [hover, setHover] = useState<string | null>(null);
  const hm = (t: number) => secondsToTime(t).slice(0, 5);

  return (
    <div>
      <svg
        viewBox={`0 0 ${W} 64`}
        className={`w-full ${onSeek ? "cursor-pointer" : ""}`}
        role="img"
        aria-label="Activities through the day"
        onClick={
          onSeek
            ? (e) => {
                const r = e.currentTarget.getBoundingClientRect();
                onSeek(((e.clientX - r.left) / r.width) * DAY);
              }
            : undefined
        }
      >
        <rect x={0} y={14} width={W} height={22} rx={4} fill="var(--surface-muted, #f1f1ee)" />
        {segments.map((s, i) => (
          <rect
            key={i}
            x={x(s.start)}
            y={14}
            width={Math.max(x(s.end) - x(s.start), 1)}
            height={22}
            fill={s.color}
            onMouseEnter={() => setHover(`${s.label} · ${hm(s.start)}–${hm(s.end)}`)}
            onMouseLeave={() => setHover(null)}
          />
        ))}
        {markers.map((m, i) => (
          <g key={i}>
            <line x1={x(m.t)} x2={x(m.t)} y1={6} y2={40} stroke={TONE[m.tone]} strokeWidth={2.5} />
            <circle
              cx={x(m.t)}
              cy={6}
              r={6}
              fill={TONE[m.tone]}
              onMouseEnter={() => setHover(`${hm(m.t)} · ${m.title}`)}
              onMouseLeave={() => setHover(null)}
            />
          </g>
        ))}
        {now !== undefined && now < DAY - 1 && (
          <line x1={x(now)} x2={x(now)} y1={8} y2={42} stroke="var(--foreground, #222)" strokeWidth={2} />
        )}
        {[0, 3, 6, 9, 12, 15, 18, 21].map((h) => (
          <text key={h} x={x(h * 3600) + 2} y={58} fontSize={13} fill="#8a8a85">
            {String(h).padStart(2, "0")}:00
          </text>
        ))}
      </svg>
      <p className="h-5 text-xs font-medium text-foreground">{hover ?? ""}</p>
      {legend.length > 0 && (
        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted">
          {legend.map(([label, color]) => (
            <span key={label} className="flex items-center gap-1">
              <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: color }} />
              {label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
