'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { verifyCertificate } from '@/lib/api';

export default function VerifyCertificatePage() {
  const { certificateId } = useParams<{ certificateId: string }>();
  const [status, setStatus] = useState<'loading' | 'valid' | 'invalid'>('loading');
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    if (!certificateId) return;

    verifyCertificate(certificateId)
      .then((res) => {
        setData(res.data);
        setStatus(res.data.valid ? 'valid' : 'invalid');
      })
      .catch(() => setStatus('invalid'));
  }, [certificateId]);

  if (status === 'loading') {
    return <div className="container section">Verifying certificate...</div>;
  }

  if (status === 'invalid' || !data?.valid) {
    return (
      <div className="container section" style={{ maxWidth: 560, textAlign: 'center' }}>
        <h1 style={{ fontSize: 28, marginBottom: 12 }}>Certificate not found</h1>
        <p style={{ color: 'var(--text-muted)' }}>This certificate could not be verified. Please check the ID and try again.</p>
      </div>
    );
  }

  return (
    <div className="container section" style={{ maxWidth: 680 }}>
      <div className="card" style={{ padding: 28 }}>
        <p style={{ textTransform: 'uppercase', letterSpacing: 1.2, fontSize: 12, color: 'var(--brand)', marginBottom: 10 }}>Verification status</p>
        <h1 style={{ fontSize: 28, marginTop: 0 }}>Valid certificate</h1>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 10 }}>
          <li><strong>Certificate ID:</strong> {data.certificate_number}</li>
          <li><strong>Learner:</strong> {data.student_name || 'Student'}</li>
          <li><strong>Course:</strong> {data.course_title || data.course}</li>
          <li><strong>Issued:</strong> {data.issued_at ? new Date(data.issued_at).toLocaleDateString() : 'N/A'}</li>
        </ul>
      </div>
    </div>
  );
}
