import { NextResponse } from 'next/server';

import { createRequestId, dataHeaders, errorResponse } from '@/lib/apiError';
import { getForecast } from '@/lib/dataSource';

export const dynamic = 'force-dynamic';

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(_request: Request, { params }: RouteContext) {
  const requestId = createRequestId();

  try {
    const { id } = await params;
    const result = await getForecast(id);

    return NextResponse.json(result.data, {
      headers: dataHeaders(result, requestId, 'no-store'),
    });
  } catch (error) {
    return errorResponse(error, requestId);
  }
}
