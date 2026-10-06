import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re


def html_entries(response, source, config):
    soup = BeautifulSoup(response.content, 'html.parser')
    if soup.select('title') and any(word in soup.title.get_text().lower() for word in ('just a moment', 'captcha', 'access denied')):
        raise ValueError('Protected source; skipped without bypass')
    if source['type'] == 'article':
        title = soup.select_one('meta[property="og:title"]')
        description = soup.select_one('meta[property="og:description"]')
        published = soup.select_one('meta[property="article:published_time"],meta[name="pubdate"],meta[name="pubdate:published_time"]')
        body = soup.select_one('.detail-content, .detail__content, .content-detail, article')
        if not title or not body:
            raise ValueError('Article metadata/body unavailable')
        # Read only public evidence sentences; never store a full article.
        text = body.get_text(' ', strip=True)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        evidence = ' '.join(s for s in sentences if any(word in s.casefold() for word in ('có hiệu lực', 'hiệu lực thi hành', 'ban hành ngày', 'được thông qua')))
        return [dict(title=title.get('content', ''), link=source['url'], summary=description.get('content', '') if description else '',
                     published=published.get('content') if published else None, legal_evidence=evidence[:config['legal_evidence_max_chars']])]
    rows = []
    for anchor in soup.select(source['selector']):
        title = anchor.get_text(' ', strip=True)
        url = urljoin(source['url'], anchor.get('href', ''))
        if title and url != source['url'] and len(title) >= source.get('title_min_chars', 0):
            rows.append(dict(title=title, link=url))
            if len(rows) >= config['html_source_max_items']:
                break
    return rows


def fetch_sources(config, logger):
    entries, results = [], []
    for source in config['sources']:
        if not source.get('enabled', True):
            logger.info('SOURCE SKIPPED %s: %s', source['name'], source.get('reason', 'disabled'))
            results.append(dict(name=source['name'], status='SKIPPED', count=0, reason=source.get('reason', 'disabled')))
            continue
        try:
            response = requests.get(source['url'], timeout=config['request_timeout'],
                                    headers={'User-Agent': config['user_agent']})
            response.raise_for_status()
            if len(response.content) > config['max_feed_bytes']:
                raise ValueError('Feed exceeds configured size limit')
            if source.get('type') in ('html', 'article'):
                rows = html_entries(response, source, config)
            else:
                feed = feedparser.parse(response.content)
                if not feed.entries and (feed.bozo or not feed.version):
                    raise ValueError('Invalid RSS/Atom feed')
                if feed.bozo:
                    logger.warning('RSS MALFORMED %s: using %d readable entries', source['name'], len(feed.entries))
                rows = feed.entries
            entries.extend((entry, source) for entry in rows)
            results.append(dict(name=source['name'], status='OK', count=len(rows)))
            logger.info('SOURCE OK %s items=%d', source['name'], len(rows))
            if not rows and source.get('fallback'):
                logger.warning('SOURCE EMPTY %s; FALLBACK -> %s', source['name'], source['fallback'])
        except (requests.RequestException, ValueError) as exc:
            logger.warning('SOURCE ERROR %s: %s', source['name'], exc)
            results.append(dict(name=source['name'], status='ERROR', count=0, reason=str(exc)))
            if source.get('fallback'):
                logger.info('SOURCE FALLBACK %s -> %s', source['name'], source['fallback'])
    return entries, results
