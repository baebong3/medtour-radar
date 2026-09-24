# -*- coding: utf-8 -*-
"""트랙 정의 · 범주 분류 · 점수 규칙 (collect.py · build.py 공용)"""
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

MED = '의료관광'
WEL = '웰니스'

TRACKS = {
    MED: {
        'label': '의료관광',
        'desc': '외국인환자 유치 · 제도 · 경쟁국',
        'ko': ['외국인환자 유치', '의료관광', '"메디컬코리아"', '의료관광 비자', '외국인환자 유치기관',
               '한국관광공사 의료관광', '보건산업진흥원 외국인환자', '의료해외진출법',
               '"K-뷰티" 의료관광', '의료관광 브로커', '외국인환자 진료비', '지자체 의료관광'],
        'en': ['"medical tourism" Korea', '"medical tourism" Thailand', '"medical tourism" Turkey',
               '"medical tourism" Malaysia', '"health tourism" USHAS', 'MHTC Malaysia healthcare travel',
               '"medical tourism" Dubai OR "Abu Dhabi"', 'Saudi "treatment abroad" patients'],
        'cats': [
            ('정책·제도', ['비자', '사증', '법률', '개정', '시행령', '고시', '제도', '규제', '지정', '인증',
                         '법무부', '복지부', '정부', '국회', '심의', '허용', '완화', '의료해외진출']),
            ('통계·실적', ['실적', '통계', '집계', '발표', '증가', '감소', '역대', '돌파', '지출', '경제효과',
                         '만 명', '만명', '억원', '조원', '유치실적', '카드']),
            ('지자체·지역', ['시가', '도가', '서울시', '부산', '인천', '대구', '광주', '대전', '제주', '경북',
                          '경남', '전북', '전남', '충북', '충남', '강원', '지자체', '지역']),
            ('기업·의료기관', ['병원', '의원', '협약', 'MOU', '업무협약', '기업', '플랫폼', '진출',
                           '투자', '유치업체', '에이전시', '협회']),
            ('해외·경쟁국', ['태국', '튀르키예', '말레이시아', '싱가포르', '일본', '인도', 'UAE', '두바이',
                          '사우디', '카타르', '쿠웨이트', '중동', 'Thailand', 'Turkey', 'Malaysia',
                          'Singapore', 'Dubai', 'Japan', 'India']),
            ('리스크·사건', ['불법', '브로커', '적발', '분쟁', '부작용', '소송', '과징금', '처분', '논란',
                          '무자격', '수수료', '과잉', '피해', '무임승차']),
        ],
        'weights': [
            (['비자', '사증', '제도', '개정', '규제', '지정'], 3),
            (['불법', '브로커', '적발', '분쟁', '부작용', '논란'], 4),
            (['한국관광공사', '관광공사', '보건복지부', '복지부', '보건산업진흥원', '진흥원'], 3),
            (['실적', '통계', '유치실적', '경제효과'], 2),
            (['중동', 'UAE', '사우디', '카타르', '쿠웨이트', '두바이'], 2),
            (['태국', '튀르키예', '말레이시아', '싱가포르'], 2),
            (['중증', '재활', '암', '이식', '검진'], 2),
            (['지역', '비수도권', '지자체'], 1),
        ],
        'core': ['외국인환자', '의료관광', '유치기관', '유치실적', '메디컬코리아', '의료 관광',
                 'medical tourism', 'health tourism', '환자 유치', '외국인 환자', '해외환자', '국제진료', 'medical travel'],
    },
    WEL: {
        'label': '웰니스',
        'desc': '치유관광 · 웰니스 자원 · 융복합',
        'ko': ['웰니스관광', '치유관광', '웰니스 관광지', '치유관광산업', '산림치유', '해양치유',
               '한방 웰니스', '템플스테이 관광', '웰니스 의료관광 융복합', '명상 관광',
               '스파 리조트 관광', '웰니스 클러스터'],
        'en': ['"wellness tourism" Korea', '"wellness tourism" market', 'Global Wellness Institute tourism',
               '"wellness travel" Asia', 'spa tourism Japan OR Thailand'],
        'cats': [
            ('정책·제도', ['법률', '시행', '개정', '고시', '제도', '지정', '인증', '문체부', '산림청',
                         '해양수산부', '정부', '국회', '예산', '바우처', '육성', '클러스터']),
            ('통계·실적', ['실적', '통계', '집계', '이용객', '방문객', '시장규모', '조사', '만 명', '만명',
                         '억원', '조원', '만족도', '효과']),
            ('지자체·지역', ['시가', '도가', '서울시', '경기도', '부산', '인천', '강원', '제주', '경북',
                          '경남', '전북', '전남', '충북', '충남', '군은', '지자체', '지역', '25선', '100선']),
            ('기업·시설', ['리조트', '호텔', '스파', '온천', '숙박', '기업', '투자', '개관', '협약', 'MOU',
                        '센터', '페어', '상품']),
            ('해외·트렌드', ['글로벌', '세계', '해외', '태국', '일본', '유럽', '미국', 'Global Wellness',
                          'wellness tourism', 'spa', '트렌드']),
            ('리스크·쟁점', ['불법', '과장', '허위', '광고', '논란', '분쟁', '부작용', '안전', '위생',
                          '유사의료', '제재', '적발']),
        ],
        'weights': [
            (['법률', '제도', '지정', '인증', '바우처', '클러스터', '예산'], 3),
            (['불법', '과장', '허위', '논란', '제재', '안전'], 4),
            (['한국관광공사', '관광공사', '문체부', '문화체육관광부', '산림청'], 3),
            (['통계', '이용객', '시장규모', '만족도', '실증'], 2),
            (['의료관광', '외국인환자', '융복합', '연계'], 3),
            (['글로벌', '해외', '태국', '일본'], 2),
            (['지역', '비수도권', '지자체'], 1),
        ],
        'core': ['웰니스', '치유관광', '산림치유', '해양치유', '템플스테이', '온천', '스파',
                 'wellness', '명상', '한방', '치유'],
    },
}


def track_of(it):
    return it.get('track') or MED


def relevant(it, track=None):
    """트랙 핵심어가 '제목'에 있는 기사만 분석(헤드라인 · 이슈 순위 · 주제어 · 지역)에 씀
    (요약까지 보면 웰니스는 거의 모든 기사가 걸려 잡음이 섞임)"""
    cfg = TRACKS[track or track_of(it)]
    txt = (it.get('title') or '').lower()
    return any(k.lower() in txt for k in cfg['core'])


def score_item(it, track=None):
    cfg = TRACKS[track or track_of(it)]
    txt = (it.get('title', '') + ' ' + (it.get('summary') or ''))   # 편집 메모(note)는 점수에 쓰지 않음
    s = 0
    for words, w in cfg['weights']:
        if any(k in txt for k in words):
            s += w
    s += 2 if any(k in txt for k in cfg['core']) else -2
    try:
        d = datetime.strptime(it['date'], '%Y-%m-%d').replace(tzinfo=KST)
        age = (datetime.now(KST) - d).days
        s += 3 if age <= 3 else (2 if age <= 7 else (1 if age <= 14 else 0))
    except Exception:
        pass
    return s


def classify(it, track=None):
    cfg = TRACKS[track or track_of(it)]
    txt = it.get('title', '') + ' ' + (it.get('summary') or '')
    best, hit = '기타', 0
    for name, words in cfg['cats']:
        n = sum(1 for k in words if k in txt)
        if n > hit:
            best, hit = name, n
    return best


