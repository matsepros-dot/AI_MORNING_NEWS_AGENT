import re
from rapidfuzz.fuzz import ratio


def same_story(a, b, threshold):
    if a['url'] == b['url'] or a['duplicate_key'] == b['duplicate_key']:
        return True
    left, right = a['duplicate_key'], b['duplicate_key']
    # Different numbers often mean a new rate, period or development.
    if re.findall(r'\d+', left) != re.findall(r'\d+', right):
        return False
    return ratio(left, right) >= threshold


def deduplicate(items, config):
    ordered = sorted(items, key=lambda x: (x['official'], x['source_priority'], x['published_at'] or '', len(x['description'])), reverse=True)
    unique = []
    for item in ordered:
        if not any(same_story(item, old, config['fuzzy_duplicate_threshold']) for old in unique):
            unique.append(item)
    return unique
