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
있다 없다 등 및 또 더 수 것 중 명 곳 건 년 월 일 억 조 만 원 위 차 개 약 첫 새 전 후 내 외
the of and in to for a on with by at from is as
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
    t = re.sub(r'\[[^\]]*\]|\([^)]*\)|【[^】]*】', ' ', t or '')       # [단독] (종합) 등
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
        a, b = max(i - 1, 0), min(i + 1, len(ws) - 1)
    else:
        a, b = min(pos), max(pos)
    while a > 0 and b - a < 5 and len(' '.join(ws[a - 1:b + 1])) <= 30:   # 너무 짧으면 앞 낱말로 맥락 보강
        a -= 1
    words = [JOSA.sub('', w) if len(w) > 2 else w for w in ws[a:b + 1]]
    if b + 1 < len(ws) and _norm_word(ws[b + 1]) in ACTION:
        words.append(_norm_word(ws[b + 1]))
    s = ' '.join(w for w in words if w)
    return s if 4 <= len(s) <= 34 else None


def extract(items):
    """items : 최근 기간 기사(score 포함) → (헤드라인, 묶음 기사 목록) / 없으면 (None, [])"""
    if not items:
        return None, []
    docs = []
    for it in items:
        tt = tokens(it['title'])
        docs.append((it, tt, tokens(it.get('summary')) - tt))
    weight, df = defaultdict(float), Counter()
    for it, tt, st in docs:
        w = 1.0 + max(it['score'], 0) / 10.0
        for t in tt:
            weight[t] += w
            df[t] += 1
        for t in st:
            weight[t] += 0.3 * w
    cands = [t for t in weight if df[t] >= 2]
    if not cands:
        return None, []
    k1 = max(cands, key=lambda t: (weight[t], df[t], len(t)))
    cluster = [(it, tt) for it, tt, _ in docs if k1 in tt]
    co = Counter()
    for it, tt in cluster:
        for t in tt:
            if t != k1 and t not in k1 and k1 not in t:
                co[t] += 1
    others = [t for t, n in co.most_common(4) if n >= max(2, len(cluster) // 3)][:2]
    keys = set([k1] + others)

    arts = sorted((it for it, _ in cluster), key=lambda x: (-x['score'], x['date']))
    # 대표 제목 : 주제어를 가장 많이 담은 제목 중 점수가 높은 것
    best = max(arts, key=lambda it: (len(keys & tokens(it['title'])), it['score']))
    head = _span(best['title'], keys, k1)
    if not head:
        head = ' · '.join([k1] + others[:1])
    return head, arts
