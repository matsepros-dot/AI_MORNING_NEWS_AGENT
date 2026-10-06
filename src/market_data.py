import json
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import requests


def number(value):
    result = float(str(value).replace(',', ''))
    if not math.isfinite(result) or result < 0:
        raise ValueError('Invalid market value')
    return result


def fetch_markets(config, logger, now, previous=None):
    cards, results = [], []
    for source in config.get('market_sources', []):
        try:
            response = requests.get(source['url'], params=source.get('params'), timeout=config['request_timeout'], headers={'User-Agent': config['user_agent']})
            response.raise_for_status()
            rows = []
            if source['kind'] == 'fx':
                tree = ET.fromstring(response.content)
                date_text = tree.findtext('DateTime')
                if not date_text:
                    raise ValueError('Missing source timestamp')
                updated = datetime.strptime(date_text.strip(), '%m/%d/%Y %I:%M:%S %p').replace(tzinfo=now.tzinfo)
                for row in tree.findall('Exrate'):
                    if row.get('CurrencyCode') in source['currencies']:
                        rows.append(dict(label=row.get('CurrencyCode')+'/VND', value=number(row.get('Sell')), buy=number(row.get('Transfer')), unit='VND', kind='fx', updated_at=updated.isoformat()))
            elif source['kind'] == 'crypto':
                payload = response.json()
                for key, label in [('bitcoin', 'Bitcoin'), ('ethereum', 'Ethereum')]:
                    row = payload[key]
                    updated = datetime.fromtimestamp(row['last_updated_at'], timezone.utc)
                    change = float(row['usd_24h_change']) if row.get('usd_24h_change') is not None else None
                    if change is not None and not math.isfinite(change):
                        raise ValueError('Invalid price change')
                    rows.append(dict(label=label, value=number(row['usd']), change=change, unit='USD', kind='crypto', updated_at=updated.isoformat()))
            if not rows:
                raise ValueError('No supported market data')
            for row in rows:
                row.update(source=source['name'], url=source['url'], stale=(now-datetime.fromisoformat(row['updated_at'])).total_seconds() > config['market_max_age_hours'] * 3600)
            cards.extend(rows)
            results.append(dict(name=source['name'], status='OK', count=len(rows)))
            logger.info('MARKET OK %s cards=%d', source['name'], len(rows))
        except (requests.RequestException, ValueError, KeyError, TypeError, ET.ParseError, OverflowError) as exc:
            results.append(dict(name=source['name'], status='ERROR', reason=str(exc)))
            logger.warning('MARKET ERROR %s: %s', source['name'], exc)
            # Keep old quotes clearly marked; never invent or relabel their update time.
            cards.extend(dict(row, stale=True) for row in (previous or []) if row.get('source') == source['name'])
    return cards, results
