import os
import json

def append_policy(root_dir, target_dir, target_file_name):
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file == 'output.md':
                source_path = os.path.join(root, file)
            
                # 使用父目录名称作为文件名前缀
                dir_name = os.path.basename(root)
                unique_filename = f"{dir_name}.txt"
                target_path = os.path.join(target_dir, unique_filename)
                
                # 读取md文件
                with open(source_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                summary_path = os.path.join(root, target_file_name)
                with open(summary_path, 'r') as f:
                    summary = json.load(f)
                    
                try:
                    district = summary['subtree'][0].get('district')
                    time = summary['subtree'][0].get('release_time')
                except:
                    print(summary_path)
                    
                content += f'\n\n---------------------------------------------\n|title|\n{dir_name}\n|district|\n{district}\n|time|\n{time}\n|outline|\n无\n'
                
                # 把content写入到目标文件
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
def append_book(root_dir, target_dir):
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file == 'output.md':
                source_path = os.path.join(root, file)
            
                # 使用父目录名称作为文件名前缀
                dir_name = os.path.basename(root)
                unique_filename = f"{dir_name}.txt"
                target_path = os.path.join(target_dir, unique_filename)
                
                # 读取md文件
                with open(source_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                content += f'\n\n---------------------------------------------\n|title|\n{source_path}\n|district|无\n|time|\n无\n|outline|\n'
                
                # 确保目标目录存在
                os.makedirs(target_dir, exist_ok=True)
                
                # 把content写入到目标文件
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
# 用例示范     
policy_directory = './output_policy'  # 替换为实际的根目录路径
book_directory = './book_md'  # 替换为实际的根目录路径
target_directory = './md_for_graphrag'  # 替换为实际的目标目录路径
policy_json_file_name = 'content.json'  # 替换为实际的文件名

append_policy(policy_directory, target_directory, policy_json_file_name)
append_book(book_directory, target_directory)