from urllib.parse import urlsplit
from bs4 import BeautifulSoup


def valid_image_url(url, config):
    try:
        parts = urlsplit(url)
        return parts.scheme == 'https' and not parts.username and parts.hostname and any(parts.hostname == domain or parts.hostname.endswith('.'+domain) for domain in config['image_allowed_domains'])
    except (ValueError, AttributeError):
        return False


def thumbnail(entry, config):
    if not config.get('image_enabled', False):
        return None
    candidates = [row.get('url') for row in entry.get('media_thumbnail', [])]
    candidates.extend(row.get('url') for row in entry.get('media_content', []) if row.get('medium') == 'image' or row.get('type', '').startswith('image/'))
    candidates.extend(row.get('href') for row in entry.get('enclosures', []) if row.get('type', '').startswith('image/'))
    soup = BeautifulSoup(entry.get('summary') or entry.get('description', ''), 'html.parser')
    candidates.extend(img.get('src') for img in soup.select('img[src]'))
    return next((url for url in candidates if url and valid_image_url(url, config)), None)
