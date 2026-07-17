import streamlit as st
import google.generativeai as genai
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="원클릭 SNS 콘텐츠 마스터", layout="wide", page_icon="🚀")

st.title("🚀 원클릭 SNS 콘텐츠 마스터")
st.caption("URL 또는 원본 글 → 10장 카드뉴스 + 모든 플랫폼 콘텐츠 자동 생성")

st.sidebar.header("⚙️ 설정")
api_key = st.sidebar.text_input("Gemini API Key", type="password")
st.sidebar.markdown("[API 키 발급](https://aistudio.google.com/app/apikey)")

st.sidebar.markdown("---")
st.sidebar.header("🎨 카드뉴스 설정")
point_color = st.sidebar.color_picker("포인트 컬러", "#FF6B6B")

st.sidebar.markdown("---")
st.sidebar.header("📱 추가 생성 옵션")
gen_shorts = st.sidebar.checkbox("🎬 쇼츠/릴스 대본", value=True)
gen_captions = st.sidebar.checkbox("📱 플랫폼별 캡션", value=True)
gen_threads = st.sidebar.checkbox("🧵 스레드 타래", value=False)
gen_blog = st.sidebar.checkbox("📝 블로그 요약", value=False)

def crawl_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'lxml')
        
        if 'blog.naver.com' in url:
            iframe = soup.find('iframe', id='mainFrame')
            if iframe:
                iframe_url = 'https://blog.naver.com' + iframe['src']
                response = requests.get(iframe_url, headers=headers, timeout=10)
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'lxml')
        
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        content = ""
        for selector in [
            ('div', 'article_view'), ('div', 'tt_article_useless_p_margin'),
            ('div', 'se-main-container'), ('div', 'wrap_body'),
        ]:
            article = soup.find(selector[0], class_=selector[1])
            if article:
                content = article.get_text(separator='\n', strip=True)
                break
        
        if not content:
            article = soup.find('div', id='postViewArea') or soup.find('article') or soup.find('main')
            if article:
                content = article.get_text(separator='\n', strip=True)
        
        if not content:
            body = soup.find('body')
            if body:
                content = body.get_text(separator='\n', strip=True)
        
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        return '\n'.join(lines)[:10000]
    except:
        return None

def parse_cards(text):
    """카드 데이터 파싱 - 다양한 형식 대응"""
    cards = re.findall(r'===CARD===(.*?)===END===', text, re.DOTALL)
    
    card_data = []
    for card in cards:
        def extract(pattern):
            m = re.search(pattern, card)
            return m.group(1).strip() if m else ""
        
        큰제목 = extract(r'큰제목:\s*(.*?)(?=\n(?:부제목|본문|시각스타일|이미지프롬프트|디자인가이드|캡처유도):|$)')
        시각스타일 = extract(r'시각스타일:\s*(.*?)(?=\n(?:이미지프롬프트|디자인가이드|캡처유도):|$)')
        이미지프롬프트 = extract(r'이미지프롬프트:\s*(.*?)(?=\n(?:디자인가이드|캡처유도):|$)')
        디자인가이드 = extract(r'디자인가이드:\s*(.*?)(?=\n(?:캡처유도):|$)')
        
        card_data.append({
            "번호": extract(r'번호:\s*(.*)'),
            "역할": extract(r'역할:\s*(.*)'),
            "큰제목": 큰제목.replace('\n', ' ').strip(),
            "부제목": extract(r'부제목:\s*(.*)'),
            "본문": extract(r'본문:\s*(.*)'),
            "시각스타일": 시각스타일.replace('\n', ' ').strip(),
            "이미지프롬프트": 이미지프롬프트.replace('\n', ' ').strip(),
            "디자인가이드": 디자인가이드.replace('\n', ' ').strip(),
            "캡처유도": extract(r'캡처유도:\s*(.*)')
        })
    return card_data

def parse_section(text, section_name):
    """섹션 파싱 - 다양한 형식 대응"""
    patterns = [
        rf'===SECTION_{section_name}===(.*?)(?====SECTION_|$)',
        rf'##\s*SECTION_{section_name}\s*(.*?)(?=##\s*SECTION_|$)',
        rf'\*\*SECTION_{section_name}\*\*(.*?)(?=\*\*SECTION_|$)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            if content:
                return content
    return None

st.markdown("### 📥 콘텐츠 입력")

input_mode = st.radio(
    "입력 방식 선택",
    ["🔗 URL 입력 (자동 크롤링)", "📝 원본 글 직접 입력"],
    horizontal=True
)

source_text = ""

if input_mode == "🔗 URL 입력 (자동 크롤링)":
    url = st.text_input("블로그 URL", placeholder="예: 티스토리, 브런치, 네이버 블로그")
    st.caption("💡 티스토리/브런치는 잘됨. 네이버 블로그는 실패 시 직접 입력")
    
    if url and st.button("🔍 URL에서 내용 가져오기"):
        with st.spinner("URL 분석 중..."):
            crawled = crawl_url(url)
            if crawled and len(crawled) > 100:
                st.session_state['crawled_text'] = crawled
                st.success(f"✅ 크롤링 성공! ({len(crawled)}자)")
            else:
                st.error("❌ 크롤링 실패")
                st.session_state['crawled_text'] = ""
    
    source_text = st.text_area(
        "📝 가져온 내용 (수정 가능)",
        value=st.session_state.get('crawled_text', ''),
        height=300
    )
else:
    source_text = st.text_area(
        "📝 원본 글 붙여넣기",
        height=300,
        placeholder="블로그 글, 유튜브 대본을 여기에..."
    )

st.markdown("### 🎯 콘텐츠 정보")
col1, col2 = st.columns(2)
with col1:
    target_audience = st.text_input("타깃 독자", placeholder="예: 30대 직장인")
with col2:
    brand_name = st.text_input("브랜드/계정명", placeholder="예: @hanasence")

custom_note = st.text_input("💡 특별 요청 (선택)", placeholder="예: 특정 키워드 강조")

st.markdown("---")

if st.button("🚀 전체 콘텐츠 생성하기", type="primary", use_container_width=True):
    if not api_key:
        st.error("⚠️ API Key를 입력하세요!")
    elif not source_text or len(source_text) < 50:
        st.warning("⚠️ 원본이 너무 짧습니다.")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with st.spinner('AI 생성 중... (30초~1분)'):
                target = target_audience if target_audience else "일반 독자"
                brand = brand_name if brand_name else "@브랜드"
                extra = f"\n특별요청: {custom_note}" if custom_note else ""
                
                extra_sections = ""
                if gen_shorts:
                    extra_sections += "\n\n===SECTION_SHORTS===\n[쇼츠 대본]\n60초 영상용, 카드뉴스 흐름 그대로, 화면연출+자막 포함\n"
                if gen_captions:
                    extra_sections += "\n\n===SECTION_CAPTIONS===\n[플랫폼별 캡션]\n- 인스타 캡션 + 해시태그 15개\n- 페이스북 캡션 (상세)\n- 네이버 튤립 (짧게)\n- 네이버 클립 설명\n"
                if gen_threads:
                    extra_sections += "\n\n===SECTION_THREADS===\n[스레드 타래 5~7개]\n원본 문체 유지\n"
                if gen_blog:
                    extra_sections += "\n\n===SECTION_BLOG===\n[블로그 요약]\nSEO 키워드 포함 3~5줄\n"
                
                prompt = f"""당신은 프로 카드뉴스 기획자입니다.

⚠️ 매우 중요한 출력 규칙:
1. 반드시 아래 형식을 100% 정확히 지킬 것
2. 마크다운 ## ** 절대 사용 금지
3. 반드시 "===SECTION_CARDS===" 로 시작
4. 각 카드는 "===CARD===" 로 시작하고 "===END===" 로 끝
5. 반드시 10장 모두 완성
6. 각 필드는 한 줄로 작성

[기본 정보]
- 타깃: {target}
- 브랜드: {brand}
- 포인트 컬러: {point_color}
{extra}

[10장 구조]
1장(표지): 큰 글자 2줄
2장(문제제기): 카톡 스타일
3장(원인분석): 대조/차트
4장(로드맵): 타임라인
5장(솔루션1): 이미지+텍스트
6장(솔루션2): 이미지+텍스트
7장(솔루션3): 이미지+텍스트
8장(요약): 체크리스트
9장(클로징): 감성
10장(CTA): {brand} 표기

===SECTION_CARDS===

===CARD===
번호: 1
역할: 표지
큰제목: 한 줄로 작성
부제목: 한 줄로 작성
본문: 한 줄로 작성
시각스타일: 한 줄로 작성
이미지프롬프트: 영어로 한 줄
디자인가이드: 한 줄로 작성
캡처유도: 한 줄로 작성
===END===

(이런 식으로 10장 모두 작성)
{extra_sections}

원본글:
{source_text}
"""
                response = model.generate_content(prompt)
                result = response.text
                
                st.success("✅ 생성 완료!")
                
                with st.expander("🔍 AI 원본 응답 확인 (디버깅용)"):
                    st.text(result)
                
                st.markdown("---")
                
                tab_names = ["🎴 카드뉴스 (10장)"]
                if gen_shorts: tab_names.append("🎬 쇼츠")
                if gen_captions: tab_names.append("📱 캡션")
                if gen_threads: tab_names.append("🧵 스레드")
                if gen_blog: tab_names.append("📝 블로그")
                
                tabs = st.tabs(tab_names)
                tab_idx = 0
                
                with tabs[tab_idx]:
                    card_data = parse_cards(result)
                    
                    if card_data and len(card_data) > 0:
                        st.info(f"✅ 총 {len(card_data)}장의 카드가 생성됨")
                        
                        df = pd.DataFrame(card_data)
                        
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            st.info("💡 CSV를 Canva 대량 제작에 업로드!")
                        with col_b:
                            csv = df.to_csv(index=False).encode('utf-8-sig')
                            st.download_button(
                                "📥 CSV 다운로드",
                                csv, 'cardnews.csv', 'text/csv',
                                type="primary", use_container_width=True
                            )
                        
                        for card in card_data:
                            icon_map = {
                                "표지": "🎯", "문제 제기": "💬", "문제제기": "💬",
                                "원인 분석": "📊", "원인분석": "📊",
                                "로드맵": "🗺️",
                                "솔루션 1": "💡", "솔루션1": "💡",
                                "솔루션 2": "💡", "솔루션2": "💡",
                                "솔루션 3": "💡", "솔루션3": "💡",
                                "요약": "✅", "클로징": "🌿", "CTA": "👉"
                            }
                            icon = icon_map.get(card['역할'], "🎴")
                            title = card['큰제목'][:30] if card['큰제목'] else "제목없음"
                            
                            with st.expander(f"{icon} [{card['번호']}장 - {card['역할']}] {title}"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.markdown("### 📝 콘텐츠")
                                    st.markdown(f"**큰 제목:** {card['큰제목']}")
                                    if card['부제목']:
                                        st.markdown(f"**부제목:** {card['부제목']}")
                                    if card['본문']:
                                        st.markdown(f"**본문:** {card['본문']}")
                                
                                with col2:
                                    st.markdown("### 🎨 디자인")
                                    if card['시각스타일']:
                                        st.info(f"**시각 스타일:** {card['시각스타일']}")
                                    if card['디자인가이드']:
                                        st.success(f"**가이드:** {card['디자인가이드']}")
                                    if card['캡처유도']:
                                        st.warning(f"📸 {card['캡처유도']}")
                                
                                if card['이미지프롬프트']:
                                    st.markdown("### 🖼️ 이미지 프롬프트 (영어)")
                                    st.code(card['이미지프롬프트'], language='text')
                        
                        st.markdown("---")
                        st.subheader("📊 전체 데이터")
                        st.dataframe(df, use_container_width=True, height=400)
                    else:
                        st.error("❌ 카드 파싱 실패. 위의 '🔍 AI 원본 응답' 확인!")
                
                tab_idx += 1
                
                if gen_shorts:
                    with tabs[tab_idx]:
                        st.subheader("🎬 쇼츠/릴스 대본")
                        st.info("💡 Vrew, CapCut에 붙여넣어 사용!")
                        content = parse_section(result, 'SHORTS')
                        if content:
                            st.markdown(content)
                        else:
                            st.warning("쇼츠 대본을 찾지 못했습니다.")
                    tab_idx += 1
                
                if gen_captions:
                    with tabs[tab_idx]:
                        st.subheader("📱 플랫폼별 캡션")
                        content = parse_section(result, 'CAPTIONS')
                        if content:
                            st.markdown(content)
                        else:
                            st.warning("캡션을 찾지 못했습니다.")
                    tab_idx += 1
                
                if gen_threads:
                    with tabs[tab_idx]:
                        st.subheader("🧵 스레드 타래")
                        content = parse_section(result, 'THREADS')
                        if content:
                            st.markdown(content)
                    tab_idx += 1
                
                if gen_blog:
                    with tabs[tab_idx]:
                        st.subheader("📝 블로그 요약")
                        content = parse_section(result, 'BLOG')
                        if content:
                            st.markdown(content)
                
                st.markdown("---")
                st.info("💡 결과가 아쉬우면 다시 생성하세요!")
                
        except Exception as e:
            st.error(f"❌ 오류: {str(e)}")

st.markdown("---")
with st.expander("📖 사용 가이드"):
    st.markdown("""
    ### 🚀 사용법
    1. **API Key 입력** (사이드바)
    2. **URL 또는 원본 글 입력**
    3. **타깃/브랜드 입력**
    4. **옵션 선택** (쇼츠, 캡션 등)
    5. **생성하기 클릭!**
    
    ### 💡 결과 활용
    - **CSV 다운로드** → Canva 대량 제작
    - **쇼츠 대본** → Vrew/CapCut
    - **캡션** → 각 SNS
    """)
