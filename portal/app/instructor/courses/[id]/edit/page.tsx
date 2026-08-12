'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Upload } from 'lucide-react';
import { getCourse, updateCourse, getCategories, apiClient } from '@/lib/api';
import { RichTextEditor } from '@/components/RichTextEditor';
import { CurriculumManager } from '@/components/CurriculumManager';

export default function EditCoursePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [categories, setCategories] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [thumbnailPreview, setThumbnailPreview] = useState<string | null>(null);
  const [thumbnailFile, setThumbnailFile] = useState<File | null>(null);
  const [form, setForm] = useState<any>(null);

  useEffect(() => {
    getCourse(id).then((res) => {
      setForm(res.data);
      setThumbnailPreview(res.data.thumbnail);
    });
    getCategories().then((res) => setCategories(res.data.results ?? res.data));
  }, [id]);

  function handleThumbnail(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setThumbnailFile(file);
    if (file) setThumbnailPreview(URL.createObjectURL(file));
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    try {
      await updateCourse(Number(id), {
        title: form.title, subtitle: form.subtitle, short_description: form.short_description,
        description: form.description, notes: form.notes, notes_enabled: form.notes_enabled,
        category: form.category, level: form.level, status: form.status,
        price: form.price, is_free: form.is_free, duration_hours: form.duration_hours,
      });
      if (thumbnailFile) {
        const fd = new FormData();
        fd.append('thumbnail', thumbnailFile);
        await apiClient.patch(`/courses/${id}/`, fd);
      }
      setSaved(true);
    } finally {
      setSaving(false);
    }
  }

  if (!form) return <div className="container section">Loading...</div>;

  return (
    <div className="container section" style={{ maxWidth: 720 }}>
      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 18, marginBottom: 40 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontSize: 24 }}>Edit Course</h1>
        <button type="button" className="btn" onClick={() => router.push(`/courses/${form.slug}`)}>View live page</button>
      </div>
      {saved && <p style={{ color: 'var(--brand)' }}>Saved.</p>}

      <div>
        <label className="label">Course thumbnail</label>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ width: 100, height: 70, borderRadius: 8, background: 'var(--surface-2)', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {thumbnailPreview ? <img src={thumbnailPreview} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : <Upload size={18} color="var(--text-muted)" />}
          </div>
          <label className="btn" style={{ cursor: 'pointer' }}>
            Change image
            <input type="file" accept="image/*" onChange={handleThumbnail} style={{ display: 'none' }} />
          </label>
        </div>
      </div>

      <div>
        <label className="label">Course topic (title)</label>
        <input className="input" value={form.title} onChange={(e) => setForm((f: any) => ({ ...f, title: e.target.value }))} />
      </div>

      <div>
        <label className="label">Subtitle</label>
        <input className="input" value={form.subtitle ?? ''} onChange={(e) => setForm((f: any) => ({ ...f, subtitle: e.target.value }))} />
      </div>

      <div>
        <label className="label">Short description</label>
        <input className="input" value={form.short_description ?? ''} onChange={(e) => setForm((f: any) => ({ ...f, short_description: e.target.value }))} />
      </div>

      <div>
        <label className="label">Description</label>
        <RichTextEditor value={form.description ?? ''} onChange={(html) => setForm((f: any) => ({ ...f, description: html }))} />
      </div>

      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <label className="label">Course notes</label>
          <label style={{ display: 'flex', gap: 8, fontSize: 13, color: 'var(--text-muted)' }}>
            <input type="checkbox" checked={form.notes_enabled} onChange={(e) => setForm((f: any) => ({ ...f, notes_enabled: e.target.checked }))} />
            Show as note card
          </label>
        </div>
        <RichTextEditor value={form.notes ?? ''} onChange={(html) => setForm((f: any) => ({ ...f, notes: html }))} />
      </div>

      <div style={{ display: 'flex', gap: 14 }}>
        <div style={{ flex: 1 }}>
          <label className="label">Category</label>
          <select className="input" value={form.category ?? ''} onChange={(e) => setForm((f: any) => ({ ...f, category: e.target.value }))}>
            <option value="">Select category</option>
            {categories.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div style={{ flex: 1 }}>
          <label className="label">Status</label>
          <select className="input" value={form.status} onChange={(e) => setForm((f: any) => ({ ...f, status: e.target.value }))}>
            <option value="draft">Draft</option>
            <option value="pending_approval">Pending Approval</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </select>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 14, alignItems: 'flex-end' }}>
        <label style={{ display: 'flex', gap: 8, fontSize: 13 }}>
          <input type="checkbox" checked={form.is_free} onChange={(e) => setForm((f: any) => ({ ...f, is_free: e.target.checked }))} />
          Free course
        </label>
        {!form.is_free && (
          <div>
            <label className="label">Price (ETB)</label>
            <input className="input" type="number" value={form.price} onChange={(e) => setForm((f: any) => ({ ...f, price: e.target.value }))} />
          </div>
        )}
      </div>

      <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Saving...' : 'Save Changes'}</button>
      </form>

      <CurriculumManager courseId={Number(id)} initialSections={form.sections ?? []} />
    </div>
  );
}
