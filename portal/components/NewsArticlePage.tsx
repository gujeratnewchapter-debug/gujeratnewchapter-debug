'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, ArrowUpRight } from 'lucide-react';

import { ApiImage } from '@/components/ApiImage';
import { getNews, getNewsArticle, resolveMediaUrl } from '@/lib/api';
import { NewsArticleCard, formatNewsDate, type NewsArticle } from '@/components/NewsArticleCard';

type ArticleState = 'loading' | 'ready' | 'missing' | 'error';

export default function NewsArticlePage({ slug }: { slug: string }) {
  const [article, setArticle] = useState<NewsArticle | null>(null);
  const [related, setRelated] = useState<NewsArticle[]>([]);
  const [state, setState] = useState<ArticleState>('loading');
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    let active = true;
    setState('loading');
    getNewsArticle(slug).then((response) => {
      if (!active) return;
      setArticle(response.data);
      setState('ready');
      getNews().then((newsResponse) => {
        if (!active) return;
        setRelated(newsResponse.data.filter((item) => item.slug !== slug).slice(0, 3));
      }).catch((requestError) => {
        console.error('Failed to load related news:', requestError);
      });
    }).catch((requestError: any) => {
      if (!active) return;
      if (requestError?.response?.status === 404) {
        setState('missing');
      } else {
        console.error('Failed to load news article:', requestError);
        setState('error');
      }
    });
    return () => { active = false; };
  }, [slug, retryCount]);

  if (state === 'loading') {
    return <div className="container news-article-status" role="status">Loading this story…</div>;
  }

  if (state === 'missing') {
    return (
      <div className="container news-article-status news-empty-state">
        <p className="news-eyebrow">404 / Story not found</p>
        <h1>This story isn’t available.</h1>
        <p>It may have moved or is no longer published.</p>
        <Link href="/news" className="news-view-all"><ArrowLeft size={17} aria-hidden="true" /> Back to News</Link>
      </div>
    );
  }

  if (state === 'error' || !article) {
    return (
      <div className="container news-article-status news-empty-state" role="alert">
        <p className="news-eyebrow">We couldn’t reach the newsroom</p>
        <h1>This story didn’t load.</h1>
        <p>Please check your connection and try again.</p>
        <button type="button" className="news-retry" onClick={() => setRetryCount((count) => count + 1)}>
          Try again
        </button>
      </div>
    );
  }

  const paragraphs = article.content.split(/\n\s*\n/).map((paragraph) => paragraph.trim()).filter(Boolean);

  return (
    <article className="news-article-page">
      <header className="news-article-header container">
        <Link href="/news" className="news-back-link"><ArrowLeft size={16} aria-hidden="true" /> Back to News</Link>
        <div className="news-article-heading">
          <p className="news-article-category">{article.category}</p>
          <h1>{article.title}</h1>
          <p className="news-article-deck">{article.short_description}</p>
          <div className="news-article-byline">
            <span>By {article.author}</span>
            <span aria-hidden="true">·</span>
            <time dateTime={article.published_at ?? article.created_at}>{formatNewsDate(article.published_at)}</time>
          </div>
        </div>
      </header>

      <div className="news-article-hero">
        <ApiImage
          src={resolveMediaUrl(article.featured_image)}
          alt={article.image_alt_text || article.title}
          fill
          priority
          sizes="(max-width: 800px) 100vw, 1200px"
          style={{ objectFit: 'cover' }}
        />
      </div>

      <div className="container news-article-layout">
        <aside className="news-article-aside">
          <p>THE JOURNAL</p>
          <span>Ideas, insight, and updates from Ethiopian Startup School.</span>
          <Link href="/news">Explore all stories <ArrowUpRight size={15} aria-hidden="true" /></Link>
        </aside>
        <div className="news-article-content">
          {paragraphs.map((paragraph, index) => <p key={`${index}-${paragraph.slice(0, 18)}`}>{paragraph}</p>)}
          <div className="news-article-signoff">
            <span aria-hidden="true" />
            <p>{article.author}</p>
          </div>
        </div>
      </div>

      <footer className="container news-article-footer">
        <Link href="/news" className="news-back-link"><ArrowLeft size={16} aria-hidden="true" /> Back to News</Link>
        {related.length > 0 && (
          <section className="news-related" aria-labelledby="related-news-title">
            <div className="news-related-heading">
              <div>
                <p className="news-eyebrow">Keep exploring</p>
                <h2 id="related-news-title">More from the newsroom</h2>
              </div>
              <Link href="/news" className="news-view-all">All stories <ArrowUpRight size={17} aria-hidden="true" /></Link>
            </div>
            <div className="news-related-grid">
              {related.map((item) => <NewsArticleCard key={item.id} article={item} />)}
            </div>
          </section>
        )}
      </footer>
    </article>
  );
}
