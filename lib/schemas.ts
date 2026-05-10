import 'server-only';

import { z } from 'zod';

const HORIZON_HOURS = 240;
const ENCODER_HOURS = 168;
const ENSEMBLE_MEMBERS = 16;

const finiteNumber = z.number().finite();
const probability = finiteNumber.min(0).max(1);
const pct = finiteNumber.min(0).max(100);
const isoTimestamp = z
  .string()
  .datetime({ offset: true })
  .refine((value) => value.endsWith('Z'), { message: 'timestamp must be UTC with Z suffix' });
const source = z.enum(['fixtures', 'cos']);
const nodeId = z.enum([
  'dominion-hub',
  'caiso-sp15',
  'caiso-np15',
  'ercot-houston',
  'miso-indiana-hub',
  'miso-illinois-hub',
  'spp-north-hub',
  'spp-south-hub',
  'nyiso-zone-j',
  'nyiso-zone-a',
  'iso-ne-mass-hub',
  'pjm-western-hub',
  'pjm-aep-dayton',
  'ercot-north',
  'ercot-west',
  'caiso-zp26',
  'bpa-pnw',
  'duke-carolinas',
  'tva-tennessee',
  'fpl-florida',
]);
const replayId = z.enum(['texas-2021', 'pjm-2023']);

function timestampsAreSortedWithNoWideGaps(timestamps: string[]): boolean {
  let previous = Number.NEGATIVE_INFINITY;

  for (const timestamp of timestamps) {
    const current = Date.parse(timestamp);

    if (!Number.isFinite(current) || current <= previous) {
      return false;
    }

    if (Number.isFinite(previous) && current - previous > 2 * 60 * 60 * 1000) {
      return false;
    }

    previous = current;
  }

  return true;
}

const sortedTimestamps = (length: number) =>
  z
    .array(isoTimestamp)
    .length(length)
    .refine(timestampsAreSortedWithNoWideGaps, {
      message: 'timestamps must be sorted ascending with no gap greater than 2h',
    });

const quantileSeriesSchema = z
  .object({
    target: z.literal('demand_mw'),
    unit: z.literal('MW'),
    timestamps: sortedTimestamps(HORIZON_HOURS),
    p10: z.array(finiteNumber).length(HORIZON_HOURS),
    p25: z.array(finiteNumber).length(HORIZON_HOURS),
    p50: z.array(finiteNumber).length(HORIZON_HOURS),
    p75: z.array(finiteNumber).length(HORIZON_HOURS),
    p90: z.array(finiteNumber).length(HORIZON_HOURS),
  })
  .refine(
    (series) =>
      series.p10.every(
        (p10, i) =>
          p10 <= series.p25[i] &&
          series.p25[i] <= series.p50[i] &&
          series.p50[i] <= series.p75[i] &&
          series.p75[i] <= series.p90[i],
      ),
    { message: 'forecast quantiles must be monotonic at every index' },
  );

const historySeriesSchema = z.object({
  timestamps: sortedTimestamps(ENCODER_HOURS),
  demand_mw: z.array(finiteNumber).length(ENCODER_HOURS),
});

const overlaySeriesSchema = z
  .object({
    timestamps: z.array(isoTimestamp).max(HORIZON_HOURS).refine(timestampsAreSortedWithNoWideGaps, {
      message: 'actuals overlay timestamps must be sorted ascending with no gap greater than 2h',
    }),
    demand_mw: z.array(finiteNumber).max(HORIZON_HOURS),
  })
  .refine((series) => series.timestamps.length === series.demand_mw.length, {
    message: 'actuals overlay timestamps and values must have equal length',
  });

const allocationSchema = z
  .object({
    pct,
    pct_p50: pct,
    pct_p10: pct,
    p90_stress_fraction: probability,
  })
  .refine((allocation) => allocation.pct <= allocation.pct_p50 && allocation.pct_p50 <= allocation.pct_p10, {
    message: 'allocation pct must satisfy pct <= pct_p50 <= pct_p10',
  });

const stressTimelinePointSchema = z.object({
  hour_offset: z.number().int().min(0).max(HORIZON_HOURS - 1),
  stress_probability: probability,
});

const ensembleSpreadSchema = z
  .object({
    variable: z.literal('temperature_2m'),
    unit: z.literal('celsius'),
    timestamps: sortedTimestamps(HORIZON_HOURS),
    members: z.array(z.array(finiteNumber).length(HORIZON_HOURS)).length(ENSEMBLE_MEMBERS),
  })
  .refine((spread) => spread.members.every((member) => member.length === spread.timestamps.length), {
    message: 'ensemble members must align with timestamps',
  });

const dataCenterSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  operator: z.string().min(1),
  tier: z.enum(['large', 'medium', 'small']),
  capacity_mw: finiteNumber.positive(),
  committed_draw_mw: z.object({
    p10: finiteNumber.min(0),
    p50: finiteNumber.min(0),
    p90: finiteNumber.min(0),
  }),
});

export const NodeSchema = z.object({
  id: nodeId,
  name: z.string().min(1),
  iso: z.string().min(1),
  state: z.string().min(1),
  ba_code: z.string().min(1),
  lat: finiteNumber,
  lon: finiteNumber,
  stress_probability: probability,
  allocation_pct: pct,
  is_live: z.boolean(),
});

export const NodesResponseSchema = z.object({
  schema_version: z.literal(1),
  issued_at: isoTimestamp,
  published_at: isoTimestamp,
  source,
  nodes: z.array(NodeSchema).min(4),
});

const forecastBaseObjectSchema = z.object({
  node_id: nodeId,
  schema_version: z.literal(1),
  issued_at: isoTimestamp,
  published_at: isoTimestamp,
  source,
  horizon_hours: z.literal(HORIZON_HOURS),
  encoder_hours: z.literal(ENCODER_HOURS),
  quantile_levels: z.tuple([
    z.literal(0.1),
    z.literal(0.25),
    z.literal(0.5),
    z.literal(0.75),
    z.literal(0.9),
  ]),
  stress_threshold_demand_mw: finiteNumber,
  history: historySeriesSchema,
  forecast: quantileSeriesSchema,
  allocation: allocationSchema,
  stress_timeline: z.array(stressTimelinePointSchema).length(HORIZON_HOURS),
  ensemble_spread: ensembleSpreadSchema,
  data_centers: z.array(dataCenterSchema).length(3),
});

type ForecastRefinable = z.infer<typeof forecastBaseObjectSchema>;

const withForecastRefinements = <Schema extends z.ZodTypeAny>(schema: Schema) =>
  schema.superRefine((payload: z.infer<Schema>, ctx) => {
    const forecastPayload = payload as ForecastRefinable;

    if (!forecastPayload.ensemble_spread.timestamps.every((t, i) => t === forecastPayload.forecast.timestamps[i])) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'ensemble timestamps must match forecast timestamps',
        path: ['ensemble_spread', 'timestamps'],
      });
    }

    if (!forecastPayload.stress_timeline.every((point, i) => point.hour_offset === i)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'stress timeline hour offsets must be contiguous from zero',
        path: ['stress_timeline'],
      });
    }
  });

export const ForecastResponseSchema = withForecastRefinements(forecastBaseObjectSchema);

export const LiveResponseSchema = z.object({
  node_id: nodeId,
  schema_version: z.literal(1),
  fetched_at: isoTimestamp,
  source,
  eia: z.object({
    demand_mw: finiteNumber,
    demand_forecast_mw: finiteNumber,
    demand_deviation_pct: finiteNumber,
  }),
  weather: z.object({
    temperature_2m_c: finiteNumber,
    wind_speed_10m_ms: finiteNumber,
    ensemble_member_count: z.literal(ENSEMBLE_MEMBERS),
  }),
});

export const ReplayResponseSchema = withForecastRefinements(
  forecastBaseObjectSchema.extend({
    event_id: replayId,
    event_name: z.string().min(1),
    actual_event_date: isoTimestamp,
    narrative: z.string().min(1),
    actuals_overlay: overlaySeriesSchema,
  }),
).refine((payload) => payload.actuals_overlay.timestamps.every((t: string, i: number) => t === payload.forecast.timestamps[i]), {
  message: 'actuals overlay timestamps must align with forecast timestamps',
});

export const ErrorEnvelopeSchema = z.object({
  error: z.object({
    code: z.enum([
      'NODE_NOT_FOUND',
      'REPLAY_NOT_FOUND',
      'UPSTREAM_UNAVAILABLE',
      'SCHEMA_INVALID',
      'SCHEMA_VERSION_UNSUPPORTED',
      'INTERNAL_ERROR',
    ]),
    message: z.string().min(1),
    source,
    request_id: z.string().min(1),
  }),
});
