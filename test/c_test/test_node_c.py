"""

c_node_md_img 节点整体测试

按图节点的调用方式传入 state，跑完整流程（扫描图片 → 生成摘要 →
上传 MinIO → 替换引用 → 保存新 MD），最后打印处理后的 MD 文件路径。

注意：本节点会真实调用多模态大模型并上传图片到 MinIO，
需保证 .env 中 OPENAI_* / MINIO_* 配置正确、服务可访问。

"""

from processor.import_processor.base import setup_logging
from processor.import_processor.nodes.c_node_md_img import NodeMDImg
from processor.import_processor.state import create_default_state

setup_logging()

# ==================== 测试数据 ====================
md_path = r"D:\output\hak180使用说明书\hak180使用说明书.md"

with open(md_path, "r", encoding="utf-8") as f:
    md_content = f.read()


def main():
    # 构造节点所需的 state：md_path + md_content
    state = create_default_state(md_path=md_path, md_content=md_content)

    node = NodeMDImg()

    # 按图节点调用方式执行，返回更新后的 state
    result = node(state)

    # 处理后的 MD 文件路径（原文件备份为 xxx_new.md）
    print(f"\n处理后 MD 文件路径：{result['md_path']}")


if __name__ == "__main__":
    main()
