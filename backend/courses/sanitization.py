import bleach


ALLOWED_TAGS = sorted(set(bleach.sanitizer.ALLOWED_TAGS).union({
    'a', 'b', 'blockquote', 'br', 'code', 'em', 'h1', 'h2', 'h3', 'h4',
    'hr', 'i', 'li', 'ol', 'p', 'pre', 'strong', 'u', 'ul',
}))
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'target', 'rel'],
}
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


def sanitize_rich_text(value):
    return bleach.clean(
        value or '',
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
