import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import time

# --- 环境加载与配置 ---
current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, ".env"))
st.set_page_config(page_title="Prompt 炼金室", page_icon="⚗️", layout="wide")

# --- 高级赛博紫蓝风格 CSS ---
st.markdown(f"""
<style>
    .stApp {{
        background-color: #121826;
        color: #E0E6FF;
    }}
    .stTextArea, .stSelectbox, .stExpander {{
        background-color: #1E293B !important;
        border-radius: 16px;
        border: 1px solid #2b3647;
    }}
    .main-title {{
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(45deg, #7B61FF, #58A6FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 25px rgba(123, 97, 255, 0.3);
        margin-bottom: 20px;
    }}
    div.stButton > button:first-child {{
        background: linear-gradient(135deg, #7B61FF 0%, #58A6FF 100%);
        color: white;
        border: none;
        padding: 0.7rem 2rem;
        border-radius: 50px;
        font-weight: bold;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(123, 97, 255, 0.3);
        width: 100%;
    }}
    div.stButton > button:first-child:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(123, 97, 255, 0.4);
    }}
    .result-card {{
        background: #1E293B;
        border: 1px solid #7B61FF33;
        padding: 20px;
        border-radius: 18px;
        box-shadow: 0 0 20px rgba(123, 97, 255, 0.05);
    }}
    .stToggle [data-testid="stToggle"] {{
        background-color: #7B61FF;
    }}
</style>
""", unsafe_allow_html=True)

# ======================= 会话状态初始化 =======================
if "history" not in st.session_state:
    st.session_state.history = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "favorites" not in st.session_state:
    st.session_state.favorites = []
if "input_cache" not in st.session_state:
    st.session_state.input_cache = ""

# ======================= API 初始化 =======================
api_key = os.getenv("DEEPSEEK_API_KEY")
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com") if api_key else None

# ======================= 【功能2】场景模板库 =======================
templates = {
    "请选择模板": "",
    "小红书爆款文案": "请帮我写一篇小红书风格的文案，主题清晰，有吸引力，带emoji，分段清晰，口语化强。",
    "职场周报模板": "请帮我生成一份专业周报，包含本周工作、遇到问题、下周计划，简洁专业。",
    "代码生成指令": "你是专业程序员，请按清晰步骤、带注释、可直接运行来实现需求。",
    "学术摘要优化": "请用学术化、严谨、简洁、正式的语言优化这段内容。",
    "短视频脚本": "请生成一个口播类短视频脚本，有镜头感、节奏快、有记忆点、有吸引力。",
    "简历 bullet 优化": "请把这段经历改成专业简历 bullet，量化成果，动词开头。"
}

# ======================= 【功能5】角色预设库 =======================
roles = {
    "通用Prompt专家": "你是专业的Prompt工程师，擅长结构化、清晰化指令。",
    "产品经理": "你是资深产品经理，逻辑清晰，输出结构完整。",
    "前端工程师": "你是专业前端，擅长HTML/CSS/JS，代码规范易懂。",
    "后端工程师": "你是后端开发者，注重逻辑、安全、效率。",
    "设计师": "你是UI/UX设计师，输出美观、用户体验优先。",
    "职场顾问": "你是资深职场顾问，表达专业、得体、高效。",
    "语文老师": "你是语文教师，文笔优美，逻辑通顺，修辞恰当。",
    "健身教练": "你是专业健身教练，给出科学、安全、可执行的计划。"
}

# ======================= 侧边栏：历史 + 收藏 + 搜索 =======================
with st.sidebar:
    st.markdown("### 📜 炼金遗迹")
    search = st.text_input("🔍 搜索历史", placeholder="输入关键词搜索")
    if st.button("清空遗迹"):
        st.session_state.history = []
        st.rerun()

    filtered = [item for item in st.session_state.history if search.lower() in item["raw"].lower() or search.lower() in item.get("alias", "").lower()]

    for idx, item in enumerate(reversed(filtered)):
        title = item.get("alias", f"🔮 {item['time']} - {item['style']}")
        with st.expander(title):
            st.caption(item["raw"][:50] + "..." if len(item["raw"]) > 50 else item["raw"])
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button(f"复用", key=f"reuse_{idx}"):
                    st.session_state.input_cache = item["raw"]
                    st.rerun()
            with col_b:
                fav = "⭐ 已收藏" if item in st.session_state.favorites else "☆ 收藏"
                if st.button(fav, key=f"fav_{idx}"):
                    if item in st.session_state.favorites:
                        st.session_state.favorites.remove(item)
                    else:
                        st.session_state.favorites.append(item)
                    st.rerun()
            new_name = st.text_input("重命名", key=f"alias_{idx}", label_visibility="collapsed", placeholder="输入别名")
            if new_name:
                item["alias"] = new_name

# ======================= 主界面 =======================
st.markdown('<h1 class="main-title">⚗️ Prompt 炼金室</h1>', unsafe_allow_html=True)
col_input, col_result = st.columns([1, 1.2], gap="large")

# ======================= 左侧：炼金区 =======================
with col_input:
    st.markdown("### ⚒️ 投料锻造")

    # ======================= 【新增】自定义场景模板 =======================
    tpl = st.selectbox("📋 常用场景模板", options=list(templates.keys()) + ["✅ 自定义模板"])
    if tpl == "✅ 自定义模板":
        custom_template = st.text_area("输入你的自定义模板", placeholder="例如：请帮我生成一份专业推广文案...")
        st.session_state.input_cache = custom_template
    else:
        if templates[tpl]:
            st.session_state.input_cache = templates[tpl]

    # ======================= 【新增】自定义AI角色 =======================
    role_options = list(roles.keys()) + ["✅ 自定义角色"]
    selected_role = st.selectbox("👤 设定AI角色", options=role_options)
    if selected_role == "✅ 自定义角色":
        custom_role = st.text_input("输入自定义角色", placeholder="例如：专业理财顾问、心理咨询师...")
        role_content = custom_role
    else:
        role_content = roles[selected_role]

    # 输入框
    user_input = st.text_area(
        "原料仓",
        value=st.session_state.input_cache,
        height=220,
        placeholder="输入你的需求，一键生成专业Prompt",
        label_visibility="collapsed"
    )

    # 功能选项
    col1, col2 = st.columns(2)
    with col1:
        # ======================= 【新增】自定义炼金流派 =======================
        style_options = ["通用", "小红书", "学术", "代码", "职场", "✅ 自定义流派"]
        style_preset = st.selectbox("炼金流派", style_options)
        if style_preset == "✅ 自定义流派":
            custom_style = st.text_input("输入自定义流派", placeholder="例如：幽默搞笑、严肃正式、文艺温柔...")
            style_preset = custom_style
    with col2:
        mode = st.selectbox("输出模式", ["标准版", "三风格对比版", "中英双语版"])

    # 【功能4】智能中英互译
    translate_mode = st.selectbox("翻译模式", ["不翻译", "中文→英文Prompt", "英文→中文Prompt"])

    # 【功能6】约束自动补全
    auto_constraint = st.checkbox("自动补充约束（字数/格式/结构）")

    if st.button("🔥 开始炼金"):
        if not api_key:
            st.error("请配置API Key")
        elif not user_input.strip():
            st.warning("请输入需求内容")
        else:
            with st.spinner("炼金进行中..."):
                # ====================== 系统提示词 ======================
                sys = f"""
你是专业Prompt工程师，只做一件事：将用户的白话需求，优化为【专业结构化Prompt】。
绝对不要直接生成文案、代码、周报、脚本等最终内容！
严格按 Role-Context-Task-Constraints 输出。
角色：{selected_role}
风格：{style_preset}
"""
                if auto_constraint:
                    sys += "\n请自动补充合理的约束条件：字数、格式、输出结构、语气、禁止内容。"
                if translate_mode == "中文→英文Prompt":
                    sys += "\n最终输出：AI专用地道英文Prompt。"
                if translate_mode == "英文→中文Prompt":
                    sys += "\n最终输出：专业中文结构化Prompt。"
                if mode == "三风格对比版":
                    sys += "\n请输出三个版本：简洁版、详细版、专业版，清晰分块。每个版本都只输出Prompt，不生成内容。"
                if mode == "中英双语版":
                    sys += "\n输出：中文专业Prompt + 英文专业Prompt。"

                # 调用DeepSeek API
                resp = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "system", "content": sys}, {"role": "user", "content": user_input}]
                )
                res = resp.choices[0].message.content

                st.session_state.last_result = {
                    "optimized": res,
                    "log": f"角色：{selected_role} | 风格：{style_preset} | 约束：{'自动补全' if auto_constraint else '无'}"
                }

                st.session_state.history.append({
                    "time": datetime.now().strftime("%H:%M"),
                    "style": style_preset,
                    "raw": user_input,
                    "result": res,
                    "alias": ""
                })

# ======================= 右侧：结果展示 =======================
with col_result:
    st.markdown("### 💎 锻造产物")
    if st.session_state.last_result:
        with st.container():
            st.markdown('<div class="result-card">', unsafe_allow_html=True)
            st.code(st.session_state.last_result["optimized"], language="markdown")
            st.caption(st.session_state.last_result["log"])
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("⚗️ 炼金炉已就绪，请投入原料")