# -*- coding: utf-8 -*-
"""
핵심 이슈 주제 추출 - 여러 기사 제목에 겹쳐 나오는 주제어로 그날의 헤드라인을 만듦

  1) 제목을 낱말로 나누고 조사를 떼어 냄(요약은 보조로 약하게 반영)
  2) 일반어(의료관광 · 환자 · 확대 · 개최 등)는 제외, 숫자는 단위가 붙은 경우만 허용(112곳 · 40% 등)
  3) 주제어 1 = 여러 기사 제목에 걸쳐 나온 말 중 (기사 점수 가중) 합이 가장 큰 말
     주제어 2 · 3 = 주제어 1이 나온 기사 제목들에서 함께 자주 나온 말
  4) 대표 기사 제목에서 주제어들이 걸친 구간을 잘라 헤드라인으로 씀
     예) 「법무부, 의료관광 우수 유치기관 112곳으로 확대」 → 「법무부 의료관광 우수 유치기관 112곳」
     구간이 너무 길거나 어색하면 「주제어 1 · 주제어 2」로 대체

사람이 정한 헤드라인이 있으면 그것을 우선함 : data/headline.json
  {"date": "2026-09-24", "의료관광": "비자 인증기관 112곳 확대", "웰니스": "치유관광산업지구 지정 논의"}
  (date가 오늘과 같을 때만 적용)
"""
import json, os, re
from collections import Counter, defaultdict

JOSA = re.compile(r'(에서는|으로는|에서|으로|까지|부터|에게|이나|이다|하는|하고|했다|한다|된다|하며|했음|됐음|함|됨|음|임|된|은|는|이|가|을|를|의|에|로|과|와|도|만)$')
UNIT = re.compile(r'^\d[\d,.]*(곳|명|건|개|개국|개소|억|조|만명|만|%|배|위)$')

STOP = set('''
의료관광 의료 관광 관광객 외국인 외국인환자 환자 환자들 한국 국내 해외 유치 웰니스 웰니스관광 치유관광 치유
k k의료 k웰니스 k-의료관광 단독 종합 속보 포토 영상 칼럼 사설 인터뷰 기고
기사 관련 대한 위해 통해 대해 이번 올해 지난해 지난 오늘 내년 최근 가장 모든 이상 이하 가운데 최대 최초 최고
확대 개최 추진 강화 지원 발표 증가 감소 선정 협력 시대 넘어 최다 성료 개막 체결 참가 운영 진행 마련 도입 시행
나선다 나서 넓힌다 넓혀 잡아라 쓴다 썼다 쏠린 몰린 뜬다 뜨는 키워야 키운다 달성 돌파 기록 전망 예정 계획 효과
본격 시동 탄력 청신호 눈길 기대 주목 모색 해법 변화 활성화 가능 필요 문제 방안 길 열어야
센터 사업 행사 프로그램 서비스 산업 시장 정책 기관 기업 병원 협약 mou 업무협약 뉴스 신문 일보
취임 발의 선임 임명 육성 부의장 의장 의원 대표 회장 원장 장관 교수 시장 군수 구청장 이사장 위원장 사장 지정 확장 개발 우수 신규 성공 조성 완료 공개 출시 오픈 선보여 선보인 제공 활용 연계 소개 공략 겨냥 잇는 잇따라
있다 없다 등 및 또 더 수 것 중 명 곳 건 년 월 일 억 조 만 원 위 차 개 약 첫 새 전 후 내 외
the of and in to for a on with by at from is as
추석 설 설날 명절 연휴 황금연휴 여름 가을 겨울 봄 휴가 휴가철 주말 이벤트 할인 특가 특별 진행 방문객 여행 여행지 힐링 코스 추천 즐기는 즐기기 떠나는 어디로 체험 축제 페스티벌
'''.split())


def _words(text):
    for m in re.finditer(r'[가-힣A-Za-z0-9][가-힣A-Za-z0-9%·\-]*', text or ''):
        yield m


def _norm_word(w):
    w = w.strip('·-').lower()
    if len(w) > 2:
        w = JOSA.sub('', w)
    return w


def tokens(text):
    out = set()
    for m in _words(text):
        w = _norm_word(m.group(0))
        if len(w) < 2 or w in STOP:
            continue
        if re.search(r'\d', w) and not UNIT.match(w):
            continue
        out.add(w)
    return out


def load_override(root, track, today_s):
    p = os.path.join(root, 'data', 'headline.json')
    try:
        d = json.load(open(p, encoding='utf-8'))
        if d.get('date') == today_s and d.get(track):
            return d[track]
    except Exception:
        pass
    return None


def _clean_title(t):
    t = re.sub(r'케이\s*\(K\)\s*-?\s*', 'K-', t or '')                       # 케이(K)-의료관광 → K-의료관광
    t = re.sub(r'\[[^\]]*\]|\([^)]*\)|【[^】]*】', ' ', t)       # [단독] (종합) 등
    t = re.sub(r'[\"“”‘’\'「」『』<>…·,:;!?]|\.{2,}', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


ACTION = set('확대 지정 선정 도입 시행 개정 폐지 허용 완화 강화 급증 감소 증가 개최 출범 체결 추진 논의 발표 신설 확정 중단 재개 돌파'.split())


def _span(title, keys, k1):
    """제목에서 주제어들이 걸친 구간(낱말 단위)을 잘라내고, 바로 뒤 서술어(확대 · 지정 등)가 있으면 붙임"""
    t = _clean_title(title)
    ws = t.split(' ')
    hit = lambda w: _norm_word(w) in keys or any(k in w.lower() for k in keys)
    pos = [i for i, w in enumerate(ws) if hit(w)]
    if not pos:
        return None
    if len(pos) == 1:                                   # 주제어가 하나뿐이면 앞뒤 한 낱말씩
        i = pos[0]
        a, b = max(i - 1, 0), i
    else:
        a, b = min(pos), max(pos)
    while a > 0 and b - a < 5 and len(' '.join(ws[a - 1:b + 1])) <= 30:   # 너무 짧으면 앞 낱말로 맥락 보강
        a -= 1
    words = list(ws[a:b + 1])                           # 조사는 끝 낱말에서만 뗌(중간은 자연스러운 문장 유지)
    if len(words[-1]) > 2:
        words[-1] = JOSA.sub('', words[-1])
    if b + 1 < len(ws) and _norm_word(ws[b + 1]) in ACTION:
        words.append(_norm_word(ws[b + 1]))
    s = ' '.join(w for w in words if w)
    return s if 4 <= len(s) <= 34 else None


def _seg_title(title):
    """제목을 말줄임 · 쉼표 · 하이픈 경계로 나눈 마디 목록(따옴표 · 머리말 제거, 가운뎃점은 유지)"""
    s = re.sub(r'케이\s*\(K\)\s*-?\s*', 'K-', title or '')
    if re.search(r'(\.{2,}|…)\s*$', s):                  # 끝이 잘린 제목 : 잘린 낱말은 버림
        s = re.sub(r'\s*\S*(\.{2,}|…)\s*$', '', s)
    s = re.sub(r'\[[^\]]*\]|\([^)]*\)|【[^】]*】', ' ', s)
    s = re.sub(r'[\"“”‘’\'「」『』<>]', '', s)
    segs = [re.sub(r'\s+', ' ', x).strip(' ·') for x in re.split(r'…|\.{2,}|,| - |\||:|;|!|\?', s)]
    return [x for x in segs if x]


def _fit(seg, lim=60):
    ws = seg.split(' ')
    while len(' '.join(ws)) > lim and len(ws) > 2:
        ws = ws[:-1]
    if len(ws[-1]) > 2:
        ws[-1] = JOSA.sub('', ws[-1]) or ws[-1]
    return ' '.join(ws)


def _story_head(best, story_tokens, lim=40):
    """대표 제목 → 헤드라인 : 주제어가 가장 많은 마디에서 시작해 40자 안에서 뒤 마디를 이어 붙임(말줄임 없이 완결된 마디 단위)"""
    segs = _seg_title(best['title'])
    if not segs:
        return None
    who = re.compile(r'(의원|부의장|의장|대표|회장|원장|병원장|장관|차관|교수|시장|군수|구청장|지사|청장|이사장|위원장|사장|총장)$')
    good = [j for j in range(len(segs)) if not who.search(segs[j])] or list(range(len(segs)))   # '○○○ 부의장' 같은 인물 마디는 제외
    i = max(good, key=lambda j: (len(tokens(segs[j]) & story_tokens), -j))
    out = segs[i]
    for sg in segs[i + 1:]:
        if who.search(sg) or len(out) + 2 + len(sg) > lim:
            break
        out += ', ' + sg
    return _fit(out, 60)


def stories(items, k=5):
    """items : 최근 기간 기사(score 포함) → 기사 묶음 k개 [(헤드라인, 기사 목록, 매체 수), ...] (큰 순)

    묶음 : 제목 주제어가 3개 이상(짧은 제목은 2개 이상이면서 절반 이상) 겹치는 기사
    묶음 크기 = 기사 점수 가중 합 × 매체 다양성, 가장 큰 묶음부터 떼어 내며 반복
    """
    docs = [(it, tokens(it['title'])) for it in items if re.search('[가-힣]', it['title'])]   # 헤드라인은 한국어 기사로만
    docs = [(it, tt) for it, tt in docs if len(tt) >= 2]

    def near(a, b):
        c = len(a & b)
        return c >= 3 or (c >= 2 and c / max(min(len(a), len(b)), 1) >= 0.5)

    out = []
    while docs and len(out) < k:
        best_story, best_w = None, 0
        for it, tt in docs:
            story = [(o, ot) for o, ot in docs if o is it or near(tt, ot)]
            media = len(set((o.get('media') or o['url']) for o, _ in story))
            if len(story) < 2 or media < 2:
                continue
            w = sum(1.0 + max(o['score'], 0) / 5.0 for o, _ in story) * (1 + 0.15 * media)
            if w > best_w:
                best_story, best_w = story, w
        if not best_story:
            break
        cnt = Counter(t for _, ot in best_story for t in ot)
        story_tokens = {t for t, n in cnt.items() if n >= max(2, len(best_story) // 3)}
        cut = lambda d: bool(re.search(r'(\.{2,}|…)\s*$', d[0]['title']))           # 잘린 제목은 대표에서 후순위
        rep = max(best_story, key=lambda d: (not cut(d), sum(len(d[1] & o[1]) for o in best_story if o[0] is not d[0]),
                                             d[0]['score']))
        arts = sorted((o for o, _ in best_story), key=lambda x: (-x['score'], x['date']))
        arts.remove(rep[0]); arts.insert(0, rep[0])
        media = len(set((o.get('media') or o['url']) for o in arts))
        out.append((_story_head(rep[0], story_tokens), arts, media))
        ids = {id(o) for o in arts}
        docs = [d for d in docs if id(d[0]) not in ids]
    return out


def extract(items):
    """가장 큰 기사 묶음 하나 → (헤드라인, 기사 목록) / 없으면 (None, [])"""
    st = stories(items, 1) if items else []
    return (st[0][0], st[0][1]) if st else (None, [])


def rising(now_items, prev_items, k=8, min_now=3):
    """이번 기간 대비 직전 기간 제목 주제어 기사 수 변화 → [(낱말, 이번, 직전), ...] 증가 폭 큰 순"""
    def df(items):
        c = Counter()
        for it in items:
            c.update(tokens(it['title']))
        return c
    a, b = df(now_items), df(prev_items)
    try:
        import region
        places = {w for v in region.ALIAS.values() for w in v.split()} | set(region.SIDO)
    except Exception:
        places = set()
    ok = lambda w: (not UNIT.match(w) and re.search('[가-힣]', w)
                    and w not in places and re.sub(r'(시|군|도|구)(의회|청)?$', '', w) not in places)
    # 인명(○○○ 의원 · 부의장 · 대표 등 직함 앞 세 글자)과 서술어(~다)는 주제어에서 뺌
    role = re.compile(r'([가-힣]{3})\s*(?:[가-힣]{0,8}\s*)?(의원|부의장|의장|대표|회장|원장|병원장|장관|차관|교수|시장|군수|구청장|지사|청장|이사장|위원장|사장|총장|국장|과장|센터장|씨)')
    names = set()
    for it in now_items:
        for m in role.finditer(it['title']):
            names.add(m.group(1))
        names.update(re.findall(r'([가-힣]{3})\s*[가-힣]*(?:의회|시장|군수)\s*[가-힣]*(?:의장|부의장|의원)', it['title']))
    ok2 = lambda w: ok(w) and w not in names and not w.endswith('다')
    rows = [(w, n, b.get(w, 0)) for w, n in a.items() if n >= min_now and ok2(w)]
    rows.sort(key=lambda r: (-(r[1] - r[2]), -r[1], r[0]))
    rows = [r for r in rows if r[1] > r[2]]
    # 같은 사건의 낱말이 줄줄이 오르지 않도록, 이미 뽑힌 낱말과 늘 함께 나오는 낱말은 건너뜀
    picked, seen_docs = [], []
    for w, n, p in rows:
        docs = {i for i, it in enumerate(now_items) if w in tokens(it['title'])}
        if any(len(docs & d) / max(len(docs), 1) >= 0.6 for d in seen_docs):
            continue
        picked.append((w, n, p)); seen_docs.append(docs)
        if len(picked) >= k:
            break
    return picked
