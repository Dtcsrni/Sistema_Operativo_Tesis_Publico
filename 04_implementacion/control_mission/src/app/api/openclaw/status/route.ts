import { NextResponse } from 'next/server';
import { getOpenClawGatewayUrl } from '@/lib/openclaw/config';

export const dynamic = 'force-dynamic';

// GET /api/openclaw/status - Check OpenClaw connection status
export async function GET() {
  try {
    const gatewayUrl = getOpenClawGatewayUrl();
    const healthUrl = new URL('/health', gatewayUrl.replace(/^ws(s?):\/\//, 'http$1://'));
    const response = await fetch(healthUrl, { cache: 'no-store' });
    if (!response.ok) {
      return NextResponse.json({
        connected: false,
        error: `Gateway health check failed (${response.status})`,
        gateway_url: gatewayUrl,
      });
    }

    const health = await response.json();
    return NextResponse.json({
      connected: true,
      gateway_url: gatewayUrl,
      health,
    });
  } catch (error) {
    console.error('OpenClaw status check failed:', error);
    return NextResponse.json(
      {
        connected: false,
        error: 'Internal server error',
      },
      { status: 500 }
    );
  }
}
