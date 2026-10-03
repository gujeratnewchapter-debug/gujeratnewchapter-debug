import type { Metadata } from 'next';
import NewsArticlePage from '@/components/NewsArticlePage';

type PageProps = { params: { slug: string } };

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL
  || (process.env.NODE_ENV === 'development'
    ? 'http://localhost:8000/api'
    : 'https://ethiopian-startup-school-api.onrender.com/api');

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  try {
    const response = await fetch(`${apiBaseUrl.replace(/\/+$/, '')}/news/${encodeURIComponent(params.slug)}/`, {
      next: { revalidate: 60 },
    });
    if (!response.ok) throw new Error(`News API returned ${response.status}`);
    const article = await response.json();
    return {
      title: `${article.title} | Ethiopian Startup School`,
      description: article.short_description,
      openGraph: {
        title: article.title,
        description: article.short_description,
        type: 'article',
        publishedTime: article.published_at ?? undefined,
        images: article.featured_image ? [{ url: article.featured_image }] : undefined,
      },
    };
  } catch (error) {
    console.error('Unable to load news metadata:', error);
    return {
      title: 'News | Ethiopian Startup School',
      description: 'Updates and stories from Ethiopian Startup School.',
    };
  }
}

export default function NewsArticleRoute({ params }: PageProps) {
  return <NewsArticlePage slug={params.slug} />;
}
