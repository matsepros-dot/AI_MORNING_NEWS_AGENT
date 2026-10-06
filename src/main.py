import argparse
import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.fetcher import fetch_sources
from src.normalizer import normalize
from src.classifier import classify
from src.scorer import score
from src.deduplicator import deduplicate
from src.history import load_history, merge_live, atomic_write
from src.freshness import freshness, sort_live
from src.legal_rules import apply_legal
from src.topic_cluster import cluster_topics
from src.market_data import fetch_markets
from src.renderer import render
from src.publisher import publish
from src.logger_setup import setup_logger


def select_live(items, config):
    current = [x for x in items if x['freshness_bucket'] in ('latest', 'recent')]
    older = [x for x in items if x['freshness_bucket'] in ('ongoing', 'reference')][:config['legal_rules']['reference_max_items']]
    selected, counts = [], {}
    for category in config['keywords']:
        candidate = next((x for x in current if x['category'] == category), None)
        if candidate and len(selected) < config['max_items']-len(older):
            selected.append(candidate)
            counts[category] = 1
    for item in current:
        if len(selected) >= config['max_items']-len(older):
            break
        category = item['category']
        if item not in selected and counts.get(category, 0) < config['section_max_items']:
            selected.append(item)
            counts[category] = counts.get(category, 0)+1
    selected.extend(older)
    return sort_live(selected)


def run(root, config, logger, no_publish=False):
    now = datetime.now(ZoneInfo(config['timezone']))
    report = dict(version=config['version'], started_at=now.isoformat(), status='FAIL')
    logger.info('START V%s %s', config['version'], now.isoformat())
    try:
        history_path = root / config['output_paths']['history']
        history = load_history(history_path)
        raw, sources = fetch_sources(config, logger)
        report.update(sources=sources, fetched=len(raw))
        if not any(source['status'] == 'OK' for source in sources):
            logger.error('ALL SOURCES FAILED: website/archive/history preserved')
            report['reason'] = 'All public sources failed; outputs preserved'
            return 1
        normalized = []
        for entry, source in raw:
            try:
                item = normalize(entry, source, now, config)
                published = datetime.fromisoformat(item['published_at'] or item['fetched_at'])
                if (published-now).total_seconds()/3600 > config['future_tolerance_hours']:
                    logger.warning('FUTURE DATE SKIP %s', item['url'])
                    continue
                if not item['published_at']:
                    logger.info('MISSING DATE %s', item['url'])
                normalized.append(item)
            except (ValueError, TypeError, KeyError) as exc:
                logger.warning('NORMALIZE SKIP %s', exc)
        logger.info('NORMALIZE items=%d raw=%d', len(normalized), len(raw))
        merged = merge_live(history, normalized, now, config)
        for item in merged:
            score(freshness(apply_legal(classify(item, config), config, now), config, now), config, now)
        unique = deduplicate(merged, config)
        active = [x for x in unique if x['freshness_bucket'] != 'stale']
        topics = cluster_topics(active, config)
        selected = select_live(sort_live(topics), config)
        logger.info('DEDUP items=%d TOPICS=%d LIVE=%d SELECT=%d', len(unique), len(topics), len(active), len(selected))
        report.update(normalized=len(normalized), deduplicated=len(unique), filtered=len(active), topics=len(topics), selected=len(selected),
                      categories={key: sum(x['category'] == key for x in selected) for key in config['keywords']},
                      freshness={key: sum(x['freshness_bucket'] == key for x in selected) for key in ('latest', 'recent', 'ongoing', 'reference')},
                      legal_after_cutoff=sum(bool(x.get('legal_effective_date')) and x['legal_effective_date'] >= config['legal_rules']['effective_from'] for x in selected))
        if not selected:
            logger.error('NO LIVE ITEMS: existing outputs preserved')
            report['reason'] = 'No retained eligible items'
            return 1
        market_path = root / 'data/market.json'
        previous_market = json.loads(market_path.read_text(encoding='utf-8')) if market_path.exists() else []
        markets, market_results = fetch_markets(config, logger, now, previous_market)
        report['market_sources'] = market_results
        render(root, config, selected, now, markets)
        logger.info('RENDER OK live page and daily snapshot')
        for item in merged:
            item['edition_date'] = now.date().isoformat()
            item.setdefault('topic_key', '')
        atomic_write(history_path, json.dumps(merged, ensure_ascii=False, indent=2)+'\n')
        atomic_write(market_path, json.dumps(markets, ensure_ascii=False, indent=2)+'\n')
        logger.info('HISTORY OK records=%d', len(merged))
        published = no_publish or publish(root, logger, config)
        report['publish'] = 'SKIPPED' if no_publish else 'PASS' if published else 'FAIL'
        report['status'] = 'PASS' if published and len(selected) >= config['min_items'] else 'PARTIAL'
        return 0 if report['status'] == 'PASS' else 2
    except Exception:
        logger.exception('RUN FAILED; review log before retry')
        return 1
    finally:
        report['ended_at'] = datetime.now(ZoneInfo(config['timezone'])).isoformat()
        atomic_write(root / 'data/run_report.json', json.dumps(report, ensure_ascii=False, indent=2))
        logger.info('END status=%s', report['status'])


@contextmanager
def run_lock(root):
    with (root / '.run.lock').open('a+b') as lock:
        lock.seek(0)
        lock.write(b'0')
        lock.flush()
        lock.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            if os.name == 'nt':
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-publish', action='store_true')
    args = parser.parse_args()
    config = json.loads((ROOT / 'config/config.json').read_text(encoding='utf-8'))
    logger = setup_logger(ROOT / config['output_paths']['log'])
    try:
        with run_lock(ROOT):
            return run(ROOT, config, logger, args.no_publish)
    except OSError:
        logger.exception('Could not acquire run lock; another run may be active')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
