#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import argparse
import sys

"""合并两个metadata.json文件，删除重复的key"""

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
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"📁 创建输出目录: {output_dir}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ 合并后的文件已保存到: {output_path}")
        return True
    except Exception as e:
        print(f"❌ 错误：保存文件 '{output_path}' 时发生异常: {e}")
        return False

def merge_metadata(file1_path, file2_path, output_path=None):
    """合并两个metadata.json文件，删除重复的key"""
    # 加载两个JSON文件
    file1_data = load_json_file(file1_path)
    file2_data = load_json_file(file2_path)
    
    if file1_data is None or file2_data is None:
        print("❌ 无法继续合并操作")
        return False
    
    # 统计文件信息
    file1_keys = set(file1_data.keys())
    file2_keys = set(file2_data.keys())
    
    # 找出重复的key
    duplicate_keys = file1_keys.intersection(file2_keys)
    
    # 创建合并后的字典
    merged_data = file1_data.copy()  # 先复制第一个文件的所有内容
    
    # 添加第二个文件中不重复的key
    new_keys_added = 0
    for key, value in file2_data.items():
        if key not in merged_data:
            merged_data[key] = value
            new_keys_added += 1
    
    # 输出合并统计信息
    print(f"📊 合并统计:")
    print(f"   - 第一个文件: {len(file1_keys)} 条记录")
    print(f"   - 第二个文件: {len(file2_keys)} 条记录")
    print(f"   - 重复的key: {len(duplicate_keys)} 个")
    print(f"   - 新增的记录: {new_keys_added} 条")
    print(f"   - 合并后的总记录数: {len(merged_data)} 条")
    
    # 如果有重复的key，列出一部分示例
    if duplicate_keys:
        sample_duplicates = list(duplicate_keys)[:5]  # 只显示前5个
        print(f"   - 重复key示例: {sample_duplicates}")
        if len(duplicate_keys) > 5:
            print(f"   - ... 还有 {len(duplicate_keys) - 5} 个重复的key")
    
    # 如果没有指定输出路径，默认使用第一个文件的路径，但添加merged前缀
    if output_path is None:
        file1_dir = os.path.dirname(file1_path)
        file1_name = os.path.basename(file1_path)
        output_path = os.path.join(file1_dir, f"merged_{file1_name}")
    
    # 保存合并后的文件
    return save_json_file(merged_data, output_path)

def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(description='合并两个metadata.json文件，删除重复的key')
    parser.add_argument('file1', help='第一个metadata.json文件的路径')
    parser.add_argument('file2', help='第二个metadata.json文件的路径')
    parser.add_argument('-o', '--output', help='合并后的输出文件路径')
    
    args = parser.parse_args()
    
    # 执行合并操作
    success = merge_metadata(args.file1, args.file2, args.output)
    
    # 根据操作结果设置退出码
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()