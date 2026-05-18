"""平台公共工具函数"""


def parse_model_id(model_id: str) -> tuple:
    """解析模型ID，返回 (vendor, short_name)

    例如:
        "meta/llama-3.3" → ("meta", "llama-3.3")
        "gpt-4" → ("unknown", "gpt-4")
    """
    if "/" in model_id:
        parts = model_id.split("/", 1)
        return parts[0], parts[1]
    return "unknown", model_id
