import feedparser
import requests


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
            feed = feedparser.parse(response.content)
            if not feed.entries and feed.bozo:
                raise ValueError('Invalid RSS/Atom feed')
            entries.extend((entry, source) for entry in feed.entries)
            results.append(dict(name=source['name'], status='OK', count=len(feed.entries)))
            logger.info('SOURCE OK %s items=%d', source['name'], len(feed.entries))
        except (requests.RequestException, ValueError) as exc:
            logger.warning('SOURCE ERROR %s: %s', source['name'], exc)
            results.append(dict(name=source['name'], status='ERROR', count=0, reason=str(exc)))
    return entries, results
