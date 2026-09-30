import React from "react";

export default function GridLines({
  gap = 64,
  stroke = 1,
  majorEvery = 4,
  className = "",
  style = {},
}: {
  gap?: number;
  stroke?: number;
  majorEvery?: number;
  className?: string;
  style?: React.CSSProperties;
}) {
  const majorGap = gap * majorEvery;

  return (
    <div
      aria-hidden
      className={`pointer-events-none absolute inset-0 ${className}`}
      style={{
        backgroundImage: `
          linear-gradient(to right, rgba(255, 255, 255, 0.06) ${stroke}px, transparent ${stroke}px) ,
          linear-gradient(to bottom, rgba(255,255,255,.06) ${stroke}px, transparent ${stroke}px),
          linear-gradient(to right, rgba(255,255,255,.12) ${stroke}px, transparent ${stroke}px),
          linear-gradient(to bottom, rgba(255,255,255,.12) ${stroke}px, transparent ${stroke}px)
        `,
        backgroundSize: `
          ${gap}px ${gap}px,
          ${gap}px ${gap}px,
          ${majorGap}px ${majorGap}px,
          ${majorGap}px ${majorGap}px
        `,
        backgroundPosition: "center",
        ...style,
      }}
    />
  );
}
