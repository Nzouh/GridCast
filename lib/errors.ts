import type { ErrorCode } from './types';

export abstract class GridCastError extends Error {
  abstract readonly code: ErrorCode;
  abstract readonly status: number;
}

export class NodeNotFoundError extends GridCastError {
  readonly code = 'NODE_NOT_FOUND';
  readonly status = 404;

  constructor(id: string) {
    super(`Node '${id}' is not a known id.`);
    this.name = 'NodeNotFoundError';
  }
}

export class ReplayNotFoundError extends GridCastError {
  readonly code = 'REPLAY_NOT_FOUND';
  readonly status = 404;

  constructor(id: string) {
    super(`Replay '${id}' is not a known event id.`);
    this.name = 'ReplayNotFoundError';
  }
}

export class UpstreamError extends GridCastError {
  readonly code = 'UPSTREAM_UNAVAILABLE';
  readonly status = 502;

  constructor(message = 'Upstream data source is unavailable.', options?: ErrorOptions) {
    super(message, options);
    this.name = 'UpstreamError';
  }
}

export class SchemaError extends GridCastError {
  readonly code = 'SCHEMA_INVALID';
  readonly status = 500;

  constructor(message = 'Data source payload failed schema validation.', options?: ErrorOptions) {
    super(message, options);
    this.name = 'SchemaError';
  }
}

export class SchemaVersionUnsupportedError extends GridCastError {
  readonly code = 'SCHEMA_VERSION_UNSUPPORTED';
  readonly status = 500;

  constructor(version: unknown) {
    super(`Schema version '${String(version)}' is not supported.`);
    this.name = 'SchemaVersionUnsupportedError';
  }
}
