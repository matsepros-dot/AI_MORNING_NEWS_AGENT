import json
import os
from datetime import date, timedelta


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
