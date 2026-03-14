import streamlit as st
import google.generativeai as genai
import requests
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
        "last_post_time": None, 
        "last_gen_time": None,
        "gen_interval_min": 60,
        "post_interval_min": 60,
        "selected_model": "models/gemini-1.5-flash",
        "topic_input": "비트코인 실시간 시황 요약해줘",
        "char_range": [50, 150],
        "post_style": "머니독 스타일(사투리)",
        "target_days": ["월", "수", "금"],
        "start_t": "09:00:00",
        "end_t": "22:00:00"
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
        "last_post_time": st.session_state.last_post_time,
        "last_gen_time": st.session_state.last_gen_time,
        "gen_interval_min": st.session_state.gen_interval_min,
        "post_interval_min": st.session_state.post_interval_min,
        "selected_model": st.session_state.selected_model,
        "topic_input": st.session_state.topic_input,
        "char_range": st.session_state.char_range,
        "post_style": st.session_state.post_style,
        "target_days": st.session_state.target_days,
        "start_t": st.session_state.start_t.isoformat() if isinstance(st.session_state.start_t, datetime.time) else st.session_state.start_t,
        "end_t": st.session_state.end_t.isoformat() if isinstance(st.session_state.end_t, datetime.time) else st.session_state.end_t
    }
    with open(SAVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# API 설정
GEMINI_API_KEY = "AIzaSyD8D2wbkqLZiHjTIbsdnZxE2f2j4BHhewc"
THREADS_ACCESS_TOKEN = "THAASO1xKLZAo9BUVFRYW9sY2xqVWxlR20zMG5HTkhaSFY5elRhRGozOWZAWczBvMjhGNnNEbTl6RzR1MFlTWnhMR1YwLTJxOTlxZAU5GRkVfRkc2dXlic3dSOHZApcjNrQm53SHBVcWdEdjFDVFJDWHl2YTJXX1JfY01GZAVNNclFLQjg1UTNaMWMzUnhadWo0b2sZD"
THREADS_USER_ID = "25381408474865854"

genai.configure(api_key=GEMINI_API_KEY)

if 'initialized' not in st.session_state:
    saved = load_data()
    for k, v in saved.items(): st.session_state[k] = v
    try:
        st.session_state.start_t = datetime.time.fromisoformat(saved["start_t"])
        st.session_state.end_t = datetime.time.fromisoformat(saved["end_t"])
    except:
        st.session_state.start_t, st.session_state.end_t = datetime.time(9,0), datetime.time(22,0)
    st.session_state.initialized = True

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

def publish_to_threads(content):
    base_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}"
    params = {'media_type': 'TEXT', 'text': content, 'access_token': THREADS_ACCESS_TOKEN}
    try:
        res = requests.post(f"{base_url}/threads", data=params).json()
        if 'id' in res:
            requests.post(f"{base_url}/threads_publish", data={'creation_id': res['id'], 'access_token': THREADS_ACCESS_TOKEN})
            return True
    except: pass
    return False

# --- UI 구성 ---
st.set_page_config(page_title="Threads Auto posting system", layout="wide")

# [핵심] 화살표 회전 및 상태별 색상 CSS
st.markdown("""
    <style>
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    .spinning { display: inline-block; animation: spin 2s linear infinite; font-size: 24px; }
    .stopped { display: inline-block; color: #888; font-size: 24px; }
    .status-card { padding: 20px; border-radius: 12px; border: 1px solid #333; background-color: #0e1117; text-align: center; margin-bottom: 25px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 BK의 24시간 쓰레드 자동화 시스템(Test ver.)")
st.markdown("##### **AI가 24시간 쉬지 않고 글을 쓰고 올리는 머니독 전용 무인 조종실입니다!**")
st.markdown("##### :red[**gemini-2.5-flash 한도 초과로 429 error 발생시 아래 모델들 중에서 골라서 이용할 것**]")
st.markdown("""
<small>
gemini-3-flash-preview<br>
gemini-2.5-flash-lite<br>
gemini-3.1-flash-lite
</small>
""", unsafe_allow_html=True)
st.divider()

st_autorefresh(interval=60000, key="auto_worker")

available_models = get_available_models()

with st.sidebar:
    st.header("⚙️ 무인 엔진 스위치")
    auto_gen_mode = st.toggle("✍️ AI 자동 글 생성", value=False)
    auto_post_mode = st.toggle("🚀 완전 자동 업로드", value=False)
    
    # [수정] 가동 상태 세부 표시 로직
    pending_count = len([item for item in st.session_state.queue if not item.get("posted", False)])
    
    if auto_gen_mode and auto_post_mode:
        status_text, status_color, status_icon = "FULL AUTOMATION", "#00FF00", "spinning"
        status_desc = f"글 생성 + 업로드 가동 중 ({pending_count}개 대기)"
    elif auto_gen_mode:
        status_text, status_color, status_icon = "GEN ONLY", "#00BFFF", "spinning"
        status_desc = "AI 글 생성만 가동 중"
    elif auto_post_mode:
        status_text, status_color, status_icon = "UPLOAD ONLY", "#FFA500", "spinning"
        status_desc = f"자동 업로드만 가동 중 ({pending_count}개 대기)"
    else:
        status_text, status_color, status_icon = "ENGINE PAUSED", "#888", "stopped"
        status_desc = "엔진이 멈춰있십니더"

    st.markdown(f"""
    <div class="status-card">
        <span class="{status_icon}" style="color:{status_color};">🔄</span><br>
        <b style="color:{status_color}; font-size: 18px;">{status_text}</b><br>
        <small style="color:#bbb;">{status_desc}</small>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    with st.popover("🕒 10분 단위 간격 설정"):
        minute_options = [i for i in range(10, 610, 10)] 
        st.session_state.gen_interval_min = st.selectbox("AI 생성 간격", options=minute_options, index=minute_options.index(st.session_state.gen_interval_min) if st.session_state.gen_interval_min in minute_options else 5)
        st.session_state.post_interval_min = st.selectbox("자동 업로드 간격", options=minute_options, index=minute_options.index(st.session_state.post_interval_min) if st.session_state.post_interval_min in minute_options else 5)
        if st.button("설정 저장", key="sidebar_save_btn"): save_data(); st.success("저장 완료!")
    if st.button("데이터 싹 비우기", key="sidebar_clear_btn"): st.session_state.queue = []; save_data(); st.rerun()

t1, t2 = st.tabs(["✨ 생성 및 스케줄 설정", "📋 콘텐츠 보관함"])

with t1:
    st.subheader("📝 AI 포스팅 제어")
    midx = available_models.index(st.session_state.selected_model) if st.session_state.selected_model in available_models else 0
    st.session_state.selected_model = st.selectbox("🤖 사용할 AI 모델 선택", available_models, index=midx)
    st.session_state.topic_input = st.text_area("AI 주제 입력 (프롬프트)", value=st.session_state.topic_input)
    
    if st.button("✨ 지금 즉시 AI 초안 생성하기", use_container_width=True, type="primary"):
        if not st.session_state.topic_input: st.warning("주제를 입력해주이소!")
        else:
            save_data()
            with st.spinner("AI가 글 쓰는 중..."):
                res_text = generate_draft(st.session_state.topic_input, st.session_state.char_range[0], st.session_state.char_range[1], st.session_state.post_style, st.session_state.selected_model) 
                st.session_state.queue.append({
                    "time": datetime.datetime.now().strftime("%m-%d %H:%M"), 
                    "content": res_text, "model": st.session_state.selected_model, 
                    "target_max": st.session_state.char_range[1], "posted": False
                })
                save_data(); st.success("초안 생성 완료!")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.char_range = st.slider("글자 수 (최소~최대)", 10, 300, value=tuple(st.session_state.char_range))
        st.session_state.post_style = st.selectbox("말투 설정", ["머니독 스타일(사투리)", "전문적 시황 분석", "친절한 이웃"], index=0)
    with col2:
        st.session_state.target_days = st.multiselect("요일 선택", ["월", "화", "수", "목", "금", "토", "일"], default=st.session_state.target_days)
        cs, ce = st.columns(2)
        st.session_state.start_t = cs.time_input("가동 시작", value=st.session_state.start_t)
        st.session_state.end_t = ce.time_input("가동 종료", value=st.session_state.end_t)

    if st.button("💾 현재 모든 설정값 저장하기"): save_data(); st.success("박제 완료!")

    now = datetime.datetime.now()
    if ["월","화","수","목","금","토","일"][now.weekday()] in st.session_state.target_days and st.session_state.start_t <= now.time() <= st.session_state.end_t:
        if auto_gen_mode:
            lg = st.session_state.last_gen_time
            if lg is None or (now - datetime.datetime.fromisoformat(lg)).total_seconds() >= st.session_state.gen_interval_min * 60:
                new_txt = generate_draft(st.session_state.topic_input, st.session_state.char_range[0], st.session_state.char_range[1], st.session_state.post_style, st.session_state.selected_model)
                st.session_state.queue.append({"time": now.strftime("%m-%d %H:%M"), "content": new_txt, "model": st.session_state.selected_model, "target_max": st.session_state.char_range[1], "posted": False})
                st.session_state.last_gen_time = now.isoformat(); save_data(); st.toast("✍️ 자동 생성 완료!")
        
        if auto_post_mode:
            unposted = [idx for idx, item in enumerate(st.session_state.queue) if not item.get("posted", False)]
            if unposted:
                lp = st.session_state.last_post_time
                if lp is None or (now - datetime.datetime.fromisoformat(lp)).total_seconds() >= st.session_state.post_interval_min * 60:
                    if publish_to_threads(st.session_state.queue[unposted[0]]['content']):
                        st.session_state.queue[unposted[0]]["posted"] = True
                        st.session_state.last_post_time = now.isoformat(); save_data(); st.toast("🚀 자동 업로드 성공!"); st.rerun()

with t2:
    st.subheader("📋 콘텐츠 목록 관리")
    sub_tabs = st.tabs(["전체 보기", "⏳ 대기 중", "✅ 발행 완료"])
    
    def display_item(idx, item, tab_id):
        is_posted = item.get("posted", False)
        with st.container(border=True):
            status = ":green[**[발행완료]**]" if is_posted else ":orange[**[대기중]**]"
            st.caption(f"🕒 {item['time']} | 🤖 {item.get('model', 'Gemini')} | {status}")
            edited = st.text_area(f"수정 (ID: {idx+1})", item['content'], key=f"{tab_id}_area_{idx}", height=120)
            st.session_state.queue[idx]['content'] = edited
            curr_len = len(edited)
            limit = item.get('target_max', 300)
            color = "red" if curr_len > limit else "green"
            st.markdown(f"📏 글자 수: :{color}[**{curr_len}**] / {limit}자")
            c1, c2, _ = st.columns([1, 1, 4])
            if c1.button("🚀 즉시 발행", key=f"{tab_id}_ok_{idx}", disabled=is_posted):
                if publish_to_threads(edited):
                    st.session_state.queue[idx]["posted"] = True
                    save_data(); st.success("발행 완료!"); st.rerun()
            if c2.button("🗑️ 삭제", key=f"{tab_id}_del_{idx}"):
                st.session_state.queue.pop(idx); save_data(); st.rerun()

    with sub_tabs[0]:
        for i, it in enumerate(reversed(st.session_state.queue)):
            display_item(len(st.session_state.queue)-1-i, it, "all")
    with sub_tabs[1]:
        for idx, it in reversed(list(enumerate(st.session_state.queue))):
            if not it.get("posted"): display_item(idx, it, "pending")
    with sub_tabs[2]:
        for idx, it in reversed(list(enumerate(st.session_state.queue))):
            if it.get("posted"): display_item(idx, it, "completed")

st.divider()
st.caption(f"© 2026 MoneyDock Auto | 세부 상태창이 적용된 버전입니더.")