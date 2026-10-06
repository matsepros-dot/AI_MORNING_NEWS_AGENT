from datetime import datetime

BUCKET_ORDER = {'latest': 0, 'recent': 1, 'ongoing': 2, 'reference': 3, 'stale': 4}
BUCKET_LABELS = {'latest': 'Mới nhất', 'recent': 'Cũ hơn', 'ongoing': 'Đang tiếp diễn', 'reference': 'Tham chiếu', 'stale': 'Đã cũ'}


def freshness(item, config, now):
    date = datetime.fromisoformat(item.get('published_at') or item['first_seen_at'])
    age = max(0, (now - date).total_seconds() / 3600)
    is_legal = item.get('is_legal', False)
    if age <= config['lookback_hours']:
        bucket = 'latest'
    elif age <= config['recent_hours']:
        bucket = 'recent'
    elif is_legal and ((item.get('legal_effective_date') or '') >= config['legal_rules']['effective_from'] or item.get('reference')) and age <= config['legal_reference_retention_days'] * 24:
        bucket = 'reference'
    elif item.get('ongoing') and age <= config['main_page_retention_days'] * 24:
        bucket = 'ongoing'
    elif item.get('reference') and age <= config['reference_retention_days'] * 24:
        bucket = 'reference'
    else:
        bucket = 'stale'
    item.update(freshness_bucket=bucket, freshness_label=BUCKET_LABELS[bucket], age_hours=round(age, 1))
    return item


def sort_live(items):
    return sorted(items, key=lambda x: (BUCKET_ORDER[x['freshness_bucket']], -x['score'], -(datetime.fromisoformat(x.get('published_at') or x['first_seen_at']).timestamp())))
