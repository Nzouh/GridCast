export function stressLevel(p: number): 'green' | 'amber' | 'red' {
  if (p < 0.2) return 'green';
  if (p < 0.5) return 'amber';
  return 'red';
}

export function allocationPct(p90StressFraction: number): number {
  return Math.round((1 - p90StressFraction) * 100);
}
