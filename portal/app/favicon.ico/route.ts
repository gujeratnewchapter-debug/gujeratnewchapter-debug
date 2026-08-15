import { NextResponse } from 'next/server';
import { readFileSync } from 'fs';
import { join } from 'path';

export async function GET() {
  try {
    const faviconPath = join(process.cwd(), 'public', 'favicon.svg');
    const svg = readFileSync(faviconPath, 'utf8');
    return new NextResponse(svg, {
      headers: {
        'Content-Type': 'image/svg+xml',
        'Cache-Control': 'public, max-age=3600',
      },
    });
  } catch (error) {
    return new NextResponse('Missing favicon asset', {
      status: 404,
      headers: { 'Content-Type': 'text/plain' },
    });
  }
}
