import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';
import { ApiImage } from '@/components/ApiImage';
import { resolveMediaUrl, type NewsArticle } from '@/lib/api';

export type { NewsArticle } from '@/lib/api';

export function formatNewsDate(value: string | null) {
  if (!value) return 'Recently published';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Recently published';
  return new Intl.DateTimeFormat('en-ET', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(date);
}

export function NewsArticleCard({
  article,
  featured = false,
}: {
  article: NewsArticle;
  featured?: boolean;
}) {
  return (
    <Link
      href={`/news/${article.slug}`}
      className={`news-card-link${featured ? ' news-card-link-featured' : ''}`}
      aria-label={`Read ${article.title}`}
    >
      <article className="news-card">
        <div className="news-card-image">
          <ApiImage
            src={resolveMediaUrl(article.featured_image)}
            alt={article.image_alt_text || article.title}
            fill
            sizes={featured
              ? '(max-width: 680px) 100vw, (max-width: 1050px) 45vw, 50vw'
              : '(max-width: 640px) 100vw, (max-width: 1000px) 50vw, 33vw'}
            style={{ objectFit: 'cover' }}
          />
          <span className="news-card-category">{article.category}</span>
        </div>
        <div className="news-card-copy">
          <p className="news-card-date">{formatNewsDate(article.published_at)}</p>
          <h3>{article.title}</h3>
          <p className="news-card-description">{article.short_description}</p>
          <span className="news-card-read-more">
            Read more <ArrowUpRight size={16} aria-hidden="true" />
          </span>
        </div>
      </article>
    </Link>
  );
}
