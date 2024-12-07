import json
import re
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from utils import config_model, generate_response_text, save_json

API_KEY = 'DEFINE_API_SERVICE_KEY'
BASE_URL = 'DEFINE_API_BASE_URL'
MODEL_NAME = 'DEFINE_MODEL_NAME'
model = config_model()

def generate_paths(node, path=[]):
    path = path + [node["title"]]
    if "topics" not in node or not node["topics"]:
        return [path]
    paths = []
    for topic in node["topics"]:
        new_paths = generate_paths(topic, path)
        for p in new_paths:
            paths.append(p)
    return paths

# Generate all paths
all_paths = []

with open('xmind.json', 'r', encoding='utf-8') as f:
    knowledge_network = json.load(f)

for item in knowledge_network:
    all_paths.extend(generate_paths(item))

def list_subdirectories(directory):
    return [name for name in os.listdir(directory) if os.path.isdir(os.path.join(directory, name))]

# Example usage
directory = './output'  # Replace this with the target output folder path
subdirectories = list_subdirectories(directory)

for index, path in enumerate(all_paths):
    target_dir = '_'.join(path)
    target_dir = target_dir[:70] if len(target_dir) > 70 else target_dir
    if target_dir not in subdirectories:
        os.makedirs(f'./output/{target_dir}', exist_ok=True)
        
        query = f'{path}\n这是一个电力市场政策知识体系层级的list，list中从前往后是从大方面到小方面，根据这个生成这一subject的syllabus'
        response_text = generate_response_text(model, query, model_name=MODEL_NAME)
        
        with open(f'./output/{target_dir}/syllabus.txt', 'w', encoding='utf-8') as f:
            f.write(response_text)

        query = '根据以下课程大纲列出10-30个class session，每个class session对应5个左右的key concept，输出格式为json，格式为[{[class_session名称]:[各个key_concept的list]}\n {[class_session名称]:[各个key_concept的list]}]' + '\n' + response_text
        class_key_content = generate_response_text(model, query, model_name=MODEL_NAME)
        
        class_key_content = re.sub(r'^```json', '', class_key_content)
        class_key_content = re.sub(r'```$', '', class_key_content)
        
        save_json(class_key_content, f'./output/{target_dir}/class_key.json')
