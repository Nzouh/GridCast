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

export function formatMw(value: number): string {
  if (Math.abs(value) >= 1000) {
    return `${(value / 1000).toFixed(1)} GW`;
  }
  return `${Math.round(value).toLocaleString()} MW`;
}
