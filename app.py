import streamlit as st
import google.generativeai as genai
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import zipfile

st.set_page_config(page_title="원클릭 SNS 콘텐츠 마스터", layout="wide", page_icon="🚀")

# ─────────────────────────────────────────
# 🎨 템플릿 세트 정의
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

def get_font(size, bold=False):
    try:
        path = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf" if bold else "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

def wrap_text(text, font, max_width, draw):
    lines, current = [], ""
    for char in text:
        test = current + char
        if draw.textbbox((0,0), test, font=font)[2] > max_width:
            if current:
                lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines

def draw_text_centered(draw, text, y, font, color, W, max_w, line_gap=8):
    lines = wrap_text(text, font, max_w, draw)
    for i, line in enumerate(lines):
        bb = draw.textbbox((0,0), line, font=font)
        x = (W - (bb[2]-bb[0])) / 2
        draw.text((x, y + i*(bb[3]-bb[1]+line_gap)), line, font=font, fill=color)
    return lines

def draw_text_left(draw, text, x, y, font, color, max_w, line_gap=8):
    lines = wrap_text(text, font, max_w, draw)
    for i, line in enumerate(lines):
        bb = draw.textbbox((0,0), line, font=font)
        draw.text((x, y + i*(bb[3]-bb[1]+line_gap)), line, font=font, fill=color)
    return lines

def add_overlay(img, x1, y1, x2, y2, color_rgb, alpha=180):
    overlay = Image.new('RGBA', img.size, (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    d.rectangle([x1, y1, x2, y2], fill=(*color_rgb, alpha))
    return Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')

def add_rounded_box(draw, x1, y1, x2, y2, fill_rgb, alpha=200, radius=20):
    overlay = Image.new('RGBA', (1080,1080), (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    d.rounded_rectangle([x1,y1,x2,y2], radius=radius, fill=(*fill_rgb, alpha))
    return overlay

# ─────────────────────────────────────────
# 🖼️ 10장 각각 최적 구도 카드 생성
# ─────────────────────────────────────────
def create_card_image(card_num, card, template_set, bg_image=None):
    W, H = 1080, 1080
    colors = TEMPLATE_SETS[template_set]
    bg_rgb   = hex_to_rgb(colors["bg"])
    txt_rgb  = hex_to_rgb(colors["text"])
    pt_rgb   = hex_to_rgb(colors["point"])
    sub_rgb  = hex_to_rgb(colors["sub_bg"])

    title = card.get("큰제목", "")
    sub   = card.get("부제목", "")
    body  = card.get("본문", "")

    # 배경 이미지 or 단색
    if bg_image:
        base = bg_image.copy().resize((W, H)).convert('RGB')
    else:
        base = Image.new('RGB', (W, H), bg_rgb)

    # ════════════════════════════════
    # 1장: 표지 (1:9 법칙)
    # ════════════════════════════════
    if card_num == 1:
        img = base.copy()
        # 하단 45% 반투명 오버레이
        img = add_overlay(img, 0, int(H*0.55), W, H, bg_rgb, alpha=210)
        draw = ImageDraw.Draw(img)
        # 포인트 라인
        draw.rectangle([(80, int(H*0.57)), (200, int(H*0.57)+6)], fill=pt_rgb)
        # 큰 제목
        f_title = get_font(80, bold=True)
        draw_text_centered(draw, title, int(H*0.60), f_title, txt_rgb, W, W-120)
        # 부제목
        f_sub = get_font(36)
        draw_text_centered(draw, sub, int(H*0.78), f_sub, pt_rgb, W, W-160)
        # 카드 번호
        f_num = get_font(26)
        draw.text((W-80, H-50), "1/10", font=f_num, fill=pt_rgb)

    # ════════════════════════════════
    # 2장: 문제제기 (카톡 스타일)
    # ════════════════════════════════
    elif card_num == 2:
        img = Image.new('RGB', (W, H), (254, 229, 0))  # 카톡 노란 배경
        draw = ImageDraw.Draw(img)
        # 상단 헤더
        draw.rectangle([(0,0),(W,100)], fill=(230,207,0))
        f_header = get_font(36, bold=True)
        draw_text_centered(draw, "💬 " + (sub or "많이들 물어보시는 질문"), 32, f_header, (50,50,50), W, W-80)
        # 말풍선들
        bubbles = [
            (60,  140, title or "이거 저도 해당되나요?", False),
            (300, 300, body or "저도 궁금했어요!", False),
            (60,  460, "저는 잘 몰라서요 ㅠㅠ", False),
            (250, 600, "저도요! 알려주세요!", False),
        ]
        for bx, by, btxt, is_right in bubbles:
            f_b = get_font(34)
            bb = draw.textbbox((0,0), btxt, font=f_b)
            bw = min(bb[2]-bb[0]+50, W-120)
            bh = bb[3]-bb[1]+36
            if is_right:
                bx = W - bw - 60
            draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=22, fill="white")
            draw.text((bx+25, by+18), btxt, font=f_b, fill="#333333")
        # 하단 시간
        f_time = get_font(28)
        draw.text((40, H-70), "오후 3:45", font=f_time, fill="#888888")
        draw.text((W-80, H-50), "2/10", font=get_font(26), fill="#888888")

    # ════════════════════════════════
    # 3장: 원인분석 (A vs B 좌우 대칭)
    # ════════════════════════════════
    elif card_num == 3:
        img = Image.new('RGB', (W, H), bg_rgb)
        draw = ImageDraw.Draw(img)
        # 좌측 (❌ 부정)
        draw.rectangle([(0,0),(W//2, H)], fill=hex_to_rgb("#F0F0F0"))
        # 우측 (✅ 긍정)
        draw.rectangle([(W//2,0),(W, H)], fill=pt_rgb)
        # 중앙 구분선
        draw.rectangle([(W//2-3,0),(W//2+3,H)], fill="#FFFFFF")
        # 중앙 VS 원
        draw.ellipse([(W//2-45, H//2-45),(W//2+45, H//2+45)], fill="white")
        f_vs = get_font(40, bold=True)
        draw.text((W//2-25, H//2-25), "VS", font=f_vs, fill=pt_rgb)
        # 상단 제목
        f_title = get_font(52, bold=True)
        draw_text_centered(draw, title or "이런 차이가 있어요!", 60, f_title, txt_rgb, W, W-80)
        # 좌측 텍스트
        f_side = get_font(44, bold=True)
        draw.text((W//4-80, int(H*0.25)), "❌", font=get_font(60), fill="#FF4444")
        f_content = get_font(34)
        left_text = sub or "모르는 사람"
        draw_text_centered(draw, left_text, int(H*0.40), f_content, hex_to_rgb("#555555"), W//2, W//2-60)
        # 우측 텍스트
        draw.text((W//4*3-40, int(H*0.25)), "✅", font=get_font(60), fill="#FFFFFF")
        right_text = body or "아는 사람"
        draw_text_centered(draw, right_text, int(H*0.40), f_content, hex_to_rgb("#FFFFFF"), W, W//2-60)
        # 하단
        f_bottom = get_font(36, bold=True)
        draw_text_centered(draw, "당신은 어느 쪽인가요?", int(H*0.88), f_bottom, txt_rgb, W, W-80)
        draw.text((W-80, H-50), "3/10", font=get_font(26), fill=pt_rgb)

    # ════════════════════════════════
    # 4장: 로드맵 (타임라인)
    # ════════════════════════════════
    elif card_num == 4:
        img = base.copy()
        img = add_overlay(img, 0, 0, W, H, bg_rgb, alpha=200)
        draw = ImageDraw.Draw(img)
        # 제목
        f_title = get_font(64, bold=True)
        draw_text_centered(draw, title or "전체 흐름 한눈에!", 80, f_title, txt_rgb, W, W-80)
        # 포인트 언더라인
        draw.rectangle([(W//2-100, 160),(W//2+100, 166)], fill=pt_rgb)
        # 타임라인 노드
        steps = (body or "확인/신청/접수/완료").split('/')
        steps = steps[:4] if len(steps) >= 4 else steps + ["완료"]*(4-len(steps))
        node_y = int(H * 0.50)
        node_xs = [200, 420, 660, 880]
        # 연결선
        draw.line([(node_xs[0], node_y), (node_xs[-1], node_y)], fill=pt_rgb, width=6)
        for i, (nx, step) in enumerate(zip(node_xs, steps)):
            # 노드 원
            draw.ellipse([(nx-45, node_y-45),(nx+45, node_y+45)], fill=pt_rgb)
            draw.ellipse([(nx-35, node_y-35),(nx+35, node_y+35)], fill="white")
            # 번호
            f_node = get_font(40, bold=True)
            num_str = str(i+1)
            bb = draw.textbbox((0,0), num_str, font=f_node)
            draw.text((nx-(bb[2]-bb[0])//2, node_y-(bb[3]-bb[1])//2), num_str, font=f_node, fill=pt_rgb)
            # 단계명
            f_step = get_font(32)
            draw_text_centered(draw, step.strip(), node_y+60, f_step, txt_rgb, nx*2 if i==0 else W, 180)
        # 하단 설명
        f_sub = get_font(36)
        draw_text_centered(draw, sub or "이제 하나씩 알려드릴게요!", int(H*0.78), f_sub, pt_rgb, W, W-120)
        draw.text((W-80, H-50), "4/10", font=get_font(26), fill=pt_rgb)

    # ════════════════════════════════
    # 5~7장: 솔루션 (이미지60% + 텍스트40%)
    # ════════════════════════════════
    elif card_num in [5, 6, 7]:
        num_map = {5: ("①", "5"), 6: ("②", "6"), 7: ("③", "7")}
        sol_num, page_num = num_map[card_num]
        img = base.copy()
        # 하단 40% 흰색 박스
        img = add_overlay(img, 0, int(H*0.58), W, H, hex_to_rgb(colors["sub_bg"]), alpha=240)
        draw = ImageDraw.Draw(img)
        # 포인트 라인 (이미지/텍스트 경계)
        draw.rectangle([(0, int(H*0.58)),(W, int(H*0.58)+6)], fill=pt_rgb)
        # 솔루션 번호 (크게)
        f_num_big = get_font(100, bold=True)
        draw.text((60, int(H*0.58)+20), sol_num, font=f_num_big, fill=pt_rgb)
        # 제목
        f_title = get_font(56, bold=True)
        draw_text_left(draw, title or f"솔루션 {sol_num}", 180, int(H*0.62), f_title, txt_rgb, W-220)
        # 본문
        f_body = get_font(34)
        draw_text_left(draw, body or "구체적인 방법을 알려드릴게요.", 60, int(H*0.78), f_body, txt_rgb, W-120)
        # 부제목
        f_sub = get_font(30)
        draw_text_left(draw, sub or "", 60, int(H*0.88), f_sub, pt_rgb, W-120)
        draw.text((W-80, H-50), f"{page_num}/10", font=get_font(26), fill=pt_rgb)

    # ════════════════════════════════
    # 8장: 요약 (체크리스트) ⭐
    # ════════════════════════════════
    elif card_num == 8:
        # 배경 흐리게
        if bg_image:
            blurred = base.copy().filter(ImageFilter.GaussianBlur(radius=8))
        else:
            blurred = Image.new('RGB', (W,H), sub_rgb)
        img = blurred
        # 중앙 흰색 박스
        overlay = add_rounded_box(None, 60, 80, W-60, H-80, hex_to_rgb(colors["sub_bg"]), alpha=230, radius=30)
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        # 상단 제목
        f_title = get_font(60, bold=True)
        draw_text_centered(draw, "📌 " + (title or "지금까지 정리!"), 120, f_title, txt_rgb, W, W-120)
        # 구분선
        draw.rectangle([(120, 210),(W-120, 216)], fill=pt_rgb)
        # 체크리스트
        items = body.split('/') if '/' in body else body.split('.')
        items = [x.strip() for x in items if x.strip()][:4]
        if not items:
            items = ["첫 번째 핵심 정보", "두 번째 핵심 정보", "세 번째 핵심 정보"]
        f_check = get_font(38, bold=True)
        f_check_body = get_font(30)
        for i, item in enumerate(items):
            y_item = 260 + i * 150
            # 체크박스
            draw.rounded_rectangle([(80, y_item),(130, y_item+50)], radius=8, fill=pt_rgb)
            f_ck = get_font(32, bold=True)
            draw.text((90, y_item+8), "✓", font=f_ck, fill="white")
            # 항목
            draw_text_left(draw, item, 150, y_item, f_check, txt_rgb, W-200)
        # 저장 유도 (핵심!)
        draw.rectangle([(80, int(H*0.83)),(W-80, int(H*0.83)+4)], fill=pt_rgb)
        f_save = get_font(38, bold=True)
        draw_text_centered(draw, "💾 저장하고 두고두고 봐요!", int(H*0.86), f_save, pt_rgb, W, W-100)
        draw.text((W-80, H-50), "8/10", font=get_font(26), fill=pt_rgb)

    # ════════════════════════════════
    # 9장: 클로징 (킨포크 감성)
    # ════════════════════════════════
    elif card_num == 9:
        img = base.copy()
        # 전체 반투명 오버레이 (감성)
        img = add_overlay(img, 0, 0, W, H, bg_rgb, alpha=160)
        draw = ImageDraw.Draw(img)
        # 상단 포인트 라인
        draw.rectangle([(W//2-60, 120),(W//2+60, 126)], fill=pt_rgb)
        # 명언 (큰 따옴표)
        f_quote = get_font(120, bold=True)
        draw.text((80, int(H*0.25)), '"', font=f_quote, fill=pt_rgb)
        # 명언 텍스트
        f_title = get_font(52, bold=True)
        draw_text_centered(draw, title or "작은 정보 하나가\n큰 변화를 만듭니다", int(H*0.38), f_title, txt_rgb, W, W-160)
        # 닫는 따옴표
        draw.text((W-120, int(H*0.62)), '"', font=f_quote, fill=pt_rgb)
        # 출처
        draw.rectangle([(W//2-80, int(H*0.72)),(W//2+80, int(H*0.72)+3)], fill=pt_rgb)
        f_source = get_font(32)
        draw_text_centered(draw, sub or "- 오늘의 한마디", int(H*0.75), f_source, txt_rgb, W, W-200)
        draw.text((W-80, H-50), "9/10", font=get_font(26), fill=pt_rgb)

    # ════════════════════════════════
    # 10장: CTA (행동 유도)
    # ════════════════════════════════
    elif card_num == 10:
        img = base.copy()
        img = add_overlay(img, 0, 0, W, H, bg_rgb, alpha=180)
        draw = ImageDraw.Draw(img)
        # 상단 질문
        f_q = get_font(52, bold=True)
        draw_text_centered(draw, title or "도움이 되셨나요? 😊", 120, f_q, txt_rgb, W, W-100)
        # 포인트 라인
        draw.rectangle([(W//2-100,210),(W//2+100,216)], fill=pt_rgb)
        # CTA 버튼 3개
        buttons = [
            ("💾 저장하기", int(H*0.35)),
            ("👥 팔로우", int(H*0.52)),
            ("💬 댓글 남기기", int(H*0.69)),
        ]
        for btn_text, btn_y in buttons:
            # 버튼 박스
            draw.rounded_rectangle(
                [(160, btn_y),(W-160, btn_y+80)],
                radius=40, fill=pt_rgb
            )
            f_btn = get_font(40, bold=True)
            draw_text_centered(draw, btn_text, btn_y+20, f_btn, hex_to_rgb("#FFFFFF"), W, W-200)
        # 계정명
        f_brand = get_font(40, bold=True)
        brand = card.get("부제목", "@hanasence")
        draw_text_centered(draw, brand, int(H*0.88), f_brand, pt_rgb, W, W-100)
        draw.text((W-80, H-50), "10/10", font=get_font(26), fill=pt_rgb)

    else:
        img = base.copy()

    return img

def img_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

def create_zip(images):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        for i, img in enumerate(images):
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
st.sidebar.caption("1장만 올려도 10장 전부 적용! 각 장마다 다른 레이아웃 자동 적용")
bg_file = st.sidebar.file_uploader(
    "배경 이미지 (1장)",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=False
)

bg_image = None
if bg_file:
    bg_image = Image.open(bg_file).convert('RGB').resize((1080, 1080))
    st.sidebar.image(bg_image, caption="업로드된 배경 이미지", use_column_width=True)
    st.sidebar.success("✅ 배경 이미지 적용됨!")

st.sidebar.markdown("---")
st.sidebar.header("📱 추가 생성 옵션")
gen_shorts = st.sidebar.checkbox("🎬 쇼츠/릴스 대본", value=True)
gen_captions = st.sidebar.checkbox("📱 플랫폼별 캡션", value=True)
gen_threads = st.sidebar.checkbox("🧵 스레드 타래", value=False)
gen_blog = st.sidebar.checkbox("📝 블로그 요약", value=False)

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
            ('div', 'post-body'), ('div', 'entry-content'),
            ('div', 'article_view'), ('div', 'se-main-container'),
            ('div', 'wrap_body'),
        ]:
            el = soup.find(tag_name, class_=cls)
            if el:
                content = el.get_text(separator='\n', strip=True)
                if len(content) > 200:
                    break
        if not content or len(content) < 200:
            for tag_name in ['article', 'main']:
                el = soup.find(tag_name)
                if el:
                    content = el.get_text(separator='\n', strip=True)
                    if len(content) > 200:
                        break
        if not content or len(content) < 200:
            longest = ""
            for div in soup.find_all('div'):
                t = div.get_text(separator='\n', strip=True)
                if len(t) > len(longest):
                    longest = t
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
        if cards:
            break
    card_data = []
    for card in cards:
        def extract(field):
            m = re.search(rf'{field}:\s*(.*?)(?=\n\w+:|$)', card, re.DOTALL)
            if m:
                r = m.group(1).strip()
                r = re.sub(r'\*\*(.*?)\*\*', r'\1', r)
                return r.replace('\n', ' ').strip()
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
    source_text = st.text_area("📝 내용 (수정 가능)",
                               value=st.session_state.get('crawled_text', ''), height=200)
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
8장 요약(체크리스트, 저장유도) / 9장 클로징(감성명언) / 10장 CTA({brand})

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
    card_data = st.session_state.get('card_data', [])

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
                st.info("🖼️ 업로드된 배경 이미지 적용됨!")

            df = pd.DataFrame(card_data)
            col_a, col_b = st.columns([3,1])
            with col_a:
                st.info("💡 CSV를 Canva 대량 제작에 업로드!")
            with col_b:
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 CSV 다운로드", csv,
                                  'cardnews.csv', 'text/csv',
                                  use_container_width=True)

            st.markdown("---")

            if st.button("🖼️ 카드 이미지 생성하기", type="primary", use_container_width=True):
                with st.spinner("10장 이미지 생성 중..."):
                    imgs = []
                    prog = st.progress(0)
                    for i, card in enumerate(card_data[:10]):
                        img = create_card_image(i+1, card, selected_set, bg_image)
                        imgs.append(img)
                        prog.progress((i+1)/10)
                    st.session_state['generated_images'] = imgs
                st.success("✅ 이미지 생성 완료!")

            if 'generated_images' in st.session_state:
                imgs = st.session_state['generated_images']

                # ZIP 다운로드
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
                                    new_title = st.text_input("큰제목", value=card.get('큰제목',''), key=f"t_{idx}")
                                    new_sub   = st.text_input("부제목", value=card.get('부제목',''), key=f"s_{idx}")
                                    new_body  = st.text_input("본문",   value=card.get('본문',''),   key=f"b_{idx}")

                                    if st.button(f"🔄 {idx+1}장 재생성", key=f"r_{idx}"):
                                        updated = card.copy()
                                        updated['큰제목'] = new_title
                                        updated['부제목'] = new_sub
                                        updated['본문']   = new_body
                                        new_img = create_card_image(idx+1, updated, selected_set, bg_image)
                                        imgs[idx] = new_img
                                        st.session_state['generated_images'] = imgs
                                        st.rerun()

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
                icon  = icon_map.get(card['역할'], "🎴")
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
with st.expander("📖 사용 가이드"):
    st.markdown("""
    ### 🚀 사용법
    1. **API Key** 입력 (사이드바)
    2. **템플릿 세트** 선택 (A~D)
    3. **배경 이미지** 업로드 (선택, 1장만 올려도 10장 적용!)
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
