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
    """URL 크롤링 - 개선판"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 네이버 블로그 iframe 처리
        if 'blog.naver.com' in url:
            iframe = soup.find('iframe', id='mainFrame')
            if iframe:
                iframe_url = 'https://blog.naver.com' + iframe['src']
                response = requests.get(iframe_url, headers=headers, timeout=15)
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'lxml')
        
        # 불필요한 태그 제거
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "button"]):
            tag.decompose()
        
        content = ""
        
        # 블로그스팟 (Blogger)
        if 'blogspot.com' in url or 'blogger.com' in url:
            article = soup.find('div', class_='post-body') or soup.find('div', class_='entry-content')
            if article:
                content = article.get_text(separator='\n', strip=True)
        
        # 티스토리
        if not content:
            article = soup.find('div', class_='article_view') or soup.find('div', class_='tt_article_useless_p_margin') or soup.find('div', class_='entry-content')
            if article:
                content = article.get_text(separator='\n', strip=True)
        
        # 네이버 블로그
        if not content:
            article = soup.find('div', class_='se-main-container') or soup.find('div', id='postViewArea')
            if article:
                content = article.get_text(separator='\n', strip=True)
        
        # 브런치
        if not content:
            article = soup.find('div', class_='wrap_body')
            if article:
                content = article.get_text(separator='\n', strip=True)
        
        # 워드프레스/일반
        if not content:
            article = soup.find('article') or soup.find('main') or soup.find('div', class_='post-content')
            if article:
                content = article.get_text(separator='\n', strip=True)
        
        # 최후: body 전체에서 긴 텍스트 블록 찾기
        if not content or len(content) < 200:
            all_divs = soup.find_all('div')
            longest_text = ""
            for div in all_divs:
                text = div.get_text(separator='\n', strip=True)
                if len(text) > len(longest_text) and len(text) > 300:
                    longest_text = text
            content = longest_text
        
        # 정리
        lines = [line.strip() for line in content.split('\n') if line.strip() and len(line.strip()) > 2]
        content = '\n'.join(lines)
        
        return content[:15000] if content else None
        
    except Exception as e:
        return None

def parse_cards(text):
    """카드 데이터 파싱 - 강화판"""
    # === CARD === 블록 찾기 (다양한 형식 대응)
    patterns = [
        r'===CARD===(.*?)===END===',
        r'===\s*CARD\s*===(.*?)===\s*END\s*===',
        r'\*\*CARD\*\*(.*?)\*\*END\*\*',
    ]
    
    cards = []
    for pattern in patterns:
        cards = re.findall(pattern, text, re.DOTALL)
        if cards:
            break
    
    card_data = []
    for card in cards:
        def extract(field_name):
            # 다양한 형식 대응
            patterns = [
                rf'{field_name}:\s*(.*?)(?=\n(?:번호|역할|큰제목|부제목|본문|시각스타일|이미지프롬프트|디자인가이드|캡처유도):|$)',
                rf'\*\*{field_name}\*\*:\s*(.*?)(?=\n\*\*|$)',
                rf'{field_name}\s*:\s*(.*?)(?=\n|$)',
            ]
            for pattern in patterns:
                m = re.search(pattern, card, re.DOTALL)
                if m:
                    result = m.group(1).strip()
                    # 마크다운 제거
                    result = re.sub(r'\*\*(.*?)\*\*', r'\1', result)
                    result = re.sub(r'\*(.*?)\*', r'\1', result)
                    return result.replace('\n', ' ').strip()
            return ""
        
        card_data.append({
            "번호": extract('번호'),
            "역할": extract('역할'),
            "큰제목": extract('큰제목'),
            "부제목": extract('부제목'),
            "본문": extract('본문'),
            "시각스타일": extract('시각스타일'),
            "이미지프롬프트": extract('이미지프롬프트'),
            "디자인가이드": extract('디자인가이드'),
            "캡처유도": extract('캡처유도')
        })
    return card_data

def parse_section(text, section_name):
    """섹션 파싱 - 강화판"""
    patterns = [
        rf'===SECTION_{section_name}===(.*?)(?=(?:===SECTION_|===END_ALL|$))',
        rf'##\s*SECTION_{section_name}\s*(.*?)(?=(?:##\s*SECTION_|$))',
        rf'\*\*SECTION_{section_name}\*\*(.*?)(?=(?:\*\*SECTION_|$))',
        rf'SECTION_{section_name}\s*(.*?)(?=(?:SECTION_[A-Z]|$))',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            if content and len(content) > 20:
                # 마크다운 정리
                content = re.sub(r'^={3,}\s*', '', content, flags=re.MULTILINE)
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
    url = st.text_input("블로그 URL", placeholder="티스토리, 블로그스팟, 브런치 등")
    st.caption("💡 잘됨: 티스토리/브런치/블로그스팟 | 어려움: 네이버 블로그")
    
    if url and st.button("🔍 URL에서 내용 가져오기"):
        with st.spinner("URL 분석 중..."):
            crawled = crawl_url(url)
            if crawled and len(crawled) > 200:
                st.session_state['crawled_text'] = crawled
                st.success(f"✅ 크롤링 성공! ({len(crawled)}자)")
            else:
                st.error("❌ 크롤링 실패. 아래에 직접 붙여넣어 주세요.")
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
                    extra_sections += "\n\n===SECTION_SHORTS===\n60초 쇼츠 대본, 화면연출+자막 포함\n"
                if gen_captions:
                    extra_sections += "\n\n===SECTION_CAPTIONS===\n인스타/페북/튤립/클립 캡션 (해시태그 15개)\n"
                if gen_threads:
                    extra_sections += "\n\n===SECTION_THREADS===\n스레드 타래 5~7개\n"
                if gen_blog:
                    extra_sections += "\n\n===SECTION_BLOG===\n블로그 요약 3~5줄\n"
                
                prompt = f"""당신은 프로 카드뉴스 기획자입니다.

⚠️ 절대 규칙:
1. 마크다운 문법 (##, **, ---) 절대 사용 금지
2. 반드시 "===SECTION_CARDS===" 로 시작
3. 각 카드는 "===CARD===" 로 시작하고 "===END===" 로 끝
4. 반드시 10장 모두 완성
5. 각 필드 값은 한 줄로 작성
6. 필드명 뒤에 반드시 콜론(:) 사용

[기본 정보]
- 타깃: {target}
- 브랜드: {brand}
- 포인트 컬러: {point_color}
{extra}

[10장 카드 구조]
1장: 표지 (임팩트)
2장: 문제제기 (공감)
3장: 원인분석
4장: 로드맵
5장: 솔루션1
6장: 솔루션2
7장: 솔루션3
8장: 요약
9장: 클로징
10장: CTA ({brand})

===SECTION_CARDS===

===CARD===
번호: 1
역할: 표지
큰제목: 여기에 한 줄로
부제목: 여기에 한 줄로
본문: 여기에 한 줄로
시각스타일: 여기에 한 줄로
이미지프롬프트: 여기에 영어로 한 줄
디자인가이드: 여기에 한 줄로
캡처유도: 여기에 한 줄로
===END===

===CARD===
번호: 2
역할: 문제제기
(동일 형식으로 계속)
===END===

(반드시 10장 모두 작성){extra_sections}

원본글:
{source_text}
"""
                response = model.generate_content(prompt)
                result = response.text
                
                st.success("✅ 생성 완료!")
                
                with st.expander("🔍 AI 원본 응답 (디버깅용)"):
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
                        st.success(f"✅ 총 {len(card_data)}장의 카드 생성 완료!")
                        
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
                        
                        st.markdown("---")
                        
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
                            title = card['큰제목'][:40] if card['큰제목'] else "제목없음"
                            
                            with st.expander(f"{icon} [{card['번호']}장 - {card['역할']}] {title}"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.markdown("### 📝 콘텐츠")
                                    if card['큰제목']:
                                        st.markdown(f"**큰 제목:**\n{card['큰제목']}")
                                    if card['부제목']:
                                        st.markdown(f"**부제목:**\n{card['부제목']}")
                                    if card['본문']:
                                        st.markdown(f"**본문:**\n{card['본문']}")
                                
                                with col2:
                                    st.markdown("### 🎨 디자인")
                                    if card['시각스타일']:
                                        st.info(f"**시각 스타일:**\n{card['시각스타일']}")
                                    if card['디자인가이드']:
                                        st.success(f"**가이드:**\n{card['디자인가이드']}")
                                    if card['캡처유도']:
                                        st.warning(f"📸 {card['캡처유도']}")
                                
                                if card['이미지프롬프트']:
                                    st.markdown("### 🖼️ 이미지 프롬프트 (영어)")
                                    st.code(card['이미지프롬프트'], language='text')
                        
                        st.markdown("---")
                        st.subheader("📊 전체 데이터 표")
                        st.dataframe(df, use_container_width=True, height=400)
                    else:
                        st.error("❌ 카드 파싱 실패")
                        st.info("💡 위의 '🔍 AI 원본 응답' 를 열어서 확인해주세요")
                
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
                st.info("💡 결과가 아쉬우면 다시 생성 버튼을 누르세요!")
                
        except Exception as e:
            st.error(f"❌ 오류: {str(e)}")

st.markdown("---")
with st.expander("📖 사용 가이드"):
    st.markdown("""
    ### 🚀 사용법
    1. **API Key 입력** (사이드바)
    2. **URL 또는 원본 글 입력**
       - 🔗 URL: 티스토리/블로그스팟/브런치 (자동)
       - 📝 직접: 네이버 블로그 (복붙)
    3. **타깃/브랜드 입력**
    4. **옵션 선택** (쇼츠, 캡션 등)
    5. **생성하기!**
    
    ### 💡 결과 활용
    - **CSV 다운로드** → Canva 대량 제작
    - **쇼츠 대본** → Vrew/CapCut
    - **캡션** → 각 SNS
    """)
