import copy
import json
import logging
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, Mock

import requests
from bs4 import BeautifulSoup
from src.normalizer import normalize
from src.classifier import classify
from src.scorer import score, select_top
from src.deduplicator import deduplicate
from src.history import load_history, update_history, unseen
from src.fetcher import fetch_sources
from src.main import run
from src.publisher import publish

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config/config.json').read_text(encoding='utf-8'))
NOW = datetime.now(timezone.utc)
LOGGER = logging.getLogger('tests')
LOGGER.addHandler(logging.NullHandler())


def entry(title='Ngân hàng thay đổi lãi suất', url='https://example.org/news', **extra):
    return dict(title=title, link=url, published=NOW.isoformat(), summary='<p>Mô tả công khai</p>', **extra)


def item(title='Ngân hàng thay đổi lãi suất', url='https://example.org/news', source=None):
    result = normalize(entry(title, url), source or CONFIG['sources'][0], NOW, CONFIG)
    return score(classify(result, CONFIG), CONFIG, NOW)


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'templates', self.root / 'templates')

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_date_description_html_and_url(self):
        raw = dict(title='<b>Thuế mới</b>', link='https://example.org/a?utm_source=x&id=2#x', summary='<script>bad</script>')
        value = normalize(raw, CONFIG['sources'][0], NOW, CONFIG)
        self.assertIsNone(value['published_at'])
        self.assertEqual(value['description'], '')
        self.assertEqual(value['title'], 'Thuế mới')
        self.assertEqual(value['url'], 'https://example.org/a?id=2')
        with self.assertRaises(ValueError):
            normalize(dict(title='X', link='javascript:alert(1)'), CONFIG['sources'][0], NOW, CONFIG)
        missing_score = score(classify(value, CONFIG), CONFIG, NOW)['score']
        value['published_at'] = NOW.isoformat()
        self.assertGreater(score(value, CONFIG, NOW)['score'], missing_score)

    def test_all_categories_and_keyword_boundaries(self):
        for title, expected in [('Quy định hóa đơn điện tử và kế toán', 'finance_accounting'), ('Doanh nghiệp xuất khẩu', 'economy_business'), ('Bão mạnh trên thế giới', 'hot_news')]:
            self.assertEqual(item(title)['category'], expected)
        self.assertNotIn('AI', item('Hai người gặp nhau')['keywords'])

    def test_dedup_official_priority_fuzzy_and_numbers(self):
        a = item()
        official = item(url='https://official.org/1', source=dict(name='Official', priority=10, official=True))
        self.assertEqual(deduplicate([a, official], CONFIG), [official])
        self.assertEqual(len(deduplicate([a, item('Ngân hàng thay đổi lãi suất!', 'https://other.org/2')], CONFIG)), 1)
        self.assertEqual(len(deduplicate([item('Lãi suất 5% tháng 10'), item('Lãi suất 6% tháng 11', 'https://other.org/3')], CONFIG)), 2)
        self.assertEqual(len(deduplicate([item('Doanh nghiệp mở nhà máy ở Hà Nội'), item('Doanh nghiệp đóng nhà máy ở Đà Nẵng', 'https://other.org/4')], CONFIG)), 2)
        self.assertEqual(len(deduplicate([item('Thuế mới áp dụng cho doanh nghiệp'), item('Thuế mới áp dụng cho doanh nghiệp.', 'https://other.org/5')], CONFIG)), 1)

    def test_top_diversity(self):
        rows = [item('Thuế mới', 'https://e.org/1'), item('Thuế mới thứ hai', 'https://e.org/2'), item('Doanh nghiệp đầu tư', 'https://e.org/3')]
        for index, row in enumerate(rows):
            row['score'] = 70-index
        self.assertEqual(select_top(rows, CONFIG)[1]['category'], 'economy_business')

    def test_source_dead_timeout_zero_and_surviving_source(self):
        config = copy.deepcopy(CONFIG)
        config['sources'] = [dict(name=str(n), url='https://example.org/rss', priority=1) for n in range(4)]
        empty = Mock(content=b'<rss version="2.0"><channel><title>Empty</title></channel></rss>')
        good = Mock(content=b'<rss version="2.0"><channel><item><title>News</title><link>https://e.org/1</link></item></channel></rss>')
        with patch('src.fetcher.requests.get', side_effect=[requests.ConnectionError('dead'), requests.Timeout('timeout'), empty, good]):
            rows, results = fetch_sources(config, LOGGER)
        self.assertEqual(len(rows), 1)
        self.assertEqual([r['status'] for r in results], ['ERROR', 'ERROR', 'OK', 'OK'])
        self.assertEqual(results[2]['count'], 0)

    def test_offline_preserves_all_output(self):
        files = ['index.html', 'archive/index.html', 'data/history.json']
        for name in files:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('[]' if name.endswith('.json') else 'previous', encoding='utf-8')
        before = {name: (self.root / name).read_bytes() for name in files}
        with patch('src.main.fetch_sources', return_value=([], [])):
            self.assertEqual(run(self.root, CONFIG, LOGGER, True), 1)
        self.assertEqual(before, {name: (self.root / name).read_bytes() for name in files})

    def test_rerun_real_pipeline_archive_history_html(self):
        rows = [(entry(title=f'Doanh nghiệp đầu tư dự án {n}', url=f'https://example.org/{n}'), CONFIG['sources'][0]) for n in range(12)]
        rows[0] = (dict(title='Thuế và hóa đơn điện tử', link='https://example.org/tax'), CONFIG['sources'][0])
        rows[1] = (entry(title='Bão mạnh trên thế giới', url='https://example.org/storm'), CONFIG['sources'][1])
        rows.append((dict(entry(), published=(NOW - timedelta(hours=26)).isoformat()), CONFIG['sources'][0]))
        with patch('src.main.fetch_sources', return_value=(rows, [])):
            self.assertEqual(run(self.root, CONFIG, LOGGER, True), 0)
            self.assertEqual(run(self.root, CONFIG, LOGGER, True), 0)
        history = load_history(self.root / 'data/history.json')
        self.assertEqual(len(history), 12)
        self.assertEqual(len(list((self.root / 'archive').glob('????-??-??.html'))), 1)
        self.assertEqual({x['category'] for x in history}, set(CONFIG['keywords']))
        soup = BeautifulSoup((self.root / 'index.html').read_text(encoding='utf-8'), 'html.parser')
        self.assertEqual(len(soup.select('.news-card')), 12)
        for link in soup.select('a[target]'):
            self.assertEqual(set(link['rel']), {'noopener', 'noreferrer'})
        self.assertIsNotNone(soup.find('meta', attrs={'name': 'viewport'}))
        self.assertEqual(soup.html['lang'], 'vi')

    def test_history_retention_and_new_url(self):
        today = NOW.date().isoformat()
        previous = (NOW.date() - timedelta(days=1)).isoformat()
        stale = (NOW.date() - timedelta(days=60)).isoformat()
        path = self.root / 'history.json'
        rows = [dict(item(), edition_date=previous), dict(item(url='https://e.org/stale'), edition_date=stale)]
        self.assertEqual(unseen([item(), item(url='https://e.org/new')], rows, today)[0]['url'], 'https://e.org/new')
        update_history(path, rows, [item(url='https://e.org/new')], today, 45)
        self.assertEqual(len(load_history(path)), 2)
        path.write_text('invalid', encoding='utf-8')
        with self.assertRaises(json.JSONDecodeError):
            load_history(path)
        self.assertEqual(path.read_text(), 'invalid')

    def test_git_no_changes_still_retries_push(self):
        (self.root / 'index.html').write_text('news')
        def fake_git(root, *args):
            if args[0] == 'branch': return 'main'
            if args[:3] == ('remote', 'get-url', 'origin'): return CONFIG['publish']['remote']
            return ''
        with patch('src.publisher.git', side_effect=fake_git) as mocked:
            self.assertTrue(publish(self.root, LOGGER, CONFIG))
        self.assertIn(('push', 'origin', 'main'), [call.args[1:] for call in mocked.call_args_list])
        self.assertNotIn('commit', [call.args[1] for call in mocked.call_args_list])

    def test_git_push_failure_and_stage_guard(self):
        def fake_git(root, *args):
            if args[0] == 'branch': return 'main'
            if args[0] == 'remote': return CONFIG['publish']['remote']
            if args[0] == 'push': raise RuntimeError('offline')
            return ''
        with patch('src.publisher.git', side_effect=fake_git):
            self.assertFalse(publish(self.root, LOGGER, CONFIG))
        def unsafe(root, *args):
            if args[0] == 'diff': return 'KEY.txt'
            return fake_git(root, *args)
        with patch('src.publisher.git', side_effect=unsafe) as mocked:
            self.assertFalse(publish(self.root, LOGGER, CONFIG))
        self.assertNotIn('commit', [call.args[1] for call in mocked.call_args_list])


if __name__ == '__main__':
    unittest.main()
