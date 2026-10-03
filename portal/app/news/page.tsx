import type { Metadata } from 'next';
import NewsIndexPage from '@/components/NewsIndexPage';

export const metadata: Metadata = {
  title: 'News & Ideas | Ethiopian Startup School',
  description: 'Updates, lessons, and perspectives for Ethiopia’s aspiring founders.',
};

export default function NewsPage() {
  return <NewsIndexPage />;
}
