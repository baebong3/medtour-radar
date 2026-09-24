# -*- coding: utf-8 -*-
"""기사 URL 도메인 → 매체명 (네이버 API는 매체명을 주지 않아 도메인으로 판별)"""
from urllib.parse import urlparse

DOMAINS = {
    'yna.co.kr': '연합뉴스', 'yonhapnewstv.co.kr': '연합뉴스TV', 'newsis.com': '뉴시스', 'news1.kr': '뉴스1',
    'chosun.com': '조선일보', 'biz.chosun.com': '조선비즈', 'joongang.co.kr': '중앙일보', 'donga.com': '동아일보',
    'hani.co.kr': '한겨레', 'khan.co.kr': '경향신문', 'hankookilbo.com': '한국일보', 'seoul.co.kr': '서울신문',
    'segye.com': '세계일보', 'kmib.co.kr': '국민일보', 'munhwa.com': '문화일보', 'naeil.com': '내일신문',
    'mk.co.kr': '매일경제', 'hankyung.com': '한국경제', 'sedaily.com': '서울경제', 'edaily.co.kr': '이데일리',
    'mt.co.kr': '머니투데이', 'asiae.co.kr': '아시아경제', 'fnnews.com': '파이낸셜뉴스', 'heraldcorp.com': '헤럴드경제',
    'ajunews.com': '아주경제', 'etoday.co.kr': '이투데이', 'newspim.com': '뉴스핌', 'dailian.co.kr': '데일리안',
    'inews24.com': '아이뉴스24', 'etnews.com': '전자신문', 'zdnet.co.kr': '지디넷코리아', 'bizwatch.co.kr': '비즈워치',
    'nocutnews.co.kr': '노컷뉴스', 'ohmynews.com': '오마이뉴스', 'pressian.com': '프레시안', 'mediatoday.co.kr': '미디어오늘',
    'kbs.co.kr': 'KBS', 'imbc.com': 'MBC', 'sbs.co.kr': 'SBS', 'jtbc.co.kr': 'JTBC', 'ytn.co.kr': 'YTN',
    'mbn.co.kr': 'MBN', 'ichannela.com': '채널A', 'tvchosun.com': 'TV조선', 'korea.kr': '정책브리핑',
    'imaeil.com': '매일신문', 'busan.com': '부산일보', 'kookje.co.kr': '국제신문', 'yeongnam.com': '영남일보',
    'kyeonggi.com': '경기일보', 'kgnews.co.kr': '경기신문', 'incheonilbo.com': '인천일보', 'jejunews.com': '제주일보',
    'jemin.com': '제민일보', 'kwnews.co.kr': '강원일보', 'kado.net': '강원도민일보', 'jnilbo.com': '전남일보',
    'kjdaily.com': '광주매일신문', 'jjan.kr': '전북일보', 'cctoday.co.kr': '충청투데이', 'daejonilbo.com': '대전일보',
    'medigatenews.com': '메디게이트뉴스', 'medifonews.com': '메디포뉴스', 'khanews.com': '병원신문',
    'docdocdoc.co.kr': '청년의사', 'dailymedi.com': '데일리메디', 'medicaltimes.com': '메디칼타임즈',
    'bosa.co.kr': '의학신문', 'mdtoday.co.kr': '메디컬투데이', 'k-health.com': '헬스경향', 'hidoc.co.kr': '하이닥',
    'medipana.com': '메디파나뉴스', 'monews.co.kr': '뉴스더보이스', 'kormedi.com': '코메디닷컴',
    'healthchosun.com': '헬스조선', 'rapportian.com': '라포르시안', 'medicalworldnews.co.kr': '메디컬월드뉴스',
    'akomnews.com': '한의신문', 'dailydental.co.kr': '치의신보', 'dentalnews.or.kr': '치과신문',
    'medipharmhealth.co.kr': '메디팜헬스뉴스', 'themedical.kr': '더메디컬', 'medicaldaily.co.kr': '의약일보',
    'traveltimes.co.kr': '여행신문', 'ttlnews.com': '여행레저신문', 'gtn.co.kr': '관광레저신문',
    'tournews21.com': '투어코리아', 'ktnbm.co.kr': '한국관광신문', 'travelnbike.com': '트래블바이크뉴스',
    'wikitree.co.kr': '위키트리', 'insight.co.kr': '인사이트', 'sisajournal.com': '시사저널',
    'g-enews.com': '글로벌이코노믹', 'biztribune.co.kr': '비즈트리뷴', 'wolyo.co.kr': '월요신문',
    'foodtoday.or.kr': '푸드투데이', 'theicn.co.kr': 'THE인천', 'jungbunews.com': '중부뉴스통신',
    'newsseoul.co.kr': '뉴스서울', 'cbci.co.kr': 'CBC뉴스', 'goodmorningvietnam.co.kr': '굿모닝베트남미디어',
    'daum.net': '다음뉴스', 'naver.com': '네이버뉴스', 'mohw.go.kr': '보건복지부', 'mcst.go.kr': '문화체육관광부',
    'knto.or.kr': '한국관광공사', 'khidi.or.kr': '한국보건산업진흥원',
    'thaiexaminer.com': 'Thai Examiner', 'mlit.go.jp': '일본 관광청', 'reuters.com': 'Reuters',
    'bloomberg.com': 'Bloomberg', 'cnn.com': 'CNN', 'bbc.com': 'BBC', 'koreaherald.com': 'The Korea Herald',
    'koreatimes.co.kr': 'The Korea Times', 'koreajoongangdaily.joins.com': 'Korea JoongAng Daily',
    'globalwellnesssummit.com': 'Global Wellness Summit', 'globalwellnessinstitute.org': 'Global Wellness Institute',
    'gulfnews.com': 'Gulf News', 'khaleejtimes.com': 'Khaleej Times', 'thenationalnews.com': 'The National',
    'bangkokpost.com': 'Bangkok Post', 'nationthailand.com': 'The Nation Thailand', 'thestar.com.my': 'The Star',
    'nst.com.my': 'New Straits Times', 'dailysabah.com': 'Daily Sabah', 'hurriyetdailynews.com': 'Hürriyet Daily News',
}


def media_name(media, url):
    """저장된 매체명이 도메인 형태이면 한글 매체명으로 바꿈. 모르는 도메인은 도메인 그대로"""
    m = (media or '').strip()
    host = urlparse(url or '').netloc.lower().replace('www.', '').replace('m.', '', 1) if url else ''
    if m and '.' not in m:
        return m                      # 이미 사람이 읽는 매체명(Google 뉴스 제공분)
    cand = (m or host).lower().replace('www.', '')
    parts = cand.split('.')
    for i in range(len(parts) - 1):   # news.mt.co.kr → mt.co.kr 순으로 줄여 가며 조회
        d = '.'.join(parts[i:])
        if d in DOMAINS:
            return DOMAINS[d]
    return m or host
