import { NextResponse } from 'next/server';

import { createRequestId, dataHeaders, errorResponse } from '@/lib/apiError';
import { getLive } from '@/lib/dataSource';

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(_request: Request, { params }: RouteContext) {
  const requestId = createRequestId();

  try {
    const { id } = await params;
    const result = await getLive(id);

    return NextResponse.json(result.data, {
      headers: dataHeaders(result, requestId, 's-maxage=60, stale-while-revalidate=120'),
    });
  } catch (error) {
    return errorResponse(error, requestId);
  }
}
