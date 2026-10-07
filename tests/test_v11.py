import copy
import json
import logging
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import requests
import yaml
from src.classifier import classify
from src.normalizer import normalize
from src.scorer import score
from src.legal_rules import apply_legal
from src.freshness import freshness, sort_live
from src.topic_cluster import cluster_topics
from src.history import merge_live, atomic_write
from src.images import thumbnail
from src.market_data import fetch_markets
from src.fetcher import fetch_sources
from src.main import run
from src.publisher import git, publish
from src.cloud_publish import cloud_publish

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT/'config/config.json').read_text(encoding='utf-8'))
NOW = datetime(2026, 10, 6, 7, tzinfo=ZoneInfo(CONFIG['timezone']))
LOGGER = logging.getLogger('v11tests')
LOGGER.addHandler(logging.NullHandler())


def row(title, age=0, official=False, url=None, description=''):
    entry = dict(title=title, link=url or 'https://example.org/'+str(abs(hash(title))), published=(NOW-timedelta(hours=age)).isoformat(), summary=description)
    source = dict(name='Test source', priority=8, official=official, category='hot_news')
    item = normalize(entry, source, NOW, CONFIG)
    classify(item, CONFIG)
    apply_legal(item, CONFIG, NOW)
    freshness(item, CONFIG, NOW)
    score(item, CONFIG, NOW)
    return item


class V11Tests(unittest.TestCase):
    def test_effective_date_cutoff_and_uncertainty(self):
        item = row('Thông tư thuế có hiệu lực từ ngày 01/07/2026', official=True)
        self.assertEqual(item['legal_effective_date'], '2026-07-01')
        self.assertEqual(item['legal_status'], 'Tham chiếu')
        self.assertTrue(item['legal_verified'])
        for title in ['Dự thảo luật dự kiến có hiệu lực từ ngày 01/07/2026', 'Luật chưa có hiệu lực từ ngày 01/07/2026', 'Thông tư thuế ngày chưa xác định', 'Thông tư có hiệu lực từ ngày 31/02/2026']:
            self.assertIsNone(row(title, official=True)['legal_effective_date'])
        self.assertEqual(row('Luật thuế có hiệu lực từ 01/01/2027', official=True)['legal_status'], 'Sắp có hiệu lực')
        nonofficial = row('Thông tư thuế có hiệu lực từ ngày 01/07/2026')
        self.assertNotEqual(nonofficial['priority'], 'CAO')
        before = row('Thông tư thuế có hiệu lực từ ngày 01/06/2026', official=True)
        self.assertGreater(item['score'], before['score'])

    def test_multiple_effective_dates_do_not_invent(self):
        item = row('Hướng dẫn các luật mới', official=True, description='Luật A có hiệu lực từ 01/07/2026. Luật B có hiệu lực từ 01/08/2026.')
        self.assertIsNone(item['legal_effective_date'])
        item = row('Luật xây dựng có hiệu lực từ 01/07/2026', official=True, description='Một số điều có hiệu lực từ 01/01/2026.')
        self.assertEqual(item['legal_effective_date'], '2026-07-01')
        self.assertTrue(item['legal_date_caveat'])

    def test_new_market_categories(self):
        titles = {'vietnam_stocks':'VN-Index và HNX tăng thanh khoản', 'gold':'Giá vàng SJC và vàng nhẫn', 'fx':'Tỷ giá USD/VND hôm nay', 'crypto':'Bitcoin và Ethereum cập nhật thị trường', 'legal_policy':'Luật mới và nghị định có hiệu lực', 'finance_accounting':'Kế toán và hóa đơn điện tử', 'economy_business':'Doanh nghiệp xuất khẩu tăng đầu tư'}
        for category, title in titles.items():
            self.assertEqual(row(title)['category'], category)
        self.assertNotEqual(row('Chứng khoán Mỹ lập kỷ lục')['category'], 'vietnam_stocks')

    def test_freshness_sorted_and_old_legal_retained(self):
        items = [row('Thuế có hiệu lực từ 01/07/2026', age=90*24, official=True), row('Doanh nghiệp đầu tư', age=30), row('Tin thế giới', age=2), row('Tin thế giới rất cũ', age=1000)]
        self.assertEqual([x['freshness_bucket'] for x in sort_live(items)], ['latest','recent','reference','stale'])
        items[0]['score'] = 10000
        self.assertEqual(sort_live(items)[0]['freshness_bucket'], 'latest')
        ongoing = row('Chính sách đang theo dõi', age=100)
        ongoing['ongoing'] = True
        self.assertEqual(freshness(ongoing, CONFIG, NOW)['freshness_bucket'], 'ongoing')

    def test_topic_newer_update_and_distinct_projects(self):
        older = row('VN-Index tăng 10 điểm trong phiên giao dịch hôm nay', age=5)
        newer = row('VN-Index tăng 15 điểm trong phiên giao dịch hôm nay', age=1)
        leaders = cluster_topics([older,newer], CONFIG)
        self.assertEqual(len(leaders), 1)
        self.assertEqual(leaders[0]['url'], newer['url'])
        self.assertEqual(leaders[0]['related_count'], 1)
        self.assertEqual(len(cluster_topics([row('Doanh nghiệp đầu tư dự án 1'),row('Doanh nghiệp đầu tư dự án 2')], CONFIG)), 2)

    def test_history_migration_missing_fields_and_retention(self):
        old = row('Kế toán và thuế', age=20)
        old.pop('first_seen_at')
        old.pop('last_seen_at')
        new = copy.deepcopy(old)
        new.update(published_at=None, description='', fetched_at=NOW.isoformat())
        rows = merge_live([old], [new], NOW, CONFIG)
        self.assertEqual(rows[0]['first_seen_at'], old['fetched_at'])
        self.assertEqual(rows[0]['published_at'], old['published_at'])
        self.assertEqual(rows[0]['last_seen_at'], NOW.isoformat())
        expired = row('Tin cũ', age=24*100)
        expired['last_seen_at'] = (NOW-timedelta(days=100)).isoformat()
        self.assertFalse(merge_live([expired], [], NOW, CONFIG))

    def test_tvpl_403_404_malformed_fallback(self):
        config = copy.deepcopy(CONFIG)
        config['sources'] = [dict(name='TVPL',url='https://thuvienphapluat.vn/',priority=7,fallback='Government'),dict(name='Government',url='https://example.org/rss',priority=10)]
        good = Mock(content=b'<rss version="2.0"><channel><item><title>Official news</title><link>https://e.org/1</link></item></channel></rss>')
        for problem in [requests.HTTPError('403'), requests.HTTPError('404'), requests.Timeout('timeout')]:
            with patch('src.fetcher.requests.get', side_effect=[problem,good]):
                with self.assertLogs('v11tests',level='INFO') as captured:
                    rows, results = fetch_sources(config, LOGGER)
            self.assertEqual(len(rows), 1)
            self.assertTrue(any('FALLBACK' in line for line in captured.output))
        malformed = Mock(content=b'<html>not RSS</html>')
        with patch('src.fetcher.requests.get',side_effect=[malformed,good]):
            rows, results = fetch_sources(config, LOGGER)
        self.assertEqual(results[0]['status'],'ERROR')

    def test_images_missing_invalid_and_rss_thumbnail(self):
        self.assertIsNone(thumbnail({}, CONFIG))
        self.assertIsNone(thumbnail({'media_thumbnail':[{'url':'javascript:alert(1)'}]}, CONFIG))
        self.assertIsNone(thumbnail({'media_thumbnail':[{'url':'https://127.0.0.1/image.jpg'}]}, CONFIG))
        self.assertIsNone(thumbnail({'media_thumbnail':[{'url':'https://vnecdn.net.evil.org/image.jpg'}]}, CONFIG))
        url = 'https://i1-vnexpress.vnecdn.net/image.jpg'
        self.assertEqual(thumbnail({'summary':f'<img src="{url}">'}, CONFIG), url)
        self.assertIn('error', (ROOT/'static/image-fallback.js').read_text())

    def test_market_failure_retains_timestamp_and_marks_old(self):
        previous = [{'label':'Bitcoin','value':100,'unit':'USD','source':'CoinGecko','updated_at':NOW.isoformat(),'url':'https://api.coingecko.com','kind':'crypto'}]
        with patch('src.market_data.requests.get',side_effect=requests.ConnectionError('offline')):
            cards, results = fetch_markets(CONFIG, LOGGER, NOW, previous)
        self.assertEqual(len(cards),1)
        self.assertTrue(cards[0]['stale'])
        self.assertEqual(cards[0]['updated_at'],NOW.isoformat())
        with patch('src.market_data.requests.get',return_value=Mock(content=b'<html/>',json=lambda:{})):
            cards, results = fetch_markets(CONFIG, LOGGER, NOW)
        self.assertFalse(cards)

    def test_no_new_news_retains_live_items(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            shutil.copytree(ROOT/'templates',root/'templates')
            item=row('Thông tư thuế có hiệu lực từ ngày 01/07/2026',age=90*24,official=True)
            item['last_seen_at']=datetime.now(ZoneInfo(CONFIG['timezone'])).isoformat()
            atomic_write(root/'data/history.json',json.dumps([item]))
            config=copy.deepcopy(CONFIG);config['min_items']=1
            with patch('src.main.fetch_sources',return_value=([],[{'name':'RSS','status':'OK','count':0}])),patch('src.main.fetch_markets',return_value=([],[])):
                self.assertEqual(run(root,config,LOGGER,True),0)
            page=(root/'index.html').read_text(encoding='utf-8')
            self.assertIn('Tham chiếu',page)
            if datetime.now(ZoneInfo(CONFIG['timezone'])).date().isoformat() == CONFIG.get('schedule_trial', {}).get('date'):
                self.assertIn('Lịch thử hôm nay: mỗi 30 phút, 08:00–17:30',page)
            else:
                self.assertIn('Lịch cập nhật: 08:00 và 13:30 mỗi ngày',page)
            self.assertIn('Cập nhật gần nhất:',page)
            self.assertIn('datetime="',page)
            self.assertEqual(len(json.loads((root/'data/history.json').read_text())),1)

    def test_workflow_syntax_schedule_and_least_privilege(self):
        value = yaml.safe_load((ROOT/'.github/workflows/morning-news.yml').read_text())
        triggers = value.get('on',value.get(True))
        self.assertEqual([entry['cron'] for entry in triggers['schedule']], ['0 1 * * *', '30 6 * * *', '0 2-10 7 10 *', '30 1-5,7-10 7 10 *'])
        self.assertEqual(CONFIG['scheduler_times'], ['08:00', '13:30'])
        self.assertNotIn('workflow_dispatch',triggers)
        self.assertEqual(value['permissions'],{'contents':'write'})
        self.assertEqual(value['jobs']['update-news']['runs-on'],'ubuntu-latest')
        self.assertFalse(value['concurrency']['cancel-in-progress'])

    def test_cloud_publish_requires_runner(self):
        with patch.dict(os.environ,{'GITHUB_ACTIONS':'false'}):
            with self.assertRaises(RuntimeError):
                cloud_publish(ROOT,CONFIG,LOGGER)

    def test_real_cloud_push_conflict_regenerates_latest_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);remote=root/'remote.git';checkout=root/'checkout';other=root/'other'
            git(root,'init','--bare',str(remote));checkout.mkdir()
            git(checkout,'init','-b','main');git(checkout,'config','user.name','Test');git(checkout,'config','user.email','test@example.invalid')
            git(checkout,'remote','add','origin',str(remote))
            (checkout/'index.html').write_text('initial')
            atomic_write(checkout/'data/history.json','[]')
            config=copy.deepcopy(CONFIG);config['publish']['remote']=str(remote)
            self.assertTrue(publish(checkout,LOGGER,config))
            git(root,'clone','--branch','main',str(remote),str(other))
            git(other,'config','user.name','Owner');git(other,'config','user.email','owner@example.invalid')
            (checkout/'index.html').write_text('runner update')
            conflict=[True]
            def conflicting_git(path,*args):
                if args[0]=='push' and conflict[0]:
                    conflict[0]=False
                    (other/'README.md').write_text('owner change must survive')
                    atomic_write(other/'data/history.json','[{"url":"https://owner.org/retained"}]')
                    git(other,'add','README.md','data/history.json');git(other,'commit','-m','owner update');git(other,'push','origin','main')
                return git(path,*args)
            def regenerate():
                rows=json.loads((checkout/'data/history.json').read_text())
                rows.append({'url':'https://runner.org/new'})
                atomic_write(checkout/'data/history.json',json.dumps(rows))
                (checkout/'index.html').write_text('regenerated')
            with patch.dict(os.environ,{'GITHUB_ACTIONS':'true'}),patch('src.cloud_publish.git',side_effect=conflicting_git):
                self.assertTrue(cloud_publish(checkout,config,LOGGER,regenerate))
            self.assertEqual((checkout/'README.md').read_text(),'owner change must survive')
            self.assertEqual(len(json.loads((checkout/'data/history.json').read_text())),2)
            self.assertEqual(git(checkout,'rev-parse','HEAD'),git(checkout,'rev-parse','origin/main'))
            before=git(checkout,'rev-parse','HEAD')
            with patch.dict(os.environ,{'GITHUB_ACTIONS':'true'}):
                self.assertTrue(cloud_publish(checkout,config,LOGGER,regenerate))
            self.assertEqual(before,git(checkout,'rev-parse','HEAD'))


if __name__ == '__main__':
    unittest.main()
