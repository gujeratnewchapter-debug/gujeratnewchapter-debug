'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Camera, CheckCircle2, CreditCard, GraduationCap, PencilLine, Save, Sparkles } from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { getMyCertificates, getMyEnrollments, resendVerification, apiClient, updateMe } from '@/lib/api';
import { useI18n } from '@/lib/i18n';

export default function ProfilePage() {
  const { user, isAuthenticated, isBackendAuthenticated, isLoading, signOut, refreshProfile } = useAuth();
  const { t } = useI18n();
  const router = useRouter();
  const [certificates, setCertificates] = useState<any[]>([]);
  const [enrollments, setEnrollments] = useState<any[]>([]);
  const [resent, setResent] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [draft, setDraft] = useState({
    first_name: '',
    last_name: '',
    phone_number: '',
    bio: '',
  });

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.push('/');
  }, [isLoading, isAuthenticated]);

  useEffect(() => {
    if (!isBackendAuthenticated) return;

    getMyCertificates()
      .then((res) => setCertificates(res.data.results ?? res.data))
      .catch((err) => { console.error('Failed to load certificates:', err); });

    getMyEnrollments()
      .then((res) => setEnrollments(res.data.results ?? res.data))
      .catch((err) => { console.error('Failed to load enrollments:', err); });
  }, [isBackendAuthenticated]);

  useEffect(() => {
    if (user) {
      setDraft({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        phone_number: user.phone_number || '',
        bio: user.bio || '',
      });
    }
  }, [user]);

  const completedCourses = useMemo(
    () => enrollments.filter((item) => (item.progress_percent ?? 0) >= 100).length,
    [enrollments],
  );

  const activeProgress = useMemo(
    () => enrollments.reduce((sum, item) => sum + (item.progress_percent ?? 0), 0) / (enrollments.length || 1),
    [enrollments],
  );

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

  async function handleSaveProfile() {
    setSavingProfile(true);
    try {
      await updateMe({
        first_name: draft.first_name.trim(),
        last_name: draft.last_name.trim(),
        phone_number: draft.phone_number.trim(),
        bio: draft.bio.trim(),
      });
      await refreshProfile();
      setIsEditing(false);
    } finally {
      setSavingProfile(false);
    }
  }

  if (isLoading || !isAuthenticated) return <div className="container section">Loading...</div>;

  return (
    <div className="container section" style={{ maxWidth: 980 }}>
      <div className="card" style={{ padding: 24, marginBottom: 24 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 18, alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <label style={{ position: 'relative', cursor: 'pointer' }} title="Change photo">
              {user?.avatar ? (
                <img src={user.avatar} alt="" style={{ width: 72, height: 72, borderRadius: '50%', objectFit: 'cover' }} />
              ) : (
                <div style={{ width: 72, height: 72, borderRadius: '50%', background: 'var(--brand)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28, fontWeight: 700 }}>
                  {(user?.first_name?.[0] ?? user?.username?.[0] ?? '?').toUpperCase()}
                </div>
              )}
              <div style={{ position: 'absolute', bottom: -2, right: -2, width: 24, height: 24, borderRadius: '50%', background: 'var(--surface-2)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Camera size={12} />
              </div>
              <input type="file" accept="image/*" onChange={handleAvatarChange} style={{ display: 'none' }} disabled={uploadingAvatar} />
            </label>
            <div>
              <p style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>{user?.first_name || user?.username} {user?.last_name}</p>
              <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '4px 0 0' }}>
                {user?.role === 'instructor' ? 'Instructor' : user?.role === 'super_admin' ? 'Admin' : 'Student'} · @{user?.username}
              </p>
              <p style={{ color: 'var(--text-muted)', fontSize: 12, margin: '6px 0 0' }}>{user?.email}</p>
            </div>
          </div>

          <button className="btn btn-primary" onClick={() => setIsEditing((current) => !current)}>
            <PencilLine size={15} /> {isEditing ? 'Cancel' : 'Edit profile'}
          </button>
        </div>

        {!user?.is_email_verified && (
          <div className="card" style={{ borderColor: 'var(--accent)', marginTop: 18 }}>
            <p style={{ fontSize: 13, marginBottom: 10 }}>Your email isn't verified yet.</p>
            {resent ? (
              <p style={{ fontSize: 13, color: 'var(--brand)' }}>Verification email resent — check your inbox.</p>
            ) : (
              <button className="btn btn-accent" onClick={handleResend}>Resend verification email</button>
            )}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14, marginTop: 18 }}>
          <div className="card">
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Enrolled courses</p>
            <p style={{ fontSize: 28, fontWeight: 700, margin: 0 }}>{enrollments.length}</p>
          </div>
          <div className="card">
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Certificates</p>
            <p style={{ fontSize: 28, fontWeight: 700, margin: 0 }}>{certificates.length}</p>
          </div>
          <div className="card">
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Completed</p>
            <p style={{ fontSize: 28, fontWeight: 700, margin: 0 }}>{completedCourses}</p>
          </div>
          <div className="card">
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Avg. progress</p>
            <p style={{ fontSize: 28, fontWeight: 700, margin: 0 }}>{Math.round(activeProgress)}%</p>
          </div>
        </div>
      </div>

      {isEditing && (
        <div className="card" style={{ padding: 20, marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2 style={{ fontSize: 18, margin: 0 }}>Update your profile</h2>
            <Sparkles size={16} color="var(--brand)" />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
            <label style={{ display: 'grid', gap: 8, fontSize: 13 }}>
              <span>First name</span>
              <input className="input" value={draft.first_name} onChange={(e) => setDraft({ ...draft, first_name: e.target.value })} />
            </label>
            <label style={{ display: 'grid', gap: 8, fontSize: 13 }}>
              <span>Last name</span>
              <input className="input" value={draft.last_name} onChange={(e) => setDraft({ ...draft, last_name: e.target.value })} />
            </label>
            <label style={{ display: 'grid', gap: 8, fontSize: 13 }}>
              <span>Phone number</span>
              <input className="input" value={draft.phone_number} onChange={(e) => setDraft({ ...draft, phone_number: e.target.value })} />
            </label>
          </div>

          <label style={{ display: 'grid', gap: 8, fontSize: 13, marginTop: 16 }}>
            <span>Bio</span>
            <textarea className="input" rows={4} value={draft.bio} onChange={(e) => setDraft({ ...draft, bio: e.target.value })} />
          </label>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 18 }}>
            <button className="btn btn-primary" onClick={handleSaveProfile} disabled={savingProfile}>
              <Save size={15} /> {savingProfile ? 'Saving...' : 'Save changes'}
            </button>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 24 }}>
        <div className="card" style={{ padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
            <GraduationCap size={18} color="var(--brand)" />
            <h2 style={{ fontSize: 18, margin: 0 }}>Course progress</h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {enrollments.length === 0 && (
              <p style={{ color: 'var(--text-muted)', margin: 0 }}>You haven’t enrolled in a course yet.</p>
            )}
            {enrollments.map((course: any) => (
              <div key={course.id} className="card" style={{ padding: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                  <span style={{ fontWeight: 600 }}>{course.course_detail?.title || course.course_name || 'Course'}</span>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{course.progress_percent ?? 0}%</span>
                </div>
                <div style={{ height: 8, background: 'var(--surface-2)', borderRadius: 99, overflow: 'hidden', marginTop: 10 }}>
                  <div style={{ width: `${course.progress_percent ?? 0}%`, height: '100%', background: 'var(--brand)' }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card" style={{ padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
            <CheckCircle2 size={18} color="var(--brand)" />
            <h2 style={{ fontSize: 18, margin: 0 }}>Achievements</h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Certificates earned</span>
              <strong>{certificates.length}</strong>
            </div>
            <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Courses completed</span>
              <strong>{completedCourses}</strong>
            </div>
            <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Learning streak</span>
              <strong>{Math.min(7, Math.max(1, Math.round((activeProgress || 0) / 12 + 1))) } days</strong>
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ padding: 20, marginTop: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <CreditCard size={18} color="var(--brand)" />
          <h2 style={{ fontSize: 18, margin: 0 }}>Certificates</h2>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
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
      </div>

      <div style={{ marginTop: 24, display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <button className="btn" onClick={() => router.push('/dashboard')}>Back to dashboard</button>
        <button className="btn" onClick={() => { signOut(); router.push('/'); }}>{t('logOut')}</button>
      </div>
    </div>
  );
}
