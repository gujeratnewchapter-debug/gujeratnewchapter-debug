import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="container section" style={{ textAlign: 'center', paddingTop: 80, paddingBottom: 80 }}>
      <h1 style={{ fontSize: 36, marginBottom: 16 }}>Page not found</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: 28 }}>The page you were looking for does not exist. Please check the URL or return to the home page.</p>
      <Link href="/" className="btn btn-primary">Go back home</Link>
    </div>
  );
}
