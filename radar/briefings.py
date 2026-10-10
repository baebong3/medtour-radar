# -*- coding: utf-8 -*-
"""일일 이슈 브리핑 PDF 모음 페이지 생성 - docs/briefings/brief_YYYYMMDD.pdf 를 날짜순으로 나열

사용: python radar/briefings.py
새 브리핑은 docs/briefings/brief_YYYYMMDD.pdf 로 넣고 이 스크립트를 다시 실행하면 목록이 갱신됨
"""
import os, re, html, json
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, 'docs', 'briefings')
CACHE = os.path.join(DIR, 'headlines.json')
KST = timezone(timedelta(hours=9))
WD = '월화수목금토일'
PAT = re.compile(r'^brief_(\d{8})\.pdf$')

# 1번(전폭) 카드의 태그줄 : '1 리스크·분쟁 의료관광 원문 검증'
TAG = re.compile(r'^1\s*\S.*?(?:원문\s*검증|원문\s*미확인)\s*$')
LEAD = re.compile(r'^금일\s*중점')
DROP = re.compile(r'^(○|시사점|자료원|중요도 분류|과업)')


def items():
    out = []
    if not os.path.isdir(DIR):
        return out
    for f in os.listdir(DIR):
        m = PAT.match(f)
        if m:
            d = datetime.strptime(m.group(1), '%Y%m%d')
            out.append((d, f, os.path.getsize(os.path.join(DIR, f))))
    return sorted(out, reverse=True)


def extract(path):
    """브리핑 PDF 1쪽에서 주요 이슈 1번 카드의 제목(헤드라인)을 뽑음. 실패하면 빈 문자열"""
    try:
        from pypdf import PdfReader
        lines = [l.strip() for l in PdfReader(path).pages[0].extract_text().split('\n')]
    except Exception:
        return ''
    lines = [l for l in lines if l]
    idx = None
    for i, l in enumerate(lines):
        if TAG.match(l):
            idx = i
            break
    if idx is None:
        for i, l in enumerate(lines):
            if LEAD.match(l):
                idx = i + 1
                break
    if idx is None or idx + 1 >= len(lines):
        return ''
    t = lines[idx + 1]
    if DROP.match(t):
        return ''
    # 제목이 두 줄로 끊긴 경우 이어 붙임
    if len(t) < 30 and idx + 2 < len(lines):
        nxt = lines[idx + 2]
        if not DROP.match(nxt) and not re.match(r'^\d\s*\S', nxt):
            t = t + ' ' + nxt
    return re.sub(r'\s+', ' ', t).strip()


def headlines(it):
    """{파일명: 헤드라인}. docs/briefings/headlines.json 에 저장해 두고 새 PDF만 새로 읽음.
    이 파일의 값을 직접 고치면 그 문구가 그대로 쓰임(자동 추출이 어긋났을 때 수동 교정용)"""
    try:
        cache = json.load(open(CACHE, encoding='utf-8'))
    except Exception:
        cache = {}
    changed = False
    for _, f, _sz in it:
        if f not in cache:
            cache[f] = extract(os.path.join(DIR, f))
            changed = True
    names = {f for _, f, _sz in it}
    for f in [k for k in cache if k not in names]:
        del cache[f]
        changed = True
    if changed:
        try:
            os.makedirs(DIR, exist_ok=True)
            json.dump(cache, open(CACHE, 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1, sort_keys=True)
        except Exception:
            pass
    return cache


def summary():
    """메인 페이지 머리글용 (건수, 최신 날짜 문자열, 최신 파일명)"""
    it = items()
    if not it:
        return 0, '', ''
    d, f, _ = it[0]
    return len(it), d.strftime('%Y.%m.%d'), f


CSS = """<style>
@font-face{font-family:'PretendardSub';font-weight:400 600;src:url(../assets/fonts/pretendard-sub-Regular.woff2) format('woff2')}
@font-face{font-family:'PretendardSub';font-weight:700 900;src:url(../assets/fonts/pretendard-sub-ExtraBold.woff2) format('woff2')}
:root{color-scheme:light;--ink:#1C1B1B;--sub:#5F5D5C;--muted:#8D8B8B;--rule:#E7E4E2;--bg:#FAF8F6;--red:#D80024;--org:#E49000}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--ink);font-family:'PretendardSub','Pretendard','Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',sans-serif;-webkit-font-smoothing:antialiased}
a{color:inherit}
.mast{border-bottom:1px solid var(--rule)}
.mast .in{max-width:880px;margin:0 auto;padding:14px 16px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.logo{height:30px}
.vr{width:1px;height:32px;background:#DEDBD9}
.t1{display:block;font-size:12px;color:var(--muted)}
.t2{display:block;font-size:19px;font-weight:800;letter-spacing:-.3px}
.back{margin-left:auto;font-size:13px;font-weight:700;text-decoration:none;border:1px solid var(--rule);border-radius:999px;padding:7px 14px}
.ribbon{display:flex;height:4px}.ribbon i{flex:1}.ribbon i:nth-child(1){background:#D80024}.ribbon i:nth-child(2){background:#E49000}.ribbon i:nth-child(3){background:#F2DF4E}.ribbon i:nth-child(4){background:#E478A8}
.wrap{max-width:880px;margin:0 auto;padding:22px 16px 48px}
.lead{background:var(--bg);border-radius:10px;padding:14px 16px;font-size:14px;line-height:1.6;color:var(--sub)}
.lead b{color:var(--ink)}
.kpi{display:flex;gap:28px;margin:18px 0 6px;flex-wrap:wrap}
.kpi div{font-size:12px;color:var(--muted)}.kpi b{display:block;font-size:24px;font-weight:800;color:var(--ink);font-variant-numeric:tabular-nums}
.kpi .o b{color:var(--org)}
h2{font-size:15px;font-weight:800;margin:28px 0 8px;padding-bottom:8px;border-bottom:1.5px solid var(--ink)}
ul{list-style:none;margin:0;padding:0}
li{display:flex;align-items:center;gap:14px;padding:11px 2px;border-bottom:1px solid var(--rule);flex-wrap:wrap}
.d{font-weight:800;font-size:15px;font-variant-numeric:tabular-nums;min-width:118px}
.w{font-size:13px;color:var(--muted);min-width:34px}
.n{flex:1;min-width:0;font-size:13.5px;line-height:1.45;color:var(--ink);font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.n.e{color:var(--muted);font-weight:400}
.new{display:inline-block;margin-left:6px;background:var(--red);color:#fff;font-size:11px;font-weight:800;border-radius:4px;padding:1px 6px}
.btn{font-size:13px;font-weight:800;text-decoration:none;border-radius:8px;padding:7px 12px;white-space:nowrap}
.btn.v{border:1px solid var(--rule);color:var(--sub)}
.btn.dl{background:var(--org);color:#fff}
.foot{margin-top:30px;font-size:12px;color:var(--muted);display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
@media (max-width:560px){.d{min-width:96px}.back{margin-left:0}
li{gap:8px 12px}
.n{order:9;flex-basis:100%;white-space:normal;font-size:13px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}}
</style>"""


def build():
    it = items()
    now = datetime.now(KST)
    o = ['<!doctype html><html lang="ko"><head><meta charset="utf-8">'
         '<meta name="viewport" content="width=device-width,initial-scale=1">'
         '<title>일일 이슈 브리핑 모음 | 의료관광 · 웰니스 이슈 레이더</title>' + CSS + '</head><body>']
    o.append('<header class="mast"><div class="in"><img class="logo" src="../assets/kto_signature.png" alt="한국관광공사">'
             '<span class="vr"></span><div><span class="t1">발주 한국관광공사 · 수행 (주)서던포스트</span>'
             '<span class="t2">일일 이슈 브리핑 모음</span></div>'
             '<a class="back" href="../">이슈 레이더로 돌아가기</a></div>'
             '<div class="ribbon"><i></i><i></i><i></i><i></i></div></header><div class="wrap">')
    o.append('<p class="lead">「2026 방한 의료관광 시장조사 및 중장기 사업 전략수립」 과업의 <b>일일 이슈 브리핑(A4 1쪽 PDF)</b>을 날짜별로 모아 둠. '
             '새 브리핑이 만들어지면 이 페이지에 자동으로 추가됨</p>')
    if it:
        o.append('<div class="kpi"><div class="o"><b>{:,}건</b>누적 브리핑</div><div><b>{}</b>최신 브리핑</div><div><b>{}</b>첫 브리핑</div></div>'
                 .format(len(it), it[0][0].strftime('%Y.%m.%d'), it[-1][0].strftime('%Y.%m.%d')))
    hl = headlines(it)
    cur = None
    for k, (d, f, sz) in enumerate(it):
        ym = d.strftime('%Y년 %-m월')
        if ym != cur:
            if cur is not None:
                o.append('</ul>')
            o.append('<h2>%s</h2><ul>' % ym)
            cur = ym
        name = '이슈브리핑_%s.pdf' % d.strftime('%Y%m%d')
        h = (hl.get(f) or '').strip()
        cls, txt = ('n', html.escape(h)) if h else ('n e', 'PDF · %s KB' % '{:,}'.format(round(sz / 1024)))
        o.append('<li><span class="d">%s%s</span><span class="w">(%s)</span>'
                 '<span class="%s" title="%s">%s</span>'
                 '<a class="btn v" href="%s" target="_blank" rel="noopener">보기</a>'
                 '<a class="btn dl" href="%s" download="%s">다운로드</a></li>'
                 % (d.strftime('%Y. %m. %d.'), '<span class="new">최신</span>' if k == 0 else '', WD[d.weekday()],
                    cls, html.escape(h), txt, f, f, html.escape(name)))
    if cur is not None:
        o.append('</ul>')
    if not it:
        o.append('<p class="lead">아직 등록된 브리핑이 없음</p>')
    o.append('<div class="foot"><span>자료원 : medtour-radar 자동수집 데이터베이스 · 브리핑은 원문 대조 검증 후 작성</span>'
             '<span>%s 갱신 · <b>(주)서던포스트</b></span></div></div></body></html>' % now.strftime('%Y.%m.%d %H:%M'))
    os.makedirs(DIR, exist_ok=True)
    open(os.path.join(DIR, 'index.html'), 'w', encoding='utf-8').write(''.join(o))
    print('브리핑 모음 생성 : %d건' % len(it))


if __name__ == '__main__':
    build()
