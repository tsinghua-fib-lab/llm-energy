import requests
import json
import re
import concurrent.futures
import time

# Deploy Energy Bonito to the local server and use the local API for inference

def extract_qa(content):
    question_pattern = r"Question:\s*(.*?)\s*Options"
    options_pattern = r"Options:\s*(.*?)\s*<\|pipe\|>"
    answer_pattern = r"<\|pipe\|>\s*(.*)"

    question_match = re.search(question_pattern, content, re.DOTALL)
    option_match = re.search(options_pattern, content, re.DOTALL)
    answer_match = re.search(answer_pattern, content, re.DOTALL)

    question = question_match.group(1).strip() if question_match else "未找到问题"
    options = option_match.group(1).strip() if option_match else "未找到选项"  
    answer = answer_match.group(1).strip() if answer_match else "未找到答案"

    return question, answer, options

def process_chunk(chunk, url):
    tuning_json = []
    for index, context in enumerate(chunk):
        new_dict = {'context': context}
        new_qa_list = []
        qa_dict = {}
        data = {
            "model": "Qwen2-7B-Instruct",
            "messages": [
                {
                    "role": "user",
                    "content": f'<|tasktype|>\nmultiple-choice question answering\n<|context|>\n{context}\n<|task|>\n'
                }
            ],
            "temperature": 0.7,
            "top_p": 0.95
        }

        # Send POST request to local API
        response = requests.post(url, json=data)

        # Process response
        if response.status_code == 200:
            result = response.json()
            try:
                receive = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                question, answer, options = extract_qa(receive)
                qa_dict['question'] = question
                qa_dict['options'] = options
                qa_dict['answer'] = answer
            except:
                print('json_error')
                qa_dict['question'] = 'json_error'
                qa_dict['options'] = 'json_error'
                qa_dict['answer'] = 'json_error'
        else:
            failed_message = f'Request failed with status code: {response.status_code}'
            print(failed_message)
            qa_dict['question'] = failed_message
            qa_dict['options'] = failed_message
            qa_dict['answer'] = failed_message

        new_qa_list.append(qa_dict)

        new_dict['q&a'] = new_qa_list
        tuning_json.append(new_dict)
        print(f'{index} is finished with URL: {url}')

    return tuning_json


PARALLEL_CNT = 'ADD_YOUR_PARALLEL_CNT'  # Desired parallel count
INPUT_JSON_FILE = 'ADD_YOUR_INPUT_JSON_FILE'  # Input JSON file
OUTPUT_TUNING_DATA_FILE = 'ADD_YOUR_OUTPUT_TUNING_DATA_FILE'  # Output JSON file
url_list = [f"http://localhost:800{i}/v1/chat/completions" for i in range(PARALLEL_CNT)]

with open(INPUT_JSON_FILE, 'r') as f: 
    json_data = json.load(f)
    
task_type = ['what', 'how', 'why', 'when', 'list the main points', 'difference']

# Split json_data
chunk_size = len(json_data) // PARALLEL_CNT
json_chunks = [json_data[i:i + chunk_size] for i in range(0, len(json_data), chunk_size)]

# If not divisible, the last chunk contains all remaining content
if len(json_chunks) > PARALLEL_CNT:
    json_chunks[-2].extend(json_chunks[-1])
    json_chunks = json_chunks[:-1]

# Use ProcessPoolExecutor for parallel processing
with concurrent.futures.ProcessPoolExecutor(max_workers=PARALLEL_CNT) as executor:
    future_to_chunk = {executor.submit(process_chunk, chunk, url): url for chunk, url in zip(json_chunks, url_list)}

    all_results = []
    for future in concurrent.futures.as_completed(future_to_chunk):
        result = future.result()
        all_results.extend(result)

with open(OUTPUT_TUNING_DATA_FILE, 'w', encoding='utf-8') as f:
    json.dump(all_results, f, ensure_ascii=False, indent=4)
