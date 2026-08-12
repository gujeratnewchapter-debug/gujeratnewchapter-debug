import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { BookOpen } from 'lucide-react';

export function CourseCard({ course }: { course: any }) {
  return (
    <Link href={`/courses/${course.slug}`} className="card" style={{ display: 'block', padding: 0, overflow: 'hidden' }}>
      <div style={{ height: 140, background: 'var(--surface-2)', position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {course.thumbnail ? (
          <Image src={course.thumbnail} alt={course.title} fill style={{ objectFit: 'cover' }} unoptimized />
        ) : (
          <BookOpen size={28} color="var(--text-muted)" />
        )}
      </div>
      <div style={{ padding: 16 }}>
        <p style={{ fontSize: 15, fontWeight: 600, margin: '0 0 4px' }}>{course.title}</p>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 10px' }}>
          {course.instructor_name} · {course.category_name}
        </p>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="badge">{course.level}</span>
          <span style={{ fontWeight: 700, color: 'var(--brand)', fontSize: 13 }}>
            {course.is_free ? 'Free' : `${course.price} ETB`}
          </span>
        </div>
      </div>
    </Link>
  );
}
