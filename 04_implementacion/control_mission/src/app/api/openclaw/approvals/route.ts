import { NextResponse } from 'next/server';
import { getOpenClawGatewayUrl } from '@/lib/openclaw/config';

export const dynamic = 'force-dynamic';

function gatewayHttpUrl(pathname: string): URL {
  const baseUrl = getOpenClawGatewayUrl().replace(/^ws(s?):\/\//, 'http$1://');
  return new URL(pathname, baseUrl);
}

export async function GET() {
  try {
    const response = await fetch(gatewayHttpUrl('/approvals'), { cache: 'no-store' });
    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      return NextResponse.json(
        {
          status: 'error',
          error: payload?.error || `OpenClaw approvals request failed (${response.status})`,
        },
        { status: response.status },
      );
    }

    return NextResponse.json(payload);
  } catch (error) {
    console.error('OpenClaw approvals list failed:', error);
    return NextResponse.json({ status: 'error', error: 'openclaw_gateway_unavailable' }, { status: 502 });
  }
}

export async function DELETE() {
  try {
    const response = await fetch(gatewayHttpUrl('/approvals'), {
      method: 'DELETE',
      cache: 'no-store',
    });
    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      return NextResponse.json(
        {
          status: 'error',
          error: payload?.error || `OpenClaw approvals clear failed (${response.status})`,
        },
        { status: response.status },
      );
    }

    return NextResponse.json(payload);
  } catch (error) {
    console.error('OpenClaw approvals clear failed:', error);
    return NextResponse.json({ status: 'error', error: 'openclaw_gateway_unavailable' }, { status: 502 });
  }
}
