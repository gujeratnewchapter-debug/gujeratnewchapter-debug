import DOMPurify from 'dompurify';

const ALLOWED_TAGS = [
  'a', 'b', 'blockquote', 'br', 'code', 'em', 'h1', 'h2', 'h3', 'h4',
  'hr', 'i', 'li', 'ol', 'p', 'pre', 'strong', 'u', 'ul',
];

const ALLOWED_ATTR = ['href', 'target', 'rel'];

export function sanitizeRichText(value: string | null | undefined) {
  if (!value || typeof window === 'undefined') return '';

  return DOMPurify.sanitize(value, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
    FORBID_TAGS: ['style', 'svg', 'math', 'form', 'input', 'iframe', 'object', 'embed'],
    FORBID_ATTR: ['style', 'srcset'],
  });
}
