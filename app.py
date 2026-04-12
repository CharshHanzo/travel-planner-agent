import asyncio
import os
from datetime import date

import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor


load_dotenv()

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_MODEL = "qwen-plus-2025-07-28"
WEATHER_MCP_URL = "http://127.0.0.1:8000/mcp"

STATUS_FLOW = [
    ("TravelSupervisor", "主管正在分派任务..."),
    ("WeatherAgent", "WeatherAgent 正在分析天气..."),
    ("ActivityAgent", "ActivityAgent 正在搜索活动..."),
    ("FoodAgent", "FoodAgent 正在推荐餐厅..."),
]

SUPERVISOR_PROMPT = """
你是出行规划主管。

对于每一个出行规划请求，你必须严格按顺序委派：
1. 先交给 WeatherAgent 获取天气与出行提醒
2. 再交给 ActivityAgent 获取活动与行程方向
3. 最后交给 FoodAgent 获取餐饮建议

不要跳过任何一个 Agent。
如果某个 Agent 暂时没有完全匹配的工具，就让它基于用户输入、其他 Agent 的上下文和已有工具结果给出简洁建议。
收集完三个 Agent 的结果后，再由你整合成最终答复。

最终答复要求：
1. 必须使用 Markdown
2. 使用 `# 最终行程建议` 作为标题
3. 至少包含“天气与出行提醒”“活动建议”“餐饮建议”“推荐行程”“预算建议”
4. 内容简洁、可执行，不要暴露中间推理过程
""".strip()


st.set_page_config(
    page_title="智能出行决策助手",
    page_icon="🧭",
    layout="centered",
)


st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #f6f8fb 0%, #eef3f8 100%);
        }
        .block-container {
            max-width: 860px;
            padding-top: 2.2rem;
            padding-bottom: 2rem;
        }
        .hero, .card {
            background: #ffffff;
            border-radius: 18px;
            padding: 1.3rem;
            box-shadow: 0 10px 30px rgba(31, 41, 55, 0.08);
            border: 1px solid rgba(148, 163, 184, 0.18);
        }
        .hero h1 {
            margin-bottom: 0.4rem;
            color: #0f172a;
            font-size: 2rem;
        }
        .hero p {
            margin-bottom: 0;
            color: #475569;
            line-height: 1.6;
        }
        .section-title {
            color: #0f172a;
            font-size: 1.02rem;
            font-weight: 600;
            margin-bottom: 0.8rem;
        }
        .tip {
            color: #475569;
            font-size: 0.95rem;
            line-height: 1.7;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_state() -> None:
    defaults = {
        "result_markdown": "",
        "request_error": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def get_mcp_import_error() -> str | None:
    try:
        import langchain_mcp_adapters.client  # noqa: F401
        import mcp  # noqa: F401
        return None
    except ModuleNotFoundError as exc:
        return f"缺少 Python 依赖：{exc.name}"


def extract_message_content(message: object) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        fragments = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                fragments.append(item.get("text", ""))
            else:
                fragments.append(str(item))
        return "\n".join(fragment for fragment in fragments if fragment)
    return str(content)


def render_status_flow(visited: set[str], current: str | None = None) -> str:
    lines = []
    for agent_name, label in STATUS_FLOW:
        if agent_name in visited:
            prefix = "✅"
        elif current == agent_name:
            prefix = "🔄"
        else:
            prefix = "⏳"
        lines.append(f"{prefix} {label}")
    return "\n\n".join(lines)


def detect_active_agent(namespace: tuple[str, ...], data: object) -> str | None:
    haystack = " ".join(namespace)
    if isinstance(data, dict):
        haystack = f"{haystack} {' '.join(data.keys())}"
    for agent_name, _ in STATUS_FLOW:
        if agent_name in haystack:
            return agent_name
    return None


@st.cache_resource(show_spinner=False)
def build_mcp_client():
    from langchain_mcp_adapters.client import MultiServerMCPClient

    return MultiServerMCPClient(
        {
            "weather": {
                "transport": "http",
                "url": WEATHER_MCP_URL,
            }
        }
    )


@st.cache_resource(show_spinner=False)
def build_travel_graph():
    client = build_mcp_client()
    mcp_tools = run_async(client.get_tools())

    model = ChatOpenAI(
        model=DASHSCOPE_MODEL,
        api_key=DASHSCOPE_API_KEY,
        base_url=DASHSCOPE_BASE_URL,
        temperature=0.4,
    )

    weather_agent = create_react_agent(
        model=model,
        tools=mcp_tools,
        name="WeatherAgent",
        prompt=(
            "你是 WeatherAgent，只负责天气与出行提醒。"
            "优先调用 MCP 工具 `get_weather` 获取天气结果。"
            "只输出天气和出行注意事项，不要回答活动或餐饮内容。"
        ),
    )
    activity_agent = create_react_agent(
        model=model,
        tools=mcp_tools,
        name="ActivityAgent",
        prompt=(
            "你是 ActivityAgent，只负责活动、景点和路线方向。"
            "当前工具来自统一的 MCP Client；如果没有完全匹配的活动工具，"
            "你可以基于用户输入、天气结果和城市常识给出简洁建议。"
            "不要回答餐饮内容。"
        ),
    )
    food_agent = create_react_agent(
        model=model,
        tools=mcp_tools,
        name="FoodAgent",
        prompt=(
            "你是 FoodAgent，只负责餐厅和用餐建议。"
            "当前工具来自统一的 MCP Client；如果没有完全匹配的餐饮工具，"
            "你可以基于用户预算、口味偏好、天气结果和城市常识给出简洁建议。"
            "不要回答活动内容。"
        ),
    )

    workflow = create_supervisor(
        [weather_agent, activity_agent, food_agent],
        model=model,
        prompt=SUPERVISOR_PROMPT,
        output_mode="last_message",
        parallel_tool_calls=False,
        supervisor_name="TravelSupervisor",
    )
    return workflow.compile(name="travel_planner_supervisor")


def build_user_request(
    city: str,
    travel_date: date,
    people_count: int,
    budget: int,
    taste: str,
    departure: str,
) -> str:
    departure_text = departure.strip() if departure.strip() else "未提供"
    return f"""
请为我生成一份城市出行建议，并综合天气、活动、餐饮三方面信息。

用户信息：
- 城市：{city}
- 日期：{travel_date.strftime("%Y-%m-%d")}
- 人数：{people_count}
- 总预算：{budget} 元
- 口味偏好：{taste}
- 出发地点：{departure_text}

要求：
1. 结果必须使用 Markdown
2. 用 `# 最终行程建议` 作为主标题
3. 行程要紧凑但不过满，优先给出当天可执行的安排
4. 如果信息不足，可以做合理假设，但要明确写出假设
5. 必须综合天气、活动、餐饮三个维度
""".strip()


def run_travel_graph(
    city: str,
    travel_date: date,
    people_count: int,
    budget: int,
    taste: str,
    departure: str,
) -> str:
    graph = build_travel_graph()
    user_message = build_user_request(
        city=city,
        travel_date=travel_date,
        people_count=people_count,
        budget=budget,
        taste=taste,
        departure=departure,
    )
    latest_messages = []
    visited_agents: set[str] = set()

    with st.status("多智能体正在协作...", expanded=True) as status:
        placeholder = st.empty()
        placeholder.markdown(render_status_flow(visited_agents, current="TravelSupervisor"))

        for namespace, mode, data in graph.stream(
            {"messages": [{"role": "user", "content": user_message}]},
            stream_mode=["updates", "values"],
            subgraphs=True,
        ):
            if mode == "updates":
                active_agent = detect_active_agent(namespace, data)
                if active_agent:
                    visited_agents.add(active_agent)
                    label = dict(STATUS_FLOW)[active_agent]
                    placeholder.markdown(render_status_flow(visited_agents, current=active_agent))
                    status.update(label=label, state="running", expanded=True)
            elif mode == "values" and not namespace and isinstance(data, dict) and "messages" in data:
                latest_messages = data["messages"]

        placeholder.markdown(render_status_flow(set(dict(STATUS_FLOW).keys())))
        status.update(label="决策完成", state="complete", expanded=True)

    if not latest_messages:
        raise RuntimeError("未从 LangGraph Supervisor 获取到最终消息。")

    return extract_message_content(latest_messages[-1])


init_state()
mcp_import_error = get_mcp_import_error()

st.markdown(
    """
    <div class="hero">
        <h1>智能出行决策助手</h1>
        <p>基于 LangGraph Supervisor 多智能体协作，生成一份简洁可执行的出行建议。</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")
st.markdown('<div class="section-title">出行信息</div>', unsafe_allow_html=True)

if not DASHSCOPE_API_KEY:
    st.error("未读取到 .env 中的 DASHSCOPE_API_KEY，请先配置后再使用。")
elif mcp_import_error:
    st.error(
        f"{mcp_import_error}。当前项目使用 MCP 客户端，在 Windows 下还需要安装 `pywin32`。"
    )

with st.form("travel_form"):
    left_col, right_col = st.columns(2)

    with left_col:
        city = st.text_input("城市", value="广州", placeholder="例如：广州")
        travel_date = st.date_input("日期选择", value=date.today(), min_value=date.today())
        people_count = st.number_input("人数", min_value=1, max_value=10, value=2, step=1)

    with right_col:
        budget = st.number_input("预算（元）", min_value=0, value=300, step=50)
        taste = st.selectbox("口味偏好", ["辣", "清淡", "不挑"], index=2)
        departure = st.text_input("出发地点（可选）", placeholder="例如：天河区、广州南站")

    submitted = st.form_submit_button(
        "生成建议",
        use_container_width=True,
        disabled=not DASHSCOPE_API_KEY or mcp_import_error is not None,
    )


if submitted and DASHSCOPE_API_KEY and not mcp_import_error:
    st.session_state.request_error = ""
    st.session_state.result_markdown = ""
    try:
        st.session_state.result_markdown = run_travel_graph(
            city=city.strip() or "广州",
            travel_date=travel_date,
            people_count=int(people_count),
            budget=int(budget),
            taste=taste,
            departure=departure,
        )
    except Exception as exc:
        st.session_state.request_error = f"调用 LangGraph Supervisor 失败：{exc}"


if st.session_state.request_error:
    st.error(st.session_state.request_error)


st.write("")
if st.session_state.result_markdown:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("结果展示")
    st.markdown(st.session_state.result_markdown)
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.markdown(
        """
        <div class="card tip">
            提交后会调用 LangGraph Supervisor 多智能体流程，并在这里渲染 Markdown 格式的最终行程建议。
        </div>
        """,
        unsafe_allow_html=True,
    )
