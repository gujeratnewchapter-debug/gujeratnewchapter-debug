import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { BookOpen } from 'lucide-react';

export function CourseCard({ course }: { course: any }) {
  return (
    <Link href={`/courses/${course.slug}?id=${course.id}`} className="card course-card">
      <div className="course-card-media" aria-hidden="true">
        {course.thumbnail ? (
          <Image src={course.thumbnail} alt={course.title} fill priority style={{ objectFit: 'cover' }} unoptimized />
        ) : (
          <BookOpen size={28} color="var(--text-muted)" />
        )}
      </div>
      <div className="course-card-body">
        <p className="course-card-title">{course.title}</p>
        <div className="course-card-meta course-card-instructor">
          {course.instructor_photo ? (
            <Image
              src={course.instructor_photo}
              alt=""
              width={22}
              height={22}
              unoptimized
            />
          ) : (
            <span className="course-card-instructor-fallback" aria-hidden="true">
              {(course.instructor_name || 'I').charAt(0).toUpperCase()}
            </span>
          )}
          <span>{course.instructor_name || 'Instructor'}</span>
          <span aria-hidden="true">·</span>
          <span>{course.category_name}</span>
        </div>
        <div className="course-card-footer">
          <span className="badge">{course.level}</span>
          <span className="course-card-price">
            {course.is_free ? 'Free' : `${course.price} ETB`}
          </span>
        </div>
      </div>
    </Link>
  );
}
