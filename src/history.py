import json
import os
from datetime import date, timedelta
from datetime import datetime


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(content, encoding='utf-8')
    os.replace(temporary, path)


def load_history(path):
    if not path.exists():
        return []
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, list):
        raise ValueError('History must be a list; refusing to overwrite')
    return value


def unseen(items, history, today):
    # Keep the same day's articles eligible on rerun. New URLs remain eligible.
    previous_urls = {x['url'] for x in history if x['edition_date'] != today}
    return [item for item in items if item['url'] not in previous_urls]


def update_history(path, history, items, today, retention):
    cutoff = (date.fromisoformat(today) - timedelta(days=retention)).isoformat()
    rows = [x for x in history if cutoff <= x['edition_date'] and x['edition_date'] != today]
    rows.extend(dict(item, edition_date=today) for item in items)
    atomic_write(path, json.dumps(rows, ensure_ascii=False, indent=2) + '\n')


def merge_live(history, incoming, now, config):
    rows = {}
    for item in history:
        item = dict(item)
        item.setdefault('first_seen_at', item.get('fetched_at') or item.get('published_at') or now.isoformat())
        item.setdefault('last_seen_at', item.get('fetched_at') or item['first_seen_at'])
        item.setdefault('reference', False)
        item.setdefault('ongoing', False)
        rows[item['url']] = item
    for item in incoming:
        old = rows.get(item['url'])
        if old:
            item['first_seen_at'] = old['first_seen_at']
            # Missing fields on a later feed do not erase earlier source evidence.
            for key in ('published_at', 'description', 'image_url', 'legal_evidence'):
                if not item.get(key) and old.get(key):
                    item[key] = old[key]
        item['last_seen_at'] = now.isoformat()
        rows[item['url']] = item
    cutoff = now - timedelta(days=config['history_retention_days'])
    retained = [x for x in rows.values() if datetime.fromisoformat(x['last_seen_at']) >= cutoff]
    return sorted(retained, key=lambda x: x['last_seen_at'], reverse=True)[:config['history_max_items']]
