import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
import datetime
import json
import os
import time
from streamlit_autorefresh import st_autorefresh

# [#] 저장용 파일 경로
SAVE_FILE = "moneydock_data.json"

# [#] 한국 표준시(KST)를 계산하는 함수 (에러 방지를 위해 Naive 방식으로 처리)
def get_now_kst():
    # 서버 시간(UTC)에 9시간을 더해서 순수한 한국 시간으로 반환합니더.
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)

# [#] 데이터 불러오기 함수
def load_data():
    defaults = {
        "queue": [], 
        "last_gen_time": None,
        "gen_interval_min": 60,
        "selected_model": "models/gemini-1.5-flash",
        "topic_input": "비트코인 실시간 시황 요약해줘",
        "char_range": [50, 150],
        "post_style": "친절한 이웃",
        "target_days": ["월", "화", "수", "목", "금", "토", "일"],
        "start_t": "09:00:00",
        "end_t": "22:00:00",
        "auto_gen_mode": False
    }
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                for key, val in defaults.items():
                    if key not in saved_data: saved_data[key] = val
                return saved_data
        except: return defaults
    return defaults

# [#] 데이터 저장 함수
def save_data():
    data = {
        "queue": st.session_state.queue,
        "last_gen_time": st.session_state.last_gen_time,
        "gen_interval_min": st.session_state.gen_interval_min,
        "selected_model": st.session_state.selected_model,
        "topic_input": st.session_state.topic_input,
        "char_range": st.session_state.char_range,
        "post_style": st.session_state.post_style,
        "target_days": st.session_state.target_days,
        "start_t": st.session_state.start_t.isoformat() if isinstance(st.session_state.start_t, datetime.time) else st.session_state.start_t,
        "end_t": st.session_state.end_t.isoformat() if isinstance(st.session_state.end_t, datetime.time) else st.session_state.end_t,
        "auto_gen_mode": st.session_state.auto_gen_mode
    }
    with open(SAVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# API 및 세션 초기화
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

if 'initialized' not in st.session_state:
    saved = load_data()
    for k, v in saved.items():
        st.session_state[k] = v
    if isinstance(st.session_state.start_t, str):
        st.session_state.start_t = datetime.time.fromisoformat(st.session_state.start_t)
    if isinstance(st.session_state.end_t, str):
        st.session_state.end_t = datetime.time.fromisoformat(st.session_state.end_t)
    st.session_state.initialized = True
    st.session_state.success_msg = None

@st.cache_resource
def get_available_models():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return models if models else ["models/gemini-1.5-flash"]
    except: return ["models/gemini-1.5-flash"]

# [강화] 글자 수 제한 강화 버전 함수
def generate_draft(topic, min_len, max_len, style, model_name):
    try:
        model = genai.GenerativeModel(model_name)
        prompt = f"""
        너는 '글자 수 제한 전문가'이자 베테랑 카피라이터다.
        주제: {topic}
        말투: {style}

        [절대 준수 규칙]
        1. 결과물은 반드시 공백을 포함하여 **{min_len}자 이상 {max_len}자 이하**여야 한다. (현재 설정 범위: {min_len}~{max_len}자)
        2. 다른 설명이나 인사말은 일절 생략하고 오직 '게시글 내용'만 출력하라.
        3. 작성 프로세스:
           - 1단계: 주제에 맞는 내용을 작성한다.
           - 2단계: 작성한 글의 글자 수를 스스로 센다.
           - 3단계: 글자 수가 {min_len}~{max_len}자 사이가 아니라면, 내용을 줄이거나 늘려서 다시 맞춘다.
           - 4단계: 최종 글자 수가 확실히 범위 안에 들어왔을 때만 그 내용을 출력한다.
        
        지금 바로 이 규칙에 맞춰 {style} 말투로 작성해라.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"AI 오류 발생: {e}"

# --- UI 구성 ---
st.set_page_config(page_title="AI Post Assistant", layout="wide")

# 카카오톡 링크
KAKAO_LINK = "https://open.kakao.com/o/s2lFw8Nf" 

st.markdown(f"""
    <style>
    @keyframes spin {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
    .spinning {{ display: inline-block; animation: spin 2s linear infinite; color: #00BFFF; font-size: 24px; }}
    .status-card {{ padding: 15px; border-radius: 12px; border: 1px solid #333; background-color: #0e1117; text-align: center; }}
    .vertical-line {{ border-left: 1px solid #444; height: 320px; margin: 40px auto 0 auto; width: 1px; }}
    .kakao-floating-btn {{
        position: fixed; bottom: 80px; right: 40px; width: 60px; height: 60px;
        background-color: #FEE500; border-radius: 50%; box-shadow: 4px 10px 20px rgba(0,0,0,0.3);
        display: flex; justify-content: center; align-items: center; z-index: 9999;
        cursor: pointer; transition: all 0.3s ease; text-decoration: none;
    }}
    .kakao-icon {{ width: 35px; height: 35px; }}
    </style>
    <a href="https://open.kakao.com/o/s2lFw8Nf" target="_blank" class="kakao-floating-btn">
        <img src="https://upload.wikimedia.org/wikipedia/commons/e/e3/KakaoTalk_logo.svg" class="kakao-icon">
    </a>
    """, unsafe_allow_html=True)

st.title("🤖 AI 콘텐츠 생성 비서")

st.markdown("##### :red[**gemini-2.5-flash 한도 초과 시 아래 모델들 중에서 골라서 이용할 것**]")
st.markdown("""<small>gemini-3-flash-preview<br>
gemini-2.5-flash-lite<br>
gemini-3.1-flash-lite</small>""", unsafe_allow_html=True)
st.divider()

if st.session_state.success_msg:
    st.success(st.session_state.success_msg)
    st.session_state.success_msg = None 

# 자동 생성 모드일 때만 새로고침 가동
if st.session_state.auto_gen_mode:
    st_autorefresh(interval=60000, key="auto_worker")

available_models = get_available_models()

with st.sidebar:
    st.header("⚙️ 엔진 컨트롤")
    st.toggle("✍️ AI 자동 생성 ON", key="auto_gen_mode", on_change=save_data)
    unused_count = len([item for item in st.session_state.queue if not item.get("used", False)])
    status_text = "생성 중..." if st.session_state.auto_gen_mode else "정지됨"
    status_color = "#00BFFF" if st.session_state.auto_gen_mode else "#888"
    st.markdown(f"""<div class="status-card"><b style="color:{status_color};">{status_text}</b><br><small>대기 중 콘텐츠: {unused_count}개</small></div>""", unsafe_allow_html=True)
    st.divider()
    if st.button("보관함 전체 비우기"): 
        st.session_state.queue = []
        save_data(); st.rerun()

t1, t2 = st.tabs(["✨ 글 생성 및 설정", "📋 콘텐츠 보관함"])

with t1:
    st.subheader("📝 프롬프트 작성")
    st.text_area("작성할 주제나 상황 입력", key="topic_input", height=150)
    
    col_left, col_mid, col_right = st.columns([1, 0.1, 1])
    with col_left:
        st.markdown("### ⚙️ 세부설정")
        st.slider("글자 수 범위", 10, 500, key="char_range")
        st.selectbox("말투 설정", ["친절한 이웃", "딱딱한 비서", "친한 친구"], key="post_style")
        st.selectbox("사용할 AI 모델 선택", available_models, key="selected_model")
    
    with col_mid:
        st.markdown('<div class="vertical-line"></div>', unsafe_allow_html=True)
        
    with col_right:
        st.markdown("### 📅 스케줄설정")
        st.multiselect("가동 요일 선택", ["월", "화", "수", "목", "금", "토", "일"], key="target_days")
        time_col1, time_col2 = st.columns(2)
        time_col1.time_input("가동 시작", key="start_t")
        time_col2.time_input("가동 종료", key="end_t")
        st.selectbox("자동 생성 간격(분)", [i for i in range(10, 610, 10)], key="gen_interval_min")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 현재 설정값 저장하기", use_container_width=True):
        save_data()
        st.session_state.success_msg = "✅ 설정이 안전하게 저장되었습니다."
        st.rerun()

    if st.button("✨ 즉시 AI 초안 생성", use_container_width=True, type="primary"):
        if st.session_state.topic_input:
            with st.spinner("AI가 작성 중입니다..."):
                res = generate_draft(st.session_state.topic_input, st.session_state.char_range[0], st.session_state.char_range[1], st.session_state.post_style, st.session_state.selected_model) 
                # [시간 수정] Naive 한국 시간으로 저장
                now_kst = get_now_kst()
                st.session_state.queue.append({"time": now_kst.strftime("%m-%d %H:%M"), "content": res, "used": False})
                save_data(); st.session_state.success_msg = "✅ 초안 생성 완료!"; st.rerun()

    # 자동화 엔진 로직
    # [시간 수정] Naive 한국 시간 기준으로 현재 시각 파악
    now = get_now_kst()
    if st.session_state.auto_gen_mode and ["월","화","수","목","금","토","일"][now.weekday()] in st.session_state.target_days:
        if st.session_state.start_t <= now.time() <= st.session_state.end_t:
            lg = st.session_state.last_gen_time
            # lg(문자열)를 다시 불러올 때 naive하게 처리하여 비교 에러 방지
            if lg is None or (now - datetime.datetime.fromisoformat(lg)).total_seconds() >= st.session_state.gen_interval_min * 60:
                new_txt = generate_draft(st.session_state.topic_input, st.session_state.char_range[0], st.session_state.char_range[1], st.session_state.post_style, st.session_state.selected_model)
                st.session_state.queue.append({"time": now.strftime("%m-%d %H:%M"), "content": new_txt, "used": False})
                st.session_state.last_gen_time = now.isoformat(); save_data(); st.rerun()

with t2:
    unused_list = [(i, item) for i, item in enumerate(st.session_state.queue) if not item["used"]]
    used_list = [(i, item) for i, item in enumerate(st.session_state.queue) if item["used"]]
    st.subheader(f"📋 콘텐츠 보관함")
    sub_tabs = st.tabs([f"전체 ({len(st.session_state.queue)})", f"사용전 ({len(unused_list)})", f"사용후 ({len(used_list)})"])
    
    def render_queue_item(idx, item, tab_id):
        with st.container(border=True):
            char_c = len(item['content'])
            col_s, col_t, col_c = st.columns([1, 2.5, 1.5])
            with col_s:
                checked = st.checkbox("사용 완료", value=item["used"], key=f"chk_{tab_id}_{idx}")
                if checked != item["used"]:
                    st.session_state.queue[idx]["used"] = checked
                    save_data(); st.rerun()
            with col_t: st.caption(f"🕒 {item['time']} | ID: {idx+1}")
            with col_char: # 여기서 col_char가 정의 안 되어있어서 에러 났을 수도 있겠네예. col_c로 바꿉니다.
                st.markdown(f"<p style='text-align:right; color:#00BFFF; font-size:13px;'>{char_c}자</p>", unsafe_allow_html=True)
            
            lines = item['content'].count('\n') + (len(item['content']) // 42) + 2
            h = max(130, lines * 27)
            edited = st.text_area("수정", item['content'], key=f"ed_{tab_id}_{idx}", height=h)
            if edited != item['content']:
                st.session_state.queue[idx]['content'] = edited; save_data()
            
            c1, c2 = st.columns([3, 1])
            with c1:
                js_code = f"navigator.clipboard.writeText({json.dumps(edited)})"
                components.html(f"""<button onclick="{js_code}" style="background:#00BFFF; border:none; padding:8px; border-radius:5px; width:100%; cursor:pointer; font-weight:bold;">📋 텍스트 복사</button>""", height=45)
            with c2:
                if st.button("🗑️ 삭제", key=f"dl_{tab_id}_{idx}", use_container_width=True):
                    st.session_state.queue.pop(idx); save_data(); st.rerun()

    with sub_tabs[0]:
        for idx, item in enumerate(reversed(st.session_state.queue)):
            render_queue_item(len(st.session_state.queue)-1-idx, item, "all")
    with sub_tabs[1]:
        for r_idx, item in reversed(unused_list): render_queue_item(r_idx, item, "un")
    with sub_tabs[2]:
        for r_idx, item in reversed(used_list): render_queue_item(r_idx, item, "ud")

st.divider()
st.caption("© 2026 BK. 인공지능이 쓰고 BK가 직접 검수한 명품 비서")
