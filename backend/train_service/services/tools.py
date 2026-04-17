import requests
from langchain.tools import tool
from ..config import TRAIN_SVC_URL

@tool
def get_training_progress(task_id: str) -> str:
    """获取指定训练任务的当前进度。如果不知道 task_id，请先询问用户或提示当前无运行任务。"""
    if not task_id or task_id.strip() == "":
        return "未提供任务ID，请指定要查询的训练任务ID。"
    try:
        resp = requests.get(f"{TRAIN_SVC_URL}/train/training/progress/{task_id}")
        if resp.status_code == 200:
            data = resp.json()
            return f"阶段: {data.get('phase')}, 进度: {data.get('progress_percent')}%, 当前误差: {data.get('error')}"
        else:
            return "未找到该训练任务"
    except Exception:
        return "无法获取训练进度"

@tool
def suggest_hyperparameters(model_type: str) -> str:
    """根据模型类型提供推荐的超参数设置"""
    suggestions = {
        "bpnn_classifier": "隐藏层: 100, 学习率: 0.001, 最大迭代: 200",
        "bpnn_regressor": "隐藏层: 50, 学习率: 0.01, 最大迭代: 100",
        "cnn_classifier": "卷积核: 32,64, 学习率: 0.0001, epochs: 50"
    }
    return suggestions.get(model_type, "请提供具体模型类型")

@tool
def explain_model(model_type: str) -> str:
    """解释指定模型类型的基本原理和结构"""
    explanations = {
        "bpnn_classifier": "BP神经网络分类器使用反向传播算法，通过梯度下降优化交叉熵损失...",
        "cnn_classifier": "卷积神经网络通过卷积层提取图像特征，池化层降低维度，全连接层分类..."
    }
    return explanations.get(model_type, "选择模型: bpnn_classifier, cnn_classifier")