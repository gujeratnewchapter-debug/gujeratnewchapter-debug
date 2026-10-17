'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

import { getNotices, type Notice } from '@/lib/api';
import { formatNoticeDate } from '@/lib/notices';

export default function NoticesPage() {
  const [notices, setNotices] = useState<Notice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const loadNotices = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const response = await getNotices();
      setNotices(response.data);
    } catch (requestError) {
      console.error('Failed to load notices:', requestError);
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadNotices();
  }, [loadNotices]);

  return (
    <main className="notices-page">
      <header className="notices-hero">
        <div className="container notices-hero-inner">
          <Link href="/" className="news-back-link">
            <ArrowLeft size={16} aria-hidden="true" /> Home
          </Link>
          <p className="news-eyebrow">Updates from the school</p>
          <h1>Notices</h1>
          <p className="notices-intro">
            Important updates and announcements from Ethiopian Startup School.
          </p>
        </div>
      </header>

      <section className="container notices-content" aria-label="Published notices">
        {loading ? (
          <p className="news-state" role="status">Loading notices…</p>
        ) : error ? (
          <div className="news-state news-state-error" role="alert">
            <span>Notices are temporarily unavailable.</span>
            <button type="button" className="news-retry" onClick={() => void loadNotices()}>Try again</button>
          </div>
        ) : notices.length === 0 ? (
          <div className="notices-empty">
            <span className="notices-empty-mark" aria-hidden="true">ESS</span>
            <h2>No published notices</h2>
            <p>There are no current announcements. Please check back later.</p>
          </div>
        ) : (
          <div className="notices-list">
            {notices.map((notice) => (
              <article className="notice-entry" key={notice.id}>
                <div className="notice-entry-meta">
                  <span>School notice</span>
                  <time dateTime={notice.created_at}>{formatNoticeDate(notice.created_at)}</time>
                </div>
                <div className="notice-entry-copy">
                  <h2>{notice.title}</h2>
                  <p>{notice.body}</p>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
