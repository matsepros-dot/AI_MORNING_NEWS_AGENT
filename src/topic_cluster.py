import hashlib
import re
from datetime import datetime
from rapidfuzz.fuzz import ratio


def cluster_topics(items, config):
    groups = []
    # New developments lead a topic; official/source quality breaks date ties.
    for item in sorted(items, key=lambda x: (x.get('published_at') or x['first_seen_at'], x.get('official', False), x['source_priority']), reverse=True):
        words = set(item['duplicate_key'].split())
        group = None
        for candidate in groups:
            first = candidate[0]
            if re.findall(r'\d+', item['duplicate_key']) != re.findall(r'\d+', first['duplicate_key']):
                if not any(term in item['title'].casefold() and term in first['title'].casefold() for term in config['topic_numeric_update_terms']):
                    continue
            other = set(first['duplicate_key'].split())
            shared = len(words & other)
            overlap = shared / max(len(words | other), 1)
            if item['category'] == first['category'] and shared >= config['topic_min_shared_words'] and overlap >= config['topic_overlap_threshold'] and ratio(item['duplicate_key'], first['duplicate_key']) >= config['topic_cluster_threshold']:
                group = candidate
                break
        if group is None:
            group = []
            groups.append(group)
        group.append(item)
    leaders = []
    for group in groups:
        key = hashlib.sha256(group[0]['duplicate_key'].encode()).hexdigest()[:16]
        for item in group:
            item['topic_key'] = key
        leader = group[0]
        leader['related_count'] = len(group)-1
        leaders.append(leader)
    return leaders
