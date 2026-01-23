import json
import os


def convert_json_to_txt(input_file, output_file):
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 找不到文件 {input_file}")
        return

    try:
        # 读取 JSON 文件
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        lines = []

        # 遍历 JSON 数据
        for key, value_list in data.items():
            # 1. 处理标题：去除下划线后的 ID (例如: "乙酰胆碱_156169" -> "乙酰胆碱")
            # 如果 key 中没有下划线，则保留原样
            clean_name = key.split('_')[0] if '_' in key else key

            # 添加分割线和标题
            lines.append(f"=== {clean_name} ===")

            # 2. 处理内容列表
            if value_list:
                for section in value_list:
                    # 获取章节标题 (例如: 药理作用)
                    title = section.get('title', '')
                    if title:
                        lines.append(f"【{title}】")

                    # 获取并格式化条目 (例如: 1. 心血管系统)
                    items = section.get('items', [])
                    for index, item in enumerate(items, 1):
                        lines.append(f"{index}. {item}")

            # 每个主条目后添加空行，方便阅读
            lines.append("")

            # 写入 TXT 文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"成功导出！文件已保存为: {output_file}")

    except json.JSONDecodeError:
        print(f"错误: {input_file} 不是有效的 JSON 格式。")
    except Exception as e:
        print(f"发生未知错误: {e}")


if __name__ == "__main__":
    # 配置输入和输出文件名
    INPUT_FILENAME = 'structure_data.json'
    OUTPUT_FILENAME = 'human_readable_structure.txt'

    convert_json_to_txt(INPUT_FILENAME, OUTPUT_FILENAME)