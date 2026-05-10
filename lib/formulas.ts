export function stressLevel(p: number): 'green' | 'amber' | 'red' {
  if (p < 0.2) return 'green';
  if (p < 0.5) return 'amber';
  return 'red';
}

export function allocationPct(p90StressFraction: number): number {
  return Math.round((1 - p90StressFraction) * 100);
}

type Quantiles = {
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
};

const QUANTILE_POINTS = [
  ['p10', 0.1],
  ['p25', 0.25],
  ['p50', 0.5],
  ['p75', 0.75],
  ['p90', 0.9],
] as const;

export function stressFromQuantiles(quantiles: Quantiles, threshold: number): number {
  if (threshold <= quantiles.p10) return 1;

  for (let i = 0; i < QUANTILE_POINTS.length - 1; i += 1) {
    const [lowKey, lowProbability] = QUANTILE_POINTS[i];
    const [highKey, highProbability] = QUANTILE_POINTS[i + 1];
    const lowValue = quantiles[lowKey];
    const highValue = quantiles[highKey];

    if (threshold <= highValue) {
      if (highValue === lowValue) {
        return 1 - highProbability;
      }

      const fraction = (threshold - lowValue) / (highValue - lowValue);
      const cdf = lowProbability + (highProbability - lowProbability) * fraction;
      return Math.max(0, Math.min(1, 1 - cdf));
    }
  }

  const p75 = quantiles.p75;
  const p90 = quantiles.p90;
  if (p90 <= p75) return 0;

  const p99 = p90 + ((p90 - p75) / (0.9 - 0.75)) * (0.99 - 0.9);
  if (threshold >= p99) return 0;

  const cdf = 0.9 + ((0.99 - 0.9) * (threshold - p90)) / (p99 - p90);
  return Math.max(0, Math.min(1, 1 - cdf));
}
