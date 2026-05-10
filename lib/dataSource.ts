import 'server-only';

import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { ZodError, type ZodType } from 'zod';

import {
  ForecastResponseSchema,
  LiveResponseSchema,
  NodesResponseSchema,
  ReplayResponseSchema,
} from './schemas';
import type { DataSource, ForecastResponse, LiveResponse, NodesResponse, ReplayResponse } from './types';
import {
  NodeNotFoundError,
  ReplayNotFoundError,
  SchemaError,
  SchemaVersionUnsupportedError,
  UpstreamError,
} from './errors';

export const VALID_LIVE_NODE_IDS = [
  'dominion-hub',
  'caiso-sp15',
  'caiso-np15',
  'ercot-houston',
] as const;
export const VALID_SYNTHETIC_NODE_IDS = [
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
] as const;
export const VALID_NODE_IDS = [...VALID_LIVE_NODE_IDS, ...VALID_SYNTHETIC_NODE_IDS] as const;
export const VALID_REPLAY_IDS = ['texas-2021', 'pjm-2023'] as const;

export type LiveNodeId = (typeof VALID_LIVE_NODE_IDS)[number];
export type SyntheticNodeId = (typeof VALID_SYNTHETIC_NODE_IDS)[number];
export type NodeId = (typeof VALID_NODE_IDS)[number];
export type ReplayId = (typeof VALID_REPLAY_IDS)[number];
export type DataSourceResult<T> = { data: T; fallbackUsed: boolean; stale: boolean };

const rawDataSource = process.env.GRIDCAST_DATA_SOURCE ?? 'fixtures';
export const activeDataSourceMode: DataSource = rawDataSource === 'cos' ? 'cos' : 'fixtures';
const cosBaseUrl = process.env.COS_BASE_URL;
const fixtureFallbackEnabled = process.env.GRIDCAST_ENABLE_FIXTURE_FALLBACK === 'true';
const maxFreshAgeMs = 25 * 60 * 60 * 1000;

if (activeDataSourceMode === 'cos' && !cosBaseUrl) {
  throw new Error('COS_BASE_URL must be set when GRIDCAST_DATA_SOURCE=cos');
}

function validateNodeId(id: string): NodeId {
  if (VALID_NODE_IDS.includes(id as NodeId)) {
    return id as NodeId;
  }

  throw new NodeNotFoundError(id);
}

function validateReplayId(id: string): ReplayId {
  if (VALID_REPLAY_IDS.includes(id as ReplayId)) {
    return id as ReplayId;
  }

  throw new ReplayNotFoundError(id);
}

async function readFixtureJson(objectPath: string): Promise<unknown> {
  const filePath = path.join(process.cwd(), 'fixtures', objectPath);
  const body = await readFile(filePath, 'utf8');

  try {
    return JSON.parse(body) as unknown;
  } catch (error) {
    throw new SchemaError(`Fixture '${objectPath}' is not valid JSON.`, { cause: error });
  }
}

async function readCosJson(objectPath: string): Promise<unknown> {
  const url = `${cosBaseUrl!.replace(/\/+$/, '')}/${objectPath}`;
  let response: Response;

  try {
    response = await fetch(url, { cache: 'no-store' });
  } catch (error) {
    throw new UpstreamError(`Failed to read '${objectPath}' from COS.`, { cause: error });
  }

  if (!response.ok) {
    throw new UpstreamError(`COS returned ${response.status} for '${objectPath}'.`);
  }

  try {
    return (await response.json()) as unknown;
  } catch (error) {
    throw new SchemaError(`COS object '${objectPath}' is not valid JSON.`, { cause: error });
  }
}

async function readJson(objectPath: string): Promise<{ raw: unknown; fallbackUsed: boolean }> {
  if (activeDataSourceMode === 'fixtures') {
    return { raw: await readFixtureJson(objectPath), fallbackUsed: false };
  }

  try {
    return { raw: await readCosJson(objectPath), fallbackUsed: false };
  } catch (error) {
    if (fixtureFallbackEnabled && error instanceof UpstreamError) {
      return { raw: await readFixtureJson(objectPath), fallbackUsed: true };
    }

    throw error;
  }
}

function assertSchemaVersion(raw: unknown, objectPath: string): void {
  if (!raw || typeof raw !== 'object' || !('schema_version' in raw)) {
    throw new SchemaError(`Payload '${objectPath}' is missing schema_version.`);
  }

  const version = (raw as { schema_version: unknown }).schema_version;

  if (version !== 1) {
    throw new SchemaVersionUnsupportedError(version);
  }
}

function validatePayload<T>(schema: ZodType<T>, raw: unknown, objectPath: string): T {
  assertSchemaVersion(raw, objectPath);

  try {
    return schema.parse(raw);
  } catch (error) {
    if (error instanceof ZodError) {
      throw new SchemaError(`Payload '${objectPath}' failed schema validation: ${error.message}`, { cause: error });
    }

    throw error;
  }
}

function isStale(timestamp: string): boolean {
  return Date.now() - Date.parse(timestamp) > maxFreshAgeMs;
}

async function loadValidated<T>(
  objectPath: string,
  schema: ZodType<T>,
  staleTimestamp: (data: T) => string | null,
): Promise<DataSourceResult<T>> {
  const { raw, fallbackUsed } = await readJson(objectPath);
  const data = validatePayload(schema, raw, objectPath);
  const timestamp = staleTimestamp(data);

  return {
    data,
    fallbackUsed,
    stale: timestamp ? isStale(timestamp) : false,
  };
}

export async function getNodes(): Promise<DataSourceResult<NodesResponse>> {
  return loadValidated('nodes.json', NodesResponseSchema, (data) => data.published_at);
}

export async function getForecast(id: string): Promise<DataSourceResult<ForecastResponse>> {
  const nodeId = validateNodeId(id);

  return loadValidated(`forecast/${nodeId}.json`, ForecastResponseSchema, (data) => data.published_at);
}

export async function getLive(id: string): Promise<DataSourceResult<LiveResponse>> {
  const nodeId = validateNodeId(id);

  return loadValidated(`live/${nodeId}.json`, LiveResponseSchema, (data) => data.fetched_at);
}

export async function getReplay(eventId: string): Promise<DataSourceResult<ReplayResponse>> {
  const replayId = validateReplayId(eventId);

  return loadValidated(`replay/${replayId}.json`, ReplayResponseSchema, () => null);
}

export {
  NodeNotFoundError,
  ReplayNotFoundError,
  SchemaError,
  SchemaVersionUnsupportedError,
  UpstreamError,
};
