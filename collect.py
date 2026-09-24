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
NAVER = 'https://openapi.naver.com/v1/search/news.json?query={q}&display=100&sort=date'

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


def from_naver(track, q, since, cid, secret):
    raw = fetch(NAVER.format(q=urllib.parse.quote(q)),
                {'X-Naver-Client-Id': cid, 'X-Naver-Client-Secret': secret})
    out = []
    for e in json.loads(raw).get('items', []):
        try:
            d = parsedate_to_datetime(e['pubDate']).astimezone(KST)
        except Exception:
            continue
        if d < since:
            continue
        url = e.get('originallink') or e.get('link')
        media = urllib.parse.urlparse(url).netloc.replace('www.', '')
        out.append({'track': track, 'title': clean(e.get('title')), 'url': url, 'media': media,
                    'date': d.strftime('%Y-%m-%d'), 'summary': clean(e.get('description'))[:240],
                    'source': 'naver'})
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=3)
    ap.add_argument('--seed', help='JSON 파일을 DB에 적재(초기 데이터 · 수작업 보강용)')
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
                    got += from_naver(track, q.replace('"', ''), since, cid, secret)
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


if __name__ == '__main__':
    main()
