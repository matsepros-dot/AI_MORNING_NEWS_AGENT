from datetime import datetime


def score(item, config, now):
    weights = config['scoring_weights']
    date = datetime.fromisoformat(item['published_at'] or item['fetched_at'])
    age = max(0, (now - date).total_seconds() / 3600)
    freshness = max(0, 1 - age / config['lookback_hours'])
    item['score'] = round(item['source_priority'] * weights['source_priority'] +
                          freshness * weights['freshness'] +
                          item['keyword_score'] * weights['keyword_importance'] +
                          len(item['keywords']) * weights['keyword_count'] +
                          bool(item['keywords']) * weights['category_relevance'] +
                          bool(item['description']) * weights['description'] +
                          (len(item['title']) >= config['title_min_chars']) * weights['title_quality'] -
                          (item['published_at'] is None) * weights['missing_date_penalty'], 2)
    item['priority'] = 'CAO' if item['score'] >= config['priority_thresholds']['high'] else 'TRUNG BINH' if item['score'] >= config['priority_thresholds']['medium'] else 'THAP'
    return item


def select_top(items, config):
    top = []
    remaining = list(items)
    while remaining and len(top) < config['top_items']:
        best = remaining[0]
        categories = {item['category'] for item in top}
        candidate = next((item for item in remaining if item['category'] not in categories and best['score'] - item['score'] <= config['top_diversity_margin']), best)
        top.append(candidate)
        remaining.remove(candidate)
    return top
