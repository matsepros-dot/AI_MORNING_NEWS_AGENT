from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .history import atomic_write
from .scorer import select_top

CATEGORIES = {'finance_accounting': 'Tài chính – Kế toán – Thuế', 'legal_policy': 'Chính sách / Pháp lý đáng chú ý',
              'economy_business': 'Kinh tế – Doanh nghiệp', 'vietnam_stocks': 'Chứng khoán Việt Nam',
              'gold': 'Vàng', 'fx': 'Tỷ giá', 'crypto': 'Crypto', 'hot_news': 'Tin nóng'}


def render(root, config, items, now, markets=None):
    env = Environment(loader=FileSystemLoader(root / 'templates'), autoescape=select_autoescape(['html']))
    env.filters['news_time'] = lambda value: datetime.fromisoformat(value).astimezone(now.tzinfo).strftime('%d/%m %H:%M') if value else 'Chưa có ngày nguồn'
    paths = config['output_paths']
    archive = root / paths['archive']
    archive.mkdir(parents=True, exist_ok=True)
    current = [x for x in items if x['freshness_bucket'] in ('latest', 'recent')]
    context = dict(items=items, current=current, older=[x for x in items if x['freshness_bucket'] in ('ongoing', 'reference')],
                   latest=sorted(current, key=lambda x: x.get('published_at') or x['first_seen_at'], reverse=True)[:config['latest_items']],
                   top=select_top(sorted(current or items, key=lambda x:x['score'], reverse=True), config), categories=CATEGORIES, now=now,
                   edition=now.date().isoformat(), count=len(items), minimum=config['min_items'], markets=markets or [], version=config['version'], scheduler_times=config['scheduler_times'], schedule_trial=config.get('schedule_trial', {}))
    template = env.get_template('index.html')
    archive_content = template.render(**context, prefix='../', archive_link='index.html')
    atomic_write(archive / (context['edition'] + '.html'), archive_content)
    atomic_write(root / paths['index'], template.render(**context, prefix='', archive_link=paths['archive'] + '/index.html'))
    editions = sorted((p.stem for p in archive.glob('????-??-??.html')), reverse=True)
    atomic_write(archive / 'index.html', env.get_template('archive_index.html').render(editions=editions))
