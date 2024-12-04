import json
import requests
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../bench_multi_choice')))
from utils import save_json

model_name = input('Please input the model name: ')
file_name = f'../extract_short_questions/{model_name}.json'

with open('../extract_short_questions/API-inference.json', 'r') as f:
    short_answer = json.load(f)

port = 'YOUR_LOCAL_LLM_API_PORT'
url = f"http://localhost:{port}/v1/chat/completions"

for s in short_answer:
    question = s['question']
    query = f'回答以下这个简答题/论述题，使用中文回答，回答可以尽量长和详细，或者是分点回答:\n{question}'
    
    data = {
            "model": "qwen2-7b-chat",
            "messages": [
                {
                    "role": "user",
                    "content": query
                }
            ],
            "temperature": 0.5,
            "top_p": 0.95
    }
    
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        receive = result.get('choices', [{}])[0].get('message', '').get('content', '').strip()
    else:
        print(f'Request failed with status code: {response.status_code}')
        
    s['new-energy-llm'] = receive
        
# save to short_answer.json
save_json(short_answer, file_name, isstr = False)