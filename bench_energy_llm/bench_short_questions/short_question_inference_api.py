import json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from utils import config_model, generate_response_text, save_json

API_KEY = 'DEFINE_YOUR_API_SERVICE_KEY'
BASE_URL = 'DEFINE_API_BASE_URL'

model_name = input('Please input the model name: ')
file_name = f'../extract_short_questions/{model_name}.json'

with open('../extract_short_questions/API-inference.json', 'r') as f:
    short_answer = json.load(f)

model = config_model(API_KEY, BASE_URL)

url = "http://localhost:8000/v1/chat/completions"

test_model_name_list = [model_name]

for s in short_answer:
    question = s['question']
    query = f'回答以下这个简答题/论述题，使用中文回答，回答可以尽量长和详细，或者是分点回答:\n{question}'
    
    for model_name in test_model_name_list:
        response = generate_response_text(model, query, model_name = model_name)
        
        s['new-energy-llm'] = response
        
model_name = model_name.split('/')[-1]
file_name = f'../extract_short_questions/{model_name}.json'
save_json(short_answer, file_name, isstr = False)