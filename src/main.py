import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.fetcher import fetch_sources
from src.normalizer import normalize
from src.classifier import classify
from src.scorer import score
from src.deduplicator import deduplicate
from src.history import load_history, unseen, update_history, atomic_write
from src.renderer import render
from src.publisher import publish
from src.logger_setup import setup_logger


def run(root, config, logger, no_publish=False):
    # Windows local timezone follows Task Scheduler and the machine clock.
    now = datetime.now().astimezone()
    report = dict(started_at=now.isoformat(), status='FAIL')
    logger.info('START %s', now.isoformat())
    try:
        paths = config['output_paths']
        history_path = root / paths['history']
        history = load_history(history_path)
        raw, sources = fetch_sources(config, logger)
        report.update(sources=sources, fetched=len(raw))
        normalized = []
        for entry, source in raw:
            try:
                item = normalize(entry, source, now, config)
                if item['published_at'] is None:
                    logger.info('MISSING DATE %s', item['url'])
                published = datetime.fromisoformat(item['published_at'] or item['fetched_at'])
                age = (now - published).total_seconds() / 3600
                if -config['future_tolerance_hours'] <= age <= config['lookback_hours']:
                    normalized.append(score(classify(item, config), config, now))
            except (ValueError, TypeError, KeyError) as exc:
                logger.warning('NORMALIZE SKIP %s', exc)
        logger.info('NORMALIZE fresh=%d raw=%d', len(normalized), len(raw))
        unique = deduplicate(normalized, config)
        logger.info('DEDUP items=%d', len(unique))
        eligible = unseen(unique, history, now.date().isoformat())
        ranked = sorted(eligible, key=lambda x: x['score'], reverse=True)
        selected = ranked[:config['max_items']]
        if config.get('ensure_category_coverage', True):
            for category in config['keywords']:
                if not any(x['category'] == category for x in selected):
                    candidate = next((x for x in ranked if x['category'] == category), None)
                    if candidate:
                        if len(selected) == config['max_items']:
                            replace = next((x for x in reversed(selected) if sum(y['category'] == x['category'] for y in selected) > 1), None)
                            if replace:
                                selected.remove(replace)
                        if len(selected) < config['max_items']:
                            selected.append(candidate)
            selected.sort(key=lambda x: x['score'], reverse=True)
        report.update(normalized=len(normalized), deduplicated=len(unique), filtered=len(eligible), selected=len(selected),
                      categories={key: sum(x['category'] == key for x in selected) for key in config['keywords']})
        logger.info('SELECT items=%d', len(selected))
        if not selected:
            logger.error('NO NEWS: existing website/archive/history preserved')
            report['reason'] = 'No fresh eligible news; outputs preserved'
            return 1
        render(root, config, selected, now)
        logger.info('RENDER OK index/archive')
        update_history(history_path, history, selected, now.date().isoformat(), config['history_retention_days'])
        logger.info('HISTORY OK')
        published = True if no_publish else publish(root, logger, config)
        report['publish'] = 'SKIPPED' if no_publish else 'PASS' if published else 'FAIL'
        report['status'] = 'PASS' if published and len(selected) >= config['min_items'] else 'PARTIAL'
        return 0 if report['status'] == 'PASS' else 2
    except Exception:
        logger.exception('RUN FAILED; check log before retry')
        return 1
    finally:
        report['ended_at'] = datetime.now().astimezone().isoformat()
        atomic_write(root / 'data/run_report.json', json.dumps(report, ensure_ascii=False, indent=2))
        logger.info('END status=%s', report['status'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-publish', action='store_true')
    args = parser.parse_args()
    config = json.loads((ROOT / 'config/config.json').read_text(encoding='utf-8'))
    logger = setup_logger(ROOT / config['output_paths']['log'])
    # OS file lock is released on exit, including a crashed process.
    import msvcrt
    with (ROOT / '.run.lock').open('a+b') as lock:
        lock.seek(0)
        lock.write(b'0')
        lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            logger.warning('Another run is active')
            return 2
        try:
            return run(ROOT, config, logger, args.no_publish)
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == '__main__':
    raise SystemExit(main())
