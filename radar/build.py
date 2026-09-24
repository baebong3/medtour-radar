# -*- coding: utf-8 -*-
"""
data/news.db → docs/index.html (GitHub Pages 공개 페이지)

  - 의료관광 / 웰니스 트랙을 라디오 토글로 전환 (자바스크립트 없음)
  - 트랙마다 : KPI · 최근 30일 일별 수집 추이 · 주목 이슈 5건 · 범주 분포 · 범주별 목록
  - 제목과 요약이 같은 기사(통신사 전재 등)는 한 건만 표시
  - 범주별 목록은 10건만 보이고 나머지는 「더보기」로 펼침 (자바스크립트 없이 동작)
  - 목록 머리글(일자 · 매체 · 제목)을 누르면 정렬 (자바스크립트가 켜진 환경에서만)

사용법
  python radar/build.py
  python radar/build.py --days 14
"""
import argparse, html, io, os, re, sqlite3, sys
from datetime import datetime, timedelta
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules import TRACKS, KST, MED, WEL, score_item
from media import media_name

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, 'data', 'news.db')
OUT = os.path.join(ROOT, 'docs', 'index.html')
SHOW = 10          # 범주별로 처음 보여줄 건수

EXTRA_CSS = """<style>
.grid .span2{grid-column:1/-1}
a{color:#0B4A87;text-decoration:none}a:hover{text-decoration:underline}
.tag{display:inline-block;font-size:10px;font-weight:700;border-radius:20px;padding:2px 8px;background:#EAF0F7;color:#0B4A87}
.tag.hot{background:#F4E9E9;color:#8A2222}
.top{display:flex;gap:10px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #EDF0F5}
.rank{font-size:17px;font-weight:800;color:#00ACDC;min-width:26px}
.tt{font-size:13px;font-weight:700;line-height:1.45}
.tm{font-size:11px;color:#8A93A0;margin-top:3px}
.ts{font-size:11.5px;color:#3A4757;margin-top:4px;line-height:1.55}
.bars{margin-top:8px}
.bar{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:11.5px}
.bar .nm{width:92px;text-align:right;color:#3A4757}
.bar .bb{height:14px;border-radius:3px;background:#0B4A87}
.bar .vv{font-weight:700;color:#16202C}
svg .xl{font-size:10px;fill:#8A93A0;text-anchor:middle;font-family:'Pretendard','Malgun Gothic',sans-serif}
svg .vt{font-size:10px;fill:#16202C;font-weight:600;text-anchor:middle;font-family:'ChivoNum','Pretendard',sans-serif}
/* 트랙 토글 */
.trk{position:absolute;opacity:0;pointer-events:none}
.tabs{display:flex;gap:8px;margin:2px 0 14px;flex-wrap:wrap}
.tabs label{cursor:pointer;font-size:13px;font-weight:700;padding:9px 18px;border-radius:999px;
background:#fff;border:1px solid #E7EAF0;color:#5A6675}
.tabs label span{display:block;font-size:10.5px;font-weight:600;color:#A6AEBB;margin-top:2px}
#trk-med:checked~.wrap .tabs label[for=trk-med],
#trk-wel:checked~.wrap .tabs label[for=trk-wel]{background:#002B58;border-color:#002B58;color:#fff}
#trk-med:checked~.wrap .tabs label[for=trk-med] span,
#trk-wel:checked~.wrap .tabs label[for=trk-wel] span{color:#AFC3DA}
.pane{display:none}
#trk-med:checked~.wrap .pane-med{display:block}
#trk-wel:checked~.wrap .pane-wel{display:block}
/* 더보기 : 체크박스 + 형제 선택자 */
.more{position:absolute;opacity:0;pointer-events:none}
.ttab tr.ex{display:none}
.more:checked~.tw .ttab tr.ex{display:table-row}
.mbtn{display:block;margin-top:10px;text-align:center;font-size:12px;font-weight:700;color:#0B4A87;
background:#F3F6FA;border:1px solid #E7EAF0;border-radius:8px;padding:8px;cursor:pointer}
.mbtn .c{display:none}
.more:checked~.mbtn .o{display:none}
.more:checked~.mbtn .c{display:inline}
/* 정렬 머리글 */
.ttab th.sort{cursor:pointer;user-select:none;white-space:nowrap}
.ttab th.sort:after{content:' ↕';font-weight:400;opacity:.55}
.ttab th.sort.asc:after{content:' ↑';opacity:1}
.ttab th.sort.desc:after{content:' ↓';opacity:1}
.ttab td.md{color:#5A6675;word-break:keep-all}
@media print{.pane{display:block !important}.tabs,.mbtn{display:none}.ttab tr.ex{display:table-row}}
</style>"""

# 머리글을 누르면 정렬하고, 정렬 후에도 앞의 10건만 보이게 다시 표시 (자바스크립트 꺼진 환경에서는 동작하지 않음)
SORT_JS = """<script>
document.querySelectorAll('table.sortable').forEach(function(t){
  var show=%d;
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
      rows.forEach(function(r,i){r.classList.toggle('ex',i>=show);tb.appendChild(r)});
    });
  });
});
</script>""" % SHOW


def esc(s):
    return html.escape(s or '')


def norm(s):
    """중복 판정용 정규화 : 공백 · 문장부호 · 대소문자 차이를 무시"""
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


def daily_chart(items, today, n=30, w=720, h=170):
    days = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(n - 1, -1, -1)]
    cnt = {d: 0 for d in days}
    for it in items:
        if it['date'] in cnt:
            cnt[it['date']] += 1
    vmax = max(max(cnt.values()), 1) * 1.25
    step = (w - 20) / n
    bw = step * 0.62
    base = h - 22
    o = io.StringIO()
    o.write('<svg viewBox="0 0 %d %d" width="100%%" height="%d" xmlns="http://www.w3.org/2000/svg" role="img">' % (w, h, h))
    o.write('<line x1="10" y1="%d" x2="%d" y2="%d" stroke="#E4E9F0"/>' % (base, w - 10, base))
    for i, d in enumerate(days):
        cx = 10 + step * i + step / 2
        v = cnt[d]
        bh = v / vmax * (base - 16)
        col = '#00ACDC' if i == n - 1 else '#0B4A87'
        if v:
            o.write('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" fill="%s"/>' % (cx - bw / 2, base - bh, bw, bh, col))
            o.write('<text x="%.1f" y="%.1f" class="vt">%s</text>' % (cx, base - bh - 4, '{:,}'.format(v)))
        if i % 5 == 0 or i == n - 1:
            o.write('<text x="%.1f" y="%d" class="xl">%s</text>' % (cx, h - 6, d[5:].replace('-', '.')))
    o.write('</svg>')
    return o.getvalue()


def cat_table(key, rows_items):
    """범주 한 개의 목록 표 - 앞 10건 표시, 나머지는 더보기"""
    body = ''
    for i, r in enumerate(rows_items):
        body += ('<tr%s><td data-k="%s">%s</td><td class="md">%s</td>'
                 '<td data-k="%s"><a href="%s" target="_blank" rel="noopener">%s</a></td><td>%s</td></tr>'
                 % (' class="ex"' if i >= SHOW else '', r['date'], r['date'], esc(r['media']) or '-',
                    esc(r['title']), esc(r['url']), esc(r['title']), esc(r.get('note') or r.get('summary'))))
    rest = len(rows_items) - SHOW
    o = ''
    if rest > 0:
        o += '<input class="more" type="checkbox" id="more-%s">' % key
    o += ('<div class="tw"><table class="ttab sortable"><colgroup><col style="width:10%"><col style="width:13%">'
          '<col style="width:35%"><col style="width:42%"></colgroup><thead><tr>'
          '<th class="sort" data-col="0">일자</th><th class="sort" data-col="1">매체</th>'
          '<th class="sort" data-col="2">제목</th><th>요약 · 과업 관련성</th></tr></thead>'
          '<tbody>' + body + '</tbody></table></div>')
    if rest > 0:
        o += ('<label class="mbtn" for="more-%s"><span class="o">더보기 (%s건 더)</span>'
              '<span class="c">접기</span></label>' % (key, '{:,}'.format(rest)))
    return o


def pane(all_items, track, days, today):
    since = (today - timedelta(days=days - 1)).strftime('%Y-%m-%d')
    items = [r for r in all_items if r['date'] >= since]
    cats = [c for c, _ in TRACKS[track]['cats']] + ['기타']
    by_cat = {c: [r for r in items if r['category'] == c] for c in cats}
    by_cat = {c: v for c, v in by_cat.items() if v}
    tops = sorted(items, key=lambda x: (-x['score'], x['date']))[:5]
    today_s = today.strftime('%Y-%m-%d')
    n_today = sum(1 for r in all_items if (r.get('collected_at') or '')[:10] == today_s)
    tkey = 'med' if track == MED else 'wel'

    o = io.StringIO()
    kp = [('{:,}'.format(len(items)), '최근 %d일 기사' % days, '중복 기사 제외'),
          ('{:,}'.format(n_today), '오늘 수집', '이번 수집 회차'),
          ('{:,}'.format(len(all_items)), '누적 기사', '수집 시작 이후'),
          (str(len(by_cat)), '범주 수', '최다 : ' + (max(by_cat, key=lambda c: len(by_cat[c])) if by_cat else '-')),
          (str(tops[0]['score']) if tops else '0', '최고 점수', '주목 이슈 기준')]
    o.write('<div class="kpis">' + ''.join(
        '<div class="kpi"><div class="kv">%s</div><div class="kl">%s</div><div class="ks">%s</div></div>' % k
        for k in kp) + '</div><div class="grid">')

    o.write('<section class="card span2"><div class="eyebrow">DAILY · 수집 추이</div>'
            '<div class="ctitle">최근 30일 일별 기사 수</div><div class="csub">단위 : 건 · 보도일 기준 · 중복 기사 제외 · 마지막 막대가 오늘</div>%s</section>'
            % daily_chart(all_items, today))

    body = ''
    for i, r in enumerate(tops, 1):
        tags = '<span class="tag">%s</span>' % esc(r['category'])
        if r['score'] >= 8:
            tags += ' <span class="tag hot">주목</span>'
        body += ('<div class="top"><div class="rank">%d</div><div><div class="tt">'
                 '<a href="%s" target="_blank" rel="noopener">%s</a></div>'
                 '<div class="tm">%s · %s · 점수 %d %s</div><div class="ts">%s</div></div></div>'
                 % (i, esc(r['url']), esc(r['title']), r['date'], esc(r['media']) or '-', r['score'], tags,
                    esc(r.get('note') or r.get('summary'))))
    o.write('<section class="card span2"><div class="eyebrow">TOP · 주목 이슈</div>'
            '<div class="ctitle">최근 %d일 먼저 볼 다섯 건</div>'
            '<div class="csub">점수 = 제도 · 리스크 · 발주처 관련 키워드 + 최신성, 과업 핵심어가 없으면 감점</div>%s</section>'
            % (days, body or '<p class="note">해당 기간 기사 없음</p>'))

    mx = max((len(v) for v in by_cat.values()), default=1)
    bars = ''.join('<div class="bar"><span class="nm">%s</span><span class="bb" style="width:%.0fpx"></span>'
                   '<span class="vv">%s</span></div>' % (esc(c), max(len(v) / mx * 250, 6), '{:,}'.format(len(v)))
                   for c, v in sorted(by_cat.items(), key=lambda kv: -len(kv[1])))
    o.write('<section class="card span2"><div class="eyebrow">MIX · 범주 분포</div>'
            '<div class="ctitle">이슈가 어디에 몰렸는가</div><div class="csub">단위 : 건 · 최근 %d일</div>'
            '<div class="bars">%s</div><p class="note">범주 쏠림 자체가 신호임. 정책 · 제도가 몰리면 제도 변화 국면, '
            '리스크가 몰리면 국정감사 · 사고 국면으로 읽음</p></section>' % (days, bars))

    for ci, (c, v) in enumerate(by_cat.items()):
        v = sorted(v, key=lambda x: (-x['score'], x['date']))
        o.write('<section class="card span2"><div class="eyebrow">%s</div><div class="ctitle">%s · %s건</div>'
                '<div class="csub">관련도순 · 머리글을 누르면 일자 · 매체 · 제목순으로 정렬</div>%s</section>'
                % (esc(c), esc(c), '{:,}'.format(len(v)), cat_table('%s-%d' % (tkey, ci), v)))
    o.write('</div>')
    return o.getvalue(), len(items)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=7)
    a = ap.parse_args()

    con = sqlite3.connect(DB)
    today = datetime.now(KST)
    css = open(os.path.join(HERE, 'style.css'), encoding='utf-8').read()
    med_html, n_med = pane(load(con, MED), MED, a.days, today)
    wel_html, n_wel = pane(load(con, WEL), WEL, a.days, today)

    o = io.StringIO()
    o.write('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>의료관광 · 웰니스 이슈 레이더 | 서던포스트</title>')
    o.write(css + EXTRA_CSS + '</head><body>')
    o.write('<input class="trk" type="radio" name="trk" id="trk-med" checked>'
            '<input class="trk" type="radio" name="trk" id="trk-wel">')
    o.write('<header class="hdr"><div class="wrap"><span class="brand">의료관광 · 웰니스 이슈 레이더</span>'
            '<span class="scope">2026 방한 의료관광 시장조사 및 중장기 사업 전략수립 | (주)서던포스트</span></div></header>')
    o.write('<div class="wrap"><h1>%s 업데이트</h1>' % today.strftime('%Y년 %m월 %d일 %H:%M'))
    o.write('<p class="lead">매일 아침 자동 수집 · 갱신됨. 두 트랙을 따로 모아 범주로 나누고 과업 관련성에 따라 점수를 매김. '
            '제목과 요약이 같은 전재 기사는 한 건만 남김. 범주별 목록은 10건씩 보이고 나머지는 더보기로 펼침</p>')
    o.write('<div class="tabs"><label for="trk-med">의료관광 <span>최근 %d일 %s건 · %s</span></label>'
            '<label for="trk-wel">웰니스 <span>최근 %d일 %s건 · %s</span></label></div>'
            % (a.days, '{:,}'.format(n_med), TRACKS[MED]['desc'], a.days, '{:,}'.format(n_wel), TRACKS[WEL]['desc']))
    o.write('<div class="pane pane-med">%s</div><div class="pane pane-wel">%s</div>' % (med_html, wel_html))
    o.write('<div class="foot">수집 : 네이버 뉴스 검색 API · Google 뉴스 RSS(의료관광 %d개 · 웰니스 %d개 질의). '
            '전체 이력은 data/news.db에 누적되며, 제목과 요약이 같은 기사는 화면에서 한 건으로 합침. '
            '점수는 편집 판단을 돕는 보조 지표일 뿐 기사 중요도의 절대 기준이 아님.</div></div>'
            % (len(TRACKS[MED]['ko']) + len(TRACKS[MED]['en']), len(TRACKS[WEL]['ko']) + len(TRACKS[WEL]['en'])))
    o.write(SORT_JS + '</body></html>')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(o.getvalue())
    print('생성 : %s (의료관광 %d건 · 웰니스 %d건)' % (OUT, n_med, n_wel))


if __name__ == '__main__':
    main()
