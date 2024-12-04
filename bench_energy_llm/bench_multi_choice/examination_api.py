import json
from utils import config_model, generate_response_text
import time
from bench_util import check
from datetime import datetime

API_KEY = 'DEFINE_API_SERVICE_KEY'
BASE_URL = 'DEFINE_API_BASE_URL'
MODEL_NAME = 'DEFINE_MODEL_NAME'

mode = input('input easy or hard: ')
model = config_model(API_KEY, BASE_URL)

if mode == 'easy':
    with open('../bench_test_questions/test_1000_new.json', 'r') as f:
        json_data = json.load(f)
elif mode == 'hard':
    with open('../bench_test_questions/cot-test_dedu_fake_transfered.json', 'r') as f:
        json_data = json.load(f)
    
correct_cnt = 0

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
            query = f'{question}\n回答以上问题，只需要输出正确的答案选项（ABCD等）即可。这是一个多选题，有多个选项正确，每个答案用空格分隔。\n'
        else:
            query = f'{question}\n回答以上问题，只需要输出正确的答案选项（ABCD等）即可。这是一个单选题，只有一个答案是正确的，输出单个选项字母即可。\n'
    elif mode == 'hard':
        query = f'{question}\n回答以上问题，只需要输出正确的答案选项（ABCD等）即可。如果有多个选项正确，每个答案用空格分隔。'
    while True:
        try:
            response = generate_response_text(model, query, model_name=MODEL_NAME, temperature=0)
            break
        except Exception as e:
            print(f'Exception occurred: {e}')
            time.sleep(1)
    
    if check(answer_list, response, test):
        correct_cnt += 1
        
print(f'correct_cnt is {correct_cnt}')
    
current_time = datetime.now()
result_file_name = '../bench_result/' + str(current_time) + '_test_result.json'
with open(result_file_name, 'w') as f:
    json.dump(json_data, f, ensure_ascii=False, indent=4)