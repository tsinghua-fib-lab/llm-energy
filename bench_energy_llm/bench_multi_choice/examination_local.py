import requests
import json
from bench_util import check
from datetime import datetime
import time
        
# This script is designed to work with a locally deployed LLM using the Hugging Face inference engine. It is also compatible with other inference engines that use the same request format.
        
port = 'YOUR_LOCAL_LLM_API_PORT'
url = f"http://localhost:{port}/v1/chat/completions"
    
mode = input('input easy or hard: ')    
    
if mode == 'easy':
    with open('../bench_test_questions/test_1000_new.json', 'r') as f:
        json_data = json.load(f)
elif mode == 'hard':
    with open('../bench_test_questions/cot-test_dedu_fake_transfered.json', 'r') as f:
        json_data = json.load(f)

MAX_RETRIES = 3 # maximum number of retries for a failed request

correct_cnt = 0 # evaluation result counter

for test in json_data:
    answer_list = test['answer']
    if mode == 'easy':
        question = test['question']
        option_list = test['options']
        for opt in option_list:
            question += f'\n{opt}'
    elif mode == 'hard':
        question = test['input']
    if mode == 'easy':
        if len(answer_list) > 1:
            data = {
                    "model": "qwen2-7b-chat",
                    "messages": [
                        {
                            "role": "user",
                            "content": f'{question}\n回答以上问题，只需要输出正确的答案选项（ABCD等）即可。这是一个多选题，有多个选项正确，每个答案用空格分隔。\n'
                        }
                    ],
                    "temperature": 0,
                    "top_p": 0.95
            }
        else:
            data = {
                    "model": "qwen2-7b-chat",
                    "messages": [
                        {
                            "role": "user",
                            "content": f'{question}\n回答以上问题，只需要输出正确的答案选项（ABCD等）即可。这是一个单选题，只有一个答案是正确的，输出单个选项字母即可。\n'
                        }
                    ],
                    "temperature": 0,
                    "top_p": 0.95
            }
    elif mode == 'hard':   
        data = {
                "model": "qwen2-7b-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": f'{question}\n回答以上问题，只需要输出正确的答案选项（ABCD等）即可。如果有多个选项正确，每个答案用空格分隔。'
                    }
                ],
                "temperature": 0,
                "top_p": 0.95
        }
    
    retry_count = 0
    success = False
    
    while retry_count < MAX_RETRIES and not success:
        # Send POST request to local API
        while True:
            try:
                response = requests.post(url, json=data)
                break
            except:
                time.sleep(10)
        
        # Handle response
        if response.status_code == 200:
            result = response.json()
            receive = result.get('choices', [{}])[0].get('message', '').get('content', '').strip()
            if check(answer_list, receive, test):
                correct_cnt += 1
            success = True
        else:
            retry_count += 1
            if retry_count < MAX_RETRIES:
                print(f'Failed request, retrying {retry_count}/{MAX_RETRIES}...')
            else:
                print(f'Request failed with status code: {response.status_code}, max retries reached.')

print(f'correct_cnt is {correct_cnt}')
    
current_time = datetime.now()
result_file_name = '../bench_result/' + str(current_time) + '_test_result.json'
with open(result_file_name, 'w') as f:
    json.dump(json_data, f, ensure_ascii=False, indent=4)