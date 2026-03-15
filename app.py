import streamlit as st
import google.generativeai as genai
import datetime
import json
import os
from streamlit_autorefresh import st_autorefresh

# [#] 저장용 파일 경로
SAVE_FILE = "moneydock_data.json"

# [#] 데이터 불러오기
def load_data():
    defaults = {
        "queue": [], 
        "last_gen_time": None,
        "gen_interval_min": 60,
        "selected_model": "models/gemini-1.5-flash",
        "topic_input": "비트코인 실시간 시황 요약해줘",
        "char_range": [50, 150],
        "post_style": "머니독 스타일(사투리)",
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

# [#] 데이터 저장하기
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

# API 설정 (제미나이만 유지)
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

# [#] 세션 초기화
saved = load_data()
for key, value in saved.items():
    if key not in st.session_state:
        st.session_state[key] = value

if isinstance(st.session_state.start_t, str):
    try: st.session_state.start_t = datetime.time.fromisoformat(st.session_state.start_t)
    except: st.session_state.start_t = datetime.time(9,0)
if isinstance(st.session_state.end_t, str):
    try: st.session_state.end_t = datetime.time.fromisoformat(st.session_state.end_t)
    except: st.session_state.end_t = datetime.time(22,0)

@st.cache_resource
def get_available_models():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return models if models else ["models/gemini-1.5-flash"]
    except: return ["models/gemini-1.5-flash"]

def generate_draft(topic, min_len, max_len, style, model_name):
    try:
        model = genai.GenerativeModel(model_name)
        prompt = f"주제: {topic}\n분량: {min_len}~{max_len}자 엄수\n말투: {style}\n쓰레드 게시글로 작성해줘."
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "429" in str(e): return "⚠️ [한도 초과] 내일 다시 시도해주이소."
        return f"AI 오류: {e}"

# --- UI 구성 ---
st.set_page_config(page_title="AI Post Generator", layout="wide")

st.markdown("""
    <style>
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    .spinning { display: inline-block; animation: spin 2s linear infinite; color: #00BFFF; font-size: 24px; }
    .stopped { display: inline-block; color: #888; font-size: 24px; }
    .status-card { padding: 20px; border-radius: 12px; border: 1px solid #333; background-color: #0e1117; text-align: center; margin-bottom: 25px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 BK의 AI 콘텐츠 생산 기지")
st.markdown("##### **정지 걱정 없이 AI가 글만 억수로 잘 뽑아주는 무인 창고입니더!**")
st.divider()

st_autorefresh(interval=60000, key="auto_worker")
available_models = get_available_models()

with st.sidebar:
    st.header("⚙️ 엔진 컨트롤")
    st.toggle("✍️ AI 자동 글 생성 모드", key="auto_gen_mode", on_change=save_data)
    
    # 상태창 표시 (업로드 기능 제거됨)
    pending_count = len(st.session_state.queue)
    if st.session_state.auto_gen_mode:
        st.markdown(f"""<div class="status-card"><span class="spinning">🔄</span><br><b style="color:#00BFFF;">GEN ENGINE ACTIVE</b><br><small>글 생성 중... (현재 보관함: {pending_count}개)</small></div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="status-card"><span class="stopped">🔄</span><br><b style="color:#888;">ENGINE PAUSED</b><br><small>생성이 멈춰있십니더</small></div>""", unsafe_allow_html=True)

    st.divider()
    with st.popover("🕒 생성 간격 설정"):
        minute_options = [i for i in range(10, 610, 10)] 
        st.session_state.gen_interval_min = st.selectbox("AI 생성 간격(분)", options=minute_options, index=minute_options.index(st.session_state.gen_interval_min) if st.session_state.gen_interval_min in minute_options else 5)
        if st.button("설정 저장", key="sidebar_save_btn"): save_data(); st.success("저장 완료!")
    if st.button("보관함 싹 비우기", key="sidebar_clear_btn"): st.session_state.queue = []; save_data(); st.rerun()

t1, t2 = st.tabs(["✨ AI 글쓰기", "📋 생성된 글 목록"])

with t1:
    st.subheader("📝 맞춤형 글 생성")
    midx = available_models.index(st.session_state.selected_model) if st.session_state.selected_model in available_models else 0
    st.session_state.selected_model = st.selectbox("🤖 AI 모델 선택", available_models, index=midx)
    st.session_state.topic_input = st.text_area("어떤 글을 써드릴까예?", value=st.session_state.topic_input)
    
    if st.button("✨ 지금 즉시 초안 뽑기", use_container_width=True, type="primary"):
        if not st.session_state.topic_input: st.warning("주제를 입력해주이소!")
        else:
            with st.spinner("AI가 찰지게 글 쓰는 중..."):
                res_text = generate_draft(st.session_state.topic_input, st.session_state.char_range[0], st.session_state.char_range[1], st.session_state.post_style, st.session_state.selected_model) 
                st.session_state.queue.append({"time": datetime.datetime.now().strftime("%m-%d %H:%M"), "content": res_text, "model": st.session_state.selected_model, "target_max": st.session_state.char_range[1]})
                save_data(); st.success("보관함으로 쏙 들어갔십니더!")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.char_range = st.slider("글자 수", 10, 300, value=tuple(st.session_state.char_range))
        styles = ["머니독 스타일(사투리)", "전문적 시황 분석", "친절한 이웃", "스하리/반하리 유도형"]
        current_style = st.session_state.get("post_style", styles[0])
        st.session_state.post_style = st.selectbox("말투 설정", styles, index=styles.index(current_style) if current_style in styles else 0)
    with col2:
        st.session_state.target_days = st.multiselect("가동 요일", ["월", "화", "수", "목", "금", "토", "일"], default=st.session_state.target_days)
        cs, ce = st.columns(2)
        st.session_state.start_t = cs.time_input("가동 시작", value=st.session_state.start_t)
        st.session_state.end_t = ce.time_input("가동 종료", value=st.session_state.end_t)

    if st.button("💾 모든 설정값 저장"): save_data(); st.success("박제 완료!")

    # --- [자동 생성 엔진] ---
    now = datetime.datetime.now()
    if ["월","화","수","목","금","토","일"][now.weekday()] in st.session_state.target_days and st.session_state.start_t <= now.time() <= st.session_state.end_t:
        if st.session_state.auto_gen_mode:
            lg = st.session_state.last_gen_time
            if lg is None or (now - datetime.datetime.fromisoformat(lg)).total_seconds() >= st.session_state.gen_interval_min * 60:
                new_txt = generate_draft(st.session_state.topic_input, st.session_state.char_range[0], st.session_state.char_range[1], st.session_state.post_style, st.session_state.selected_model)
                st.session_state.queue.append({"time": now.strftime("%m-%d %H:%M"), "content": new_txt, "model": st.session_state.selected_model, "target_max": st.session_state.char_range[1]})
                st.session_state.last_gen_time = now.isoformat(); save_data(); st.toast("✍️ 새 글이 도착했십니더!")

with t2:
    st.subheader("📋 보관된 AI 초안 (여기서 복사해서 올리이소)")
    if not st.session_state.queue:
        st.info("아직 생성된 글이 없십니더. 첫 번째 탭에서 글을 생성해보이소!")
    else:
        for idx, item in enumerate(reversed(st.session_state.queue)):
            real_idx = len(st.session_state.queue) - 1 - idx
            with st.container(border=True):
                st.caption(f"🕒 {item['time']} | 🤖 {item.get('model', 'Gemini')}")
                # 텍스트 영역에 넣어서 복사하기 편하게 만듭니더
                st.text_area(f"초안 (ID: {real_idx+1})", item['content'], height=150, key=f"text_{real_idx}")
                
                c1, _ = st.columns([1, 4])
                if c1.button("🗑️ 삭제", key=f"del_{real_idx}"):
                    st.session_state.queue.pop(real_idx)
                    save_data(); st.rerun()

st.divider()
st.caption(f"© 2026 MoneyDock Auto | 업로드 기능이 제거된 안전한 AI 비서 버전입니더.")
