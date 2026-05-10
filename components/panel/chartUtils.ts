export function minMax(values: number[]): [number, number] {
  const finite = values.filter(Number.isFinite);
  if (finite.length === 0) return [0, 1];
  let min = Math.min(...finite);
  let max = Math.max(...finite);
  if (min === max) {
    min -= 1;
    max += 1;
  }
  return [min, max];
}

export function scaleLinear(value: number, domain: [number, number], range: [number, number]): number {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  return r0 + ((value - d0) / (d1 - d0)) * (r1 - r0);
}

export function linePath(points: Array<[number, number]>): string {
  return points.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`).join(' ');
}

export function smoothLine(points: Array<[number, number]>): string {
  if (points.length === 0) return '';
  if (points.length < 3) return linePath(points);

  let d = `M${points[0][0].toFixed(2)},${points[0][1].toFixed(2)}`;

  for (let i = 0; i < points.length - 1; i += 1) {
    const p0 = points[i - 1] ?? points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] ?? p2;
    const cp1x = p1[0] + (p2[0] - p0[0]) / 6;
    const cp1y = p1[1] + (p2[1] - p0[1]) / 6;
    const cp2x = p2[0] - (p3[0] - p1[0]) / 6;
    const cp2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C${cp1x.toFixed(2)},${cp1y.toFixed(2)} ${cp2x.toFixed(2)},${cp2y.toFixed(2)} ${p2[0].toFixed(2)},${p2[1].toFixed(2)}`;
  }

  return d;
}

export function areaPath(upper: Array<[number, number]>, lower: Array<[number, number]>): string {
  if (upper.length === 0 || lower.length === 0) return '';
  const top = linePath(upper);
  const bottom = lower
    .slice()
    .reverse()
    .map(([x, y]) => `L${x.toFixed(2)},${y.toFixed(2)}`)
    .join(' ');
  return `${top} ${bottom} Z`;
}

export function smoothBand(lower: Array<[number, number]>, upper: Array<[number, number]>): string {
  if (lower.length === 0 || upper.length === 0) return '';
  const top = smoothLine(upper);
  const bottom = smoothLine(lower.slice().reverse()).replace(/^M/, 'L');
  return `${top} ${bottom} Z`;
}

export function formatMw(value: number): string {
  if (Math.abs(value) >= 1000) {
    return `${(value / 1000).toFixed(1)} GW`;
  }
  return `${Math.round(value).toLocaleString()} MW`;
}
