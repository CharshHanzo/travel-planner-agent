import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
import functools
import inspect

from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.core.config import settings

# 配置日志
logger = logging.getLogger(__name__)

# 全局线程池，避免重复创建
_THREAD_POOL = ThreadPoolExecutor(max_workers=10)

# 搜索调用计数器（用于跨 Agent 全局统计）
_search_call_counts = {
    "search_activities": 0,
    "search_restaurants": 0,
    "plan_route": 0,
}

# 各工具的最大调用次数限制
_SEARCH_CALL_LIMITS = {
    "search_activities": 5,
    "search_restaurants": 5,
    "plan_route": 3,
}


def _reset_search_calls():
    """重置所有搜索工具的调用计数器（每次新请求开始时调用）"""
    _search_call_counts["search_activities"] = 0
    _search_call_counts["search_restaurants"] = 0
    _search_call_counts["plan_route"] = 0
    logger.info("搜索调用计数器已重置")


def _check_search_limit(tool_name: str) -> bool:
    """检查工具是否超过调用上限，并递增计数器
    返回 True 表示可以继续调用，False 表示已达上限
    """
    if tool_name not in _search_call_counts:
        return True
    if _search_call_counts[tool_name] >= _SEARCH_CALL_LIMITS.get(tool_name, 999):
        logger.warning(f"工具 {tool_name} 已达调用上限 {_SEARCH_CALL_LIMITS[tool_name]} 次")
        return False
    _search_call_counts[tool_name] += 1
    return True


def _get_search_call_count(tool_name: str) -> int:
    """获取当前工具的调用次数"""
    return _search_call_counts.get(tool_name, 0)

def run_async(coro):
    """使用全局线程池运行异步函数"""
    future = _THREAD_POOL.submit(asyncio.run, coro)
    return future.result()

class MCPToolClient:
    """MCP 工具客户端封装"""
    
    def __init__(self, url: str):
        self.url = url
        self.client = None
    
    async def connect(self):
        """连接到 MCP 服务器"""
        if not self.client:
            self.client = MultiServerMCPClient(
                {
                    "travel_tools": {
                        "transport": "sse",
                        "url": self.url,
                    }
                }
            )
        return self.client
    
    async def get_tools(self):
        """获取工具列表"""
        client = await self.connect()
        tools = await client.get_tools()
        logger.info(f"成功获取 {len(tools)} 个 MCP 工具")
        for tool in tools:
            logger.info(f"  - {getattr(tool, 'name', str(tool))}")
        return tools

async def get_mcp_tools():
    """异步获取 MCP 工具列表"""
    try:
        client = MCPToolClient(settings.MCP_SERVER_URL)
        tools = await client.get_tools()
        return tools
    except Exception as e:
        logger.error(f"获取 MCP 工具失败: {e}")
        return []

def create_sync_wrapper(async_func, name: str, description: str, args_schema=None):
    """创建同步工具包装器"""
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

def wrap_mcp_tools(tools):
    """将异步 MCP 工具包装为同步工具"""
    sync_tools = []
    for tool in tools:
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
    
    return sync_tools