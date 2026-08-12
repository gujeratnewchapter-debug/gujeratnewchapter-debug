import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { TechVisuals } from '@/components/TechVisuals';
import CursorImageTrail from '@/components/CursorImageTrail';

export const metadata: Metadata = {
  title: 'Ethiopian Startup School',
  description: 'Learn entrepreneurship, AI, and business — with an AI Tutor at every step.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="app-shell">
            <TechVisuals className="global-tech-visuals" />
            <CursorImageTrail />
            <Navbar />
            <main style={{ minHeight: '70vh' }}>{children}</main>
            <div className="woven-band" />
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  );
}
