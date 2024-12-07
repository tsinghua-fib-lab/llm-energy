import json
import os
import re

def split_and_get_after(text, symbol):
    # 使用split分割字符串，只分割第一个匹配到的符号
    parts = text.split(symbol, 1)
    
    # 如果符号存在，返回符号后的部分；否则，返回原有的字符串
    if len(parts) > 1:
        return parts[1]
    else:
        return text

def extract_after(text, symbol):
    course_index = text.find(symbol)
    
    if course_index != -1:
        comma_index = text.find("，", course_index)
        
        if comma_index != -1:
            return text[comma_index + 1:].strip()
    
    return text

def clean_question(question):
    question = split_and_get_after(question, ':')
    question = split_and_get_after(question, '：')
    question = extract_after(question, '课程')
    return question

def clean_answer(answer):
    answer = re.sub(r'##\d+\$\$', '', answer)
    answer = extract_after(answer, '知识库')
    return answer

# 遍历主目录
main_dir = './output'
entire_list = []

for root, dirs, files in os.walk(main_dir):
    for dir_name in dirs:
        dir_path = os.path.join(root, dir_name)
        json_path = os.path.join(dir_path, 'deduplicated_inputs.json')
        new_path = os.path.join(dir_path, 'cleaned_tuning.json')

        # 检查json文件是否存在
        if os.path.isfile(json_path):
            # 读取json文件
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            clean_list = []
            # 更新数据
            for dict in data:
                if not dict['doc_name'] in ['exception_error', 'other_error']:
                    answer = dict['output']
                    if '回答被截断' in answer:
                        continue
                    dict['output'] = clean_answer(answer)
                    question = dict['input']
                    dict['input'] = clean_question(question)
                    clean_list.append(dict)
                    entire_list.append(dict)

            # 写回json文件
            with open(new_path, 'w') as f:
                json.dump(clean_list, f, indent=4, ensure_ascii=False)
            
            print(f'{new_path} finished')
            
with open('knowledge_network_tuning_data.json', 'w') as f:
    json.dump(entire_list, f, indent=4, ensure_ascii=False)