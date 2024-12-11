import json
import re
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from utils import config_model, generate_response_text, save_json
import time

DATA_TYPE = 'QA_OR_MC' # generate tuning data for QA or MC

API_KEY = 'DEFINE_API_SERVICE_KEY'
BASE_URL = 'DEFINE_API_BASE_URL'
MODEL_NAME = 'DEFINE_MODEL_NAME'

model = config_model(API_KEY, BASE_URL)

SAVE_FILE = 'DEFINE_OUTPUT_FILE_NAME'

with open('example_json_content_list.json', 'r') as f:
    content_list = json.load(f)
    
if DATA_TYPE == 'QA':
    with open('example.txt', 'r') as f:
        text = f.read()
elif DATA_TYPE == 'MC':
    with open('mc_example.txt', 'r') as f:
        text = f.read()

def extract_json_blocks(text):
    # Regular expression to match content between ```json and ```
    pattern = re.compile(r'```json(.*?)```', re.DOTALL)
    matches = pattern.findall(text)

    if matches:
        match = matches[0]
        try:
            # Convert the extracted content to a JSON object and store it in a dictionary
            json_object = json.loads(match)
            return json_object
        except json.JSONDecodeError:
            print("Error decoding JSON in block")
            return []
    else:
        try:
            pattern = re.compile(r'\[.*?\]', re.DOTALL)
            matches = pattern.findall(text)
            match = matches[0]
            json_object = json.loads(match)
            return json_object
        except:
            raise ValueError("No matches found in the provided text.")

def request(model, temp):
    if DATA_TYPE == 'QA':
        query = f'{temp}\n\n以上是一条电力市场的政策，请从这里面提取出一个question和一个answer。question和answer都是从这条政策提取，而不是通过你自己的知识回答。问答对的种类有6种，以下是每种种类的示例:\nwhat: 什么是电力辅助服务市场？电力辅助服务市场中二次调频的性能指标k是指什么？\nwhen: 山东省电力现货市场什么时候开始试运行？\nwhy: 电力现货市场为什么会产生负电价？\nhow: 山东省独立储能电站如何在电力辅助服务市场报量报价？\nlist the main points: 储能并网需要满足哪些并网规定与标准？山东的电力辅助服务分类和具体品种有哪些？\ndifference: 广东省和山西省的二次调频性能指标计算方式有什么区别？\n\n请从政策里提取每种种类的问题-答案对，如果某个类别没有就写无，输出为json格式，中文输出，json具体格式为' + '[{"category": "具体类别"\n"question": "具体问题"\n"answer": "具体答案"},\n{...},\n{...}]\n\n'  + f'例如:{text}'
    elif DATA_TYPE == 'MC':
        query = f'{temp}\n\n以上是一条电力市场的政策，请从这里面提取出一个选择题，有四个备选答案，并给出正确答案的选项。问题和选项都是从这条政策提取，而不是通过你自己的知识回答。输出为json格式，中文输出，json具体格式为' + '{"question": "选择题问题题面"\n"options": "四个选项"\n"answer": "答案选项"}\n\n' + f'例如:{text}'
    while True:
        try:
            pair = generate_response_text(model, query, model_name=MODEL_NAME)
            return pair
        except Exception as e:
            print(f'Exception occurred: {e}')
            print('sleep 10s')
            time.sleep(10)

def save(pair, output_dict, tuning_set):
    json_obj = extract_json_blocks(pair)
    output_dict['q&a'] = json_obj
    tuning_set.append(output_dict)
    
    save_json(tuning_set, SAVE_FILE, isstr=False)

with open(SAVE_FILE, 'r') as f:
    tuning_set = json.load(f)

for index, content_obj in enumerate(content_list):
    output_dict = {}  
    output_dict['context'] = content_obj
    pair = request(model, content_obj)
    
    try:
        save(pair, output_dict, tuning_set)
    except ValueError:
        print('No matches found in the provided text.')
        continue