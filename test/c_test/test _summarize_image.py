from processor.import_processor.nodes.c_node_md_img import *


# 修复转义警告，加 r
md_path = r"D:\output\hak180使用说明书\hak180使用说明书.md"
with open(md_path, "r", encoding="utf-8") as f:
    md_content = f.read()

image_dir = Path(r"D:\output\hak180使用说明书\images")

# 实例化 NodeMDImg，注意Minio配置必须正确，否则node初始化失败
node = NodeMDImg()

doc_stem = Path(md_path).stem                      # "hak180使用说明书"
target_images = node._step_2_scan_images(md_content, image_dir)

for img_file, img_path, context in target_images:  # (文件名, 完整路径, (前文,后文))
    doc_stem = Path(md_path).stem                      # "hak180使用说明书"
target_images = node._step_2_scan_images(md_content, image_dir)

for img_file, img_path, context in target_images:  # (文件名, 完整路径, (前文,后文))
      summary = node._summarize_image(img_path, doc_stem, context)
      print(img_file, "->", summary)
