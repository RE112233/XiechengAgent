# 状态类
from typing import TypedDict, Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph import  add_messages

class State(TypedDict):
    """
    定义状态字典的结构
    参数：
        messages（list[AnyMessage]）:消息列表
        user_info(str):用户信息
    """
    # Annotated 是 Python 类型提示（type hints）中的一个工具，用于给变量或参数添加额外的元数据信息。
    messages:Annotated[list[AnyMessage],add_messages]
    user_info:str
