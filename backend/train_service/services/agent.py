import os
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
import requests

from ..config import TRAIN_SVC_URL

executor = ThreadPoolExecutor(max_workers=4)
user_memories: Dict[str, ConversationBufferMemory] = {}


def get_llm():
    """延迟创建 LLM 实例"""
    return ChatOpenAI(
        model="qwen3-max",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=0,
        timeout=10,
    )


def get_memory(user_id: str) -> ConversationBufferMemory:
    if user_id not in user_memories:
        user_memories[user_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    return user_memories[user_id]


def clear_memory(user_id: str):
    if user_id in user_memories:
        del user_memories[user_id]


def create_tools(current_task_id: Optional[str] = None):
    @tool
    def get_training_progress(dummy: str = "") -> str:
        """获取当前用户正在运行的训练任务进度。

        参数 dummy: 占位参数，无需提供任何值，直接调用即可。
        """
        if not current_task_id:
            return "当前没有正在运行的训练任务。"
        try:
            resp = requests.get(
                f"{TRAIN_SVC_URL}/train/training/progress/{current_task_id}",
                timeout=3
            )
            if resp.status_code == 200:
                data = resp.json()
                phase = data.get('phase', 'unknown')
                percent = data.get('progress_percent', 0)
                error = data.get('error', 0)
                return f"阶段: {phase}, 进度: {percent}%, 当前误差: {error:.6f}"
            else:
                return "未找到该训练任务，可能任务已结束或ID无效。"
        except requests.Timeout:
            return "获取训练进度超时，请稍后重试。"
        except Exception as e:
            return f"获取进度时出错: {str(e)}"

    @tool
    def suggest_hyperparameters(model_type: str) -> str:
        """根据模型类型提供推荐的超参数设置。参数 model_type 可选: bpnn_classifier, bpnn_regressor, cnn_classifier"""
        suggestions = {
            "bpnn_classifier": "隐藏层神经元数: 100, 学习率: 0.001, 最大迭代: 200",
            "bpnn_regressor": "隐藏层神经元数: 50, 学习率: 0.01, 最大迭代: 100",
            "cnn_classifier": "卷积核: 32,64, 学习率: 0.0001, epochs: 50"
        }
        return suggestions.get(model_type, "请提供具体模型类型: bpnn_classifier, bpnn_regressor, cnn_classifier")

    @tool
    def explain_model(model_type: str) -> str:
        """解释指定模型的基本原理。参数 model_type 可选: bpnn_classifier, cnn_classifier"""
        explanations = {
            "bpnn_classifier": "BP神经网络分类器使用反向传播算法，通过梯度下降优化交叉熵损失，适用于分类任务。",
            "cnn_classifier": "卷积神经网络通过卷积层提取图像特征，池化层降维，全连接层分类，适合图像识别。"
        }
        return explanations.get(model_type, "选择模型: bpnn_classifier, cnn_classifier")

    return [get_training_progress, suggest_hyperparameters, explain_model]


PREFIX = """你是一个专业的AI助手，回答用户关于训练进度、参数推荐、模型原理的问题。

你必须严格按照以下格式：
Question: 用户问题
Thought: 思考是否需要工具
Action: 工具名称
Action Input: 工具输入（如果需要）
Observation: 工具返回结果
... (可重复)
Thought: 我已获得足够信息
Final Answer: 用中文清晰回答用户

重要：
1. 如果工具返回错误或超时，直接告知用户并给出建议，不要反复调用。
2. 获取进度工具调用时，Action Input 可以留空或填任意值，工具会忽略它。
3. 回答要友好、简洁。
"""


def ask_sync(query: str, user_id: str, current_task_id: Optional[str] = None) -> str:
    memory = get_memory(user_id)
    tools = create_tools(current_task_id)
    llm = get_llm()

    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        memory=memory,
        verbose=True,
        handle_parsing_errors=True,
        agent_kwargs={"prefix": PREFIX},
        max_iterations=3,
        early_stopping_method="generate",
    )

    context = ""
    if current_task_id:
        context = f"（系统提示：用户当前有一个正在运行的训练任务，你可以直接调用获取进度工具查询。）\n"
    full_query = f"{context}用户问题: {query}"

    try:
        result = agent.invoke({"input": full_query})
        output = result.get("output", "")
        if not output or output.startswith("Agent stopped"):
            return "抱歉，我暂时无法处理这个问题，请稍后再试或检查训练服务状态。"
        return output
    except Exception as e:
        print(f"Agent 执行异常: {e}")
        traceback.print_exc()
        return "服务繁忙，请稍后重试。如果问题持续，请联系管理员。"


def ask_with_timeout(query: str, user_id: str, current_task_id: Optional[str] = None, timeout: int = 15) -> str:
    future = executor.submit(ask_sync, query, user_id, current_task_id)
    try:
        return future.result(timeout=timeout)
    except FutureTimeoutError:
        return "处理超时，请稍后再试。您可以尝试刷新页面或简化问题。"
    except Exception as e:
        return f"发生错误: {str(e)}"