import { NextResponse } from 'next/server';

import { createRequestId, dataHeaders, errorResponse } from '@/lib/apiError';
import { getReplay } from '@/lib/dataSource';

type RouteContext = {
  params: Promise<{ event_id: string }>;
};

export async function GET(_request: Request, { params }: RouteContext) {
  const requestId = createRequestId();

  try {
    const { event_id } = await params;
    const result = await getReplay(event_id);

    return NextResponse.json(result.data, {
      headers: dataHeaders(result, requestId, 'public, max-age=86400'),
    });
  } catch (error) {
    return errorResponse(error, requestId);
  }
}
