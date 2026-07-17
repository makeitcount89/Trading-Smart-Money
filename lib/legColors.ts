// lib/legColors.ts
// Shared per-strategy-leg color palette so every table/card that renders a dynamic list
// of strategy legs (BacktestMeta.strategyLegs) cycles through the same consistent colors
// by leg position, instead of each component hardcoding "Pure Proximity is blue, Guppy
// is green."

export interface LegColorClass {
  text: string;
  bgMuted: string; // Subtle row/section background tint
  toggleActive: string; // Active-state classes for a toggle/tab button
  border: string; // Card border accent
}

export const LEG_COLORS: LegColorClass[] = [
  { text: "text-smcBlue", bgMuted: "bg-smcBlue/5", toggleActive: "bg-smcBlue/20 text-smcBlue", border: "border-smcBlue/30" },
  { text: "text-emerald-400", bgMuted: "bg-emerald-950/10", toggleActive: "bg-emerald-400/20 text-emerald-400", border: "border-emerald-400/30" },
  { text: "text-amber-400", bgMuted: "bg-amber-950/10", toggleActive: "bg-amber-400/20 text-amber-400", border: "border-amber-400/30" },
  { text: "text-fuchsia-400", bgMuted: "bg-fuchsia-950/10", toggleActive: "bg-fuchsia-400/20 text-fuchsia-400", border: "border-fuchsia-400/30" },
];

export function legColorClass(index: number): LegColorClass {
  return LEG_COLORS[index % LEG_COLORS.length];
}
