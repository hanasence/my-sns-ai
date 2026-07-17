import streamlit as st
import google.generativeai as genai
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="원클릭 SNS 콘텐츠 마스터", layout="wide", page_icon="🚀")

st.title("🚀 원클릭 SNS 콘텐츠 마스터")
st.caption("URL 또는 원본 글 → 10장 카드뉴스 + 모든 플랫폼 콘텐츠 자동 생성")

# ===== 사이드바 =====
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

# ===== 크롤링 함수 =====
def crawl_url(url):
    """URL에서 본문 내용 추출"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
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
        
        article = soup.find('div', class_='article_view') or soup.find('div', class_='tt_article_useless_p_margin')
        if article:
            content = article.get_text(separator='\n', strip=True)
        
        if not content:
            article = soup.find('div', class_='se-main-container') or soup.find('div', id='postViewArea')
            if article:
                content = article.get_text(separator='\n', strip=True)
        
        if not content:
            article = soup.find('div', class_='wrap_body')
            if article:
                content = article.get_text(separator='\n', strip=True)
        
        if not content:
            article = soup.find('article') or soup.find('main') or soup.find('div', class_='post-content')
            if article:
                content = article.get_text(separator='\n', strip=True)
        
        if not content:
            body = soup.find('body')
            if body:
                content = body.get_text(separator='\n', strip=True)
        
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        content = '\n'.join(lines)
        
        return content[:10000]
        
    except Exception as e:
        return None

# ===== 메인 영역 =====
st.markdown("### 📥 콘텐츠 입력")

input_mode = st.radio(
    "입력 방식 선택",
    ["🔗 URL 입력 (자동 크롤링)", "📝 원본 글 직접 입력"],
    horizontal=True
)

source_text = ""

if input_mode == "🔗 URL 입력 (자동 크롤링)":
    url = st.text_input(
        "블로그 URL",
        placeholder="예: https://blog.naver.com/... 또는 티스토리, 브런치 등"
    )
    
    st.caption("💡 티스토리/브런치는 잘됨. 네이버 블로그는 실패 시 직접 입력 사용")
    
    if url:
        if st.button("🔍 URL에서 내용 가져오기"):
            with st.spinner("URL 분석 중..."):
                crawled = crawl_url(url)
                
                if crawled and len(crawled) > 100:
                    st.session_state['crawled_text'] = crawled
                    st.success(f"✅ 크롤링 성공! ({len(crawled)}자)")
                else:
                    st.error("❌ 크롤링 실패. 아래에 직접 붙여넣어 주세요.")
                    st.session_state['crawled_text'] = ""
    
    source_text = st.text_area(
        "📝 가져온 내용 (수정 가능)",
        value=st.session_state.get('crawled_text', ''),
        height=300,
        placeholder="URL에서 자동으로 가져온 내용이 여기 표시됩니다."
    )

else:
    source_text = st.text_area(
        "📝 원본 글 붙여넣기",
        height=300,
        placeholder="블로그 글, 유튜브 대본, 원본 콘텐츠를 여기에 붙여넣으세요..."
    )

# ===== 기본 정보 =====
st.markdown("### 🎯 콘텐츠 정보")
col1, col2 = st.columns(2)
with col1:
    target_audience = st.text_input(
        "타깃 독자",
        placeholder="예: 30대 직장인, 자영업자"
    )
with col2:
    brand_name = st.text_input(
        "브랜드/계정명",
        placeholder="예: @hanasence"
    )

custom_note = st.text_input(
    "💡 특별 요청 (선택)",
    placeholder="예: 특정 키워드 강조, 존댓말 사용 등"
)

# ===== 생성 버튼 =====
st.markdown("---")

if st.button("🚀 전체 콘텐츠 생성하기", type="primary", use_container_width=True):
    if not api_key:
        st.error("⚠️ 사이드바에 Gemini API Key를 입력하세요!")
    elif not source_text or len(source_text) < 50:
        st.warning("⚠️ 원본 내용이 너무 짧습니다.")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            
            with st.spinner('AI가 콘텐츠 생성 중... (약 30초)'):
                extra = f"\n특별요청: {custom_note}" if custom_note else ""
                target = target_audience if target_audience else "일반 독자"
                brand = brand_name if brand_name else "@브랜드"
                
                extra_sections = ""
                if gen_shorts:
                    extra_sections += "\n===SECTION_SHORTS===\n[쇼츠 대본]\n60초 영상용, 카드뉴스 흐름 그대로, 화면연출+자막 포함\n"
                if gen_captions:
                    extra_sections += "\n===SECTION_CAPTIONS===\n[플랫폼별 캡션]\n- 인스타 캡션 + 해시태그 15개\n- 페이스북 캡션 (상세)\n- 네이버 튤립 (짧게)\n- 네이버 클립 설명\n"
                if gen_threads:
                    extra_sections += "\n===SECTION_THREADS===\n[스레드 타래 5~7개]\n원본 문체 유지\n"
                if gen_blog:
                    extra_sections += "\n===SECTION_BLOG===\n[블로그 요약]\nSEO 키워드 포함 3~5줄 요약\n"
                
                prompt = f"""당신은 프로 카드뉴스 기획자입니다.

⚠️ 절대 규칙:
- 원본의 말투, 문체, 전문성, 핵심 키워드 유지
- 형식만 재구성

[기본 정보]
- 타깃: {target}
- 브랜드: {brand}
- 포인트 컬러: {point_color}
{extra}

[10장 카드뉴스 구조]
1장(표지): 1:9 법칙, 큰 글자 2줄, 포인트 키워드 형광색
2장(문제제기): 카톡/DM/지식인 캡처 스타일
3장(원인분석): A vs B 대조 or 차트
4장(로드맵): 타임라인 디자인
5장(솔루션1): 이미지 60%+텍스트 2줄
6장(솔루션2): 이미지 60%+텍스트 2줄
7장(솔루션3): 이미지 60%+텍스트 2줄
8장(요약): 체크박스 리스트, 캡처 유도
9장(클로징): 킨포크 감성, 여백+명언
10장(CTA): 화살표/버튼, {brand} 표기

[디자인 원칙]
- 컬러 3개만: 배경(화이트) + 텍스트(다크그레이) + 포인트({point_color})
- 폰트: 제목 두껍게, 본문 얇게

===SECTION_CARDS===

===CARD===
번호: 1
역할: 표지
큰제목: (2줄 이내, 임팩트)
부제목: (필요시)
본문: (해당시)
시각스타일: (구체적 설명)
이미지프롬프트: (영어, 상세)
디자인가이드: (구체적 지시)
캡처유도: (해당시)
===END===

(10장 모두 작성)

{extra_sections}

원본글:
{source_text}
"""
                response = model.generate_content(prompt)
                result = response.text
                
                st.success("✅ 생성 완료!")
                st.markdown("---")
                
                tab_names = ["🎴 카드뉴스 (10장)"]
                if gen_shorts: tab_names.append("🎬 쇼츠")
                if gen_captions: tab_names.append("📱 캡션")
                if gen_threads: tab_names.append("🧵 스레드")
                if gen_blog: tab_names.append("📝 블로그")
                
                tabs = st.tabs(tab_names)
                tab_idx = 0
                
                with tabs[tab_idx]:
                    cards_section = re.search(r'===SECTION_CARDS===(.*?)(?====SECTION_|$)', result, re.DOTALL)
                    if cards_section:
                        cards = re.findall(r'===CARD===(.*?)===END===', cards_section.group(1), re.DOTALL)
                        
                        card_data = []
                        for card in cards:
                            def extract(pattern):
                                m = re.search(pattern, card)
                                return m.group(1).strip() if m else ""
                            
                            card_data.append({
                                "번호": extract(r'번호:\s*(.*)'),
                                "역할": extract(r'역할:\s*(.*)'),
                                "큰제목": extract(r'큰제목:\s*(.*)'),
                                "부제목": extract(r'부제목:\s*(.*)'),
                                "본문": extract(r'본문:\s*(.*)'),
                                "시각스타일": extract(r'시각스타일:\s*(.*)'),
                                "이미지프롬프트": extract(r'이미지프롬프트:\s*(.*)'),
                                "디자인가이드": extract(r'디자인가이드:\s*(.*)'),
                                "캡처유도": extract(r'캡처유도:\s*(.*)')
                            })
                        
                        st.session_state['card_data'] = card_data
                        
                        if card_data:
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
                                    "로드맵": "🗺️", "본론 시작": "🗺️",
                                    "솔루션 1": "💡", "솔루션1": "💡",
                                    "솔루션 2": "💡", "솔루션2": "💡",
                                    "솔루션 3": "💡", "솔루션3": "💡",
                                    "요약": "✅", "클로징": "🌿", "CTA": "👉"
                                }
                                icon = icon_map.get(card['역할'], "🎴")
                                
                                with st.expander(f"{icon} [{card['번호']}장 - {card['역할']}] {card['큰제목'][:30]}"):
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
                                        st.info(f"**시각 스타일:**\n{card['시각스타일']}")
                                        st.success(f"**가이드:**\n{card['디자인가이드']}")
                                        if card['캡처유도']:
                                            st.warning(f"📸 {card['캡처유도']}")
                                    
                                    st.markdown("### 🖼️ 이미지 프롬프트 (영어)")
                                    st.code(card['이미지프롬프트'], language='text')
                            
                            st.markdown("---")
                            st.subheader("📊 전체 데이터")
                            st.dataframe(df, use_container_width=True, height=400)
                
                tab_idx += 1
                
                if gen_shorts:
                    with tabs[tab_idx]:
                        st.subheader("🎬 쇼츠/릴스 대본")
                        st.info("💡 Vrew, CapCut에 붙여넣어 사용!")
                        shorts = re.search(r'===SECTION_SHORTS===(.*?)(?====SECTION_|$)', result, re.DOTALL)
                        if shorts:
                            st.markdown(shorts.group(1).strip())
                    tab_idx += 1
                
                if gen_captions:
                    with tabs[tab_idx]:
                        st.subheader("📱 플랫폼별 캡션")
                        captions = re.search(r'===SECTION_CAPTIONS===(.*?)(?====SECTION_|$)', result, re.DOTALL)
                        if captions:
                            st.markdown(captions.group(1).strip())
                    tab_idx += 1
                
                if gen_threads:
                    with tabs[tab_idx]:
                        st.subheader("🧵 스레드 타래")
                        threads = re.search(r'===SECTION_THREADS===(.*?)(?====SECTION_|$)', result, re.DOTALL)
                        if threads:
                            st.markdown(threads.group(1).strip())
                    tab_idx += 1
                
                if gen_blog:
                    with tabs[tab_idx]:
                        st.subheader("📝 블로그 요약")
                        blog = re.search(r'===SECTION_BLOG===(.*?)(?====SECTION_|$)', result, re.DOTALL)
                        if blog:
                            st.markdown(blog.group(1).strip())
                
                st.markdown("---")
                st.info("💡 결과가 마음에 안 들면 다시 생성 버튼을 누르세요!")
                
        except Exception as e:
            st.error(f"❌ 오류: {str(e)}")

st.markdown("---")
with st.expander("📖 사용 가이드"):
    st.markdown("""
    ### 🚀 사용법
    1. **API Key 입력** (사이드바)
    2. **입력 방식 선택**
       - 🔗 URL: 티스토리/브런치 (자동)
       - 📝 직접: 네이버 블로그 (복붙)
    3. **정보 입력** (타깃, 브랜드)
    4. **옵션 선택** (필요한 플랫폼)
    5. **생성하기!**
    
    ### 💡 활용
    - **카드뉴스 CSV** → Canva 대량 제작
    - **쇼츠 대본** → Vrew/CapCut
    - **캡션** → 각 SNS
    """)
