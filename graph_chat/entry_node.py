from typing import Callable
from langchain_core.messages import ToolMessage


#
def create_entry_node(assistant_name: str, new_dialog_state: str) -> Callable:
    """
    这是一个函数工程： 创建一个入口节点函数，当对话状态转换时调用。
    该函数生成一条新的对话消息，并更新对话的状态。
    只做上下文衔接，不实现具体业务
    :param assistant_name: 新助理的名字或描述。
    :param new_dialog_state: 要更新到的新对话状态。
    :return: 返回一个根据给定的assistant_name和new_dialog_state处理对话状态的函数。
    """

    def entry_node(state: dict) -> dict:
        """
        根据当前对话状态生成新的对话消息并更新对话状态。

        :param state: 当前对话状态，包含所有消息。
        :return: 包含新消息和更新后的对话状态的字典。
        """
        # 获取最后一个消息中的工具调用ID
        tool_call_id = state["messages"][-1].tool_calls[0]["id"]

        return {
            "messages": [# 这里的ToolMessage 标记主助手和子助手之间的移交
                ToolMessage(
                    content=f"现在助手是{assistant_name}。请回顾上述主助理与用户之间的对话。"
                            f"用户的意图尚未满足。使用提供的工具协助用户。记住，您是{assistant_name}，"
                            "并且预订、更新或其他操作未完成，直到成功调用了适当的工具。"
                            "如果用户改变主意或需要帮助进行其他任务，请调用CompleteOrEscalate函数让主要的主助理接管。"
                            "不要提及你是谁——仅作为助理的代理。",
                    tool_call_id=tool_call_id,
                )
            ],
            "dialog_state": new_dialog_state,
        }
    # 保持状态：通过闭包，您可以创建一个携带额外信息 assistant_name、new_dialog_state的函数。这些信息在 create_entry_node 函数被调用时确定，并且可以在返回的 entry_node 函数中使用。
    return entry_node # 返回一个函数，这种函数称为闭包 这个函数将作为结点 子流程的入口结点
