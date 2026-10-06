import re
import unicodedata


def keyword_text(value):
    # Preserve Vietnamese accents: 'thuê' (rent) is different from 'thuế' (tax).
    return ' '.join(unicodedata.normalize('NFC', value).casefold().split())


def classify(item, config):
    title = keyword_text(item['title'])
    description = keyword_text(item['description'])
    matches = {}
    scores = {}
    for category, keywords in config['keywords'].items():
        matches[category] = []
        scores[category] = 0
        for word in keywords:
            pattern = r'(?<!\w)' + re.escape(keyword_text(word)) + r'(?!\w)'
            in_title = bool(re.search(pattern, title))
            in_description = bool(re.search(pattern, description))
            if in_title or in_description:
                matches[category].append(word)
                scores[category] += config['keyword_importance'].get(word, 1) * (in_title * config['classification_weights']['title'] + in_description * config['classification_weights']['description'])
        scores[category] *= config.get('category_match_boost', {}).get(category, 1)
    preferred = item['category']
    # Generic foreign stock headlines must not fill the Vietnam stocks section.
    vietnam_terms = ['vn-index', 'vn index', 'hnx', 'upcom', 'hose', 'việt nam', 'hà nội', 'tp.hcm']
    if 'vietnam_stocks' in scores and preferred != 'vietnam_stocks' and not any(word in title + ' ' + description for word in vietnam_terms):
        scores['vietnam_stocks'] = 0
    category = max(scores, key=lambda key: (scores[key], key == preferred))
    if scores[category] > 0:
        item['category'] = category
    if item['category'] not in matches:
        item['category'] = 'hot_news'
    item['keywords'] = matches[item['category']]
    item['keyword_score'] = scores[item['category']]
    return item
