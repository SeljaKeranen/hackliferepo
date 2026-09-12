import type { Report } from "./funding-types";
export function downloadFundingCard(
  r: Report,
  reportUrl: string,
  releaseId: string,
) {
  const s = r.summary;
  if (!r.publication_ready || !s || s.ratio === null) return;
  const canvas = document.createElement("canvas");
  canvas.width = 1200;
  canvas.height = 630;
  const g = canvas.getContext("2d")!;
  const pct = (v: number | null) =>
    v === null ? "unavailable" : `${(v * 100).toFixed(1)}%`;
  const text = (
    value: string,
    x: number,
    y: number,
    size: number,
    color = "#173d34",
  ) => {
    g.fillStyle = color;
    g.font = `${size}px Inter, sans-serif`;
    g.fillText(value, x, y);
  };
  const wrap = (
    value: string,
    x: number,
    y: number,
    size: number,
    max: number,
    lineHeight: number,
  ) => {
    g.font = `${size}px Inter, sans-serif`;
    let line = "";
    for (const char of value) {
      if (g.measureText(line + char).width > max) {
        text(line, x, y, size);
        line = "";
        y += lineHeight;
      }
      line += char;
    }
    if (line) text(line, x, y, size);
    return y;
  };
  g.fillStyle = "#f7f6f0";
  g.fillRect(0, 0, 1200, 630);
  text("LONGVIEW / AGEING RESEARCH FUNDING", 55, 55, 18, "#73866a");
  text(r.name, 55, 138, 52);
  text(pct(s.ratio), 55, 268, 110);
  text("of classified ageing research award funding", 58, 322, 24);
  text("targets biology or ageing interventions", 58, 356, 24);
  wrap(r.label, 58, 414, 17, 700, 24);
  text(r.period, 58, 452, 15);
  text(
    `Known-amount sensitivity: ${pct(s.sensitivity_lower)}–${pct(s.sensitivity_upper)}`,
    58,
    486,
    16,
  );
  text(
    "Classification scenarios, not confidence intervals. Missing amounts excluded.",
    58,
    509,
    13,
    "#73866a",
  );
  const biology = s.biology_only_ratio || 0,
    bi = Math.round(biology * 100),
    both = Math.round(s.ratio * 100);
  for (let i = 0; i < 100; i++) {
    g.fillStyle = i < bi ? "#245c44" : i < both ? "#8bab61" : "#e7dfcd";
    g.fillRect(846 + (i % 10) * 25, 186 + Math.floor(i / 10) * 25, 19, 19);
  }
  text(`Biology ${pct(biology)}`, 846, 473, 15);
  text(`Interventions ${pct(s.ratio - biology)}`, 846, 499, 15);
  g.strokeStyle = "#d9ded3";
  g.beginPath();
  g.moveTo(55, 537);
  g.lineTo(1145, 537);
  g.stroke();
  text(
    r.country === "SE"
      ? "Multi-year commitments. Selected funders; not a national spending total."
      : "Fiscal-year awards, with multi-year exceptions. Selected portfolio; not a national total.",
    58,
    558,
    13,
    "#73866a",
  );
  wrap(`Sources and method: ${reportUrl}`, 58, 585, 12, 1080, 18);
  const a = document.createElement("a");
  a.href = canvas.toDataURL();
  a.download = `longview-${r.country.toLowerCase()}-${releaseId}.png`;
  a.click();
}
