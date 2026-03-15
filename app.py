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

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

if 'initialized' not in st.session_state:
    saved = load_data()
    for k, v in saved.items(): st.session_state[k] = v
    if isinstance(st.session_state.start_t, str): st.session_state.start_t = datetime.time.fromisoformat(st.session_state.start_t)
    if isinstance(st.session_state.end_t, str): st.session_state.end_t = datetime.time.fromisoformat(st.session_state.end_t)
    st.session_state.initialized = True
    st.session_state.success_msg = None

@st.cache_resource
def get_available_models():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return sorted(models)
    except: return ["models/gemini-1.5-flash"]

# [강화] 글자 수 준수 로직 및 자동 모델 전환
def generate_draft(topic, min_len, max_len, style, selected_model):
    all_models = get_available_models()
    if selected_model in all_models: all_models.remove(selected_model)
    trial_order = [selected_model] + all_models
    
    last_err = ""
    for model_path in trial_order:
        try:
            model = genai.GenerativeModel(model_path)
            # AI에게 스스로 검토하고 글자 수를 맞추도록 명령하는 고강도 프롬프트
            prompt = f"""
            너는 글자 수 제한을 칼같이 지키는 AI 비서다.
            
            요청 주제: {topic}
            말투 설정: {style}
            
            [규칙: 반드시 지킬 것]
            1. 공백 포함 총 글자 수는 반드시 **{min_len}자 이상, {max_len}자 이하**여야 한다.
            2. 이 글자 수 범위를 지키기 위해 내용을 늘리거나 줄여라.
            3. 다른 서론이나 맺음말 없이 오직 '본문 내용'만 출력하라.
            4. 출력 전, 너 스스로 글자 수를 세어보고 범위가 틀리면 다시 써서 최종본만 보내라.
            """
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            last_err = str(e)
            if "429" in last_err or "quota" in last_err.lower(): continue
            else: break
    return f"⚠️ 모든 모델 한도 초과 혹은 오류: {last_err}"

st.set_page_config(page_title="AI Post Assistant", layout="wide")
KAKAO_LINK = "https://open.kakao.com/o/s2lFw8Nf" 

st.markdown(f"""
    <style>
    .spinning {{ display: inline-block; animation: spin 2s linear infinite; color: #00BFFF; font-size: 24px; }}
    @keyframes spin {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
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
st.markdown("##### :red[**사용 가능한 모든 모델을 동원하여 한도 초과(429) 에러를 방어합니다.**]")
st.markdown("""<small>gemini-3-flash-preview / gemini-2.5-flash-lite / gemini-3.1-flash-lite 등 가용 모델 자동 전환</small>""", unsafe_allow_html=True)
st.divider()

if st.session_state.success_msg:
    st.success(st.session_state.success_msg); st.session_state.success_msg = None 

if st.session_state.auto_gen_mode:
    st_autorefresh(interval=60000, key="auto_worker")

available_models = get_available_models()

with st.sidebar:
    st.header("⚙️ 엔진 컨트롤")
    st.toggle("✍️ AI 자동 생성 ON", key="auto_gen_mode", on_change=save_data)
    unused_count = len([item for item in st.session_state.queue if not item.get("used", False)])
    st.markdown(f"""<div class="status-card"><b>대기 중 콘텐츠: {unused_count}개</b></div>""", unsafe_allow_html=True)
    st.divider()
    if st.button("보관함 전체 비우기"): st.session_state.queue = []; save_data(); st.rerun()

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
    with col_mid: st.markdown('<div class="vertical-line"></div>', unsafe_allow_html=True)
    with col_right:
        st.markdown("### 📅 스케줄설정")
        st.multiselect("가동 요일 선택", ["월", "화", "수", "목", "금", "토", "일"], key="target_days")
        time_col1, time_col2 = st.columns(2)
        time_col1.time_input("가동 시작", key="start_t")
        time_col2.time_input("가동 종료", key="end_t")
        st.selectbox("자동 생성 간격(분)", [i for i in range(10, 610, 10)], key="gen_interval_min")

    if st.button("💾 현재 설정값 저장하기", use_container_width=True): save_data(); st.success("설정 저장 완료!"); st.rerun()
    if st.button("✨ 즉시 AI 초안 생성", use_container_width=True, type="primary"):
        if st.session_state.topic_input:
            with st.spinner("AI가 최적의 모델을 찾아 글자 수를 맞추는 중..."):
                res = generate_draft(st.session_state.topic_input, st.session_state.char_range[0], st.session_state.char_range[1], st.session_state.post_style, st.session_state.selected_model) 
                st.session_state.queue.append({"time": datetime.datetime.now().strftime("%m-%d %H:%M"), "content": res, "used": False})
                save_data(); st.session_state.success_msg = "✅ 생성 완료!"; st.rerun()

# [보관함 UI]
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
            with col_c: st.markdown(f"<p style='text-align:right; color:#00BFFF; font-size:13px; font-weight:bold;'>{char_c}자</p>", unsafe_allow_html=True)
            
            lines = item['content'].count('\n') + (len(item['content']) // 40) + 2
            h = max(130, lines * 27)
            edited = st.text_area("내용", item['content'], key=f"ed_{tab_id}_{idx}", height=h)
            if edited != item['content']:
                st.session_state.queue[idx]['content'] = edited; save_data()
            
            c1, c2 = st.columns([3, 1])
            with c1:
                js = f"navigator.clipboard.writeText({json.dumps(edited)})"
                components.html(f"""<button onclick="{js}" style="background:#00BFFF; border:none; padding:8px; border-radius:5px; width:100%; cursor:pointer; font-weight:bold;">📋 복사</button>""", height=45)
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
