import re
from datetime import date
from .classifier import keyword_text

DATE = r'(\d{1,2})[/-](\d{1,2})[/-](20\d{2})'
EFFECTIVE = re.compile(r'(?:có hiệu lực(?: thi hành)?|hiệu lực thi hành|bắt đầu có hiệu lực)\s*(?:kể )?(?:từ|vào)\s*(?:ngày\s*)?' + DATE, re.I)
ISSUED = re.compile(r'(?:ban hành|được thông qua)\s*(?:vào\s*)?(?:ngày\s*)?' + DATE, re.I)


def explicit_date(pattern, text):
    matches = []
    for match in pattern.finditer(text):
        # Negative or proposed statements must never become a confirmed date.
        before = text[max(0, match.start()-60):match.start()].casefold()
        if any(word in before for word in ('dự thảo', 'dự kiến', 'chưa', 'không', 'đề xuất')):
            continue
        try:
            value = date(int(match[3]), int(match[2]), int(match[1])).isoformat()
            matches.append((value, match.group(0)))
        except ValueError:
            continue
    unique = {value for value, _ in matches}
    return matches[0] if len(unique) == 1 else (None, '')


def apply_legal(item, config, now):
    text = ' '.join([item['title'], item['description'], item.get('legal_evidence', '')])
    normalized = keyword_text(text)
    item['is_legal'] = any(re.search(r'(?<!\w)' + re.escape(keyword_text(word)) + r'(?!\w)', normalized) for word in config['legal_keywords'])
    headline_date, headline_evidence = explicit_date(EFFECTIVE, item['title']) if item['is_legal'] else (None, '')
    body_date, body_evidence = explicit_date(EFFECTIVE, text) if item['is_legal'] else (None, '')
    item['legal_effective_date'] = headline_date or body_date
    item['effective_date_evidence'] = headline_evidence or body_evidence
    item['legal_date_caveat'] = 'Có thể có điều khoản áp dụng mốc khác; xem đầy đủ tại nguồn' if headline_date and not body_date else ''
    item['legal_issued_date'], _ = explicit_date(ISSUED, text) if item['is_legal'] else (None, '')
    item['legal_verified'] = bool(item['is_legal'] and item.get('official'))
    item['legal_status'] = 'Cần theo dõi' if item['is_legal'] else ''
    if item['is_legal']:
        effective = item['legal_effective_date']
        if effective and item['legal_verified']:
            item['legal_status'] = 'Sắp có hiệu lực' if effective > now.date().isoformat() else 'Tham chiếu'
            # A passed date alone does not establish that a law has not been repealed.
            if re.search(r'\bđang có hiệu lực\b', normalized):
                item['legal_status'] = 'Đang có hiệu lực'
        item['legal_verification_label'] = 'Nguồn chính thống; kiểm tra sửa đổi/thay thế tại nguồn' if item['legal_verified'] else 'Chưa đối chiếu nguồn chính thống'
    return item
