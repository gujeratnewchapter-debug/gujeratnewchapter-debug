'use client';

import { Lightbulb } from 'lucide-react';

export function InnovationLoader({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="innovation-loader" role="status" aria-live="polite" aria-label={label}>
      <span className="innovation-loader-orbit" aria-hidden="true" />
      <Lightbulb className="innovation-loader-bulb" aria-hidden="true" />
      <span className="innovation-loader-label">{label}<span className="innovation-loader-dots" aria-hidden="true">...</span></span>
    </div>
  );
}