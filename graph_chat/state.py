# 状态类
from typing import TypedDict, Annotated, Optional, Literal
from langchain_core.messages import AnyMessage
from langgraph.graph import  add_messages
def update_dialog_stack(left: list[str], right: Optional[str]) -> list[str]:
    """
    更新对话状态栈。
    参数:
        left (list[str]): 当前的状态栈。
        right (Optional[str]):  新的子工作流的名称。想要添加到栈中的新状态或动作。如果为 None，则不做任何更改；
                               如果为 "pop"，则弹出栈顶元素；否则将该值添加到栈中。
    返回:
        list[str]: 更新后的状态栈。
    """
    if right is None:
        return left  # 如果right是None，保持当前状态栈不变
    if right == "pop":
        # left[:-1] 表示获取列表 left 中除了最后一个元素之外的所有元素
        return left[:-1]  # 如果right是"pop"，移除栈顶元素（即最后一个状态）
    return left + [right]  # 否则，将right添加到状态栈中

# 状态类
class State(TypedDict):
    """
    定义一个结构化的字典类型，用于存储对话状态信息。
    字段:
        messages (list[AnyMessage]): 使用 Annotated 注解附加了 add_messages 功能的消息列表，
        user_info (str): 存储用户信息的字符串。
        dialog_state (list[Literal["assistant", "update_flight", "book_car_rental",
                                    "book_hotel", "book_excursion"]]): 对话状态栈，限定只能包含特定的几个值，
                                    并使用 update_dialog_stack 函数来控制其更新逻辑。
    """
    messages: Annotated[list[AnyMessage], add_messages]
    user_info: str
    dialog_state: Annotated[
        list[
            Literal[
                "assistant",# 主助手 主助手在多个助手之间进行路由
                "update_flight", # 子助手 航班预定 子助手可以看做子图 子工作流
                "book_car_rental",# 子助手  租车
                "book_hotel",# 子助手 酒店预定
                "book_excursion",# 子助手 游览 这些助手放置在 agent_assistant
            ]
        ],
        update_dialog_stack,
    ]# Literal 用于限制变量只能取某些特定的值，而不是任意字符串。
    #  dialog_state 每个子助手的状态 当前处于哪个工作流
