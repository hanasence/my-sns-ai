import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="모델 확인", layout="wide")

st.title("🔍 사용 가능한 Gemini 모델 확인")
st.caption("당신의 API Key로 어떤 모델이 되는지 확인합니다")

api_key = st.text_input("Gemini API Key 입력", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        
        st.subheader("✅ 사용 가능한 모델 목록:")
        
        models = genai.list_models()
        available_models = []
        
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                model_name = model.name.replace("models/", "")
                available_models.append(model_name)
                
                st.success(f"✅ {model_name}")
        
        st.markdown("---")
        
        if available_models:
            st.subheader("⭐ 추천 코드 (복사해서 사용)")
            
            # flash 모델 우선 추천
            recommended = None
            for m in available_models:
                if 'flash' in m.lower():
                    recommended = m
                    break
            
            if not recommended:
                recommended = available_models[0]
            
            st.code(f"model = genai.GenerativeModel('{recommended}')", language='python')
            
            st.markdown("---")
            st.subheader("📋 전체 모델 리스트")
            for m in available_models:
                st.write(f"- `{m}`")
        else:
            st.warning("사용 가능한 모델이 없습니다.")
            
    except Exception as e:
        st.error(f"오류: {e}")
        st.info("API Key가 올바른지 확인해주세요.")
