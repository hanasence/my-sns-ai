import streamlit as st
import google.generativeai as genai
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import zipfile
import os

st.set_page_config(page_title="원클릭 SNS 콘텐츠 마스터", layout="wide", page_icon="🚀")

# ─────────────────────────────────────────
# 🔤 폰트 로드 (GitHub에 올린 파일 사용)
# ─────────────────────────────────────────
def get_font(size, bold=False):
    try:
        path = "NanumGothicBold.ttf" if bold else "NanumGothic.ttf"
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

# ─────────────────────────────────────────
# 🎨 템플릿 색상 세트
# ─────────────────────────────────────────
TEMPLATE_SETS = {
    "A. 미니멀 화이트": {"bg": "#FFFFFF", "text": "#2C2C2C", "point": "#FF6B6B", "sub_bg": "#F5F5F5"},
    "B. 감성 파스텔":   {"bg": "#FFE5EC", "text": "#4A4A4A", "point": "#FF6B9D", "sub_bg": "#FFF0F5"},
    "C. 블랙 프리미엄": {"bg": "#1A1A1A", "text": "#FFFFFF", "point": "#FFD700", "sub_bg": "#2C2C2C"},
    "D. 비비드 팝":     {"bg": "#FFF8DC", "text": "#333333", "point": "#FF4500", "sub_bg": "#FFF3C0"},
}

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def wrap_text(draw, text, font, max_width):
    lines, current = [], ""
    for char in str(text):
        test = current + char
        try:
            w = draw.textbbox((0,0), test, font=font)[2]
        except:
            w = len(test) * 15
        if w > max_width and current:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines if lines else [str(text)]

def draw_text_center(draw, text, y, font, color, W, max_w, gap=15):
    if not text: return y
    lines = wrap_text(draw, str(text), font, max_w)
    current_y = y
    for line in lines:
        try:
            bb = draw.textbbox((0,0), line, font=font)
            tw, th = bb[2]-bb[0], bb[3]-bb[1]
        except:
            tw, th = len(line)*15, 30
        draw.text(((W-tw)/2, current_y), line, font=font, fill=color)
        current_y += th + gap
    return current_y

def draw_text_left(draw, text, x, y, font, color, max_w, gap=15):
    if not text: return y
    lines = wrap_text(draw, str(text), font, max_w)
    current_y = y
    for line in lines:
        try:
            bb = draw.textbbox((0,0), line, font=font)
            th = bb[3]-bb[1]
        except:
            th = 30
        draw.text((x, current_y), line, font=font, fill=color)
        current_y += th + gap
    return current_y

def add_overlay(img, x1, y1, x2, y2, color_rgb, alpha=180):
    overlay = Image.new('RGBA', img.size, (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    d.rectangle([x1,y1,x2,y2], fill=(*color_rgb, alpha))
    return Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')

def make_base(bg_image, bg_rgb, W=1080, H=1080):
    if bg_image:
        return bg_image.copy().resize((W,H), Image.LANCZOS).convert('RGB')
    return Image.new('RGB', (W,H), bg_rgb)

# ─────────────────────────────────────────
# 🖼️ 10장 카드 생성
# ─────────────────────────────────────────
def create_card(card_num, card, template_set, bg_image=None):
    W, H = 1080, 1080
    colors  = TEMPLATE_SETS[template_set]
    bg_rgb  = hex_to_rgb(colors["bg"])
    txt_rgb = hex_to_rgb(colors["text"])
    pt_rgb  = hex_to_rgb(colors["point"])
    sub_rgb = hex_to_rgb(colors["sub_bg"])
    white   = (255,255,255)

    title = str(card.get("큰제목","") or "")
    sub   = str(card.get("부제목","") or "")
    body  = str(card.get("본문","")   or "")

    # ══════════════════════════
    # 1장: 표지
    # ══════════════════════════
    if card_num == 1:
        img = make_base(bg_image, bg_rgb)
        img = add_overlay(img, 0, int(H*0.52), W, H, bg_rgb, alpha=220)
        draw = ImageDraw.Draw(img)
        draw.rectangle([(80,int(H*0.54)),(220,int(H*0.54)+5)], fill=pt_rgb)
        draw_text_center(draw, title, int(H*0.57), get_font(72,True), txt_rgb, W, W-120)
        draw_text_center(draw, sub, int(H*0.78), get_font(36), pt_rgb, W, W-160)
        draw.text((W-120,H-60), "1/10", font=get_font(28), fill=pt_rgb)

    # ══════════════════════════
    # 2장: 문제제기 (카톡)
    # ══════════════════════════
    elif card_num == 2:
        img = Image.new('RGB',(W,H),(254,229,0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0,0),(W,110)], fill=(230,207,0))
        draw_text_center(draw, "💬 " + (title or "많이들 물어보세요!"), 30, get_font(38,True), (50,50,50), W, W-80)
        bubbles = [
            (60, 160, sub or "이거 저도 해당되나요? 😮"),
            (250,300, body or "저도 궁금했어요!"),
            (60, 440, "저는 잘 몰라서요 ㅠㅠ"),
            (250,580, "저도요! 알려주세요!"),
        ]
        for bx,by,btxt in bubbles:
            f_b = get_font(30)
            try:
                bb = draw.textbbox((0,0),btxt,font=f_b)
                bw = min(bb[2]-bb[0]+50, W-140)
                bh = bb[3]-bb[1]+36
            except:
                bw,bh = 400,60
            draw.rounded_rectangle([bx,by,bx+bw,by+bh], radius=20, fill="white")
            draw.text((bx+25,by+18), btxt, font=f_b, fill="#333333")
        draw.text((40,H-70), "오후 3:45", font=get_font(26), fill="#888888")
        draw.text((W-120,H-60), "2/10", font=get_font(26), fill="#888888")

    # ══════════════════════════
    # 3장: 원인분석 (A vs B)
    # ══════════════════════════
    elif card_num == 3:
        img = Image.new('RGB',(W,H),bg_rgb)
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0,0),(W//2,H)], fill=hex_to_rgb("#EEEEEE"))
        draw.rectangle([(W//2,0),(W,H)], fill=pt_rgb)
        draw.rectangle([(W//2-3,0),(W//2+3,H)], fill="white")
        draw.rectangle([(0,0),(W,130)], fill=bg_rgb)
        draw_text_center(draw, title or "이런 차이가 있어요!", 35, get_font(50,True), txt_rgb, W, W-80)
        cx,cy = W//2, H//2
        draw.ellipse([(cx-50,cy-50),(cx+50,cy+50)], fill="white")
        draw.text((cx-22,cy-20), "VS", font=get_font(34,True), fill=pt_rgb)
        draw.text((W//4-30,180), "❌", font=get_font(60), fill="#FF4444")
        draw_text_center(draw, sub or "모르는 사람", 280, get_font(34), hex_to_rgb("#555555"), W//2, W//2-60)
        draw.text((W//4*3-30,180), "✅", font=get_font(60), fill="white")
        draw_text_center(draw, body or "아는 사람", 280, get_font(34), white, W+W//2, W//2-60)
        draw.rectangle([(0,H-120),(W,H)], fill=bg_rgb)
        draw_text_center(draw, "당신은 어느 쪽인가요?", H-95, get_font(36,True), txt_rgb, W, W-80)
        draw.text((W-120,H-60), "3/10", font=get_font(28), fill=pt_rgb)

    # ══════════════════════════
    # 4장: 로드맵
    # ══════════════════════════
    elif card_num == 4:
        img = make_base(bg_image, bg_rgb)
        img = add_overlay(img, 0, 0, W, H, bg_rgb, alpha=210)
        draw = ImageDraw.Draw(img)
        draw_text_center(draw, title or "전체 흐름 한눈에!", 80, get_font(60,True), txt_rgb, W, W-80)
        draw.rectangle([(W//2-80,170),(W//2+80,176)], fill=pt_rgb)
        steps = [s.strip() for s in body.split('/')][:4] if '/' in body else ["확인","신청","접수","완료"]
        while len(steps) < 4: steps.append("완료")
        node_y = int(H*0.50)
        node_xs = [180,400,650,870]
        draw.line([(node_xs[0],node_y),(node_xs[-1],node_y)], fill=pt_rgb, width=8)
        for i,(nx,step) in enumerate(zip(node_xs,steps)):
            draw.ellipse([(nx-48,node_y-48),(nx+48,node_y+48)], fill=pt_rgb)
            draw.ellipse([(nx-38,node_y-38),(nx+38,node_y+38)], fill="white")
            ns = str(i+1)
            try:
                bb = draw.textbbox((0,0),ns,font=get_font(38,True))
                draw.text((nx-(bb[2]-bb[0])//2, node_y-(bb[3]-bb[1])//2), ns, font=get_font(38,True), fill=pt_rgb)
            except:
                draw.text((nx-10,node_y-15), ns, font=get_font(38,True), fill=pt_rgb)
            draw_text_center(draw, step, node_y+65, get_font(30), txt_rgb, W, 200)
        draw_text_center(draw, sub or "이제 하나씩 알려드릴게요!", int(H*0.80), get_font(38), pt_rgb, W, W-120)
        draw.text((W-120,H-60), "4/10", font=get_font(28), fill=pt_rgb)

    # ══════════════════════════
    # 5~7장: 솔루션
    # ══════════════════════════
    elif card_num in [5,6,7]:
        sol_map = {5:("①","5"), 6:("②","6"), 7:("③","7")}
        sol_num, page_num = sol_map[card_num]
        img = make_base(bg_image, bg_rgb)
        img = add_overlay(img, 0, int(H*0.56), W, H, sub_rgb, alpha=245)
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0,int(H*0.56)),(W,int(H*0.56)+6)], fill=pt_rgb)
        draw.text((50,int(H*0.57)), sol_num, font=get_font(90,True), fill=pt_rgb)
        draw_text_left(draw, title, 180, int(H*0.60), get_font(52,True), txt_rgb, W-220)
        draw_text_left(draw, body, 60, int(H*0.75), get_font(34), txt_rgb, W-120)
        draw_text_left(draw, sub, 60, int(H*0.88), get_font(30), pt_rgb, W-120)
        draw.text((W-120,H-60), f"{page_num}/10", font=get_font(28), fill=pt_rgb)

    # ══════════════════════════
    # 8장: 요약
    # ══════════════════════════
    elif card_num == 8:
        if bg_image:
            base = make_base(bg_image, sub_rgb)
            img = base.filter(ImageFilter.GaussianBlur(12))
        else:
            img = Image.new('RGB',(W,H), sub_rgb)
        overlay = Image.new('RGBA',(W,H),(0,0,0,0))
        od = ImageDraw.Draw(overlay)
        od.rounded_rectangle([50,50,W-50,H-50], radius=30, fill=(*hex_to_rgb(colors["sub_bg"]),235))
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        draw_text_center(draw, "📌 " + (title or "지금까지 정리!"), 90, get_font(56,True), txt_rgb, W, W-120)
        draw.rectangle([(100,185),(W-100,191)], fill=pt_rgb)
        items = [x.strip() for x in body.split('/')] if '/' in body else [body]
        items = [x for x in items if x][:4]
        if not items: items = ["핵심 정보 1","핵심 정보 2","핵심 정보 3"]
        for i,item in enumerate(items):
            y_i = 220 + i*150
            draw.rounded_rectangle([(70,y_i),(125,y_i+55)], radius=8, fill=pt_rgb)
            draw.text((82,y_i+10), "✓", font=get_font(32,True), fill="white")
            draw_text_left(draw, item, 145, y_i+8, get_font(36,True), txt_rgb, W-200)
        draw.rectangle([(70,int(H*0.84)),(W-70,int(H*0.84)+4)], fill=pt_rgb)
        draw_text_center(draw, "💾 저장하고 두고두고 봐요!", int(H*0.87), get_font(38,True), pt_rgb, W, W-100)
        draw.text((W-120,H-60), "8/10", font=get_font(28), fill=pt_rgb)

    # ══════════════════════════
    # 9장: 클로징
    # ══════════════════════════
    elif card_num == 9:
        img = make_base(bg_image, bg_rgb)
        img = add_overlay(img, 0, 0, W, H, bg_rgb, alpha=170)
        draw = ImageDraw.Draw(img)
        draw.rectangle([(W//2-60,100),(W//2+60,106)], fill=pt_rgb)
        draw.text((60,int(H*0.22)), '"', font=get_font(140,True), fill=pt_rgb)
        draw_text_center(draw, title or "작은 정보 하나가 큰 변화를 만듭니다", int(H*0.38), get_font(50,True), txt_rgb, W, W-160)
        draw.text((W-120,int(H*0.60)), '"', font=get_font(140,True), fill=pt_rgb)
        draw.rectangle([(W//2-80,int(H*0.72)),(W//2+80,int(H*0.72)+3)], fill=pt_rgb)
        draw_text_center(draw, sub or "- 오늘의 한마디", int(H*0.75), get_font(32), txt_rgb, W, W-200)
        draw.text((W-120,H-60), "9/10", font=get_font(28), fill=pt_rgb)

    # ══════════════════════════
    # 10장: CTA
    # ══════════════════════════
    elif card_num == 10:
        img = make_base(bg_image, bg_rgb)
        img = add_overlay(img, 0, 0, W, H, bg_rgb, alpha=190)
        draw = ImageDraw.Draw(img)
        draw_text_center(draw, title or "도움이 되셨나요? 😊", 100, get_font(52,True), txt_rgb, W, W-100)
        draw.rectangle([(W//2-100,190),(W//2+100,196)], fill=pt_rgb)
        buttons = ["💾 저장하기","👥 팔로우","💬 댓글 남기기"]
        for i,btn in enumerate(buttons):
            by = 240 + i*180
            draw.rounded_rectangle([(140,by),(W-140,by+90)], radius=45, fill=pt_rgb)
            draw_text_center(draw, btn, by+22, get_font(40,True), white, W, W-200)
        draw_text_center(draw, sub or "@hanasence", int(H*0.88), get_font(42,True), pt_rgb, W, W-100)
        draw.text((W-120,H-60), "10/10", font=get_font(28), fill=pt_rgb)

    else:
        img = make_base(bg_image, bg_rgb)

    return img.convert('RGB')

def img_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

def create_zip(images):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf,'w') as zf:
        for i,img in enumerate(images):
            zf.writestr(f"card_{i+1:02d}.png", img_to_bytes(img))
    return buf.getvalue()
    # ─────────────────────────────────────────
# 🎛️ 사이드바
# ─────────────────────────────────────────
st.title("🚀 원클릭 SNS 콘텐츠 마스터")
st.caption("URL 또는 원본 글 → 10장 카드뉴스 + 모든 플랫폼 콘텐츠 자동 생성")

st.sidebar.header("⚙️ 설정")
api_key = st.sidebar.text_input("Gemini API Key", type="password")
st.sidebar.markdown("[API 키 발급](https://aistudio.google.com/app/apikey)")

st.sidebar.markdown("---")
st.sidebar.header("🎨 템플릿 세트 선택")
selected_set = st.sidebar.selectbox("템플릿 스타일", list(TEMPLATE_SETS.keys()))

colors = TEMPLATE_SETS[selected_set]
st.sidebar.markdown(f"""
<div style='display:flex;gap:8px;margin-top:8px'>
  <div style='width:30px;height:30px;background:{colors["bg"]};border:1px solid #ccc;border-radius:4px'></div>
  <div style='width:30px;height:30px;background:{colors["text"]};border:1px solid #ccc;border-radius:4px'></div>
  <div style='width:30px;height:30px;background:{colors["point"]};border-radius:4px'></div>
</div>
<small>배경 / 텍스트 / 포인트</small>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.header("🖼️ 배경 이미지 업로드 (선택)")
st.sidebar.caption("1장만 올려도 10장 전부 적용!")
bg_file = st.sidebar.file_uploader(
    "배경 이미지 (1장)",
    type=['png','jpg','jpeg'],
    accept_multiple_files=False
)

bg_image = None
if bg_file:
    try:
        bg_image = Image.open(bg_file).convert('RGB').resize((1080,1080), Image.LANCZOS)
        st.sidebar.image(bg_image, caption="업로드된 배경", use_column_width=True)
        st.sidebar.success("✅ 배경 이미지 적용!")
    except Exception as e:
        st.sidebar.error(f"이미지 오류: {e}")

st.sidebar.markdown("---")
st.sidebar.header("📱 추가 생성 옵션")
gen_shorts   = st.sidebar.checkbox("🎬 쇼츠/릴스 대본", value=True)
gen_captions = st.sidebar.checkbox("📱 플랫폼별 캡션", value=True)
gen_threads  = st.sidebar.checkbox("🧵 스레드 타래",   value=False)
gen_blog     = st.sidebar.checkbox("📝 블로그 요약",   value=False)

# ─────────────────────────────────────────
# 🌐 크롤링
# ─────────────────────────────────────────
def crawl_url(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'lxml')
        if 'blog.naver.com' in url:
            iframe = soup.find('iframe', id='mainFrame')
            if iframe:
                iframe_url = 'https://blog.naver.com' + iframe['src']
                response = requests.get(iframe_url, headers=headers, timeout=15)
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'lxml')
        for tag in soup(["script","style","nav","footer","header","aside","form","button"]):
            tag.decompose()
        content = ""
        for tag_name, cls in [
            ('div','post-body'),('div','entry-content'),
            ('div','article_view'),('div','se-main-container'),
            ('div','wrap_body'),
        ]:
            el = soup.find(tag_name, class_=cls)
            if el:
                content = el.get_text(separator='\n', strip=True)
                if len(content) > 200: break
        if not content or len(content) < 200:
            for tag_name in ['article','main']:
                el = soup.find(tag_name)
                if el:
                    content = el.get_text(separator='\n', strip=True)
                    if len(content) > 200: break
        if not content or len(content) < 200:
            longest = ""
            for div in soup.find_all('div'):
                t = div.get_text(separator='\n', strip=True)
                if len(t) > len(longest): longest = t
            content = longest
        lines = [l.strip() for l in content.split('\n') if l.strip() and len(l.strip()) > 2]
        return '\n'.join(lines)[:15000] or None
    except:
        return None

# ─────────────────────────────────────────
# 🔍 파싱
# ─────────────────────────────────────────
def parse_cards(text):
    patterns = [
        r'===CARD===(.*?)===END===',
        r'===\s*CARD\s*===(.*?)===\s*END\s*===',
    ]
    cards = []
    for p in patterns:
        cards = re.findall(p, text, re.DOTALL)
        if cards: break
    card_data = []
    for card in cards:
        def extract(field):
            m = re.search(rf'{field}:\s*(.*?)(?=\n\w+:|$)', card, re.DOTALL)
            if m:
                r = m.group(1).strip()
                r = re.sub(r'\*\*(.*?)\*\*', r'\1', r)
                return r.replace('\n',' ').strip()
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
            "캡처유도": extract('캡처유도'),
        })
    return card_data

def parse_section(text, section_name):
    patterns = [
        rf'===SECTION_{section_name}===(.*?)(?====SECTION_|$)',
        rf'SECTION_{section_name}\s*(.*?)(?=SECTION_[A-Z]|$)',
    ]
    for p in patterns:
        m = re.search(p, text, re.DOTALL)
        if m:
            content = m.group(1).strip()
            if content and len(content) > 20:
                return re.sub(r'^={3,}\s*', '', content, flags=re.MULTILINE)
    return None

# ─────────────────────────────────────────
# 📝 입력 UI
# ─────────────────────────────────────────
st.markdown("### 📥 콘텐츠 입력")
input_mode = st.radio(
    "입력 방식",
    ["🔗 URL 입력 (자동 크롤링)", "📝 원본 글 직접 입력"],
    horizontal=True
)
source_text = ""
if input_mode == "🔗 URL 입력 (자동 크롤링)":
    url = st.text_input("블로그 URL", placeholder="티스토리, 블로그스팟, 브런치 등")
    if url and st.button("🔍 내용 가져오기"):
        with st.spinner("크롤링 중..."):
            crawled = crawl_url(url)
            if crawled and len(crawled) > 200:
                st.session_state['crawled_text'] = crawled
                st.success(f"✅ 완료! ({len(crawled)}자)")
            else:
                st.error("❌ 실패. 직접 붙여넣어주세요.")
    source_text = st.text_area(
        "📝 내용 (수정 가능)",
        value=st.session_state.get('crawled_text',''),
        height=200
    )
else:
    source_text = st.text_area("📝 원본 글 붙여넣기", height=200)

st.markdown("### 🎯 콘텐츠 정보")
col1, col2 = st.columns(2)
with col1:
    target_audience = st.text_input("타깃 독자", placeholder="예: 30대 직장인")
with col2:
    brand_name = st.text_input("브랜드/계정명", placeholder="예: @hanasence")
custom_note = st.text_input("💡 특별 요청 (선택)")

st.markdown("---")

# ─────────────────────────────────────────
# 🚀 생성 버튼
# ─────────────────────────────────────────
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
                target = target_audience or "일반 독자"
                brand  = brand_name or "@브랜드"
                extra  = f"\n특별요청: {custom_note}" if custom_note else ""

                extra_sections = ""
                if gen_shorts:
                    extra_sections += """
===SECTION_SHORTS===
[60초 쇼츠 대본]
원칙: 쇼츠만 봐도 완성된 정보 제공. 구체적 방법/조건/기한/금액 포함.
구조: 0-5초 후킹 / 5-10초 문제 / 10-50초 핵심정보(구체적) / 50-60초 저장유도
화면연출+자막+내레이션 모두 포함
"""
                if gen_captions:
                    extra_sections += "\n===SECTION_CAPTIONS===\n인스타/페북/튤립/클립 캡션 (해시태그 15개)\n"
                if gen_threads:
                    extra_sections += "\n===SECTION_THREADS===\n스레드 타래 5~7개\n"
                if gen_blog:
                    extra_sections += "\n===SECTION_BLOG===\n블로그 요약 3~5줄\n"

                prompt = f"""당신은 프로 카드뉴스 기획자입니다.

⚠️ 절대 규칙:
1. 마크다운 (##, **, ---) 절대 사용 금지
2. 반드시 ===SECTION_CARDS=== 로 시작
3. 각 카드는 ===CARD=== 로 시작, ===END=== 로 끝
4. 반드시 10장 모두 완성
5. 각 필드 값은 한 줄로

[기본 정보]
타깃: {target}
브랜드: {brand}
{extra}

[10장 구조]
1장 표지 / 2장 문제제기(카톡스타일) / 3장 원인분석(A vs B)
4장 로드맵(타임라인) / 5장 솔루션1 / 6장 솔루션2 / 7장 솔루션3
8장 요약(체크리스트,저장유도) / 9장 클로징(감성명언) / 10장 CTA({brand})

[각 장 본문 작성 규칙]
- 4장 본문: 단계를 /로 구분 (예: 확인/신청/접수/완료)
- 8장 본문: 핵심 포인트를 /로 구분 (예: 첫번째팁/두번째팁/세번째팁)
- 10장 부제목: 브랜드 계정명

===SECTION_CARDS===

===CARD===
번호: 1
역할: 표지
큰제목: (임팩트 있는 한 줄)
부제목: (설명 한 줄)
본문: (핵심 메시지)
시각스타일: (디자인 방향)
이미지프롬프트: (영어로 이미지 설명)
디자인가이드: (배치 가이드)
캡처유도: (저장/공유 유도 문구)
===END===

(2~10장 동일 형식으로 반드시 완성)

{extra_sections}

원본글:
{source_text[:8000]}
"""
                response = model.generate_content(prompt)
                result = response.text
                st.session_state['result'] = result
                st.session_state['card_data'] = parse_cards(result)
                st.success("✅ 생성 완료!")

        except Exception as e:
            st.error(f"❌ 오류: {str(e)}")

# ─────────────────────────────────────────
# 📊 결과 표시
# ─────────────────────────────────────────
if 'result' in st.session_state and st.session_state['result']:
    result    = st.session_state['result']
    card_data = st.session_state.get('card_data',[])

    with st.expander("🔍 AI 원본 응답 (디버깅용)"):
        st.text(result)

    st.markdown("---")

    tab_names = ["🎴 카드뉴스"]
    if gen_shorts:   tab_names.append("🎬 쇼츠")
    if gen_captions: tab_names.append("📱 캡션")
    if gen_threads:  tab_names.append("🧵 스레드")
    if gen_blog:     tab_names.append("📝 블로그")

    tabs = st.tabs(tab_names)
    tab_idx = 0

    with tabs[tab_idx]:
        if card_data:
            st.success(f"✅ 총 {len(card_data)}장 생성 완료!")
            st.info(f"🎨 선택된 템플릿: **{selected_set}**")
            if bg_image:
                st.info("🖼️ 배경 이미지 적용됨!")

            df = pd.DataFrame(card_data)
            col_a, col_b = st.columns([3,1])
            with col_a:
                st.info("💡 CSV를 Canva 대량 제작에 업로드!")
            with col_b:
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "📥 CSV 다운로드", csv,
                    'cardnews.csv', 'text/csv',
                    use_container_width=True
                )

            st.markdown("---")

            if st.button("🖼️ 카드 이미지 생성하기", type="primary", use_container_width=True):
                with st.spinner("10장 이미지 생성 중..."):
                    imgs = []
                    prog = st.progress(0)
                    for i, card in enumerate(card_data[:10]):
                        try:
                            img = create_card(i+1, card, selected_set, bg_image)
                            imgs.append(img)
                        except Exception as e:
                            st.warning(f"{i+1}장 오류: {e}")
                            imgs.append(Image.new('RGB',(1080,1080),
                                       hex_to_rgb(TEMPLATE_SETS[selected_set]["bg"])))
                        prog.progress((i+1)/10)
                    st.session_state['generated_images'] = imgs
                st.success("✅ 이미지 생성 완료!")

            if 'generated_images' in st.session_state:
                imgs = st.session_state['generated_images']

                st.download_button(
                    "📦 전체 ZIP 다운로드 (10장)",
                    create_zip(imgs),
                    'cardnews.zip', 'application/zip',
                    type="primary", use_container_width=True
                )

                st.markdown("---")
                st.subheader("🖼️ 카드 미리보기 + 수정 + 개별 다운로드")

                for i in range(0, len(imgs), 2):
                    cols = st.columns(2)
                    for j, col in enumerate(cols):
                        idx = i + j
                        if idx < len(imgs):
                            img  = imgs[idx]
                            card = card_data[idx] if idx < len(card_data) else {}
                            with col:
                                st.image(img,
                                        caption=f"{idx+1}장 - {card.get('역할','')}",
                                        use_column_width=True)

                                with st.expander(f"✏️ {idx+1}장 수정"):
                                    new_title = st.text_input(
                                        "큰제목",
                                        value=card.get('큰제목',''),
                                        key=f"t_{idx}"
                                    )
                                    new_sub = st.text_input(
                                        "부제목",
                                        value=card.get('부제목',''),
                                        key=f"s_{idx}"
                                    )
                                    new_body = st.text_input(
                                        "본문",
                                        value=card.get('본문',''),
                                        key=f"b_{idx}"
                                    )
                                    if st.button(f"🔄 {idx+1}장 재생성", key=f"r_{idx}"):
                                        updated = card.copy()
                                        updated['큰제목'] = new_title
                                        updated['부제목'] = new_sub
                                        updated['본문']   = new_body
                                        try:
                                            new_img = create_card(idx+1, updated, selected_set, bg_image)
                                            imgs[idx] = new_img
                                            st.session_state['generated_images'] = imgs
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"재생성 오류: {e}")

                                st.download_button(
                                    f"📥 {idx+1}장 다운로드",
                                    img_to_bytes(img),
                                    f"card_{idx+1:02d}.png",
                                    "image/png",
                                    key=f"dl_{idx}",
                                    use_container_width=True
                                )

            st.markdown("---")
            st.subheader("📝 카드별 텍스트")
            icon_map = {
                "표지":"🎯","문제제기":"💬","문제 제기":"💬",
                "원인분석":"📊","원인 분석":"📊","로드맵":"🗺️",
                "솔루션1":"💡","솔루션2":"💡","솔루션3":"💡",
                "요약":"✅","클로징":"🌿","CTA":"👉"
            }
            for card in card_data:
                icon  = icon_map.get(card['역할'],"🎴")
                title = card['큰제목'][:40] if card['큰제목'] else "제목없음"
                with st.expander(f"{icon} [{card['번호']}장 - {card['역할']}] {title}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**📝 콘텐츠**")
                        if card['큰제목']: st.write(f"큰제목: {card['큰제목']}")
                        if card['부제목']: st.write(f"부제목: {card['부제목']}")
                        if card['본문']:   st.write(f"본문: {card['본문']}")
                    with c2:
                        st.markdown("**🎨 디자인**")
                        if card['시각스타일']:   st.info(card['시각스타일'])
                        if card['디자인가이드']: st.success(card['디자인가이드'])
                        if card['캡처유도']:     st.warning(f"📸 {card['캡처유도']}")
                    if card['이미지프롬프트']:
                        st.code(card['이미지프롬프트'])

            st.dataframe(df, use_container_width=True, height=400)

        else:
            st.error("❌ 카드 파싱 실패")
            st.info("💡 AI 원본 응답을 열어서 확인해주세요")

    tab_idx += 1

    if gen_shorts:
        with tabs[tab_idx]:
            st.subheader("🎬 쇼츠/릴스 대본")
            st.info("💡 Vrew, CapCut에 붙여넣어 사용!")
            content = parse_section(result,'SHORTS')
            if content: st.markdown(content)
            else: st.warning("쇼츠 대본을 찾지 못했습니다.")
        tab_idx += 1

    if gen_captions:
        with tabs[tab_idx]:
            st.subheader("📱 플랫폼별 캡션")
            content = parse_section(result,'CAPTIONS')
            if content: st.markdown(content)
            else: st.warning("캡션을 찾지 못했습니다.")
        tab_idx += 1

    if gen_threads:
        with tabs[tab_idx]:
            st.subheader("🧵 스레드 타래")
            content = parse_section(result,'THREADS')
            if content: st.markdown(content)
        tab_idx += 1

    if gen_blog:
        with tabs[tab_idx]:
            st.subheader("📝 블로그 요약")
            content = parse_section(result,'BLOG')
            if content: st.markdown(content)

st.markdown("---")
with st.expander("📖 사용 가이드"):
    st.markdown("""
    ### 🚀 사용법
    1. **API Key** 입력 (사이드바)
    2. **템플릿 세트** 선택 (A~D)
    3. **배경 이미지** 업로드 (선택, 1장만!)
    4. **URL 또는 원본 글** 입력
    5. **타깃/브랜드** 입력
    6. **생성하기** 클릭
    7. **카드 이미지 생성하기** 클릭
    8. **수정** 후 **다운로드**!

    ### 🎨 각 장 레이아웃
    | 장 | 레이아웃 |
    |----|---------|
    | 1장 | 배경+하단 제목 (1:9) |
    | 2장 | 카톡 말풍선 스타일 |
    | 3장 | 좌우 대칭 A vs B |
    | 4장 | 타임라인 |
    | 5~7장 | 상단60% 이미지+하단 텍스트 |
    | 8장 | 체크리스트 (저장 유도) |
    | 9장 | 감성 여백+명언 |
    | 10장 | CTA 버튼 |

    ### 📦 다운로드
    - 개별: 각 카드 아래 버튼
    - 전체: ZIP 다운로드
    """)
