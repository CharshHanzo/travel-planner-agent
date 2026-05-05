import asyncio
import os
import logging
import signal
import sys
from datetime import date
from concurrent.futures import ThreadPoolExecutor
import functools
from contextlib import contextmanager
from typing import Optional
import inspect

import streamlit as st
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langchain_openai import ChatOpenAI
from langchain_core.tools import StructuredTool

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局线程池，避免重复创建
_THREAD_POOL = ThreadPoolExecutor(max_workers=10)

@contextmanager
def timeout(seconds: int):
    """跨平台的超时上下文管理器"""
    if sys.platform == 'win32':
         # Windows 不支持 SIGALRM，使用线程方式
        import threading
        import time
         
        class TimeoutThread(threading.Thread):
            def __init__(self, timeout_seconds):
                super().__init__()
                self.timeout_seconds = timeout_seconds
                self.timed_out = False
                
            def run(self):
                time.sleep(self.timeout_seconds)
                self.timed_out = True
        
        # 启动超时监控线程
        timeout_thread = TimeoutThread(seconds)
        timeout_thread.daemon = True
        timeout_thread.start()
        
        try:
            yield
            # 如果任务完成，停止超时线程
            timeout_thread.timed_out = True
        except:
            # 如果发生异常，也停止超时线程
            timeout_thread.timed_out = True
            raise
        finally:
            # 检查是否超时
            if timeout_thread.is_alive():
                raise TimeoutError(f"操作超时（{seconds}秒）")
    else:
        # Unix/Linux/Mac 使用信号
        def timeout_handler(signum, frame):
            raise TimeoutError(f"操作超时（{seconds}秒）")
        
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

load_dotenv()

# LLM Provider Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "xiaomi")  # dashscope, xiaomi

# DashScope Configuration
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "")

# XIAOMI Configuration
XIAOMI_API_KEY = os.getenv("XIAOMI_API_KEY")
XIAOMI_BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
XIAOMI_MODEL = os.getenv("XIAOMI_MODEL", "MiMo-V2.5")

TRAVEL_TOOLS_MCP_URL = "http://127.0.0.1:8000/sse"


def create_llm_model():
    """根据配置创建LLM模型"""
    if LLM_PROVIDER == "dashscope":
        return ChatOpenAI(
            model=DASHSCOPE_MODEL,
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
            temperature=0.5,
        )
    elif LLM_PROVIDER == "xiaomi":
        return ChatOpenAI(
            model=XIAOMI_MODEL,
            api_key=XIAOMI_API_KEY,
            base_url=XIAOMI_BASE_URL,
            temperature=0.5,
        )
    else:
        raise ValueError(f"不支持的LLM提供商: {LLM_PROVIDER}")


STATUS_FLOW = [
    ("TravelSupervisor", "主管正在分派任务..."),
    ("WeatherAgent", "WeatherAgent 正在获取天气信息..."),
    ("ActivityAgent", "ActivityAgent 正在搜索活动..."),
    ("FoodAgent", "FoodAgent 正在推荐餐厅..."),
]

SUPERVISOR_PROMPT = """
    你是出行规划主管。

    对于每一个出行规划请求，你必须严格按顺序委派：
    1. 先交给 WeatherAgent 获取天气与出行提醒
    2. 再交给 ActivityAgent 获取活动与行程方向
    3. 最后交给 FoodAgent 获取餐饮建议

    重要提示：
    - ActivityAgent 可以使用 search_activities 和 plan_route 工具
    - FoodAgent 会从 WeatherAgent 的输出中解析天气信息
    - 不要跳过任何一个 Agent

    收集完三个 Agent 的结果后，由你整合成最终答复。

    最终答复要求：
    1. 必须使用 Markdown
    2. 使用 `# 最终行程建议` 作为标题
    3. 必须包含以下章节：
        - ## 天气与出行提醒
        - ## 活动建议（包含具体景点和路线）
        - ## 餐饮建议
        - ## 推荐行程（时间线）
        - ## 预算建议
    4. 内容简洁、可执行，不要暴露中间推理过程
    5. 行程要紧凑但不过满，优先给出当天可执行的安排
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
    """使用全局线程池运行异步函数"""
    future = _THREAD_POOL.submit(asyncio.run, coro)
    return future.result()


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
def build_mcp_tools():
    """构建MCP客户端并返回工具列表"""
    from langchain_mcp_adapters.client import MultiServerMCPClient
    
    try:
        client = MultiServerMCPClient(
            {
                "travel_tools": {
                    "transport": "sse",
                    "url": TRAVEL_TOOLS_MCP_URL,
                }
            }
        )
        
        async def _get_tools():
            tools = await client.get_tools()
            logger.info(f"成功获取 {len(tools)} 个MCP工具")
            for tool in tools:
                logger.info(f"  - {tool.name}")
            return tools
        
        mcp_tools = run_async(_get_tools())
        return mcp_tools
    except Exception as e:
        logger.error(f"获取MCP工具失败: {e}")
        st.error(f"无法连接到 MCP 服务器，请确保 travel_tools_server.py 已启动。错误: {e}")
        return []


@st.cache_resource(ttl=300, show_spinner=False)  # 5分钟过期
def build_travel_graph():
    """
    构建多智能体旅行规划图
    """
    
    # 获取MCP工具
    mcp_tools = build_mcp_tools()
    
    print(f"[INFO] 加载了 {len(mcp_tools)} 个MCP工具")
    
    if not mcp_tools:
        print("[WARNING] 没有加载到任何工具，将使用无工具的Agent")

    # 创建模型
    model = create_llm_model()

    def create_sync_wrapper(async_func, name: str, description: str, args_schema=None):
        @functools.wraps(async_func)
        def sync_func(**kwargs):
            # 始终在新线程中运行，避免事件循环冲突
            future = _THREAD_POOL.submit(asyncio.run, async_func(**kwargs))
            return future.result()
        
        return StructuredTool.from_function(
            func=sync_func,
            name=name,
            description=description,
            args_schema=args_schema,
        )
    
    # 包装所有MCP工具为同步工具
    sync_tools = []
    for tool in mcp_tools:
        try:
            tool_name = getattr(tool, 'name', str(tool))
            tool_description = getattr(tool, 'description', '')
            tool_args_schema = getattr(tool, 'args_schema', None)
            
            # 获取异步函数
            async_func = None
            if hasattr(tool, '_run') and inspect.iscoroutinefunction(tool._run):
                async_func = tool._run
            elif hasattr(tool, 'coroutine') and inspect.iscoroutinefunction(tool.coroutine):
                async_func = tool.coroutine
            elif callable(tool) and inspect.iscoroutinefunction(tool):
                async_func = tool
            
            if async_func:
                # 创建同步包装器
                sync_tool = create_sync_wrapper(
                    async_func=async_func,
                    name=tool_name,
                    description=tool_description,
                    args_schema=tool_args_schema
                )
                sync_tools.append(sync_tool)
            else:
                # 已经是同步的，直接使用
                sync_tools.append(tool)
                
        except Exception as e:
            logger.warning(f"包装工具失败: {e}")
            sync_tools.append(tool)
    
    logger.info(f"成功包装 {len(sync_tools)} 个同步工具")
    
    # 打印可用工具名称
    tool_names = [getattr(t, 'name', str(t)) for t in sync_tools]
    logger.info(f"可用工具: {tool_names}")
    
    # 创建 WeatherAgent
    weather_tools = [t for t in sync_tools if t.name == 'get_weather']
    weather_agent = create_react_agent(
        model=model,
        tools=weather_tools,
        name="WeatherAgent",
        prompt=(
            "你是 WeatherAgent，只负责天气与出行提醒。\n\n"
            "你有以下 MCP 工具可用：\n"
            "- get_weather(city, date): 获取指定城市在目标日期的天气信息\n\n"
            "工作流程：\n"
            "1. 调用 get_weather 获取用户指定城市和日期的天气\n"
            "2. 根据天气给出出行建议（如带伞、防晒、增减衣物）\n\n"
            "输出格式要求（重要）：\n"
            "最后必须输出一个 JSON 块，格式如下：\n"
            "```json\n"
            "{\n"
            "  \"weather_desc\": \"天气描述，如：晴、小雨、多云等\",\n"
            "  \"temperature\": 温度数值,\n"
            "  \"advice\": \"出行建议文本\"\n"
            "}\n"
            "```\n\n"
            "这个 JSON 将被传递给 FoodAgent 用于天气相关的餐饮推荐。\n\n"
            "只输出天气信息、出行建议和上述 JSON，不要回答活动或餐饮内容。"
        ),
    )
    
    # 创建 ActivityAgent
    activity_tools = [t for t in sync_tools if t.name in ['search_activities', 'plan_route']]
    activity_agent = create_react_agent(
        model=model,
        tools=activity_tools,
        name="ActivityAgent",
        prompt=(
            "你是 ActivityAgent，负责活动、景点和路线规划。\n\n"
            "你有以下 MCP 工具可用：\n"
            "1. search_activities(city, keyword, limit) - 搜索目的地的景点、活动、节庆等\n"
            "2. plan_route(activities, start_point) - 规划多个活动的游览顺序和交通时间\n\n"
            "重要提示：\n"
            "- search_activities 返回的结果中，每个活动包含 location 字段（坐标格式如 '113.324553,23.106414'）\n"
            "- 在调用 plan_route 时，必须使用 search_activities 返回的完整活动对象\n"
            "- plan_route 返回结果中的 optimized_activities 可以直接用于后续步骤\n"
            "- 如果用户提供了出发地点（departure），必须将其作为 start_point 参数传入 plan_route\n\n"
            "工作流程：\n"
            "第一步：调用 search_activities 搜索景点（limit=5）\n"
            "第二步：从返回结果中提取 activities 列表（包含 name 和 location）\n"
            "第三步：调用 plan_route，传入 activities 和 start_point（如果有）\n"
            "第四步：从 plan_route 结果中提取 optimized_order 和 segments 用于最终输出\n\n"
            "不要回答餐饮内容。"
        ),
    )
    
    # 创建 FoodAgent
    food_tools = [t for t in sync_tools if t.name in [
        'search_restaurants',
        'recommend_meal_plan',
        'get_restaurant_detail',
        'recommend_by_cuisine'
    ]]
    food_agent = create_react_agent(
        model=model,
        tools=food_tools,
        name="FoodAgent",
        prompt=(
            "你是 FoodAgent，只负责餐厅和用餐建议。\n\n"
            "你有以下 MCP 工具可用：\n"
            "1. search_restaurants(city, location, keyword, budget, taste, limit) - 搜索餐厅\n"
            "2. recommend_meal_plan(activities, city, taste, budget, people_count, weather_context) - 推荐用餐计划\n"
            "3. get_restaurant_detail(restaurant_id) - 获取餐厅详情\n"
            "4. recommend_by_cuisine(city, cuisine, location, budget, limit) - 按菜系推荐\n\n"
            "重要提示：\n"
            "- recommend_meal_plan 的 weather_context 参数格式：{\"weather_desc\": \"晴\", \"temperature\": 25}\n"
            "- 上一个 Agent（WeatherAgent）的输出末尾会有一个 JSON 块，格式如下：\n"
            "  ```json\n"
            "  {\"weather_desc\": \"天气描述\", \"temperature\": 温度数值, \"advice\": \"出行建议\"}\n"
            "  ```\n"
            "- 请从 WeatherAgent 的输出中解析这个 JSON，并传入 weather_context\n"
            "- 如果无法解析天气信息，weather_context 可以传 None\n\n"
            "工作流程：\n"
            "第一步：解析天气信息（如果可用）\n"
            "第二步：调用 recommend_meal_plan，传入 activities、city、taste、budget、people_count 和 weather_context\n"
            "第三步：如果需要更详细的餐厅信息，调用 get_restaurant_detail\n"
            "第四步：如果用户有特定菜系偏好，调用 recommend_by_cuisine\n\n"
            "输出要求：\n"
            "1. 推荐 2-3 家符合用户口味和预算的餐厅\n"
            "2. 结合活动位置，建议就近用餐\n"
            "3. 结合天气，给出用餐建议\n"
            "4. 估算每餐费用\n"
            "5. 不要回答活动内容"
        ),
    )

    # 创建 Supervisor
    workflow = create_supervisor(
        [weather_agent, activity_agent, food_agent],
        model=model,
        prompt=SUPERVISOR_PROMPT,
        output_mode="last_message",
        parallel_tool_calls=False,
        supervisor_name="TravelSupervisor",
    )
    
    return workflow.compile(name="travel_planner_supervisor")


def validate_inputs(city: str, travel_date: date, people_count: int, budget: int) -> tuple[bool, str]:
    """验证用户输入"""
    from datetime import timedelta
    
    if not city or not city.strip():
        return False, "城市名称不能为空"
    
    if len(city) > 50:
        return False, "城市名称过长"
    
    if people_count <= 0 or people_count > 20:
        return False, "人数必须在1-20之间"
    
    if budget <= 0:
        return False, "预算必须大于0"
    
    if budget > 100000:
        return False, "预算不能超过100000元"
    
    # 检查日期是否合理
    if travel_date < date.today():
        return False, "不能选择过去的日期"
    
    if travel_date > date.today() + timedelta(days=30):
        return False, "最多只能规划未来30天的行程"
    
    return True, ""


def build_user_request(
    city: str,
    travel_date: date,
    people_count: int,
    budget: int,
    taste: str,
    departure: str,
    activity_count: int = 3
) -> str:
    departure_text = departure.strip() if departure.strip() else "未提供"
    
    # 计算相对日期（修复日期逻辑bug）
    from datetime import date as date_type, timedelta
    today = date_type.today()
    
    def get_relative_date_str(travel_date: date, today: date) -> str:
        delta = (travel_date - today).days
        if delta == 0:
            return "今天"
        elif delta == 1:
            return "明天"
        elif delta == 2:
            return "后天"
        else:
            return travel_date.strftime("%Y-%m-%d")
    
    date_str = get_relative_date_str(travel_date, today)
    
    return f"""
请为我生成一份城市出行建议，并综合天气、活动、餐饮三方面信息。

用户信息：
- 城市：{city}
- 日期：{date_str}（对应 {travel_date.strftime("%Y-%m-%d")}）
- 人数：{people_count}
- 总预算：{budget} 元
- 口味偏好：{taste}
- 出发地点：{departure_text}
- 推荐活动数量：{activity_count}

⚠️ 重要：
- 如果出发地点不为空，ActivityAgent 在调用 plan_route 时必须将其作为 start_point 参数传入
- ActivityAgent 搜索活动时请使用 limit={activity_count}

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
    activity_count: int = 3,
    timeout_seconds: int = 60
) -> str:
    """添加超时控制"""
    try:
        graph = build_travel_graph()
        user_message = build_user_request(
            city=city,
            travel_date=travel_date,
            people_count=people_count,
            budget=budget,
            taste=taste,
            departure=departure,
            activity_count=activity_count
        )
        latest_messages = []
        visited_agents: set[str] = set()

        with st.status("多智能体正在协作...", expanded=True) as status:
            placeholder = st.empty()
            placeholder.markdown(render_status_flow(visited_agents, current="TravelSupervisor"))

            # 使用超时控制
            with timeout(timeout_seconds):
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
    
    except TimeoutError as e:
        raise RuntimeError(f"任务执行超时：{e}")
    except ConnectionError as e:
        raise RuntimeError(f"无法连接到 MCP 服务器：{e}")
    except ValueError as e:
        raise RuntimeError(f"数据格式错误：{e}")
    except Exception as e:
        raise RuntimeError(f"未知错误：{e}")


# ========== 主程序入口 ==========
init_state()
mcp_import_error = get_mcp_import_error()

# # 检查 MCP 服务器是否可用
# @st.cache_resource(show_spinner=False)
# def check_mcp_server():
#     """更可靠的服务器健康检查"""
#     try:
#         import httpx
#         # SSE 端点可能需要特定的请求头
#         response = httpx.get(
#             "http://127.0.0.1:8000/sse",
#             timeout=2.0,
#             follow_redirects=True
#         )
#         # 检查响应状态和内容类型
#         return response.status_code in [200, 202]
#     except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadTimeout):
#         return False
        
# mcp_available = check_mcp_server()
mcp_available = True
if not mcp_available:
    st.warning("⚠️ MCP 服务器未启动，请先运行 travel_tools_server.py")

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
        activity_count = st.slider("推荐活动数量", min_value=2, max_value=5, value=3)
        departure = st.text_input("出发地点（可选）", placeholder="例如：天河区、广州南站")

    submitted = st.form_submit_button(
        "生成建议",
        use_container_width=True,
        disabled=not DASHSCOPE_API_KEY or mcp_import_error is not None,
    )


if submitted and DASHSCOPE_API_KEY and not mcp_import_error:
    st.session_state.request_error = ""
    st.session_state.result_markdown = ""
    
    # 验证输入
    is_valid, error_msg = validate_inputs(city.strip(), travel_date, int(people_count), int(budget))
    if not is_valid:
        st.session_state.request_error = f"输入验证失败：{error_msg}"
    else:
        try:
            st.session_state.result_markdown = run_travel_graph(
                city=city.strip() or "广州",
                travel_date=travel_date,
                people_count=int(people_count),
                budget=int(budget),
                taste=taste,
                departure=departure,
                activity_count=int(activity_count)
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

is_langgraph_cli = os.path.exists("langgraph.json")

if is_langgraph_cli:
    # LangGraph CLI 模式：导出 graph 供 Studio 使用
    # 注意：这会立即构建 graph，可能需要几秒钟
    travel_graph = build_travel_graph()
else:
    # Streamlit 模式：正常启动
    # graph 会在用户提交表单时动态构建，不在这里导出
    pass