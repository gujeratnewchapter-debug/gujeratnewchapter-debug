'use client';

import { useParams } from 'next/navigation';
import { UnifiedCourseBuilder } from '@/components/UnifiedCourseBuilder';

export default function EditCoursePage() {
  const { id } = useParams<{ id: string }>();
  return <UnifiedCourseBuilder mode="edit" courseId={Number(id)} />;
}
