from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .history import atomic_write
from .scorer import select_top

CATEGORIES = {'finance_accounting': 'Tài chính – Kế toán', 'economy_business': 'Kinh tế – Doanh nghiệp', 'hot_news': 'Tin nóng'}


def render(root, config, items, now):
    env = Environment(loader=FileSystemLoader(root / 'templates'), autoescape=select_autoescape(['html']))
    env.filters['news_time'] = lambda value: datetime.fromisoformat(value).astimezone(now.tzinfo).strftime('%d/%m %H:%M') if value else 'Chưa có ngày nguồn'
    paths = config['output_paths']
    archive = root / paths['archive']
    archive.mkdir(parents=True, exist_ok=True)
    context = dict(items=items, top=select_top(items, config), categories=CATEGORIES, now=now,
                   edition=now.date().isoformat(), count=len(items), minimum=config['min_items'])
    template = env.get_template('index.html')
    archive_content = template.render(**context, prefix='../', archive_link='index.html')
    atomic_write(archive / (context['edition'] + '.html'), archive_content)
    atomic_write(root / paths['index'], template.render(**context, prefix='', archive_link=paths['archive'] + '/index.html'))
    editions = sorted((p.stem for p in archive.glob('????-??-??.html')), reverse=True)
    atomic_write(archive / 'index.html', env.get_template('archive_index.html').render(editions=editions))
