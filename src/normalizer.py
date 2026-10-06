import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from bs4 import BeautifulSoup
from dateutil.parser import parse


def clean(value: str) -> str:
    soup = BeautifulSoup(value or '', 'html.parser')
    for tag in soup(['script', 'style']):
        tag.decompose()
    return ' '.join(soup.get_text(' ', strip=True).split())


def title_key(value: str) -> str:
    value = unicodedata.normalize('NFD', value.casefold()).replace('đ', 'd')
    return ' '.join(re.sub(r'[^\w\s]', ' ', ''.join(c for c in value if not unicodedata.combining(c))).split())


def canonical_url(value: str) -> str:
    parts = urlsplit(value.strip())
    if parts.scheme not in ('http', 'https') or not parts.netloc:
        raise ValueError('Invalid public article URL')
    query = [(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or '/', urlencode(query), ''))


def normalize(entry, source, now, config):
    title = clean(entry.get('title', ''))
    if not title:
        raise ValueError('Missing title')
    raw_date = entry.get('published') or entry.get('updated')
    published = None
    if raw_date:
        try:
            published = parse(raw_date)
            if published.tzinfo is None:
                published = published.replace(tzinfo=now.tzinfo)
            published = published.astimezone(timezone.utc)
        except (ValueError, TypeError, OverflowError):
            pass
    description = clean(entry.get('summary') or entry.get('description', ''))
    limit = config['description_max_chars']
    if len(description) > limit:
        description = description[:limit].rsplit(' ', 1)[0] + '…'
    return dict(title=title, url=canonical_url(entry.get('link', '')), source=source['name'],
                published_at=published.isoformat() if published else None, fetched_at=now.isoformat(),
                description=description, category=source.get('category', 'hot_news'), score=0,
                keywords=[], source_priority=source['priority'], official=source.get('official', False),
                duplicate_key=title_key(title))
