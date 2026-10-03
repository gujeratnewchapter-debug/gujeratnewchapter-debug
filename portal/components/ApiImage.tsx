'use client';

import Image, { ImageProps } from 'next/image';
import { useState } from 'react';

const DEFAULT_IMAGE = '/images/course-fallback.webp';

type ApiImageProps = Omit<ImageProps, 'src' | 'onError'> & {
  src?: string | null;
  fallbackSrc?: string;
};

export function ApiImage({ src, fallbackSrc = DEFAULT_IMAGE, ...props }: ApiImageProps) {
  const source = src || fallbackSrc;
  const [failedSource, setFailedSource] = useState<string | null>(null);

  return (
    <Image
      {...props}
      src={failedSource === source ? fallbackSrc : source}
      alt={props.alt ?? ''}
      unoptimized
      onError={() => setFailedSource(source)}
    />
  );
}