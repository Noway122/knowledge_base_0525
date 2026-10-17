"""

_step_4_upload_and_replace 单独测试

只测第 4 步（上传 MinIO + 替换 MD 图片引用），
用伪造摘要跳过耗时的第 3 步多模态大模型调用。

注意：本测试会真实上传图片到 MinIO，需保证 .env 中
MINIO_* 配置正确、MinIO 服务可访问。

"""

import re
from pathlib import Path

from processor.import_processor.base import setup_logging
from processor.import_processor.nodes.c_node_md_img import NodeMDImg

setup_logging()

# ==================== 测试数据 ====================
md_path = r"D:\output\hak180使用说明书\hak180使用说明书.md"
image_dir = Path(r"D:\output\hak180使用说明书\images")

with open(md_path, "r", encoding="utf-8") as f:
    md_content = f.read()


def main():
    # 实例化节点，MinIO 配置必须正确，否则初始化 / 上传会失败
    node = NodeMDImg()

    # 步骤 1：扫描图片，得到 (图片文件名, 图片完整路径, (前文, 后文)) 列表
    target_images = node._step_2_scan_images(md_content, image_dir)
    print(f"扫描到待处理图片 {len(target_images)} 张：")
    for img_file, img_path, _ in target_images:
        print(f"  - {img_file}  ->  {img_path}")

    if not target_images:
        print("没有可处理的图片，检查图片文件夹或 MD 中的图片引用")
        return

    # 步骤 2：伪造摘要，替代耗时的 _step_3_generate_summaries
    # 关键：摘要字典的 key 必须是「图片文件名」，否则 _merge_summary_and_url 会过滤掉
    summaries = {
        img_file: f"测试摘要_{i}"
        for i, (img_file, _, _) in enumerate(target_images, start=1)
    }

    # 步骤 3：上传图片至 MinIO 并替换 MD 中的图片引用
    new_md_content = node._step_4_upload_and_replace(
        doc_stem=Path(md_path).stem,
        target_images=target_images,
        summaries=summaries,
        md_content=md_content,
    )

    # 步骤 4：校验替换结果
    pattern = re.compile(r"!\[.*?\]\(.*?\)")
    before = pattern.findall(md_content)
    after = pattern.findall(new_md_content)

    # 替换成功的标志：引用里不再是本地 images/ 路径，而是 MinIO 的 http URL
    replaced = [ref for ref in after if "http" in ref]
    still_local = [ref for ref in after if "images/" in ref or "images\\" in ref]

    print("\n" + "=" * 60)
    print(f"替换前图片引用 {len(before)} 处，替换后 {len(after)} 处")
    print(f"已替换为 MinIO URL：{len(replaced)} 处")
    print(f"仍为本地路径（上传失败/未匹配）：{len(still_local)} 处")
    print("=" * 60)
    print("替换后（前 3 处）：")
    for line in after[:3]:
        print(f"  {line}")
    if still_local:
        print("\n未替换成功的引用（前 3 处）：")
        for line in still_local[:3]:
            print(f"  {line}")


if __name__ == "__main__":
    main()
