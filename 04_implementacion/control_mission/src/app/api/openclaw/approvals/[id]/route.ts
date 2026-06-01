import { NextRequest, NextResponse } from 'next/server';
import { getOpenClawGatewayUrl } from '@/lib/openclaw/config';

export const dynamic = 'force-dynamic';

function gatewayHttpUrl(pathname: string): URL {
  const baseUrl = getOpenClawGatewayUrl().replace(/^ws(s?):\/\//, 'http$1://');
  return new URL(pathname, baseUrl);
}

export async function POST(request: NextRequest, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  const payload = await request.json().catch(() => ({}));
  const requestedStatus = typeof payload?.status === 'string' ? payload.status.trim().toLowerCase() : 'approved';
  const status = ['approved', 'rejected', 'failed'].includes(requestedStatus) ? requestedStatus : 'approved';

  try {
    const response = await fetch(gatewayHttpUrl(`/approvals/${encodeURIComponent(id)}`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
      cache: 'no-store',
    });
    const responsePayload = await response.json().catch(() => ({}));

    if (!response.ok || responsePayload?.status !== 'ok') {
      return NextResponse.json(
        {
          status: 'error',
          error: responsePayload?.error || 'approval_update_failed',
        },
        { status: response.ok ? 404 : response.status },
      );
    }

    return NextResponse.json({ status: 'ok', approval_id: id, approval_status: status });
  } catch (error) {
    console.error('OpenClaw approval update failed:', error);
    return NextResponse.json({ status: 'error', error: 'openclaw_gateway_unavailable' }, { status: 502 });
  }
}
