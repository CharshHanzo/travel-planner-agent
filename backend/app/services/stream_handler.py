import logging
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

class StreamHandler:
    """处理 LangGraph 流式输出"""
    
    def __init__(self):
        self.visited_agents = set()
        self.status_flow = [
            ("TravelSupervisor", "主管正在分派任务..."),
            ("WeatherAgent", "WeatherAgent 正在获取天气信息..."),
            ("ActivityAgent", "ActivityAgent 正在搜索活动..."),
            ("FoodAgent", "FoodAgent 正在推荐餐厅..."),
        ]
    
    async def process_stream(self, graph, user_message: str):
        """处理 graph.stream()，yield SSE 事件"""
        try:
            async for namespace, mode, data in graph.stream(
                {"messages": [{"role": "user", "content": user_message}]},
                stream_mode=["updates", "values"],
                subgraphs=True,
            ):
                if mode == "updates":
                    active_agent = self._detect_agent(namespace, data)
                    if active_agent:
                        # 发送运行状态
                        yield {
                            "event": "agent_update",
                            "data": {
                                "agent_name": active_agent,
                                "status": "running",
                                "message": self._get_status_message(active_agent, "running"),
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                        self.visited_agents.add(active_agent)
                elif mode == "values" and not namespace and isinstance(data, dict) and "messages" in data:
                    # 发送完成状态
                    for agent_name, _ in self.status_flow:
                        if agent_name in self.visited_agents:
                            yield {
                                "event": "agent_update",
                                "data": {
                                    "agent_name": agent_name,
                                    "status": "completed",
                                    "message": self._get_status_message(agent_name, "completed"),
                                    "timestamp": datetime.now().isoformat()
                                }
                            }
                    
                    # 发送结果
                    result_markdown = self._extract_final_message(data.get("messages", []))
                    yield {
                        "event": "result",
                        "data": {
                            "session_id": f"session-{datetime.now().timestamp()}",
                            "result_markdown": result_markdown
                        }
                    }
        except Exception as e:
            logger.error(f"流式处理错误: {e}")
            yield {
                "event": "error",
                "data": {"error": f"内部服务器错误：{str(e)}"}
            }
    
    def _detect_agent(self, namespace, data) -> str | None:
        """检测当前活跃的 Agent"""
        haystack = " ".join(namespace)
        if isinstance(data, dict):
            haystack = f"{haystack} {' '.join(data.keys())}"
        for agent_name, _ in self.status_flow:
            if agent_name in haystack:
                return agent_name
        return None
    
    def _get_status_message(self, agent_name: str, status: str) -> str:
        """获取状态消息"""
        return self._render_status_message(agent_name, status)
    
    def _render_status_message(self, agent_name: str, status: str) -> str:
        """渲染状态消息"""
        status_messages = {
            "running": {
                "TravelSupervisor": "主管正在分派任务...",
                "WeatherAgent": "正在获取天气信息...",
                "ActivityAgent": "正在搜索活动...",
                "FoodAgent": "正在推荐餐厅..."
            },
            "completed": {
                "TravelSupervisor": "主管决策完成",
                "WeatherAgent": "天气获取完成",
                "ActivityAgent": "活动搜索完成",
                "FoodAgent": "餐厅推荐完成"
            }
        }
        return status_messages.get(status, {}).get(agent_name, f"{agent_name} {status}")
    
    def _extract_final_message(self, messages: list) -> str:
        """提取最终消息内容"""
        if not messages:
            return ""
        
        last_message = messages[-1]
        if isinstance(last_message, dict) and "content" in last_message:
            content = last_message["content"]
            if isinstance(content, str):
                return content
        return str(last_message)