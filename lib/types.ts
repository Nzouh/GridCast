export type ISOTimeString = string;

export type LiveNodeId = 'dominion-hub' | 'caiso-sp15' | 'caiso-np15' | 'ercot-houston';
export type SyntheticNodeId =
  | 'miso-indiana-hub'
  | 'miso-illinois-hub'
  | 'spp-north-hub'
  | 'spp-south-hub'
  | 'nyiso-zone-j'
  | 'nyiso-zone-a'
  | 'iso-ne-mass-hub'
  | 'pjm-western-hub'
  | 'pjm-aep-dayton'
  | 'ercot-north'
  | 'ercot-west'
  | 'caiso-zp26'
  | 'bpa-pnw'
  | 'duke-carolinas'
  | 'tva-tennessee'
  | 'fpl-florida';
export type NodeId = LiveNodeId | SyntheticNodeId;
export type ReplayId = 'texas-2021' | 'pjm-2023';
export type StressLevel = 'green' | 'amber' | 'red';
export type DataSource = 'fixtures' | 'cos';
export type DataCenterTier = 'large' | 'medium' | 'small';

export type Node = {
  id: NodeId;
  name: string;
  iso: string;
  state: string;
  ba_code: string;
  lat: number;
  lon: number;
  stress_probability: number;
  allocation_pct: number;
  is_live: boolean;
};

export type NodesResponse = {
  schema_version: 1;
  issued_at: ISOTimeString;
  published_at: ISOTimeString;
  source: DataSource;
  nodes: Node[];
};

export type QuantileSeries = {
  target: 'demand_mw';
  unit: 'MW';
  timestamps: ISOTimeString[];
  p10: number[];
  p25: number[];
  p50: number[];
  p75: number[];
  p90: number[];
};

export type HistorySeries = {
  timestamps: ISOTimeString[];
  demand_mw: number[];
};

export type Allocation = {
  pct: number;
  pct_p50: number;
  pct_p10: number;
  p90_stress_fraction: number;
};

export type StressTimelinePoint = {
  hour_offset: number;
  stress_probability: number;
};

export type EnsembleSpread = {
  variable: 'temperature_2m';
  unit: 'celsius';
  timestamps: ISOTimeString[];
  members: number[][];
};

export type DataCenter = {
  id: string;
  name: string;
  operator: string;
  tier: DataCenterTier;
  capacity_mw: number;
  committed_draw_mw: {
    p10: number;
    p50: number;
    p90: number;
  };
};

export type ForecastResponse = {
  node_id: NodeId;
  schema_version: 1;
  issued_at: ISOTimeString;
  published_at: ISOTimeString;
  source: DataSource;
  horizon_hours: 240;
  encoder_hours: 168;
  quantile_levels: [0.1, 0.25, 0.5, 0.75, 0.9];
  stress_threshold_demand_mw: number;
  history: HistorySeries;
  forecast: QuantileSeries;
  allocation: Allocation;
  stress_timeline: StressTimelinePoint[];
  ensemble_spread: EnsembleSpread;
  data_centers: DataCenter[];
};

export type LiveResponse = {
  node_id: NodeId;
  schema_version: 1;
  fetched_at: ISOTimeString;
  source: DataSource;
  eia: {
    demand_mw: number;
    demand_forecast_mw: number;
    demand_deviation_pct: number;
  };
  weather: {
    temperature_2m_c: number;
    wind_speed_10m_ms: number;
    ensemble_member_count: 16;
  };
};

export type ReplayResponse = ForecastResponse & {
  event_id: ReplayId;
  event_name: string;
  actual_event_date: ISOTimeString;
  narrative: string;
  actuals_overlay: HistorySeries;
};

export type ForecastPoint = {
  t: ISOTimeString;
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
};

export type ErrorCode =
  | 'NODE_NOT_FOUND'
  | 'REPLAY_NOT_FOUND'
  | 'UPSTREAM_UNAVAILABLE'
  | 'SCHEMA_INVALID'
  | 'SCHEMA_VERSION_UNSUPPORTED'
  | 'INTERNAL_ERROR';

export type ErrorEnvelope = {
  error: {
    code: ErrorCode;
    message: string;
    source: DataSource;
    request_id: string;
  };
};
