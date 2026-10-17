import os
from langchain_openai import ChatOpenAI


from config.lm_config import lm_config

# 缓存字典，保存已经创建好的LLM客户端
_llm_client_cache = {}

def get_llm_client(model: str | None = None, json_model: bool = False):
    # 不传model就用配置文件里默认的模型
    m = model or lm_config.llm_model

    # 缓存key：(模型名, 是否json输出)
    key = (m, json_model)

    # 如果已经创建过这个客户端，直接返回缓存里的，不再新建
    if key in _llm_client_cache:
        return _llm_client_cache[key]

    # 新建ChatOpenAI客户端
    client = ChatOpenAI(
        model=m,
        temperature=lm_config.llm_temperature,
        base_url=lm_config.base_url,
        api_key=lm_config.api_key,
    )
    # 开启json输出
    if json_model:
        client = client.bind(response_format={"type": "json_object"})

    _llm_client_cache[key] = client
    return client


# utils/llm_utils.py

from langchain_openai import ChatOpenAI

from config.lm_config import lm_config

_llm_client_cache = {}


def get_llm_client(model: str | None = None, json_mode: bool = False) -> ChatOpenAI:
    """
    获取 LangChain ChatOpenAI 客户端实例
    - model: 允许不同节点使用不同模型
    - json_mode: True 时要求输出 JSON
    """
    m = model or lm_config.llm_model
    key = (m, json_mode)
    if key in _llm_client_cache:
        return _llm_client_cache[key]

    extra_body = {"enable_thinking": False}

    model_kwargs: dict = {}
    if json_mode:
        model_kwargs["response_format"] = {"type": "json_object"}

    client = ChatOpenAI(
        model=m,
        temperature=lm_config.llm_temperature,
        api_key=lm_config.api_key,
        base_url=lm_config.base_url,
        extra_body=extra_body,
        model_kwargs=model_kwargs,
    )
    _llm_client_cache[key] = client
    return client


if "__main__" == __name__:
    llm = get_llm_client()
    response=llm.invoke("你好")
    print(response.content)