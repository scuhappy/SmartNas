#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import argparse
import sys

"""从metadata.json的title中提取女优名字，并添加actor_name字段"""

def load_json_file(file_path):
    """加载JSON文件，处理可能的异常"""
    try:
        if not os.path.exists(file_path):
            print(f"❌ 错误：文件 '{file_path}' 不存在")
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ 错误：文件 '{file_path}' 不是有效的JSON格式: {e}")
        return None
    except Exception as e:
        print(f"❌ 错误：读取文件 '{file_path}' 时发生异常: {e}")
        return None

def save_json_file(data, output_path):
    """保存数据到JSON文件"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ 更新后的文件已保存到: {output_path}")
        return True
    except Exception as e:
        print(f"❌ 错误：保存文件 '{output_path}' 时发生异常: {e}")
        return False

def extract_actor_name(title):
    """从标题中提取女优名字，取最后一个空格字符后面的内容"""
    if not title:
        return None
    
    # 查找最后一个空格
    last_space_index = title.rfind(' ')
    if last_space_index == -1:
        return None
    
    # 提取最后一个空格后的内容作为女优名字
    actor_name = title[last_space_index + 1:].strip()
    return actor_name if actor_name else None

def process_metadata(input_file, output_file=None):
    """处理metadata.json文件，为每个条目添加actor_name字段"""
    # 加载JSON文件
    metadata = load_json_file(input_file)
    
    if metadata is None:
        print("❌ 无法继续处理操作")
        return False
    
    # 统计信息
    total_entries = len(metadata)
    updated_entries = 0
    skipped_entries = 0
    
    # 处理每个条目
    for fanhao, info in metadata.items():
        # 检查是否已经有actor_name字段
        if 'actor_name' in info and info['actor_name']:
            skipped_entries += 1
            continue
        
        # 提取女优名字
        title = info.get('title', '')
        actor_name = extract_actor_name(title)
        
        if actor_name:
            metadata[fanhao]['actor_name'] = actor_name
            updated_entries += 1
            # 输出一些示例信息
            if updated_entries <= 5:  # 只显示前5个更新的条目
                print(f"📝 更新条目: {fanhao} - 提取的女优名字: {actor_name}")
        else:
            # 如果没有提取到名字，也可以选择添加一个空的actor_name字段
            metadata[fanhao]['actor_name'] = None
            skipped_entries += 1
    
    # 输出处理统计信息
    print(f"📊 处理统计:")
    print(f"   - 总条目数: {total_entries}")
    print(f"   - 已更新的条目: {updated_entries}")
    print(f"   - 已存在或无法提取名字的条目: {skipped_entries}")
    
    # 如果没有指定输出路径，默认覆盖输入文件
    if output_file is None:
        output_file = input_file
    
    # 保存更新后的文件
    return save_json_file(metadata, output_file)

def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(description='从metadata.json的title中提取女优名字，并添加actor_name字段')
    parser.add_argument('input_file', nargs='?', default='metadata.json', help='metadata.json文件的路径，默认为当前目录下的metadata.json')
    parser.add_argument('-o', '--output', help='更新后的输出文件路径，默认覆盖输入文件')
    
    args = parser.parse_args()
    
    # 执行处理操作
    success = process_metadata(args.input_file, args.output)
    
    # 根据操作结果设置退出码
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()