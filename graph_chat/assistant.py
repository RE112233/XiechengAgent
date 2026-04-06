from graph_chat.llm_tavily import llm
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from graph_chat.state import State
from tools.car_tools import search_car_rentals, book_car_rental, update_car_rental, cancel_car_rental
from tools.flights_tools import fetch_user_flight_information, search_flights, update_ticket_to_new_flight, \
    cancel_ticket
from tools.hotels_tools import search_hotels, book_hotel, update_hotel, cancel_hotel
from tools.retriever_vector import lookup_policy
from tools.trip_tools import search_trip_recommendations, book_excursion, update_excursion, cancel_excursion

class CtripAssistant:
    # 自定义一个类，表示流程图的一个结点（复杂的） （函数也可以作为一个结点，类可以处理复杂内容）
    # 类不能直接作为节点，还需要创建对象
    def __init__(self,runnable:Runnable):
        """
        初始化助手的实例
        :param runnable: 可运行对象，通常是一个Runnable类型的
        """

        self.runnable = runnable
    # 它让类的实例可以像函数一样被调用。
    def __call__(self, state:State,config:RunnableConfig):
        """
        调用节点，执行助手任务
        :param state:当前工作流的状态
        :param config:配置 里面有旅客的信息
        :return:dic
        """
        # RunnableConfig提供了对Runnable（可运行对象）执行过程中的控制，包括：超时控制、回调函数、 并发控制、元数据传递、 标签和命名
        """
        # RunnableConfig 本质上是一个 TypedDict，结构如下：
        config = {
            # 1. 基础配置
            "timeout": Optional[float],              # 超时时间（秒）
            "max_concurrency": Optional[int],        # 最大并发数
            "run_name": Optional[str],               # 运行名称
            
            # 2. 回调和监控
            "callbacks": Optional[List],             # 回调函数列表
            "tags": Optional[List[str]],             # 标签列表
            "metadata": Optional[Dict[str, Any]],    # 元数据字典
            
            # 3. 可配置字段（重点！）
            "configurable": Optional[Dict[str, Any]],  # ← 用户自定义配置的存放位置
            
            # 4. 其他
            "run_id": Optional[UUID],                # 运行 ID
            "project_name": Optional[str],           # 项目名称
        }
        """

        while True:
            # 创建一个无限循环，一直执行，直到从self.runnable 获取的结果是有效的
            # 如果结果无效（例如没有工具调用且内容为空或内容不符合预期格式），循环将继续执行
            # configuration = config.get('configurable',{}) # 获取配置 没有则为空 # 更新 ： 将user_info放到state中
            # user_id = configuration.get('passenger_id',None)
            # 使用字典解包操作符 **    从配置中拿到旅客的id 然后加到状态中去
            # state = {**state, 'user_info':user_id} # 创建一个新的字典，将state和user_id合并
            result = self.runnable.invoke(state)
            # 模型"卡住"了：既不调用工具，也不说话空响应：模型返回空字符串或 None 格式错误：返回的内容结构不对，无法提取有效信息
            # 如果，runnable执行完后，没有得到一个实际的输出
            if not result.tool_calls and (  # 如果结果中没有工具调用，并且内容为空或内容列表的第一个元素没有"text"，则需要重新提示用户输入。
                    not result.content
                    or isinstance(result.content, list) # 内容是列表格式，但第一个元素没有 "text" 字段
                    and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "请提供一个真实的输出作为回应。")] # state 定义的时候的message是个键，里面是列表
                state = {**state, "messages": messages}
            else:  # 如果： runnable执行后已经得到，想要的输出，则退出循环
                break
                # 返回的result
                # 对象包含：
                # tool_calls：模型决定要调用的工具列表
                # content：模型的文本回复内容
        return {'messages': result}

# 主助理提示模板
primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "您是携程瑞士航空公司的客户服务助理。"
            "您的主要职责是搜索航班信息和公司政策以回答客户的查询。"
            "如果客户请求更新或取消航班、预订租车、预订酒店或获取旅行推荐，请通过调用相应的工具将任务委派给合适的专门助理。您自己无法进行这些类型的更改。"
            "只有专门助理才有权限为用户执行这些操作。"
            "用户并不知道有不同的专门助理存在，因此请不要提及他们；只需通过函数调用来安静地委派任务。"
            "向客户提供详细的信息，并且在确定信息不可用之前总是复查数据库。"
            "在搜索时，请坚持不懈。如果第一次搜索没有结果，请扩大查询范围。"
            "如果搜索无果，请扩大搜索范围后再放弃。"
            "\n\n当前用户的航班信息:\n<Flights>\n{user_info}\n</Fllights>"
            "\n当前时间: {time}.",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now()) # ：预先填充提示模板中的 time 变量，其他变量留待后续填充

# # 定义主助理使用的工具
# primary_assistant_tools = [
#     # 航班相关工具
#     fetch_user_flight_information,  # ✅ 添加：查询用户航班信息
#     search_flights,  # 搜索航班
#     lookup_policy,  # 查找公司政策的工具
#
#     # 租车相关工具
#     search_car_rentals,  # 搜索租车服务
#     book_car_rental,  # 预订租车
#     update_car_rental,  # 更新租车订单
#     cancel_car_rental,  # 取消租车
#
#     # 酒店相关工具
#     search_hotels,  # 搜索酒店
#     book_hotel,  # 预订酒店
#     update_hotel,  # 更新酒店预订
#     cancel_hotel,  # 取消酒店预订
#
#     # 旅行推荐相关工具
#     search_trip_recommendations,  # 搜索旅行推荐
#     book_excursion,  # 预订旅行项目
#     update_excursion,  # 更新旅行项目
#     cancel_excursion,  # 取消旅行项目
# ]

# 定义“只读”工具列表，这些工具不需要用户确认即可使用
safe_tools = [
    # 航班相关 - 只读
    fetch_user_flight_information,  # 查询用户航班信息
    search_flights,  # 搜索航班

    # 租车相关 - 只读
    search_car_rentals,  # 搜索租车服务

    # 酒店相关 - 只读
    search_hotels,  # 搜索酒店

    # 旅行推荐相关 - 只读
    search_trip_recommendations,  # 搜索旅行推荐

    # 政策查询 - 只读
    lookup_policy,  # 查找公司政策
]
sensitive_tools = [ # 都是对象，而不是名字
    # 航班相关 - 写操作
    update_ticket_to_new_flight,  # 更新机票到新航班
    cancel_ticket,  # 取消机票

    # 租车相关 - 写操作
    book_car_rental,  # 预订租车
    update_car_rental,  # 更新租车订单
    cancel_car_rental,  # 取消租车

    # 酒店相关 - 写操作
    book_hotel,  # 预订酒店
    update_hotel,  # 更新酒店预订
    cancel_hotel,  # 取消酒店预订

    # 旅行推荐相关 - 写操作
    book_excursion,  # 预订旅行项目
    update_excursion,  # 更新旅行项目
    cancel_excursion,  # 取消旅行项目
]

sensitive_tools_names = {tool.name for tool in sensitive_tools}


# 创建可运行对象，绑定主助理提示模板和工具集，包括委派给专门助理的工具
assistant_runnable = primary_assistant_prompt | llm.bind_tools(
    safe_tools + sensitive_tools
)

def create_assistant_node()->CtripAssistant:
    """
    创建一个助手，并返回一个可运行对象。
    :param
    :return: 可运行对象
    """


    return CtripAssistant(assistant_runnable)