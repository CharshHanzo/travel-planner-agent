import logging
from datetime import date, timedelta

from app.api.v1.schemas.travel import TravelRequest
from app.agents.graph import build_travel_graph
from app.services.stream_handler import StreamHandler

# 配置日志
logger = logging.getLogger(__name__)

class TravelPlannerService:
    def __init__(self):
        self.graph = None  # 延迟加载
    
    async def plan_travel(self, request: TravelRequest) -> str:
        """执行出行规划，返回 Markdown 结果"""
        # 验证输入
        is_valid, error_msg = self._validate_inputs(request)
        if not is_valid:
            raise ValueError(error_msg)
        
        # 延迟加载 graph
        if not self.graph:
            self.graph = build_travel_graph()
        
        # 构建用户消息
        user_message = self._build_user_message(request)
        
        # 执行规划
        result = self.graph.invoke({
            "messages": [{"role": "user", "content": user_message}]
        })
        
        # 提取结果
        messages = result.get("messages", [])
        if not messages:
            return "未生成规划结果"
        
        last_message = messages[-1]
        
        # 处理多种可能的消息格式
        final_response = ""
        if isinstance(last_message, dict) and "content" in last_message:
            content = last_message["content"]
            if isinstance(content, str):
                final_response = content
            else:
                final_response = str(content)
        elif hasattr(last_message, 'content'):
            final_response = str(last_message.content)
        else:
            final_response = str(last_message)
        
        # 恢复被转义的换行符（处理 AIMessage 字符串化后的转义）
        final_response = final_response.replace('\\n', '\n').replace('\\"', '"')
        
        return final_response
    
    async def plan_travel_stream(self, request: TravelRequest):
        """异步生成器，yield Agent 状态事件和最终结果"""
        # 验证输入
        is_valid, error_msg = self._validate_inputs(request)
        if not is_valid:
            yield {"event": "error", "data": {"error": error_msg}}
            return
        
        try:
            # 延迟加载 graph
            if not self.graph:
                self.graph = build_travel_graph()
            
            # 构建用户消息
            user_message = self._build_user_message(request)
            
            # 使用 StreamHandler 处理流
            handler = StreamHandler()
            async for event in handler.process_stream(self.graph, user_message):
                yield event
        except Exception as e:
            logger.error(f"流式规划错误: {e}")
            yield {"event": "error", "data": {"error": f"内部服务器错误：{str(e)}"}}
    
    def _build_user_message(self, request: TravelRequest) -> str:
        """构建用户消息"""
        departure_text = request.departure.strip() if request.departure else "未提供"
        
        # 计算相对日期
        today = date.today()
        delta = (request.travel_date - today).days
        if delta == 0:
            date_str = "今天"
        elif delta == 1:
            date_str = "明天"
        elif delta == 2:
            date_str = "后天"
        else:
            date_str = request.travel_date.strftime("%Y-%m-%d")
        
        return f"""
请为我生成一份城市出行建议，并综合天气、活动、餐饮三方面信息。

用户信息：
- 城市：{request.city}
- 日期：{date_str}（对应 {request.travel_date.strftime("%Y-%m-%d")}）
- 人数：{request.people_count}
- 总预算：{request.budget} 元
- 口味偏好：{request.taste}
- 出发地点：{departure_text}
- 推荐活动数量：{request.activity_count}

⚠️ 重要：
- 如果出发地点不为空，ActivityAgent 在调用 plan_route 时必须将其作为 start_point 参数传入
- ActivityAgent 搜索活动时请使用 limit={request.activity_count}

要求：
1. 结果必须使用 Markdown
2. 用 `# 最终行程建议` 作为主标题
3. 行程要紧凑但不过满，优先给出当天可执行的安排
4. 如果信息不足，可以做合理假设，但要明确写出假设
5. 必须综合天气、活动、餐饮三个维度
""".strip()
    
    def _validate_inputs(self, request: TravelRequest) -> tuple[bool, str]:
        """验证输入"""
        if not request.city or not request.city.strip():
            return False, "城市名称不能为空"
        
        if len(request.city) > 50:
            return False, "城市名称过长"
        
        if request.people_count <= 0 or request.people_count > 20:
            return False, "人数必须在1-20之间"
        
        if request.budget <= 0:
            return False, "预算必须大于0"
        
        if request.budget > 100000:
            return False, "预算不能超过100000元"
        
        # 检查日期是否合理
        if request.travel_date < date.today():
            return False, "不能选择过去的日期"
        
        if request.travel_date > date.today() + timedelta(days=30):
            return False, "最多只能规划未来30天的行程"
        
        return True, ""