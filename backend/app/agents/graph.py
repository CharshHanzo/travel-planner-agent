import logging
import functools
from datetime import datetime, timedelta

from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.agents.tools import get_mcp_tools, wrap_mcp_tools, run_async
from app.agents.prompts import SUPERVISOR_PROMPT, CHAT_SUPERVISOR_PROMPT, WEATHER_AGENT_PROMPT, ACTIVITY_AGENT_PROMPT, FOOD_AGENT_PROMPT, ROUTE_AGENT_PROMPT
from app.core.config import settings

# 配置日志
logger = logging.getLogger(__name__)


def create_llm_model():
    """根据配置创建LLM模型"""
    if settings.LLM_PROVIDER == "dashscope":
        return ChatOpenAI(
            model=settings.DASHSCOPE_MODEL,
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL,
            temperature=0.5,
        )
    elif settings.LLM_PROVIDER == "xiaomi":
        return ChatOpenAI(
            model=settings.XIAOMI_MODEL,
            api_key=settings.XIAOMI_API_KEY,
            base_url=settings.XIAOMI_BASE_URL,
            temperature=0.5,
            extra_body={
                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            },
        )
    else:
        raise ValueError(f"不支持的LLM提供商: {settings.LLM_PROVIDER}")

@functools.lru_cache(maxsize=1)
def build_travel_graph():
    """构建并返回编译后的 LangGraph 主管图"""
    
    # 获取 MCP 工具
    mcp_tools = run_async(get_mcp_tools())
    
    logger.info(f"加载了 {len(mcp_tools)} 个 MCP 工具")
    
    if not mcp_tools:
        logger.warning("没有加载到任何工具，将使用无工具的 Agent")

    # 创建模型
    model = create_llm_model()

    # 包装所有 MCP 工具为同步工具
    sync_tools = wrap_mcp_tools(mcp_tools)
    
    # 创建 WeatherAgent
    weather_tools = [t for t in sync_tools if t.name == 'get_weather']
    weather_agent = create_react_agent(
        model=model,
        tools=weather_tools,
        name="WeatherAgent",
        prompt=WEATHER_AGENT_PROMPT,
    )
    
    # 创建 ActivityAgent
    activity_tools = [t for t in sync_tools if t.name == 'search_activities']
    activity_agent = create_react_agent(
        model=model,
        tools=activity_tools,
        name="ActivityAgent",
        prompt=ACTIVITY_AGENT_PROMPT,
    )
    
    # 创建 FoodAgent
    food_tools = [t for t in sync_tools if t.name == 'search_restaurants']
    food_agent = create_react_agent(
        model=model,
        tools=food_tools,
        name="FoodAgent",
        prompt=FOOD_AGENT_PROMPT,
    )
    
    # 创建 RouteAgent
    route_tools = [t for t in sync_tools if t.name == 'plan_route']
    route_agent = create_react_agent(
        model=model,
        tools=route_tools,
        name="RouteAgent",
        prompt=ROUTE_AGENT_PROMPT,
    )

    # 创建 Supervisor
    workflow = create_supervisor(
        [weather_agent, activity_agent, food_agent, route_agent],
        model=model,
        prompt=SUPERVISOR_PROMPT,
        output_mode="last_message",
        parallel_tool_calls=False,
        supervisor_name="TravelSupervisor",
    )
    
    return workflow.compile(name="travel_planner_supervisor")

class ChatSupervisor:
    """对话式规划主管"""
    
    def __init__(self):
        """初始化 ChatSupervisor（不加载 MCP 工具）"""
        self.model = create_llm_model()
        self._initialized = False
        self.weather_agent = None
        self.activity_agent = None
        self.food_agent = None
        self.route_agent = None
    
    def initialize(self, sync_tools):
        """真正的初始化，传入已加载的工具"""
        if self._initialized:
            return
        
        logger.info(f"开始初始化 ChatSupervisor，工具数量: {len(sync_tools)}")
        
        weather_tools = [t for t in sync_tools if t.name == 'get_weather']
        self.weather_agent = create_react_agent(
            model=self.model,
            tools=weather_tools,
            name="WeatherAgent",
            prompt=WEATHER_AGENT_PROMPT,
        )
        logger.info(f"WeatherAgent 初始化完成，工具数量: {len(weather_tools)}")
        
        activity_tools = [t for t in sync_tools if t.name == 'search_activities']
        self.activity_agent = create_react_agent(
            model=self.model,
            tools=activity_tools,
            name="ActivityAgent",
            prompt=ACTIVITY_AGENT_PROMPT,
        )
        logger.info(f"ActivityAgent 初始化完成，工具数量: {len(activity_tools)}")
        
        food_tools = [t for t in sync_tools if t.name == 'search_restaurants']
        self.food_agent = create_react_agent(
            model=self.model,
            tools=food_tools,
            name="FoodAgent",
            prompt=FOOD_AGENT_PROMPT,
        )
        logger.info(f"FoodAgent 初始化完成，工具数量: {len(food_tools)}")
        
        route_tools = [t for t in sync_tools if t.name == 'plan_route']
        if route_tools:
            self.route_agent = create_react_agent(
                model=self.model,
                tools=route_tools,
                name="RouteAgent",
                prompt=ROUTE_AGENT_PROMPT,
            )
            logger.info(f"RouteAgent 初始化完成，工具数量: {len(route_tools)}")
        else:
            logger.warning("RouteAgent 未找到 plan_route 工具，跳过初始化")
        
        self._initialized = True
        logger.info("ChatSupervisor 初始化完成")
    
    def identify_intent(self, user_message):
        """识别用户意图"""
        prompt = f"""
        请分析用户消息，识别其意图类别。

        意图类别说明：
        - weather: 用户在询问天气（如"天气怎么样""会下雨吗""温度多少"）
        - activities: 用户在询问景点、活动、游玩（如"有什么好玩的""推荐景点""去哪玩"）
        - food: 用户在询问美食、餐厅、吃的（如"有什么好吃的""推荐餐厅""想吃火锅"）
        - generate_plan: 用户要求生成完整旅行计划（如"生成计划""帮我规划""做个行程"）
        - modify: 用户要求修改之前的推荐（如"换个便宜的""有没有更近的""重新推荐"）
        - general: 无法归入以上类别的消息（如问候、闲聊、仅提供信息不含明确请求）
        
        重要判断规则：
        - 如果用户只是说"想去XX玩"、"想去XX旅游"但没明确说要查天气/活动/美食，视为 general
        - 如果用户说"推荐"、"有什么"、"帮我查"等明确请求，按内容归类
        
        用户消息：{user_message}
        
        请只返回意图类别单词（weather/activities/food/generate_plan/modify/general），不要返回其他内容。
        """
        
        response = self.model.invoke(prompt)
        intent = response.content.strip().lower()
        
        valid_intents = ['weather', 'activities', 'food', 'generate_plan', 'modify', 'general']
        if intent not in valid_intents:
            logger.warning(f"无效意图 '{intent}'，回退为 general")
            return 'general'
        
        logger.info(f"意图识别：'{user_message}' → {intent}")
        return intent
    
    def extract_city(self, user_message, context):
        """从用户消息中提取城市，已有则不覆盖（除非明确指定新城市）"""
        prompt = f"""
        请从用户消息中提取目的地城市名称。
        用户消息：{user_message}
        请只返回城市名称。如果没有提到城市，返回空字符串。
        """
        
        response = self.model.invoke(prompt)
        city = response.content.strip()
        
        # 如果提取到新城市，覆盖旧值
        if city:
            return city
        # 否则保留已有城市
        return context.get('city')
    
    def extract_preferences(self, user_message, context):
        """从用户消息中提取偏好信息"""
        preferences = context.get('preferences', {})
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        prompt = f"""
        当前日期是 {today}，明天是 {tomorrow}。请从用户消息中提取以下偏好信息：
        - date: 日期（YYYY-MM-DD格式）
          - "今天" = {today}
          - "明天" = {tomorrow}
          - "后天" = {(datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")}
          - "五月四日" → {datetime.now().year}-05-04
          - "下周三" → 需要根据今天的星期几推算
        - budget: 预算（数字）
        - taste: 口味（辣/清淡/不挑）
        - people: 人数（数字）
        - transport_mode: 出行方式（walking/transit/driving/any）
          - "步行" = walking
          - "走路" = walking
          - "公共交通" = transit
          - "地铁" = transit
          - "公交" = transit
          - "自驾" = driving
          - "开车" = driving
          - "打车" = driving
          - "不限" = any
        
        用户消息：{user_message}
        
        请返回 JSON 格式，例如：
        {{"date": "{tomorrow}", "budget": 500, "taste": "辣", "people": 2, "transport_mode": "any"}}
        
        如果没有提到某项，对应字段设为 null。
        """
        
        response = self.model.invoke(prompt)
        import json
        try:
            extracted = json.loads(response.content)
            for key, value in extracted.items():
                # 过滤掉字符串 'None'、'null'、空字符串
                if value is None or value == 'None' or value == 'null' or value == '':
                    continue
                # budget 和 people 必须转为 int
                if key in ('budget', 'people') and value is not None:
                    try:
                        preferences[key] = int(value)
                    except (ValueError, TypeError):
                        pass  # 无法转换则跳过
                else:
                    preferences[key] = value
        except json.JSONDecodeError:
            pass
        
        return preferences
    
    def generate_response(self, agent_result, intent):
        """生成自然的对话回复"""
        prompt = f"""
        请将 Agent 的输出转换为自然的口语化回复。
        
        Agent 输出：{agent_result}
        
        回复要求：
        - 口语化、友好
        - 不要直接重复 Agent 输出的内容
        - 保持简洁明了
        - 符合日常交流习惯
        """
        
        response = self.model.invoke(prompt)
        return response.content.strip()
    
    def process_message(self, user_message, context=None):
        """处理用户消息"""
        # 初始化上下文
        if context is None:
            context = {
                "city": None,
                "weather": None,
                "weather_dirty": False,
                "activities": None,
                "activities_dirty": False,
                "food": None,
                "food_dirty": False,
                "preferences": {
                    "budget": None,
                    "taste": None,
                    "date": None,
                    "people": None,
                },
                "preferences_dirty": False,
            }
        
        # 1. 提取城市信息（每次都要尝试，可能用户换了城市）
        extracted_city = self.extract_city(user_message, context)
        if extracted_city:
            context['city'] = extracted_city
        
        # 2. 提取偏好信息（每次都要尝试，逐步补全）
        old_prefs = context.get("preferences", {}).copy()
        context['preferences'] = self.extract_preferences(user_message, context)
        new_prefs = context.get("preferences", {})
        
        if old_prefs != new_prefs:
            context["preferences_dirty"] = True
            if old_prefs.get("taste") != new_prefs.get("taste"):
                context["food_dirty"] = True
            if old_prefs.get("budget") != new_prefs.get("budget"):
                context["food_dirty"] = True
        
        # 3. 识别用户意图
        intent = self.identify_intent(user_message)
        logger.info(f"识别到意图：{intent}")
        
        # 4. 核心路由逻辑
        response, context = self._route_intent(intent, user_message, context)
        
        return response, context
    
    def _route_intent(self, intent, user_message, context):
        """根据意图和上下文路由到对应处理逻辑"""
        context['last_intent'] = intent  # 新增：记录当前意图
        
        # === 快速规划意图：generate_plan ===
        if intent == 'generate_plan':
            return self._handle_generate_plan(context)
        
        # === 修改意图：modify ===
        if intent == 'modify':
            return self._handle_modify(user_message, context)
        
        # === 专项查询意图 ===
        if intent == 'weather':
            return self._handle_weather(context)
        
        if intent == 'activities':
            return self._handle_activities(context)
        
        if intent == 'food':
            return self._handle_food(context, user_message)
        
        # === general 意图：关键改动 ===
        # general 不等于纯闲聊。需要判断对话阶段，缺信息就引导。
        if intent == 'general':
            return self._handle_general(user_message, context)
    
    def _handle_general(self, user_message, context):
        """处理 general 意图：智能判断是闲聊还是需要引导"""
        
        # 如果缺少城市信息，引导用户提供
        if not context['city']:
            response = self.model.invoke(
                "用户说：" + user_message +
                "。用户还没有告诉我要去哪个城市。请友好地询问他想去哪个城市旅行，语气自然不生硬。"
            ).content.strip()
            return response, context
        
        # 检查是否从学习引擎注入了偏好
        prefs = context.get('preferences', {})
        prefs_from_learning = context.get('preferences_injected', False)
        
        # 如果偏好已注入且信息齐全（日期、人数都有），直接展示功能菜单
        if prefs_from_learning and prefs.get('date') and prefs.get('people'):
            preference_hints = []
            if prefs.get('taste'):
                preference_hints.append(f"口味偏好：{prefs['taste']}")
            if prefs.get('budget'):
                preference_hints.append(f"预算：{prefs['budget']}元")
            
            hint_text = ""
            if preference_hints:
                hint_text = f"（根据您的历史偏好：{', '.join(preference_hints)}）"
            
            response = self.model.invoke(
                f"用户想去{context['city']}旅行{hint_text}，日期{prefs.get('date')}，{prefs.get('people')}人。"
                f"用户说：{user_message}。请友好地询问用户需要什么帮助，"
                f"可以提示：查看天气、推荐景点活动、推荐美食、或直接生成旅行计划。"
            ).content.strip()
            return response, context
        
        # 如果城市已有但缺少关键偏好（日期、人数、出行方式），引导用户补充
        missing = []
        if not prefs.get('date'):
            missing.append('出发日期')
        if not prefs.get('people'):
            missing.append('旅行人数')
        if not prefs.get('transport_mode'):
            missing.append('出行方式（步行、公共交通、自驾打车或不限）')
        
        if missing:
            response = self.model.invoke(
                f"用户想去{context['city']}旅行，但还没告诉我{', '.join(missing)}。"
                f"用户刚才说：{user_message}。请友好地询问这些信息，语气自然。"
            ).content.strip()
            return response, context
        
        # 信息齐全但还没有任何 Agent 结果
        if not context['weather'] and not context['activities'] and not context['food']:
            # 检查用户消息是否隐含美食需求
            food_keywords = ['口味', '清淡', '辣', '不挑', '预算', '人均', '好吃', '美食', '餐厅', '吃的', '想吃']
            has_food_hint = any(kw in user_message for kw in food_keywords)
            
            if has_food_hint and prefs.get('taste') and prefs.get('budget'):
                # 偏好齐全，直接推荐美食，不再确认
                return self._handle_food(context, user_message)
            elif has_food_hint:
                # 有美食意图但偏好不全，让 _handle_food 追问
                return self._handle_food(context, user_message)
            
            # 无明确需求，展示功能菜单
            response = self.model.invoke(
                f"用户想去{context['city']}旅行，日期{prefs.get('date')}，{prefs.get('people')}人。"
                f"用户说：{user_message}。请友好地询问用户需要什么帮助，"
                f"可以提示：查看天气、推荐景点活动、推荐美食、或直接生成旅行计划。"
            ).content.strip()
            return response, context
        
        # 其他情况：正常闲聊，但要结合已有上下文
        prompt = f"""
        请亲切自然地回复用户。
        
        已知信息：
        - 目的地：{context['city']}
        - 已获取的天气：{context.get('weather', '暂无')}
        - 已推荐的活动：{context.get('activities', '暂无')}
        - 已推荐的美食：{context.get('food', '暂无')}
        
        用户消息：{user_message}
        
        要求：
        - 友好自然
        - 简练，不要长篇大论
        - 如果用户的问题与旅行无关，简单回应后引导回旅行话题
        """
        response = self.model.invoke(prompt).content.strip()
        return response, context
    
    def _handle_weather(self, context):
        """处理天气查询"""
        if not context['city']:
            return "请问您想去哪个城市？我可以帮您查天气。", context
        
        weather_result = self.weather_agent.invoke({
            "messages": [HumanMessage(content=f"获取 {context['city']} 的天气信息，日期为 {context['preferences'].get('date', '今天')}")]
        })
        # 提取最后一条消息的文本内容
        weather_text = weather_result["messages"][-1].content
        context['weather'] = weather_text
        response = self.generate_response(weather_text, 'weather')
        return response, context
    
    def _handle_activities(self, context):
        """处理活动推荐"""
        if not context['city']:
            return "请问您想去哪个城市？我可以帮您推荐景点。", context
        
        # 构建输入消息，包含已有的偏好信息
        prefs = context.get('preferences', {})
        transport = prefs.get('transport_mode', 'any')
        input_text = f"推荐 {context['city']} 的景点和活动，出行方式：{transport}"
        if prefs.get('people'):
            input_text += f"，{prefs['people']}人出行"
        if prefs.get('date'):
            input_text += f"，日期 {prefs['date']}"
        if context.get('weather'):
            input_text += f"，天气情况参考：{context['weather']}"
        
        activity_result = self.activity_agent.invoke({
            "messages": [HumanMessage(content=input_text)],
            "limit": 5,
        })
        # 提取最后一条消息的文本内容
        activity_text = activity_result["messages"][-1].content
        context['activities'] = activity_text
        response = self.generate_response(activity_text, 'activities')
        return response, context
    
    def _handle_food(self, context, user_message=""):
        """处理美食推荐"""
        if not context['city']:
            return "请问您想去哪个城市？我可以帮您推荐美食。", context
        
        prefs = context.get('preferences', {})
        
        food_keywords = self.extract_food_keyword(user_message)
        location = self.extract_location(user_message)
        if not location:
            location = context.get('city', '')
        
        missing = []
        if not prefs.get('taste'):
            missing.append('口味偏好（比如喜欢辣的、清淡的、还是不挑）')
        if not prefs.get('budget') and not food_keywords:
            missing.append('预算范围（比如人均50以内、100左右、不限）')
        
        if missing:
            response = self.model.invoke(
                f"用户想在{context['city']}找美食，但还没告诉我{'和'.join(missing)}。"
                f"请友好地询问用户这些信息，语气自然，让用户觉得贴心。"
            ).content.strip()
            return response, context
        
        input_text = f"推荐 {location} 附近的美食和餐厅"
        if food_keywords:
            input_text += f"，具体想吃：{food_keywords}"
        if prefs.get('taste') and prefs['taste'] != '不挑':
            input_text += f"，口味偏好：{prefs['taste']}"
        if prefs.get('budget'):
            input_text += f"，预算：{prefs['budget']}元"
        if prefs.get('people'):
            input_text += f"，{prefs['people']}人用餐"
        if context.get('activities'):
            input_text += f"，活动信息参考：{context['activities']}"
        
        food_result = self.food_agent.invoke({
            "messages": [HumanMessage(content=input_text)]
        })
        food_text = food_result["messages"][-1].content
        context['food'] = food_text
        response = self.generate_response(food_text, 'food')
        return response, context
    
    def extract_location(self, user_message: str) -> str:
        """从用户消息中提取位置/地点信息"""
        if not user_message:
            return ""
        
        prompt = f"""从用户消息中提取具体的地名或位置（如"天河城"、"北京路"、"珠江新城"、"酒店附近"等）。
如果没有提到具体位置，返回空字符串。

用户消息：{user_message}

只返回位置名称，不要其他内容。"""
        
        try:
            response = self.model.invoke(prompt)
            keyword = response.content.strip()
            return keyword if keyword else ""
        except Exception as e:
            logger.warning(f"提取位置信息失败: {e}")
            return ""
    
    def extract_food_keyword(self, user_message: str) -> str:
        """从用户消息中提取美食关键词"""
        if not user_message:
            return ""
        
        prompt = f"""从用户消息中提取具体美食名称或菜系关键词（如"菌子火锅"、"川菜"、"日料"、"火锅"、"粤菜"等）。
如果没有提到具体美食，返回空字符串。

用户消息：{user_message}

只返回美食关键词，不要其他内容。如果有多个，用空格分隔。"""
        
        try:
            response = self.model.invoke(prompt)
            keyword = response.content.strip()
            return keyword if keyword else ""
        except Exception as e:
            logger.warning(f"提取美食关键词失败: {e}")
            return ""
    
    def _handle_generate_plan(self, context):
        """生成最终旅行计划"""
        city = context.get('city', '')
        prefs = context.get('preferences', {})
        date = prefs.get('date', '未指定')
        logger.info(f"生成计划 - city: '{city}', date: '{date}', prefs: {prefs}, dirty: {context.get('preferences_dirty')}")
        
        if not city:
            return "请先告诉我您想去哪个城市，我才能为您生成旅行计划。", context
        
        people = prefs.get('people', 1)
        budget = prefs.get('budget', 0)
        taste = prefs.get('taste', '不挑')
        transport_mode = prefs.get('transport_mode', 'any')
        
        if context.get("weather_dirty") or not context.get('weather'):
            logger.info("重新获取天气...")
            weather_result = self.weather_agent.invoke({
                "messages": [HumanMessage(content=f"获取 {city} 的天气信息，日期为 {date}")]
            })
            weather_text = weather_result["messages"][-1].content
            context['weather'] = weather_text
            context['weather_dirty'] = False
        
        if context.get("activities_dirty") or not context.get('activities'):
            logger.info("重新搜索活动...")
            input_text = f"推荐 {city} 的景点和活动，出行方式：{transport_mode}"
            if people:
                input_text += f"，{people}人出行"
            if date and date != '未指定':
                input_text += f"，日期 {date}"
            if context.get('weather'):
                input_text += f"，天气情况参考：{context['weather']}"
            
            activity_result = self.activity_agent.invoke({
                "messages": [HumanMessage(content=input_text)]
            })
            activity_text = activity_result["messages"][-1].content
            context['activities'] = activity_text
            context['activities_dirty'] = False
        
        if context.get("food_dirty") or not context.get('food'):
            logger.info("重新搜索美食...")
            input_text = f"推荐 {city} 的美食和餐厅"
            if taste and taste != '不挑':
                input_text += f"，口味偏好：{taste}"
            if budget:
                input_text += f"，预算：{budget}元"
            if people:
                input_text += f"，{people}人用餐"
            if context.get('activities'):
                input_text += f"，活动信息参考：{context['activities']}"
            
            food_result = self.food_agent.invoke({
                "messages": [HumanMessage(content=input_text)]
            })
            food_text = food_result["messages"][-1].content
            context['food'] = food_text
            context['food_dirty'] = False
        
        context['preferences_dirty'] = False
        
        # 生成 Markdown 计划
        prompt = f"""
        请根据以下信息生成最终的旅行计划，使用 Markdown 格式：

        【关键信息 - 必须严格使用以下数据】
        城市：{city}
        日期：{date}
        人数：{people}人
        预算：{budget}元
        口味：{taste}
        
        天气信息：{context.get('weather', '暂无')}
        活动信息：{context.get('activities', '暂无')}
        餐饮信息：{context.get('food', '暂无')}

        最终答复要求：
        1. 必须使用 Markdown
        2. 使用 `# 最终行程建议` 作为标题
        3. 行程必须针对【{city}】，日期为【{date}】
        4. 必须包含以下章节：
            - ## 天气与出行提醒
            - ## 活动建议（包含具体景点和路线）
            - ## 餐饮建议
            - ## 推荐行程（时间线）
            - ## 预算建议
        5. 内容简洁、可执行，不要暴露中间推理过程
        6. 行程要紧凑但不过满，优先给出当天可执行的安排
        
        【重要】7. 在 Markdown 末尾必须附加一个坐标 JSON 块，格式如下：
        ```json
        {{
          "coordinates": {{
            "activities": [
              {{
                "name": "景点名称",
                "location": "经度,纬度"
              }}
            ],
            "restaurants": [
              {{
                "name": "餐厅名称",
                "location": "经度,纬度"
              }}
            ],
            "route": {{
              "path": ["起点经度,纬度", "途经点经度,纬度", "终点经度,纬度"]
            }}
          }}
        }}
        ```
        location 格式必须为 "经度,纬度"（如 "113.267,23.121"）
        
        route.path 必须按行程顺序列出所有地点的坐标，起点到终点
        
        所有坐标必须从活动和餐饮信息中提取，不得编造。
        """

        response = self.model.invoke(prompt).content.strip()
        return response, context
    
    def _handle_modify(self, user_message, context):
        """处理修改请求"""
        if not context['city']:
            return "请先告诉我您想去哪个城市。", context
        
        prompt = f"""
        请分析用户消息，判断修改的目标是什么。
        只返回：weather、activities 或 food。
        
        用户消息：{user_message}
        """
        modify_target = self.model.invoke(prompt).content.strip().lower()
        logger.info(f"修改目标：{modify_target}")
        
        if modify_target == 'weather':
            context["weather_dirty"] = True
            result = self.weather_agent.invoke({
                "messages": [HumanMessage(content=f"重新获取 {context['city']} 的天气信息")]
            })
            result_text = result["messages"][-1].content
            context['weather'] = result_text
            context['weather_dirty'] = False
        elif modify_target == 'activities':
            context["activities_dirty"] = True
            prefs = context.get('preferences', {})
            input_text = f"重新推荐 {context['city']} 的景点和活动，用户要求：{user_message}"
            if prefs.get('people'):
                input_text += f"，{prefs['people']}人出行"
            if prefs.get('date'):
                input_text += f"，日期 {prefs['date']}"
            if context.get('weather'):
                input_text += f"，天气情况参考：{context['weather']}"
            
            result = self.activity_agent.invoke({
                "messages": [HumanMessage(content=input_text)]
            })
            result_text = result["messages"][-1].content
            context['activities'] = result_text
            context['activities_dirty'] = False
        elif modify_target == 'food':
            context["food_dirty"] = True
            context["preferences_dirty"] = True
            prefs = context.get('preferences', {})
            input_text = f"重新推荐 {context['city']} 的美食和餐厅，用户要求：{user_message}"
            if prefs.get('taste') and prefs['taste'] != '不挑':
                input_text += f"，口味偏好：{prefs['taste']}"
            if prefs.get('budget'):
                input_text += f"，预算：{prefs['budget']}元"
            if prefs.get('people'):
                input_text += f"，{prefs['people']}人用餐"
            if context.get('activities'):
                input_text += f"，活动信息参考：{context['activities']}"
            
            result = self.food_agent.invoke({
                "messages": [HumanMessage(content=input_text)]
            })
            result_text = result["messages"][-1].content
            context['food'] = result_text
            context['food_dirty'] = False
        else:
            return "请问您想修改哪方面的内容？天气、活动、还是美食？", context
        
        response = self.generate_response(result_text, 'modify')
        return response, context