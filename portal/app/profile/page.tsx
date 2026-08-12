'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Camera } from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { getMyCertificates, resendVerification, apiClient } from '@/lib/api';
import { useI18n } from '@/lib/i18n';

export default function ProfilePage() {
  const { user, isAuthenticated, isLoading, signOut, refreshProfile } = useAuth();
  const { t } = useI18n();
  const router = useRouter();
  const [certificates, setCertificates] = useState<any[]>([]);
  const [resent, setResent] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.push('/');
  }, [isLoading, isAuthenticated]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (isAuthenticated) getMyCertificates().then((res) => setCertificates(res.data.results ?? res.data)).catch(() => {});
  }, [isAuthenticated]);

  async function handleResend() {
    await resendVerification();
    setResent(true);
  }

  async function handleAvatarChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingAvatar(true);
    try {
      const fd = new FormData();
      fd.append('avatar', file);
      await apiClient.patch('/auth/me/', fd);
      await refreshProfile();
    } finally {
      setUploadingAvatar(false);
    }
  }

  if (isLoading || !isAuthenticated) return <div className="container section">Loading...</div>;

  return (
    <div className="container section" style={{ maxWidth: 560 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <label style={{ position: 'relative', cursor: 'pointer' }} title="Change photo">
          {user?.avatar ? (
            <img src={user.avatar} alt="" style={{ width: 64, height: 64, borderRadius: '50%', objectFit: 'cover' }} />
          ) : (
            <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'var(--brand)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, fontWeight: 700 }}>
              {(user?.first_name?.[0] ?? user?.username?.[0] ?? '?').toUpperCase()}
            </div>
          )}
          <div style={{ position: 'absolute', bottom: -2, right: -2, width: 22, height: 22, borderRadius: '50%', background: 'var(--surface-2)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Camera size={12} />
          </div>
          <input type="file" accept="image/*" onChange={handleAvatarChange} style={{ display: 'none' }} disabled={uploadingAvatar} />
        </label>
        <div>
          <p style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>{user?.first_name} {user?.last_name}</p>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: 0 }}>
            {user?.role === 'instructor' ? 'Instructor' : user?.role === 'super_admin' ? 'Admin' : 'Student'} · @{user?.username}
          </p>
          {user?.role === 'instructor' && (
            <p style={{ color: 'var(--text-muted)', fontSize: 11, margin: '4px 0 0' }}>
              {uploadingAvatar ? 'Uploading...' : 'This photo appears on all your courses'}
            </p>
          )}
        </div>
      </div>

      {!user?.is_email_verified && (
        <div className="card" style={{ borderColor: 'var(--accent)', marginBottom: 24 }}>
          <p style={{ fontSize: 13, marginBottom: 10 }}>Your email isn't verified yet.</p>
          {resent ? (
            <p style={{ fontSize: 13, color: 'var(--brand)' }}>Verification email resent — check your inbox.</p>
          ) : (
            <button className="btn btn-accent" onClick={handleResend}>Resend verification email</button>
          )}
        </div>
      )}

      <h2 style={{ fontSize: 18, marginBottom: 12 }}>Certificates</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 32 }}>
        {certificates.map((cert: any) => (
          <div key={cert.id} className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <p style={{ fontWeight: 600, margin: 0 }}>{cert.course_title}</p>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '2px 0 0' }}>No. {cert.certificate_number}</p>
            </div>
            {cert.pdf_file && <a href={cert.pdf_file} target="_blank" rel="noreferrer" className="btn">View</a>}
          </div>
        ))}
        {certificates.length === 0 && <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Complete a course to earn your first certificate.</p>}
      </div>

      <button className="btn" onClick={() => { signOut(); router.push('/'); }}>{t('logOut')}</button>
    </div>
  );
}
