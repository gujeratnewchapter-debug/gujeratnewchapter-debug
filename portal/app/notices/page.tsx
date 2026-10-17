import type { Metadata } from 'next';
import NoticesPage from '@/components/NoticesPage';

export const metadata: Metadata = {
  title: 'Notices | Ethiopian Startup School',
  description: 'Important updates and announcements from Ethiopian Startup School.',
};

export default function Page() {
  return <NoticesPage />;
}
