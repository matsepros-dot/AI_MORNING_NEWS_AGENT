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
    preferred = item['category']
    category = max(scores, key=lambda key: (scores[key], key == preferred))
    if scores[category] > 0:
        item['category'] = category
    item['keywords'] = matches[item['category']]
    item['keyword_score'] = scores[item['category']]
    return item
