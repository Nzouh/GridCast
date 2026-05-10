import { NextResponse } from 'next/server';

import { createRequestId, dataHeaders, errorResponse } from '@/lib/apiError';
import { getNodes } from '@/lib/dataSource';

export const dynamic = 'force-dynamic';

export async function GET() {
  const requestId = createRequestId();

  try {
    const result = await getNodes();

    return NextResponse.json(result.data, {
      headers: dataHeaders(result, requestId, 'no-store'),
    });
  } catch (error) {
    return errorResponse(error, requestId);
  }
}
