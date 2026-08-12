'use client';

import { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useRouter } from 'next/navigation';

export function PageNavigation() {
  const router = useRouter();
  const [canGoBack, setCanGoBack] = useState(false);

  useEffect(() => {
    setCanGoBack(window.history.length > 1);
  }, []);

  return (
    <div className="page-nav-buttons" aria-label="Page navigation">
      <button
        type="button"
        className="page-nav-btn"
        onClick={() => router.back()}
        disabled={!canGoBack}
      >
        <ChevronLeft size={16} />
        Back
      </button>
      <button
        type="button"
        className="page-nav-btn"
        onClick={() => window.history.forward()}
      >
        Next
        <ChevronRight size={16} />
      </button>
    </div>
  );
}
