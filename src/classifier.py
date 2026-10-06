import re
from .normalizer import title_key


def classify(item, config):
    text = title_key(item['title'] + ' ' + item['description'])
    matches = {}
    for category, keywords in config['keywords'].items():
        matches[category] = [word for word in keywords if re.search(r'(?<!\w)' + re.escape(title_key(word)) + r'(?!\w)', text)]
    scores = {key: sum(config['keyword_importance'].get(word, 1) for word in words) for key, words in matches.items()}
    preferred = item['category']
    category = max(scores, key=lambda key: (scores[key], key == preferred))
    if scores[category] > 0:
        item['category'] = category
    item['keywords'] = matches[item['category']]
    item['keyword_score'] = scores[item['category']]
    return item
