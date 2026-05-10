import { randomBytes } from 'node:crypto';
import { NextResponse } from 'next/server';

import { activeDataSourceMode } from './dataSource';
import { GridCastError } from './errors';
import type { ErrorEnvelope } from './types';

export function createRequestId(): string {
  return `req_${randomBytes(8).toString('hex')}`;
}

export function dataHeaders(result: { fallbackUsed: boolean; stale: boolean }, requestId: string, cacheControl: string): HeadersInit {
  return {
    'Cache-Control': cacheControl,
    'x-gridcast-request-id': requestId,
    'x-gridcast-stale': result.stale ? '1' : '0',
    'x-gridcast-fallback': result.fallbackUsed ? '1' : '0',
  };
}

export function errorResponse(error: unknown, requestId: string): NextResponse<ErrorEnvelope> {
  if (error instanceof GridCastError) {
    return NextResponse.json(
      {
        error: {
          code: error.code,
          message: error.message,
          source: activeDataSourceMode,
          request_id: requestId,
        },
      },
      { status: error.status },
    );
  }

  console.error(error);

  return NextResponse.json(
    {
      error: {
        code: 'INTERNAL_ERROR',
        message: 'Unexpected error',
        source: activeDataSourceMode,
        request_id: requestId,
      },
    },
    { status: 500 },
  );
}
