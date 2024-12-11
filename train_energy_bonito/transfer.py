import json
import random

# The ratio of dropping the negative samples, 0.9 in our experience
RATIO = 0.9

DATA_TYPE = 'QA_OR_MC' # generate tuning data for QA or MC

# Read JSON file
def read_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Save JSON file
def write_json(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def transfer_template(data, json_list):
    for item in data:
        context = item['context']
        for qa in item['q&a']:
            if 'question' in qa and 'answer' in qa:
                if qa['question'] == '无' or qa['answer'] == '无':
                    if random.random() < RATIO:
                        continue
                category = qa['category']
                question = qa['question']
                answer = qa['answer']
                dict = {}
                if DATA_TYPE == 'QA':
                    dict['input'] = f'<|tasktype|>\nextractive question answering ({category})\n<|context|>\n{context}\n<|task|>\n'
                    dict['output'] = f'Based on the following passage from the electricity market policy/article, answer the following question:\n\nPassage: {{context}}\n\nQuestion: {question}\n<|pipe|>\n{answer}'
                elif DATA_TYPE == 'MC':
                    options = qa['options']
                    dict['input'] = f'<|tasktype|>\nmultiple-choice question answering\n<|context|>\n{context}\n<|task|>\n'
                    dict['output'] = f'Based on the following passage from the electricity market policy/article, answer the following multiple-choice question:\n\nPassage: {{context}}\n\nQuestion: {question}\n\nOptions: {options}\n<|pipe|>\n{answer}'
                json_list.append(dict)
    return data

# File paths
input_file_path = ''   # Original file path
output_path = ''       # Path for the transferred file
# Read original JSON data
data = read_json(input_file_path)
tuning_data = []
transfer_template(data, tuning_data)
write_json(tuning_data, output_path)
