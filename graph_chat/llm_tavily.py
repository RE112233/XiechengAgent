from langchain_community.chat_models import  ChatTongyi
from dotenv import load_dotenv
load_dotenv()
llm = ChatTongyi(
    model="qwen3-max",  # 可选：qwen-turbo, qwen-plus, qwen-max
)
