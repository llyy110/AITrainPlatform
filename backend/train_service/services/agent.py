import os
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from .tools import get_training_progress, suggest_hyperparameters, explain_model

# 使用阿里云百炼 Qwen 模型
llm = ChatOpenAI(
    model="qwen3-max",
    openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
    openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    temperature=0,
)

tools = [get_training_progress, suggest_hyperparameters, explain_model]
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# 自定义 prompt 前缀，强化 Final Answer 要求
PREFIX = """你是一个AI助手，可以使用工具回答用户问题。
请严格遵循以下格式，不要输出任何多余的解释：
Question: 用户的问题
Thought: 你应该思考是否需要使用工具
Action: 工具名称（必须是 [get_training_progress, suggest_hyperparameters, explain_model] 之一）
Action Input: 工具的输入参数
Observation: 工具返回的结果
... (可重复 Thought/Action/Action Input/Observation)
Thought: 我现在知道如何回答用户了
Final Answer: 用自然语言回答用户的问题

注意：Final Answer 必须直接回应用户，不能只重复 Observation 内容！
"""
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,  # 关键修改
    memory=memory,
    verbose=True,
    handle_parsing_errors=True,                  # 内部容错
    agent_kwargs={"prefix": PREFIX},
)

def ask(query: str, user_id: str = None, current_task_id: str = None) -> str:
    if current_task_id:
        context = f"当前用户正在训练的任务ID是 {current_task_id}。"
    else:
        context = "当前用户没有正在运行的训练任务。"
    full_query = f"{context}\n用户问题: {query}"
    result = agent.invoke({"input": full_query})
    return result["output"]








