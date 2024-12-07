import requests
import json
import os

# Our work generates answers using the RAG system built on RAGFlow, so the following implementation is adapted to RAGFlow and the same API request format

# Define the base URL of the local RAGFlow Docker instance
BASE_URL = '' # Replace with the actual local address and port

# Example API key (if needed)
API_KEY = ''

# Request headers
headers = {
    'Authorization': f'Bearer {API_KEY}'
}

# Start a new conversation
def start_conversation(user_id):
    url = f'{BASE_URL}/api/new_conversation'
    payload = {'user_id': user_id}
    response = requests.get(url, headers=headers, json=payload)
    return response.json()['data']['id'] if response.status_code == 200 else None

# Fetch response
def fetch_response(conversation_id, question):
    url = f'{BASE_URL}/api/completion'
    payload = {}
    payload['conversation_id'] = conversation_id
    payload['messages'] = [{"role": "user", "content": question}]
    payload['stream'] = False
    payload['quote'] = True
    response = requests.post(url, headers=headers, json=payload)
    try:
        return response.json()['data']['answer'], response.json()['data']['reference']['chunks'][0]['doc_name'], response.json()['data']['reference']['chunks'][0]['content_with_weight'] if response.status_code == 200 else "None"
    except:
        with open('log.jsonl', 'a') as f:
            json.dump(response.json(), f, indent=4, ensure_ascii=False)
        try:
            return response.json()['data']['answer'], "exception_error", "exception_error"
        except:
            return response.json()['retmsg'], 'other_error', 'other_error'


def ask(input, conversation_id):
    question = f'{input}\n\n回答以上这个问题，注意分点回答，中文回答'
    answer, doc_name, content = fetch_response(conversation_id, question)
    return answer, doc_name, content

def update(dict, conversation_id):
    input = dict['input']
    answer, doc_name, content = ask(input, conversation_id)
    dict['output'] = answer
    dict['doc_name'] = doc_name
    dict['content'] = content

# Example usage
user_id = 'test_user'

# Traverse the main directory
main_dir = './output'

for root, dirs, files in os.walk(main_dir):
    for dir_name in dirs:
        dir_path = os.path.join(root, dir_name)
        json_path = os.path.join(dir_path, 'deduplicated_inputs.json')

        # Check if the json file exists
        if os.path.isfile(json_path):
            # Read the json file
            with open(json_path, 'r') as f:
                data = json.load(f)

            # Update the data
            for index, dict in enumerate(data):
                if index % 10 == 0:
                    conversation_id = start_conversation(user_id)
                update(dict, conversation_id)

            # Write back to the json file
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            print(f'{dir_path} is finished')
            
    