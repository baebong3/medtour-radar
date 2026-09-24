# -*- coding: utf-8 -*-
"""
뉴스 수집 → data/news.db 적재 (누적 · 멱등)

  - 네이버 뉴스 검색 API (NAVER_ID · NAVER_SECRET 환경변수, 있으면 사용)
  - Google 뉴스 RSS (한국어 · 영문, 키 없이 동작)
  - 같은 URL은 트랙별로 한 번만 저장 (두 트랙에 동시에 걸리는 기사는 양쪽에 모두 남음)

사용법
  python radar/collect.py              # 최근 3일
  python radar/collect.py --days 7
"""
import argparse, html, json, os, re, sqlite3, sys, time
import urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules import TRACKS, KST, classify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'data', 'news.db')

GOOGLE_KO = 'https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko'
GOOGLE_EN = 'https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en'
NAVER = 'https://openapi.naver.com/v1/search/news.json?query={q}&display=100&start={s}&sort=date'
NAVER_MAX = 1000            # 네이버 검색 API 한도 : 한 번에 100건, start 최대 1,000 → 검색어당 최근 1,000건

SCHEMA = """
CREATE TABLE IF NOT EXISTS news(
  url TEXT NOT NULL,
  track TEXT NOT NULL,
  title TEXT NOT NULL,
  media TEXT,
  date TEXT NOT NULL,
  summary TEXT,
  note TEXT,
  category TEXT,
  source TEXT,
  collected_at TEXT,
  PRIMARY KEY(url, track)
);
CREATE INDEX IF NOT EXISTS ix_news_date ON news(date);
CREATE INDEX IF NOT EXISTS ix_news_track ON news(track);
"""


def db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    return con


def clean(s):
    s = re.sub(r'<[^>]+>', ' ', s or '')
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()


def upsert(con, it):
    if not it.get('summary') and it.get('note'):
        it['summary'] = it['note'].split('→')[0].strip()   # 수작업 메모의 요약 부분만 본문 요약으로 사용
    it.setdefault('category', classify(it))
    cur = con.execute('SELECT 1 FROM news WHERE url=? AND track=?', (it['url'], it['track'])).fetchone()
    if cur:
        return 0
    # 제목과 요약까지 같은 기사(통신사 전재 등)는 URL이 달라도 한 번만 저장
    dup = con.execute('SELECT 1 FROM news WHERE track=? AND title=? AND IFNULL(summary,"")=?',
                      (it['track'], it['title'], it.get('summary') or '')).fetchone()
    if dup:
        return 0
    con.execute('INSERT INTO news(url,track,title,media,date,summary,note,category,source,collected_at) '
                'VALUES(?,?,?,?,?,?,?,?,?,?)',
                (it['url'], it['track'], it['title'], it.get('media', ''), it['date'],
                 it.get('summary', ''), it.get('note', ''), it['category'], it.get('source', ''),
                 datetime.now(KST).strftime('%Y-%m-%d %H:%M')))
    return 1


def fetch(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers=dict({'User-Agent': 'Mozilla/5.0 medtour-radar'}, **(headers or {})))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def from_naver(track, q, since, cid, secret, limit=NAVER_MAX):
    """최신순으로 100건씩 넘기며 수집 기간(since) 이전 기사가 나오거나 1,000건에 닿으면 멈춤"""
    out, start = [], 1
    while start <= min(limit, NAVER_MAX):
        raw = fetch(NAVER.format(q=urllib.parse.quote(q), s=start),
                    {'X-Naver-Client-Id': cid, 'X-Naver-Client-Secret': secret})
        items = json.loads(raw).get('items', [])
        old = False
        for e in items:
            try:
                d = parsedate_to_datetime(e['pubDate']).astimezone(KST)
            except Exception:
                continue
            if d < since:
                old = True
                continue
            url = e.get('originallink') or e.get('link')
            media = urllib.parse.urlparse(url).netloc.replace('www.', '')
            out.append({'track': track, 'title': clean(e.get('title')), 'url': url, 'media': media,
                        'date': d.strftime('%Y-%m-%d'), 'summary': clean(e.get('description'))[:240],
                        'source': 'naver'})
        if old or len(items) < 100:
            break
        start += 100
        time.sleep(0.12)
    return out


def from_google(track, url, since):
    try:
        import feedparser
    except ImportError:
        return []
    f = feedparser.parse(url)
    out = []
    for e in f.entries:
        pp = e.get('published_parsed') or e.get('updated_parsed')
        if not pp:
            continue
        d = datetime(*pp[:6], tzinfo=timezone.utc).astimezone(KST)
        if d < since:
            continue
        title = clean(e.get('title'))
        media = ''
        m = re.match(r'^(.*) - ([^-]+)$', title)
        if m:
            title, media = m.group(1).strip(), m.group(2).strip()
        out.append({'track': track, 'title': title, 'url': e.get('link', ''), 'media': media,
                    'date': d.strftime('%Y-%m-%d'), 'summary': clean(e.get('summary'))[:240],
                    'source': 'google'})
    return out


# ── 잘린 제목 복원 ─────────────────────────────────────────────
# 네이버 검색 API는 긴 제목을 '...'로 잘라서 줌 → 원문 기사의 og:title 등으로 전체 제목을 되살림
CUT = re.compile(r'\s*(\.{2,}|…)\s*$')


def is_cut(title):
    return bool(CUT.search(title or ''))


def _key(s):
    return re.sub(r'[^0-9A-Za-z가-힣]', '', html.unescape(s or '')).lower()


def _decode(raw, ctype=''):
    m = re.search(r'charset=([\w-]+)', ctype or '', re.I) or re.search(rb'<meta[^>]+charset=["\']?([\w-]+)', raw[:4000], re.I)
    enc = (m.group(1).decode() if m and isinstance(m.group(1), bytes) else (m.group(1) if m else '')) or 'utf-8'
    enc = {'ks_c_5601-1987': 'cp949', 'euc-kr': 'cp949', 'euckr': 'cp949'}.get(enc.lower(), enc)
    for e in (enc, 'utf-8', 'cp949'):
        try:
            return raw.decode(e)
        except Exception:
            pass
    return raw.decode('utf-8', 'ignore')


def match_full(cut_title, candidates):
    """잘린 제목의 앞부분과 이어지는 후보 중 가장 알맞은 전체 제목 (사이트명 꼬리 제거)"""
    pre = CUT.sub('', cut_title).strip()
    pk = _key(pre)
    if len(pk) < 6:
        return None
    for c in candidates:
        c = re.sub(r'\s+', ' ', html.unescape(c or '')).strip()
        if not c or is_cut(c) or not _key(c).startswith(pk[:max(6, len(pk) - 2)]) or len(_key(c)) <= len(pk):
            continue
        # 앞부분 이후에 나오는 사이트명 구분자( | , - , :: , < ) 뒤는 버림
        cut_at = len(pre) - 2
        m = re.search(r'\s+(\||::|<|-|–|—|:)\s+[^|]{1,30}$', c[cut_at:])
        if m:
            c = c[:cut_at + m.start()].strip()
        return c if len(_key(c)) > len(pk) else None
    return None


def page_titles(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                                                 '(KHTML, like Gecko) Chrome/124 Safari/537.36',
                                                   'Accept-Language': 'ko-KR,ko;q=0.9'})
        with urllib.request.urlopen(req, timeout=8) as r:
            doc = _decode(r.read(600000), r.headers.get('Content-Type', ''))
    except Exception:
        return []
    out = []
    for pat in (r'<meta[^>]+property=["\']og:title["\'][^>]*content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*property=["\']og:title',
                r'<meta[^>]+name=["\']twitter:title["\'][^>]*content=["\']([^"\']+)',
                r'<title[^>]*>(.*?)</title>', r'<h1[^>]*>(.*?)</h1>', r'<h2[^>]*>(.*?)</h2>'):
        out += [re.sub(r'<[^>]+>', ' ', x) for x in re.findall(pat, doc, re.I | re.S)[:3]]
    return out


def repair_titles(con, limit=250):
    rows = con.execute("SELECT DISTINCT url, title FROM news WHERE title LIKE '%...' OR title LIKE '%…' "
                       "ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
    known = [r[0] for r in con.execute('SELECT DISTINCT title FROM news')]
    fixed = 0
    for url, title in rows:
        full = match_full(title, known)                     # 다른 경로(Google RSS 등)로 들어온 전체 제목이 있으면 우선 사용
        if not full:
            full = match_full(title, page_titles(url))
            time.sleep(0.2)
        if full:
            con.execute('UPDATE news SET title=? WHERE url=? AND title=?', (full, url, title))
            fixed += 1
    con.commit()
    left = con.execute("SELECT COUNT(*) FROM news WHERE title LIKE '%...' OR title LIKE '%…'").fetchone()[0]
    print('잘린 제목 복원 %d건 · 남은 %d건' % (fixed, left))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=3)
    ap.add_argument('--max', type=int, default=NAVER_MAX, help='네이버 검색어당 최대 수집 건수(최대 1,000)')
    ap.add_argument('--seed', help='JSON 파일을 DB에 적재(초기 데이터 · 수작업 보강용)')
    ap.add_argument('--repair', type=int, default=250, help='한 번에 복원을 시도할 잘린 제목 수(0이면 건너뜀)')
    a = ap.parse_args()

    con = db()
    if a.seed:
        n = sum(upsert(con, it) for it in json.load(open(a.seed, encoding='utf-8')))
        con.commit()
        print('seed 적재 %d건' % n)
        return

    since = datetime.now(KST) - timedelta(days=a.days)
    cid, secret = os.environ.get('NAVER_ID'), os.environ.get('NAVER_SECRET')
    total = 0
    for track, cfg in TRACKS.items():
        got = []
        for q in cfg['ko']:
            if cid and secret:
                try:
                    nv = from_naver(track, q.replace('"', ''), since, cid, secret, a.max)
                    got += nv
                    print('  네이버 %-24s %4d건' % (q, len(nv)))
                except Exception as ex:
                    print('  네이버 실패 %s : %s' % (q, ex))
                time.sleep(0.15)
            got += from_google(track, GOOGLE_KO.format(q=urllib.parse.quote(q)), since)
        for q in cfg['en']:
            got += from_google(track, GOOGLE_EN.format(q=urllib.parse.quote(q)), since)
        n = sum(upsert(con, it) for it in got if it['url'] and it['title'])
        con.commit()
        total += n
        print('[%s] 후보 %d건 · 신규 적재 %d건' % (track, len(got), n))
    print('합계 신규 %d건 · DB 누적 %d건' % (total, con.execute('SELECT COUNT(*) FROM news').fetchone()[0]))
    if a.repair:
        repair_titles(con, a.repair)


if __name__ == '__main__':
    main()
