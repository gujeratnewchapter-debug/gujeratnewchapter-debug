'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, ArrowRight } from 'lucide-react';

import { getNews } from '@/lib/api';
import { NewsArticleCard, type NewsArticle } from '@/components/NewsArticleCard';

export default function NewsIndexPage() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const loadArticles = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const response = await getNews();
      setArticles(response.data);
    } catch (requestError) {
      console.error('Failed to load news articles:', requestError);
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadArticles();
  }, [loadArticles]);

  return (
    <div className="news-page">
      <section className="news-index-hero">
        <div className="container">
          <Link href="/" className="news-back-link"><ArrowLeft size={16} aria-hidden="true" /> Home</Link>
          <p className="news-eyebrow">The Ethiopian Startup School journal</p>
          <h1>News &amp; ideas<br /><span>for what’s next.</span></h1>
          <p className="news-index-intro">
            Stories and updates for founders learning, experimenting, and building with purpose.
          </p>
          {!loading && !error && articles.length > 0 && (
            <p className="news-index-count">{articles.length} {articles.length === 1 ? 'story' : 'stories'}</p>
          )}
        </div>
        <div className="news-index-motif" aria-hidden="true"><span /><span /><span /></div>
      </section>

      <section className="container news-index-content" aria-label="Published news articles">
        {loading ? (
          <p className="news-state" role="status">Loading stories…</p>
        ) : error ? (
          <div className="news-state news-state-error" role="alert">
            <span>The newsroom is temporarily unavailable.</span>
            <button type="button" className="news-retry" onClick={() => void loadArticles()}>Try again</button>
          </div>
        ) : articles.length === 0 ? (
          <div className="news-empty-state">
            <span className="news-empty-mark" aria-hidden="true">ESS</span>
            <h2>A story is taking shape.</h2>
            <p>There are no published articles just yet. Come back soon for news from the school.</p>
            <Link href="/" className="news-view-all">Return home <ArrowRight size={17} aria-hidden="true" /></Link>
          </div>
        ) : (
          <>
            <div className="news-index-feature">
              <NewsArticleCard article={articles[0]} featured />
              <div className="news-index-feature-note" aria-hidden="true">
                <span>01 / {String(articles.length).padStart(2, '0')}</span>
                <span>Latest from the school</span>
              </div>
            </div>
            {articles.length > 1 && (
              <div className="news-index-grid">
                {articles.slice(1).map((article) => <NewsArticleCard key={article.id} article={article} />)}
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
