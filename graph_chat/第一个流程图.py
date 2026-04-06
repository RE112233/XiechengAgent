import uuid

from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph,START,END
from langgraph.prebuilt import tools_condition
from tools.flights_tools import fetch_user_flight_information
from tools.init_db import update_dates
from tools.tools_handler import create_tool_node_with_fallback, _print_event
from graph_chat.assistant import create_assistant_node, safe_tools, sensitive_tools, sensitive_tools_names
from graph_chat.draw_png import draw_graph
from graph_chat.state import State
# 定义了一个流程图的构建对象
builder = StateGraph(State)



def get_user_info(state:State): # 函数作为节点的写法是轻量级的写法，有且只有一个参数 所以对于复杂的实现需要类
    """
    获取用户的航班信息并更新状态字典
    :param state: 当前状态字典
    :return:dic：包含用户信息的新状态字典
    """
    return {'user_info':fetch_user_flight_information.invoke({})}
# 助手可以在工作之前就拿到用户的信息，不用每次单独去查询 加快速度
builder.add_node('fetch_user_info',get_user_info)# get_user_info这里是函数本身作为节点而不是函数的返回对象
builder.add_node('assistant',create_assistant_node())
# 定义一个名字为"tools"的节点，该节点创建了一个带有回退机制的工具结点
# 但是工具结点可以分为安全的节点和敏感节点，需要将工具结点拆分
# builder.add_node('tools',create_tool_node_with_fallback(primary_assistant_tools))

# 把工具拆分为两个节点
builder.add_node("safe_tools",create_tool_node_with_fallback(safe_tools))
builder.add_node("sensitive_tools",create_tool_node_with_fallback(sensitive_tools))


# 定义边： 这些边决定了控制流如何移动
builder.add_edge(START, 'fetch_user_info')


# 从起点START 到“assistant” 结点添加一条边
builder.add_edge('fetch_user_info', 'assistant')
def route_conditional_tools(state:State)->str:
    """
    根据当前状态来决定下一个要执行的节点
    :param state: 当前的状态
    :return: str: 下一个要执行节点的名字
    """
    next_note = tools_condition(state)# langgraph提供的条件函数，要么是tools要么是end
    if next_note == END:
        return END
    """
    state['messages'] 的结构：
        [
            HumanMessage(content="帮我改签航班"),           # [0] 用户消息
            AIMessage(content="", tool_calls=[...]),        # [-1] AI 最新消息（包含工具调用）
        ]
    ai_message.tool_calls 的结构：
        [
            {
                "name": "update_ticket_to_new_flight",
                "args": {"ticket_no": "123", "new_flight_id": 456},
                "id": "call_abc123"
            }
        ]
    """
    ai_message = state['messages'][-1]
    tool_call = ai_message.tool_calls[0]
    if tool_call["name"] in sensitive_tools_names:# 敏感的工具调用
        return "sensitive_tools"
    return "safe_tools"

# 从 “assistant” 结点根据条件判断添加到其他结点的边
# 使用tools_condition来决定哪些条件满足时应跳转到哪些节点
builder.add_conditional_edges(
    "assistant",
    # tools_condition, # tools_condition 会检查 state["messages"] 中的最后一条消息，判断是否有工具调用 里面硬编码跳转到名称为 tools的节点
    route_conditional_tools, # 自定义的
    [{'safe_tools':'safe_tools'},'sensitive_tools', END] # 返回的节点名称一致可以简写
)

# 从"tools" 结点到"assistant" 结点添加一条边
# builder.add_edge('tools', 'assistant')
builder.add_edge('safe_tools', 'assistant')
builder.add_edge('sensitive_tools', 'assistant')


# 检查点让状态图可以持久化其状态
# 这是整个状态图的完整内存 MemorySaver 是 LangGraph 中的记忆存储器，用于保存对话状态，实现多轮对话的记忆功能。
memory = MemorySaver()

# 编译状态图，配置检查点为memory （关键！）, 配置中断点 在执行任何工具之前暂停图，将控制权交给用户
# graph = builder.compile(checkpointer=memory, interrupt_before=['tools'],)
# 改进，只有在敏感工具的前面添加中断点
graph = builder.compile(checkpointer=memory, interrupt_before=['sensitive_tools'],)
# graph = builder.compile(checkpointer=memory)

draw_graph(graph, "graph2.png")

session_id = str(uuid.uuid4())
update_dates() # 每次测试的时候，保证数据库是全新的，时间也是最近的时间

# 配置参数
config = {
    "configurable":{
        #passenger_id 用于航班工具，以获取用户的航班信息
        "passenger_id":"8149 604011",
        # 检查点由thread_id访问
        "thread_id":session_id # 保存上下文
    }
}

_printed = set() # 避免重复打印

# 执行工作流
while True:
    question = input('用户：')
    if question.lower() in ['q', 'exit', 'quit']:
        print('对话结束，拜拜！')
        break
    else:      # 这里会自动暂停                  # 输入为字典，传入二元组
        events = graph.stream({'messages': ('user', question)}, config, stream_mode='values')
        # 打印消息
        for event in events:
            _print_event(event, _printed)
        # MemorySaver会将每个会话的状态保存起来，通过thread_id来索引。当你调用get_state(config)
        # 时，它会根据thread_id从内存中取出对应的会话状态
        currnet_state = graph.get_state(config) # LangGraph 使用 thread_id 来区分不同的对话会话。如果不传 config，系统就不知道要获取哪个会话的状态。
        if currnet_state.next:
            user_input = input("您是否批准上述操作？输入'y'继续，否则，请说明您请求的更改\n")
            if user_input.strip().lower() == 'y':
                #  传入 None 表示不传入新的输入，而是从上次中断的地方继续执行
                events = graph.stream(None, config, stream_mode='values')
                # 打印消息
                for event in events:
                    _print_event(event, _printed)
            else:
                # 通过提供关于请求的更改/改变主意的指示来满足工具调用
                """
                用户：帮我改签到明天的航班
                  ↓
                assistant 节点 → 决定调用工具 update_ticket_to_new_flight
                  ↓
                生成 tool_calls（工具调用请求）
                  ↓
                准备执行 tools 节点 → 【暂停！等待用户批准】
                  ↓
                用户说："不，我不想改了" （拒绝）
                AI 正在等待工具的响应结果。如果不给它响应，AI 会一直卡住等待。所以需要伪造一个工具响应告诉 AI 发生了什么。
                """
                result = graph.stream(
                    { # 模拟工具调用的响应，让 AI 知道用户拒绝了操作 其实就是 如果用户没有截断，那么返回给下一个结点的应该是工具消息
                        "messages": [
                            ToolMessage( # tool_call_id 是工具调用的唯一标识符，用于关联工具调用和工具消息
                                tool_call_id=events["messages"][-1].tool_calls[0]["id"],
                                content=f"Tool的调用被用户拒绝。原因：'{user_input}'。",
                            )
                        ]
                    },
                    config,
                )
                # 打印事件详情
                for event in result:
                    _print_event(event, _printed)



