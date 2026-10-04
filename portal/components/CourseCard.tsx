import React from 'react';
import Link from 'next/link';
import { ApiImage } from '@/components/ApiImage';
import { prefetchCourse } from '@/lib/api';

export function CourseCard({ course }: { course: any }) {
  return (
    <Link
      href={`/courses/${course.slug}?id=${course.id}`}
      className="card course-card"
      onMouseEnter={() => prefetchCourse(course.id)}
      onFocus={() => prefetchCourse(course.id)}
    >
      <div className="course-card-media" aria-hidden="true">
        <ApiImage src={course.thumbnail} alt={course.title} fill sizes="(max-width: 640px) 100vw, (max-width: 1000px) 50vw, 33vw" style={{ objectFit: 'cover' }} />
      </div>
      <div className="course-card-body">
        <p className="course-card-title">{course.title}</p>
        <div className="course-card-meta course-card-instructor">
          {course.instructor_photo ? (
            <ApiImage
              src={course.instructor_photo}
              alt=""
              width={22}
              height={22}
              fallbackSrc="/favicon.svg"
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
