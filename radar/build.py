# -*- coding: utf-8 -*-
"""
data/news.db → docs/index.html (GitHub Pages 공개 페이지)

디자인 : 서던포스트 시그니처(S안) 레이아웃 × 한국관광공사 CI 색
  - 에디토리얼형 헤드라인 · 대형 KPI, 데이터저널형 차트(값 축 없이 막대 끝 수치)
  - 한국관광공사 시그니처 로고, CI 4색 리본(레드 · 오렌지 · 옐로 · 핑크)
  - 의료관광 트랙 = KTO 레드, 웰니스 트랙 = KTO 오렌지
  - Pretendard 서브셋(KS X 1001 한글 2,350자)을 docs/assets/fonts에 자체 호스팅

기능
  - 의료관광 / 웰니스 트랙 토글, 범주별 10건 + 더보기 : 자바스크립트 없이 동작
  - 목록 머리글(일자 · 매체 · 제목) 정렬 : 자바스크립트가 켜진 환경에서만
  - 제목과 요약이 같은 기사(전재)는 한 건만 표시

사용법
  python radar/build.py
  python radar/build.py --days 14
"""
import argparse, html, io, os, re, sqlite3, sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules import TRACKS, KST, MED, WEL, score_item
from media import media_name
import topic

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, 'data', 'news.db')
OUT = os.path.join(ROOT, 'docs', 'index.html')
SHOW = 10                     # 범주별로 처음 보여줄 건수
TEAM = '의료웰니스팀'

CSS = """<style>
@font-face{font-family:'PretendardSub';font-weight:400;font-display:swap;src:url(assets/fonts/pretendard-sub-Regular.woff2) format('woff2')}
@font-face{font-family:'PretendardSub';font-weight:600;font-display:swap;src:url(assets/fonts/pretendard-sub-SemiBold.woff2) format('woff2')}
@font-face{font-family:'PretendardSub';font-weight:800;font-display:swap;src:url(assets/fonts/pretendard-sub-ExtraBold.woff2) format('woff2')}
:root{
  --red:#D80024;--red-d:#A8001C;--org:#E49000;--org-d:#B87400;--yel:#F2DF4E;--pink:#E478A8;
  --ink:#1C1B1B;--sub:#4E4B4C;--muted:#8C8A8B;--kgray:#777576;
  --rule:#E7E4E2;--rule2:#F1EEEC;--bg:#FAF8F6;--card:#FFFFFF;--bar:#D3CFCD;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:'PretendardSub','Pretendard','Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',sans-serif;
  font-size:14px;line-height:1.55;letter-spacing:-.1px}
a{color:inherit;text-decoration:none}
.num{font-variant-numeric:tabular-nums}

/* ── 머리 : 흰 바탕 + KTO 로고 + CI 4색 리본 ── */
.mast{background:#fff;border-bottom:1px solid var(--rule)}
.mast .in{max-width:1240px;margin:0 auto;padding:14px 16px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.logo{height:36px;width:auto;display:block}
.vr{width:1px;height:30px;background:var(--rule)}
.team{display:flex;flex-direction:column;line-height:1.25}
.team .t1{font-size:12px;font-weight:600;color:var(--kgray)}
.team .t2{font-size:17px;font-weight:800;letter-spacing:-.4px}
.mast .upd{margin-left:auto;text-align:right;font-size:12px;color:var(--muted);line-height:1.4}
.mast .upd b{display:block;color:var(--ink);font-weight:600;font-size:13px}
.ribbon{display:flex;height:4px}
.ribbon i{flex:1}
.ribbon i:nth-child(1){background:var(--red)}.ribbon i:nth-child(2){background:var(--org)}
.ribbon i:nth-child(3){background:var(--yel)}.ribbon i:nth-child(4){background:var(--pink)}

.wrap{max-width:1240px;margin:0 auto;padding:0 16px}

/* ── 에디토리얼 헤드라인 ── */
.hero{padding:4px 0 22px 18px;border-left:5px solid var(--ac);margin:0 0 20px}
.eyebrow{font-size:11.5px;font-weight:800;letter-spacing:1.2px;color:var(--ac-d)}
.hero h1{font-size:32px;line-height:1.28;font-weight:800;letter-spacing:-1px;margin:6px 0 10px;word-break:keep-all;color:var(--ink)}
.dek{font-size:14px;color:var(--sub);margin:0;word-break:keep-all}
.dek a{color:var(--ink);font-weight:600;text-decoration:none;border-bottom:1px solid var(--rule)}
.dek a:hover{color:var(--ac-d);border-color:var(--ac)}

/* ── 트랙 토글 (라디오 · JS 없음) ── */
.trk{position:absolute;opacity:0;pointer-events:none}
.tabs{display:inline-flex;background:#fff;border:1px solid var(--rule);border-radius:999px;padding:4px;margin:24px 0 22px;gap:2px;flex-wrap:wrap}
.tabs label{cursor:pointer;border-radius:999px;padding:9px 20px;font-weight:800;font-size:14px;color:var(--sub);display:flex;align-items:baseline;gap:8px}
.tabs label small{font-weight:600;font-size:12px;color:var(--muted)}
#trk-med:checked~.wrap .tabs label[for=trk-med]{background:var(--red);color:#fff}
#trk-wel:checked~.wrap .tabs label[for=trk-wel]{background:var(--org);color:#fff}
#trk-med:checked~.wrap .tabs label[for=trk-med] small,#trk-wel:checked~.wrap .tabs label[for=trk-wel] small{color:rgba(255,255,255,.85)}
.pane{display:none}
#trk-med:checked~.wrap .pane-med{display:block}
#trk-wel:checked~.wrap .pane-wel{display:block}
.pane-med{--ac:var(--red);--ac-d:var(--red-d);--tint:#FCEEF0}
.pane-wel{--ac:var(--org);--ac-d:var(--org-d);--tint:#FDF4E3}

/* ── KPI 띠 ── */
.kpis{display:grid;grid-template-columns:repeat(5,1fr);background:#fff;border:1px solid var(--rule);border-top:3px solid var(--ac);margin-bottom:22px}
.kpi{padding:16px 18px;border-left:1px solid var(--rule2)}
.kpi:first-child{border-left:0}
.kv{font-size:32px;font-weight:800;letter-spacing:-1px;line-height:1.1;font-variant-numeric:tabular-nums}
.kpi:first-child .kv{color:var(--ac)}
.kl{font-size:12.5px;font-weight:600;margin-top:6px}
.ks{font-size:11.5px;color:var(--muted)}

/* ── 본문 격자 ── */
.grid{display:grid;grid-template-columns:1.35fr 1fr;gap:18px;align-items:start}
.card{background:#fff;border:1px solid var(--rule);padding:20px 22px 22px}
.span{grid-column:1/-1}
.sec{font-size:11.5px;font-weight:800;letter-spacing:1px;color:var(--ac-d)}
.h2{font-size:19px;font-weight:800;letter-spacing:-.5px;margin:4px 0 2px;word-break:keep-all}
.h2 .n{color:var(--muted);font-weight:600;font-size:15px;margin-left:4px}
.cap{font-size:12px;color:var(--muted);margin-bottom:12px}
.note{font-size:12px;color:var(--sub);border-left:3px solid var(--tint);padding-left:10px;margin:14px 0 0;word-break:keep-all}

/* 리드 기사 */
.lead{border-bottom:1px solid var(--rule);padding:6px 0 18px}
.chip{display:inline-block;font-size:11px;font-weight:700;border-radius:3px;padding:2px 7px;background:var(--tint);color:var(--ac-d)}
.chip.hot{background:var(--ac);color:#fff}
.lead .tt{font-size:21px;font-weight:800;line-height:1.38;letter-spacing:-.6px;margin:8px 0 8px;word-break:keep-all}
.lead .tt a:hover,.rest .tt a:hover,.ttab a:hover{color:var(--ac);text-decoration:underline}
.lead .ts{color:var(--sub);font-size:13.5px;word-break:keep-all}
.meta{font-size:12px;color:var(--muted);margin-top:8px}
.meta b{color:var(--sub);font-weight:600}
.rest{list-style:none;margin:0;padding:0}
.rest li{display:flex;gap:12px;padding:12px 0;border-bottom:1px solid var(--rule2)}
.rest li:last-child{border-bottom:0}
.rest .rk{font-size:20px;font-weight:800;color:var(--ac);min-width:22px;line-height:1.2;font-variant-numeric:tabular-nums}
.rest .tt{font-size:14.5px;font-weight:700;line-height:1.45;word-break:keep-all}

/* 가로 막대 (값 축 없이 막대 끝 수치) */
.hb{margin:4px 0 0}
.hb .r{display:grid;grid-template-columns:96px 1fr;align-items:center;gap:10px;margin:7px 0}
.hb .nm{font-size:12.5px;color:var(--sub);text-align:right;white-space:nowrap}
.hb .tr{display:flex;align-items:center;gap:8px}
.hb .b{height:16px;background:var(--bar);border-radius:2px}
.hb .r.top .b{background:var(--ac)}
.hb .v{font-size:13px;font-weight:800;font-variant-numeric:tabular-nums}
svg .xl{font-size:11px;fill:#8C8A8B;text-anchor:middle;font-family:'PretendardSub','Pretendard',sans-serif}
svg .vt{font-size:11px;fill:#1C1B1B;font-weight:800;text-anchor:middle;font-family:'PretendardSub','Pretendard',sans-serif}

/* 괘선 표 */
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch}
table.ttab{width:100%;border-collapse:collapse;table-layout:fixed;font-size:13px;min-width:680px}
.ttab th{text-align:left;font-weight:800;font-size:12px;color:var(--ink);padding:9px 8px;border-bottom:2px solid var(--ink);white-space:nowrap}
.ttab td{padding:10px 8px;border-bottom:1px solid var(--rule2);vertical-align:top;word-break:keep-all;line-height:1.5}
.ttab td.d,.ttab td.md{color:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}
.ttab td.ti{font-weight:700}
.ttab td.sm{color:var(--sub);font-size:12.5px}
.ttab tbody tr:last-child td{border-bottom:1px solid var(--rule)}
.ttab th.sort{cursor:pointer;user-select:none}
.ttab th.sort:after{content:' ↕';font-weight:400;color:var(--muted)}
.ttab th.sort.asc:after{content:' ↑';color:var(--ac)}
.ttab th.sort.desc:after{content:' ↓';color:var(--ac)}
.more{position:absolute;opacity:0;pointer-events:none}
.ttab tr.ex{display:none}
.more:checked~.tw .ttab tr.ex{display:table-row}
.mbtn{display:block;margin-top:14px;text-align:center;font-size:13px;font-weight:700;color:var(--ac-d);
  border:1px solid var(--ac);border-radius:999px;padding:9px;cursor:pointer;background:#fff}
.mbtn:hover{background:var(--tint)}
.mbtn .c{display:none}
.more:checked~.mbtn .o{display:none}
.more:checked~.mbtn .c{display:inline}

.cats{display:grid;gap:18px;margin-top:18px}
.foot{margin:34px 0 0;padding:18px 0 40px;border-top:1px solid var(--rule);font-size:12px;color:var(--muted);display:flex;gap:18px;flex-wrap:wrap;justify-content:space-between}
.foot b{color:var(--sub)}

@media(max-width:980px){.grid{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(3,1fr)}
  .kpi:nth-child(4){border-left:0}.kpi:nth-child(n+4){border-top:1px solid var(--rule2)}}
@media(max-width:640px){
  .hero h1{font-size:23px}.kv{font-size:26px}
  .kpis{grid-template-columns:repeat(2,1fr)}
  .kpi{border-left:0!important;border-top:1px solid var(--rule2)}.kpi:nth-child(-n+2){border-top:0}
  .kpi:nth-child(even){border-left:1px solid var(--rule2)!important}
  .kpi:last-child{grid-column:1/-1}
  .mast .upd{margin-left:0;text-align:left;width:100%}
  .vr{display:none}.logo{height:28px}
  .card{padding:16px}.lead .tt{font-size:18px}
  .tabs{display:flex}.tabs label{flex:1;justify-content:center;padding:9px 10px}
}
@media print{.pane{display:block!important}.tabs,.mbtn{display:none}.ttab tr.ex{display:table-row}}
</style>"""

# 머리글 정렬 - 정렬 후에도 앞의 10건만 보이게 다시 표시 (자바스크립트가 꺼진 환경에서는 동작하지 않음)
SORT_JS = """<script>
document.querySelectorAll('table.sortable').forEach(function(t){
  t.querySelectorAll('th.sort').forEach(function(th){
    th.addEventListener('click',function(){
      var col=+th.dataset.col, asc=!th.classList.contains('asc');
      t.querySelectorAll('th.sort').forEach(function(h){h.classList.remove('asc','desc')});
      th.classList.add(asc?'asc':'desc');
      var tb=t.tBodies[0], rows=[].slice.call(tb.rows);
      rows.sort(function(a,b){
        var x=a.cells[col].dataset.k||a.cells[col].textContent, y=b.cells[col].dataset.k||b.cells[col].textContent;
        return (asc?1:-1)*x.localeCompare(y,'ko');
      });
      rows.forEach(function(r,i){r.classList.toggle('ex',i>=%d);tb.appendChild(r)});
    });
  });
});
</script>""" % SHOW


def esc(s):
    return html.escape(s or '')


def fmt(n):
    return '{:,}'.format(n)


def norm(s):
    return re.sub(r'[\W_]+', '', (s or '').lower())


def dedupe(items):
    """제목과 요약이 모두 같은 기사는 한 건만 남김 (점수 높은 것 · 매체명 있는 것 우선)"""
    items = sorted(items, key=lambda x: (-x['score'], x['media'] == '', x['date']))
    seen, out = set(), []
    for it in items:
        key = norm(it['title']) + '|' + norm(it.get('summary'))[:120]
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def load(con, track):
    rows = con.execute('SELECT url,track,title,media,date,summary,note,category,collected_at FROM news '
                       'WHERE track=?', (track,)).fetchall()
    keys = ['url', 'track', 'title', 'media', 'date', 'summary', 'note', 'category', 'collected_at']
    items = [dict(zip(keys, r)) for r in rows]
    for it in items:
        it['score'] = score_item(it)
        it['media'] = media_name(it.get('media'), it.get('url'))
    return dedupe(items)


def daily_chart(items, today, ac, n=30, w=470, h=175):
    days = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(n - 1, -1, -1)]
    cnt = {d: 0 for d in days}
    for it in items:
        if it['date'] in cnt:
            cnt[it['date']] += 1
    vmax = max(max(cnt.values()), 1) * 1.22
    step = (w - 12) / n
    bw = step * 0.64
    base = h - 22
    o = io.StringIO()
    o.write('<svg viewBox="0 0 %d %d" width="100%%" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="최근 30일 일별 기사 수">' % (w, h))
    o.write('<line x1="6" y1="%d" x2="%d" y2="%d" stroke="#E7E4E2"/>' % (base, w - 6, base))
    for i, d in enumerate(days):
        cx = 6 + step * i + step / 2
        v = cnt[d]
        bh = v / vmax * (base - 18)
        col = ac if i == n - 1 else '#D3CFCD'
        if v:
            o.write('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1.5" fill="%s"/>' % (cx - bw / 2, base - bh, bw, bh, col))
            o.write('<text x="%.1f" y="%.1f" class="vt">%s</text>' % (cx, base - bh - 4, fmt(v)))
        if i % 7 == 2 or i == n - 1:
            o.write('<text x="%.1f" y="%d" class="xl">%s</text>' % (cx, h - 5, d[5:].replace('-', '.')))
    o.write('</svg>')
    return o.getvalue()


def cat_table(key, rows):
    body = ''
    for i, r in enumerate(rows):
        body += ('<tr%s><td class="d" data-k="%s">%s</td><td class="md">%s</td>'
                 '<td class="ti" data-k="%s"><a href="%s" target="_blank" rel="noopener">%s</a></td>'
                 '<td class="sm">%s</td></tr>'
                 % (' class="ex"' if i >= SHOW else '', r['date'], r['date'][5:].replace('-', '.'),
                    esc(r['media']) or '-', esc(r['title']), esc(r['url']), esc(r['title']),
                    esc(r.get('note') or r.get('summary'))))
    rest = len(rows) - SHOW
    o = '<input class="more" type="checkbox" id="more-%s">' % key if rest > 0 else ''
    o += ('<div class="tw"><table class="ttab sortable"><colgroup><col style="width:9%"><col style="width:13%">'
          '<col style="width:36%"><col style="width:42%"></colgroup><thead><tr>'
          '<th class="sort" data-col="0">일자</th><th class="sort" data-col="1">매체</th>'
          '<th class="sort" data-col="2">제목</th><th>요약 · 과업 관련성</th></tr></thead>'
          '<tbody>' + body + '</tbody></table></div>')
    if rest > 0:
        o += ('<label class="mbtn" for="more-%s"><span class="o">더보기 %s건</span><span class="c">접기</span></label>'
              % (key, fmt(rest)))
    return o


def summarize(all_items, track, days, today):
    since = (today - timedelta(days=days - 1)).strftime('%Y-%m-%d')
    items = [r for r in all_items if r['date'] >= since]
    cats = [c for c, _ in TRACKS[track]['cats']] + ['기타']
    by_cat = {c: [r for r in items if r['category'] == c] for c in cats}
    by_cat = {c: v for c, v in by_cat.items() if v}
    top_cat = max(by_cat, key=lambda c: len(by_cat[c])) if by_cat else None
    return items, by_cat, top_cat


def _short(title, lim=34):
    """대표 기사 제목을 헤드라인 길이로 줄임 : 말줄임 · 쉼표 앞 첫 마디, 머리 날짜 제거"""
    s = re.split(r'…|\.\.\.| - |\|', re.sub(r'\[[^\]]*\]|\([^)]*\)', ' ', title))[0].replace(',', ' ')
    s = re.sub(r'[\"“”‘’\'「」]', '', s)
    s = re.sub(r'^\s*\d+일\s*', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    if len(s) > lim:
        s = s[:lim].rsplit(' ', 1)[0]
    return s


def headline(all_items, items, track, days, today):
    """핵심 이슈 주제 한 줄 : 수동 지정 → 자동 추출(최근 기간 → 30일) → 점수 1위 기사 제목 순으로 결정"""
    today_s = today.strftime('%Y-%m-%d')
    ov = topic.load_override(ROOT, track, today_s)
    if ov:
        return ov, [], '담당자 지정'
    pools = [items]
    if not items:                                   # 이번 기간 기사가 없을 때만 30일로 넓힘
        pools.append(summarize(all_items, track, 30, today)[0])
    for pool in pools:
        h, cl = topic.extract(pool)
        strong = h and len(cl) >= 2 and (len(topic.tokens(h)) >= 2 or any(topic.UNIT.match(w) for w in h.split()))
        if strong:
            return h, cl, '관련 기사 %s건' % fmt(len(cl))
    tops = sorted(items or pools[-1], key=lambda x: (-x['score'], x['date']))
    if tops:
        return _short(tops[0]['title']), tops[:1], '점수 1위 기사 기준'
    return TRACKS[track]['label'] + ' 이슈 없음', [], ''


def pane(all_items, track, days, today):
    items, by_cat, top_cat = summarize(all_items, track, days, today)
    tops = sorted(items, key=lambda x: (-x['score'], x['date']))[:5]
    today_s = today.strftime('%Y-%m-%d')
    n_today = sum(1 for r in all_items if (r.get('collected_at') or '')[:10] == today_s)
    tkey = 'med' if track == MED else 'wel'
    ac = '#D80024' if track == MED else '#E49000'

    o = io.StringIO()
    head, cl, basis = headline(all_items, items, track, days, today)
    rep = ''
    if cl:
        r = cl[0]
        rep = (' · 대표 기사 <a href="%s" target="_blank" rel="noopener">%s</a> %s · %s'
               % (esc(r['url']), esc(r['title']), esc(r['media']) or '-', r['date'].replace('-', '.')))
    o.write('<section class="hero"><div class="eyebrow">%s 핵심 이슈 · %s</div><h1>%s</h1>'
            '<p class="dek">%s%s</p></section>'
            % (esc(TRACKS[track]['label']), today.strftime('%Y.%m.%d'), esc(head), basis, rep))
    kp = [(fmt(len(items)), '최근 %d일 기사' % days, '중복 기사 제외'),
          (fmt(n_today), '오늘 수집', '이번 수집 회차'),
          (fmt(len(all_items)), '누적 기사', '수집 시작 이후'),
          (fmt(len(by_cat)), '범주 수', '최다 : ' + (top_cat or '-')),
          (fmt(tops[0]['score']) if tops else '0', '최고 점수', '먼저 볼 기사 기준')]
    o.write('<div class="kpis">' + ''.join(
        '<div class="kpi"><div class="kv">%s</div><div class="kl">%s</div><div class="ks">%s</div></div>' % k
        for k in kp) + '</div>')

    o.write('<div class="grid">')
    # 왼쪽 : 먼저 볼 기사
    o.write('<section class="card"><div class="sec">LEAD</div><div class="h2">먼저 볼 기사</div>'
            '<div class="cap">제도 · 리스크 · 발주처 관련성과 최신성으로 매긴 점수순</div>')
    if tops:
        r = tops[0]
        chips = '<span class="chip">%s</span>' % esc(r['category'])
        if r['score'] >= 8:
            chips += ' <span class="chip hot">주목</span>'
        o.write('<div class="lead">%s<div class="tt"><a href="%s" target="_blank" rel="noopener">%s</a></div>'
                '<div class="ts">%s</div><div class="meta">%s · <b>%s</b> · 점수 %s</div></div>'
                % (chips, esc(r['url']), esc(r['title']), esc(r.get('note') or r.get('summary')),
                   r['date'].replace('-', '.'), esc(r['media']) or '-', fmt(r['score'])))
        o.write('<ol class="rest">')
        for i, r in enumerate(tops[1:], 2):
            o.write('<li><span class="rk">%d</span><div><div class="tt"><a href="%s" target="_blank" rel="noopener">%s</a></div>'
                    '<div class="meta">%s · <b>%s</b> · %s · 점수 %s</div></div></li>'
                    % (i, esc(r['url']), esc(r['title']), r['date'].replace('-', '.'), esc(r['media']) or '-',
                       esc(r['category']), fmt(r['score'])))
        o.write('</ol>')
    else:
        o.write('<p class="note">해당 기간 기사 없음</p>')
    o.write('</section>')

    # 오른쪽 : 범주 분포 + 일별 추이
    o.write('<div style="display:grid;gap:18px">')
    mx = max((len(v) for v in by_cat.values()), default=1)
    bars = ''.join('<div class="r%s"><span class="nm">%s</span><span class="tr"><span class="b" style="width:%.1f%%"></span>'
                   '<span class="v">%s</span></span></div>'
                   % (' top' if c == top_cat else '', esc(c), max(len(v) / mx * 82, 2), fmt(len(v)))
                   for c, v in sorted(by_cat.items(), key=lambda kv: -len(kv[1])))
    o.write('<section class="card"><div class="sec">MIX</div><div class="h2">이슈가 몰린 범주</div>'
            '<div class="cap">최근 %d일 · 단위 : 건</div><div class="hb">%s</div>'
            '<p class="note">정책 · 제도가 몰리면 제도 변화 국면, 리스크가 몰리면 국정감사 · 사고 국면으로 읽음</p></section>'
            % (days, bars or '<p class="note">해당 기간 기사 없음</p>'))
    o.write('<section class="card"><div class="sec">DAILY</div><div class="h2">최근 30일 수집 추이</div>'
            '<div class="cap">보도일 기준 · 단위 : 건 · 마지막 막대가 오늘</div>%s</section>'
            % daily_chart(all_items, today, ac))
    o.write('</div></div>')

    # 범주별 목록
    o.write('<div class="cats">')
    for ci, (c, v) in enumerate(sorted(by_cat.items(), key=lambda kv: -len(kv[1]))):
        v = sorted(v, key=lambda x: (-x['score'], x['date']))
        o.write('<section class="card"><div class="sec">%s</div><div class="h2">%s<span class="n">%s건</span></div>'
                '<div class="cap">관련도순 · 머리글을 누르면 일자 · 매체 · 제목순 정렬</div>%s</section>'
                % (esc(TRACKS[track]['label']), esc(c), fmt(len(v)), cat_table('%s-%d' % (tkey, ci), v)))
    o.write('</div>')
    return o.getvalue(), len(items), head


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=7)
    a = ap.parse_args()

    con = sqlite3.connect(DB)
    today = datetime.now(KST)
    med_html, n_med, med_head = pane(load(con, MED), MED, a.days, today)
    wel_html, n_wel, wel_head = pane(load(con, WEL), WEL, a.days, today)

    o = io.StringIO()
    o.write('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>의료관광 · 웰니스 이슈 레이더 | 한국관광공사 %s</title>'
            '<link rel="preload" href="assets/fonts/pretendard-sub-ExtraBold.woff2" as="font" type="font/woff2" crossorigin>'
            % TEAM)
    o.write(CSS + '</head><body>')
    o.write('<input class="trk" type="radio" name="trk" id="trk-med" checked>'
            '<input class="trk" type="radio" name="trk" id="trk-wel">')
    o.write('<header class="mast"><div class="in">'
            '<img class="logo" src="assets/kto_signature.png" alt="한국관광공사">'
            '<span class="vr"></span>'
            '<div class="team"><span class="t1">%s</span><span class="t2">의료관광 · 웰니스 이슈 레이더</span></div>'
            '<div class="upd"><b>%s 업데이트</b>매일 07:00 자동 갱신</div>'
            '</div><div class="ribbon"><i></i><i></i><i></i><i></i></div></header>'
            % (TEAM, today.strftime('%Y.%m.%d %H:%M')))
    o.write('<div class="wrap">')
    o.write('<div class="tabs"><label for="trk-med">의료관광 <small>%s건</small></label>'
            '<label for="trk-wel">웰니스 <small>%s건</small></label></div>' % (fmt(n_med), fmt(n_wel)))
    o.write('<div class="pane pane-med">%s</div><div class="pane pane-wel">%s</div>' % (med_html, wel_html))
    o.write('<footer class="foot"><span><b>한국관광공사 %s</b> · 2026 방한 의료관광 시장조사 및 중장기 사업 전략수립</span>'
            '<span>수집 · 분석 <b>(주)서던포스트</b> · 네이버 뉴스 검색 API · Google 뉴스 RSS · '
            '점수는 편집 판단을 돕는 보조 지표임</span></footer>' % TEAM)
    o.write('</div>' + SORT_JS + '</body></html>')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(o.getvalue().replace('—', '-').replace('–', '-'))
    print('생성 : %s (의료관광 %d건 · 웰니스 %d건)' % (OUT, n_med, n_wel))
    print('  헤드라인 : 의료관광 「%s」 / 웰니스 「%s」' % (med_head, wel_head))


if __name__ == '__main__':
    main()
