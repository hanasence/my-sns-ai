import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="SNS 마스터", layout="wide")

st.title("🚀 원클릭 SNS 콘텐츠 변환기")
st.caption("블로그 글 하나로 인스타/스레드/쇼츠/네이버 클립/튤립까지 한 번에!")

# 사이드바
st.sidebar.header("⚙️ 설정")
api_key = st.sidebar.text_input("Gemini API Key", type="password")
st.sidebar.markdown("[API 키 발급받기](https://aistudio.google.com/app/apikey)")

# 입력창
source_text = st.text_area("📝 원본 블로그 글을 붙여넣으세요", height=400)

if st.button("✨ 플랫폼별 게시물 생성하기", type="primary"):
    if not api_key:
        st.error("왼쪽 사이드바에 API Key를 먼저 입력해주세요!")
    elif not source_text:
        st.warning("변환할 내용을 입력해주세요.")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            with st.spinner('AI가 열심히 작업 중입니다... (약 20초 소요)'):
                prompt = f"""
당신은 SNS 마케팅 전문가입니다. 아래 블로그 글을 각 플랫폼 성격에 맞게 완벽하게 변환하세요.

## [인스타그램/페이스북]
- 첫 줄: 스크롤을 멈추게 하는 강렬한 후킹 문구
- 감성적인 이모지 사용
- 핵심 해시태그 15개

## [스레드]
- 친구에게 말하듯 반말체 (~함, ~임, ~인 듯)
- 짧게 끊어지는 타래(Thread) 형식

## [유튜브 쇼츠]
- 0~3초: 눈을 뗄 수 없는 강렬한 후킹 자막
- 전체 60초 분량의 대본
- [화면 연출] 지시사항 포함

## [네이버 클립]
- 정보 전달 중심의 깔끔한 나레이션
- 네이버 지도/쇼핑 스티커 추천 위치 표시

## [네이버 튤립]
- 이미지 한 장과 어울리는 짧고 감성적인 문구
- 관련 태그 10개

## [이미지 프롬프트 - 영어]
뻔한 사진 절대 금지! 아래 3가지 스타일로 각각 작성:
1. Cinematic photography style (시네마틱 실사)
2. 3D isometric render style (3D 아이소메트릭)
3. Surreal digital art style (초현실적 디지털 아트)

원본글:
{source_text}
"""
                response = model.generate_content(prompt)
                st.success("✅ 변환 완료!")
                st.markdown("---")
                st.markdown(response.text)
                
        except Exception as e:
            st.error(f"오류: {str(e)}")
