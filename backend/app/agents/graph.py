import logging
import functools

from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langchain_openai import ChatOpenAI

from app.agents.tools import get_mcp_tools, wrap_mcp_tools, run_async
from app.agents.prompts import SUPERVISOR_PROMPT, CHAT_SUPERVISOR_PROMPT, WEATHER_AGENT_PROMPT, ACTIVITY_AGENT_PROMPT, FOOD_AGENT_PROMPT
from app.core.config import settings

# 配置日志
logger = logging.getLogger(__name__)

@functools.lru_cache(maxsize=1)
def build_travel_graph():
    """构建并返回编译后的 LangGraph 主管图"""
    
    # 获取 MCP 工具
    mcp_tools = run_async(get_mcp_tools())
    
    logger.info(f"加载了 {len(mcp_tools)} 个 MCP 工具")
    
    if not mcp_tools:
        logger.warning("没有加载到任何工具，将使用无工具的 Agent")

    # 创建模型
    model = ChatOpenAI(
        model=settings.DASHSCOPE_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DASHSCOPE_BASE_URL,
        temperature=0.5,
    )

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
    activity_tools = [t for t in sync_tools if t.name in ['search_activities', 'plan_route']]
    activity_agent = create_react_agent(
        model=model,
        tools=activity_tools,
        name="ActivityAgent",
        prompt=ACTIVITY_AGENT_PROMPT,
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
        prompt=FOOD_AGENT_PROMPT,
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

class ChatSupervisor:
    """对话式规划主管"""
    
    def __init__(self):
        """初始化 ChatSupervisor"""
        # 获取 MCP 工具
        mcp_tools = run_async(get_mcp_tools())
        logger.info(f"加载了 {len(mcp_tools)} 个 MCP 工具")
        
        # 创建模型
        self.model = ChatOpenAI(
            model=settings.DASHSCOPE_MODEL,
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL,
            temperature=0.5,
        )
        
        # 包装所有 MCP 工具为同步工具
        sync_tools = wrap_mcp_tools(mcp_tools)
        
        # 创建 WeatherAgent
        weather_tools = [t for t in sync_tools if t.name == 'get_weather']
        self.weather_agent = create_react_agent(
            model=self.model,
            tools=weather_tools,
            name="WeatherAgent",
            prompt=WEATHER_AGENT_PROMPT,
        )
        
        # 创建 ActivityAgent
        activity_tools = [t for t in sync_tools if t.name in ['search_activities', 'plan_route']]
        self.activity_agent = create_react_agent(
            model=self.model,
            tools=activity_tools,
            name="ActivityAgent",
            prompt=ACTIVITY_AGENT_PROMPT,
        )
        
        # 创建 FoodAgent
        food_tools = [t for t in sync_tools if t.name in [
            'search_restaurants',
            'recommend_meal_plan',
            'get_restaurant_detail',
            'recommend_by_cuisine'
        ]]
        self.food_agent = create_react_agent(
            model=self.model,
            tools=food_tools,
            name="FoodAgent",
            prompt=FOOD_AGENT_PROMPT,
        )
    
    def identify_intent(self, user_message):
        """识别用户意图"""
        prompt = f"""
        请分析用户消息，识别其意图类别。
        
        支持的意图类别：
        - weather: 查询天气
        - activities: 推荐景点/活动
        - food: 推荐美食/餐厅
        - generate_plan: 生成最终旅行计划
        - modify: 修改已有推荐
        - general: 闲聊/问候/询问功能
        
        用户消息：{user_message}
        
        请只返回意图类别，不要返回其他内容。
        """
        
        response = self.model.invoke(prompt)
        intent = response.content.strip().lower()
        
        # 验证意图是否有效
        valid_intents = ['weather', 'activities', 'food', 'generate_plan', 'modify', 'general']
        if intent not in valid_intents:
            # 如果识别失败，默认为 general
            return 'general'
        
        return intent
    
    def extract_city(self, user_message, context):
        """从用户消息中提取城市信息"""
        if context.get('city'):
            return context['city']
        
        prompt = f"""
        请从用户消息中提取目的地城市名称。
        
        用户消息：{user_message}
        
        请只返回城市名称，不要返回其他内容。如果没有提到城市，请返回空字符串。
        """
        
        response = self.model.invoke(prompt)
        city = response.content.strip()
        return city if city else None
    
    def extract_preferences(self, user_message, context):
        """从用户消息中提取偏好信息"""
        preferences = context.get('preferences', {})
        
        prompt = f"""
        请从用户消息中提取以下偏好信息：
        - budget: 预算（数字）
        - taste: 口味（辣/清淡/不挑）
        - date: 日期（YYYY-MM-DD）
        - people: 人数（数字）
        
        用户消息：{user_message}
        
        请返回 JSON 格式，例如：
        {{"budget": 500, "taste": "辣", "date": "2024-05-01", "people": 2}}
        
        如果没有提到某项，对应字段设为 null。
        """
        
        response = self.model.invoke(prompt)
        import json
        try:
            extracted = json.loads(response.content)
            # 更新偏好信息
            for key, value in extracted.items():
                if value is not None:
                    preferences[key] = value
        except:
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
                "activities": None,
                "food": None,
                "preferences": {
                    "budget": None,
                    "taste": None,
                    "date": None,
                    "people": None,
                }
            }
        
        # 提取城市信息
        city = self.extract_city(user_message, context)
        if city:
            context['city'] = city
        
        # 提取偏好信息
        context['preferences'] = self.extract_preferences(user_message, context)
        
        # 识别意图
        intent = self.identify_intent(user_message)
        logger.info(f"识别到意图：{intent}")
        
        # 检查城市是否存在
        if not context['city'] and intent not in ['general']:
            return "请问您想去哪个城市旅行？", context
        
        # 根据意图处理
        if intent == 'weather':
            # 调用 WeatherAgent
            if not context['weather']:
                weather_result = self.weather_agent.invoke({"input": f"获取 {context['city']} 的天气信息"})
                context['weather'] = weather_result
                response = self.generate_response(weather_result, intent)
            else:
                response = "我已经为您获取了天气信息，需要我再帮您查询其他信息吗？"
        
        elif intent == 'activities':
            # 调用 ActivityAgent
            if not context['activities']:
                activity_result = self.activity_agent.invoke({
                    "input": f"推荐 {context['city']} 的景点和活动",
                    "weather_info": context.get('weather')
                })
                context['activities'] = activity_result
                response = self.generate_response(activity_result, intent)
            else:
                response = "我已经为您推荐了景点和活动，需要我再帮您查询其他信息吗？"
        
        elif intent == 'food':
            # 调用 FoodAgent
            if not context['food']:
                food_result = self.food_agent.invoke({
                    "input": f"推荐 {context['city']} 的美食和餐厅",
                    "activity_info": context.get('activities'),
                    "weather_info": context.get('weather')
                })
                context['food'] = food_result
                response = self.generate_response(food_result, intent)
            else:
                response = "我已经为您推荐了美食和餐厅，需要我再帮您查询其他信息吗？"
        
        elif intent == 'modify':
            # 判断修改目标
            prompt = f"""
            请分析用户消息，判断修改的目标是什么（weather/activities/food）。
            
            用户消息：{user_message}
            
            请只返回目标类别，不要返回其他内容。
            """
            
            modify_target = self.model.invoke(prompt).content.strip().lower()
            
            if modify_target == 'weather':
                weather_result = self.weather_agent.invoke({"input": f"重新获取 {context['city']} 的天气信息"})
                context['weather'] = weather_result
                response = self.generate_response(weather_result, intent)
            elif modify_target == 'activities':
                activity_result = self.activity_agent.invoke({
                    "input": f"重新推荐 {context['city']} 的景点和活动",
                    "weather_info": context.get('weather')
                })
                context['activities'] = activity_result
                response = self.generate_response(activity_result, intent)
            elif modify_target == 'food':
                food_result = self.food_agent.invoke({
                    "input": f"重新推荐 {context['city']} 的美食和餐厅",
                    "activity_info": context.get('activities'),
                    "weather_info": context.get('weather')
                })
                context['food'] = food_result
                response = self.generate_response(food_result, intent)
            else:
                response = "请问您想修改哪方面的推荐？"
        
        elif intent == 'generate_plan':
            # 检查并补调缺失的 Agent
            if not context['weather']:
                weather_result = self.weather_agent.invoke({"input": f"获取 {context['city']} 的天气信息"})
                context['weather'] = weather_result
            
            if not context['activities']:
                activity_result = self.activity_agent.invoke({
                    "input": f"推荐 {context['city']} 的景点和活动",
                    "weather_info": context.get('weather')
                })
                context['activities'] = activity_result
            
            if not context['food']:
                food_result = self.food_agent.invoke({
                    "input": f"推荐 {context['city']} 的美食和餐厅",
                    "activity_info": context.get('activities'),
                    "weather_info": context.get('weather')
                })
                context['food'] = food_result
            
            # 生成最终计划
            prompt = f"""
            请根据以下信息生成最终的旅行计划，使用 Markdown 格式：
            
            城市：{context['city']}
            天气信息：{context['weather']}
            活动信息：{context['activities']}
            餐饮信息：{context['food']}
            偏好：{context['preferences']}
            
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
            """
            
            response = self.model.invoke(prompt).content.strip()
        
        elif intent == 'general':
            # 闲聊回复
            prompt = f"""
            请对用户的消息进行友好的回应。
            
            用户消息：{user_message}
            
            回复要求：
            - 友好、自然
            - 符合日常交流习惯
            - 简洁明了
            """
            
            response = self.model.invoke(prompt).content.strip()
        
        else:
            response = "抱歉，我不太理解您的需求。请问您需要什么帮助？"
        
        return response, context