import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
import datetime
import json
import os
from streamlit_autorefresh import st_autorefresh

# [#] 저장용 파일 경로
SAVE_FILE = "moneydock_data.json"

# [#] 데이터 불러오기/저장 로직
def load_data():
    defaults = {
        "queue": [], 
        "last_gen_time": None,
        "gen_interval_min": 60,
        "selected_model": "models/gemini-1.5-flash",
        "topic_input": "비트코인 실시간 시황 요약해줘",
        "char_range": [50, 150],
        "post_style": "전문적 시황 분석",
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

# API 설정
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

# 세션 초기화
saved = load_data()
for key, value in saved.items():
    if key not in st.session_state: st.session_state[key] = value

if isinstance(st.session_state.start_t, str):
    try: st.session_state.start_t = datetime.time.fromisoformat(st.session_state.start_t)
    except: st.session_state.start_t = datetime.time(9,0)
if isinstance(st.session_state.end_t, str):
    try: st.session_state.end_t = datetime.time.fromisoformat(st.session_state.end_t)
    except: st.session_state.end_t = datetime.time(22,0)

def generate_draft(topic, min_len, max_len, style, model_name):
    try:
        model = genai.GenerativeModel(model_name)
        prompt = f"주제: {topic}\n분량: {min_len}~{max_len}자 엄수\n말투: {style}\n스레드 게시글로 작성해줘."
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "429" in str(e): return "⚠️ [한도 초과] 내일 다시 시도해 주세요."
        return f"AI 오류: {e}"

# --- UI 구성 ---
st.set_page_config(page_title="AI Post Assistant", layout="wide")

st.markdown("""
    <style>
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    .spinning { display: inline-block; animation: spin 2s linear infinite; color: #00BFFF; font-size: 24px; }
    .status-card { padding: 15px; border-radius: 12px; border: 1px solid #333; background-color: #0e1117; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 AI 콘텐츠 생성 비서")
st.divider()

st_autorefresh(interval=60000, key="auto_worker")

with st.sidebar:
    st.header("⚙️ 엔진 컨트롤")
    st.toggle("✍️ AI 자동 생성 ON", key="auto_gen_mode", on_change=save_data)
    
    pending_count = len(st.session_state.queue)
    if st.session_state.auto_gen_mode:
        st.markdown(f"""<div class="status-card"><span class="spinning">🔄</span><br><b style="color:#00BFFF;">생성 엔진 가동 중</b><br><small>보관함: {pending_count}개</small></div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="status-card"><b style="color:#888;">정지 상태</b><br><small>보관함: {pending_count}개</small></div>""", unsafe_allow_html=True)

    st.divider()
    minute_options = [i for i in range(10, 610, 10)] 
    st.session_state.gen_interval_min = st.selectbox("생성 간격(분)", options=minute_options, index=minute_options.index(st.session_state.gen_interval_min) if st.session_state.gen_interval_min in minute_options else 5)
    
    if st.button("보관함 전체 비우기", key="sidebar_clear_btn"): 
        st.session_state.queue = []
        save_data()
        st.rerun()

t1, t2 = st.tabs(["✨ 글 생성 및 설정", "📋 콘텐츠 보관함"])

with t1:
    # [변경] 세부 스케줄 및 스타일 설정을 위로 배치
    st.subheader("⚙️ 세부 스케줄 및 스타일 설정")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.char_range = st.slider("글자 수 범위", 10, 300, value=tuple(st.session_state.char_range))
        # [삭제] 머니독 스타일 및 유도형 삭제
        styles = ["전문적 시황 분석", "친절한 이웃"]
        current_style = st.session_state.get("post_style", styles[0])
        if current_style not in styles: current_style = styles[0]
        st.session_state.post_style = st.selectbox("말투 설정", styles, index=styles.index(current_style))
        
    with col2:
        st.session_state.target_days = st.multiselect("가동 요일 선택", ["월", "화", "수", "목", "금", "토", "일"], default=st.session_state.target_days)
        cs, ce = st.columns(2)
        st.session_state.start_t = cs.time_input("가동 시작 시각", value=st.session_state.start_t)
        st.session_state.end_t = ce.time_input("가동 종료 시각", value=st.session_state.end_t)

    if st.button("💾 현재 설정값 저장하기", use_container_width=True):
        save_data()
        st.success("설정 데이터가 안전하게 저장되었습니다.")

    st.divider()

    # [변경] AI 모델 및 주제 설정을 아래로 배치
    st.subheader("🤖 AI 모델 및 주제 설정")
    models = ["models/gemini-1.5-flash", "models/gemini-1.5-pro", "models/gemini-1.5-flash-8b"]
    st.session_state.selected_model = st.selectbox("사용할 AI 모델 선택", models, index=models.index(st.session_state.selected_model) if st.session_state.selected_model in models else 0)
    
    st.session_state.topic_input = st.text_area("작성할 주제나 상황을 입력하세요", value=st.session_state.topic_input, height=150)
    
    if st.button("✨ 즉시 AI 초안 생성", use_container_width=True, type="primary"):
        if not st.session_state.topic_input: st.warning("주제를 입력해 주세요.")
        else:
            with st.spinner("AI가 콘텐츠를 작성하고 있습니다..."):
                res_text = generate_draft(st.session_state.topic_input, st.session_state.char_range[0], st.session_state.char_range[1], st.session_state.post_style, st.session_state.selected_model) 
                st.session_state.queue.append({"time": datetime.datetime.now().strftime("%m-%d %H:%M"), "content": res_text})
                save_data(); st.success("초안이 보관함에 추가되었습니다.")

    # --- [자동 생성 엔진] ---
    now = datetime.datetime.now()
    if ["월","화","수","목","금","토","일"][now.weekday()] in st.session_state.target_days and st.session_state.start_t <= now.time() <= st.session_state.end_t:
        if st.session_state.auto_gen_mode:
            lg = st.session_state.last_gen_time
            if lg is None or (now - datetime.datetime.fromisoformat(lg)).total_seconds() >= st.session_state.gen_interval_min * 60:
                new_txt = generate_draft(st.session_state.topic_input, st.session_state.char_range[0], st.session_state.char_range[1], st.session_state.post_style, st.session_state.selected_model)
                st.session_state.queue.append({"time": now.strftime("%m-%d %H:%M"), "content": new_txt})
                st.session_state.last_gen_time = now.isoformat(); save_data(); st.toast("✍️ 새로운 자동 생성 글이 도착했습니다.")

with t2:
    st.subheader("📋 생성된 콘텐츠 보관함")
    if not st.session_state.queue:
        st.info("보관된 글이 없습니다. 설정 탭에서 글을 생성해 보세요.")
    else:
        for idx, item in enumerate(reversed(st.session_state.queue)):
            real_idx = len(st.session_state.queue) - 1 - idx
            with st.container(border=True):
                st.caption(f"🕒 생성 시각: {item['time']} | ID: {real_idx+1}")
                
                edited_content = st.text_area("콘텐츠 수정", item['content'], key=f"edit_{real_idx}", height=120)
                st.session_state.queue[real_idx]['content'] = edited_content
                
                # 복사 버튼
                components.html(f"""
                    <button id="copyBtn_{real_idx}" style="
                        background-color: #00BFFF;
                        color: #0e1117;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 8px;
                        cursor: pointer;
                        font-weight: bold;
                        font-size: 14px;
                        width: 100%;
                        transition: 0.3s;
                    ">📋 텍스트 복사하기</button>
                    <script>
                        document.getElementById('copyBtn_{real_idx}').onclick = function() {{
                            const text = {json.dumps(edited_content)};
                            navigator.clipboard.writeText(text).then(function() {{
                                const btn = document.getElementById('copyBtn_{real_idx}');
                                btn.innerText = '✅ 복사 완료';
                                btn.style.backgroundColor = '#28a745';
                                btn.style.color = 'white';
                                setTimeout(() => {{
                                    btn.innerText = '📋 텍스트 복사하기';
                                    btn.style.backgroundColor = '#00BFFF';
                                    btn.style.color = '#0e1117';
                                }}, 2000);
                            }});
                        }}
                    </script>
                """, height=55)
                
                if st.button("🗑️ 삭제하기", key=f"del_{real_idx}"):
                    st.session_state.queue.pop(real_idx)
                    save_data(); st.rerun()

st.divider()
st.caption(f"© 2026 AI Post Assistant | 요청하신 표준어 및 구조 변경이 완료되었습니다.")
