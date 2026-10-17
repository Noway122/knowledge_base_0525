# test_llm.py
from utils.llm_utils import get_llm_client

def test_llm():
    llm = get_llm_client()
    if not llm:
        print("❌ LLM客户端创建失败")
        return

    try:
        resp = llm.invoke("你好，请简单介绍一下RAG是什么，一句话回答")
        print("✅ 大模型调用成功！")
        print("模型返回：", resp.content)
    except Exception as e:
        print("❌ 调用大模型出错：", e)


def test_llm_json():
    # 测试json输出模式
    llm_json = get_llm_client(json_model=True)
    if not llm_json:
        print("❌ JSON模式LLM客户端创建失败")
        return
    try:
        resp = llm_json.invoke("输出json，key为name，value为'RAG知识库'")
        print("\n✅ JSON模式调用成功！")
        print("模型返回：", resp.content)
    except Exception as e:
        print("\n❌ JSON模式调用出错：", e)


if __name__ == "__main__":
    test_llm()
    test_llm_json()
