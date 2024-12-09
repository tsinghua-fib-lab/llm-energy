import json
import re
from utils import config_model, generate_response_text
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from sklearn.cluster import DBSCAN
import time
from scipy.spatial.distance import cdist

API_KEY = 'DEFINE_API_SERVICE_KEY'
BASE_URL = 'DEFINE_API_BASE_URL'
MODEL_NAME = 'DEFINE_MODEL_NAME'
model = config_model(API_KEY, BASE_URL)

def extract_subjects(content):
    prompt = f"帮我提取一个下面这个问题的概念/知识点，只需要一个最能代表的即可：\n{content}\n你的输出用概念：[[具体概念]]来表示，比如[[某某地区的电力市场交易主体]]"
    response = generate_response_text(model, prompt, temperature=0.5, model_name=MODEL_NAME)
    match = re.search(r'\[\[(.*?)\]\]', response)
    if match:
        # Extract the concept/knowledge point from the brackets
        concept = match.group(1)
    else:
        concept = 'null'
        
    return concept

def extract_subjects_options(content, correct_option):
    prompt = f"帮我提取一个下面问题下的正确选项答案的概念/知识点，只需要一个最能代表的即可：\nquesion:\n{content}\ncorrect answer:\n{correct_option}\n你的输出用概念：[[具体概念]]来表示，比如[[某某地区的电力市场交易主体]]"
    response = generate_response_text(model, prompt, temperature=0.5, model_name=MODEL_NAME)
    match = re.search(r'\[\[(.*?)\]\]', response)
    if match:
        # Extract the concept/knowledge point from the brackets
        concept = match.group(1)
    else:
        concept = 'null'
        
    return concept

file_name = 'test_1000_new.json'

with open(file_name, 'r', encoding='utf-8') as f:
    data = json.load(f)
    
for index, item in enumerate(data):
    questions = item['question']
    options_list = item['options']
    answer_list = item['answer']
    
    # Extract subjects from questions
    question_subject = extract_subjects(questions)
    item['question_subject'] = question_subject
    correct_options = item['answer']  # a list
    temp_dict = {}
    check = False
    for opt in correct_options:
        try:
            temp_dict[opt] = options_list[ord(opt) - ord('A')]
        except:
            # Remove the current item and break the loop
            data.pop(index)
            check = True
            break
    if check:
        continue
        
    option_subject = extract_subjects_options(questions, temp_dict)
    item['options_subject'] = option_subject
    
    print(f'Index: {index} finished')
    
df_dict = {
    'index': [],
    'category': [],
    'content': [],
    'embedding': []
}

model = SentenceTransformer('paraphrase-distilroberta-base-v1') 

for i, mc in enumerate(data):
    # question
    df_dict['index'].append(i)
    df_dict['category'].append('question')
    df_dict['content'].append(mc['question_subject'])
    df_dict['embedding'].append(model.encode(mc['question_subject']))
    # options
    df_dict['index'].append(i)
    df_dict['category'].append('options')
    df_dict['content'].append(mc['options_subject'])    
    df_dict['embedding'].append(model.encode(mc['options_subject']))
        
df = pd.DataFrame(df_dict)

# Function to calculate cosine similarity
def get_similar_sentences(query_embedding, embeddings, top_n=5):
    similarities = cosine_similarity([query_embedding], embeddings)[0]  # Calculate cosine similarity with all sentences
    similar_indices = similarities.argsort()[-top_n:][::-1]  # Find the indices of the most similar sentences
    return similar_indices, similarities[similar_indices]

def str_to_vector(query_embedding):
    # Remove brackets from the string and split into numerical parts
    query_embedding = query_embedding.strip('[]')  # Remove brackets
    str_list = query_embedding.split()  # Split by spaces

    # Convert the string list to floats and create a NumPy array
    query_embedding = np.array(str_list, dtype=np.float32)
    return query_embedding

def summary(query_index, df):
    df_line = df.iloc[query_index]
    base_index = df_line['index']
    base_subject = df_line['content']
    category = df_line['category']
    base_content = data[base_index][category if category == 'question' else 'options']
    base_dict = {
        'index': base_index,
        'category': category,
        'content': base_content,
        "base_subject": base_subject,
        'ori_test': data[base_index]
    }
    
    return base_dict, df_line['embedding']
    
def convert_int64(obj):
    if isinstance(obj, dict):
        return {key: convert_int64(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_int64(item) for item in obj]
    elif isinstance(obj, np.int64):
        return int(obj)  # Convert to native Python int
    else:
        return obj


total_lenght = len(df)
matching_result_list = []
for query_index in range(total_lenght):
    base_dict, query_embedding = summary(query_index, df)
    similar_indices, similar_scores = get_similar_sentences(query_embedding, np.vstack(df['embedding'].values))
    sumilar_list = []
    for idx, score in zip(similar_indices, similar_scores):
        similar_dict, _ = summary(idx, df)
        if similar_dict['category'] == base_dict['category']:
            continue
        sumilar_list.append(similar_dict)
        
    matching_result_list.append({
        'base': base_dict,
        'similar': sumilar_list
    })
    
    print(f"Matching {query_index}/{total_lenght}")
        
matching_result_list = convert_int64(matching_result_list)

with open('example.txt', 'r') as f:
    example = f.read()
        
def try_merge(base, similar):
    option_one = base if base['category'] == 'options' else similar
    question_one = base if base['category'] == 'question' else similar
    option_one_test = option_one['ori_test']
    question_one_test = question_one['ori_test']
    option_one_input = option_one_test['input']
    question_one_input = question_one_test['input']
    option_one_output = option_one_test['output']
    question_one_output = question_one_test['output']
    option_one_subject = option_one['base_subject']
    question_one_subject = question_one['base_subject']
    query = f'我这里有两道题。请你判断是否可以合并成一个更复杂的问题，从第一题的题干推导到第二题的答案，使得考生需要隐式地先推导出第一题的答案然后解答整个问题。你需要灵活地变通题目的问法和选项达到融合的效果，甚至可以不完全是从第一题的答案匹配到第二题的题干，需要灵活变通。\n几个例子如下：\n{example}\n如果你认为不适合融合，包括题目关系或者题目质量等，直接输出{{"question": "无", "options": "无", "output": "无"}}。如果可以融合则正常输出{{"question": "题干", "options": "题目选项", "output": "正确选项"}}\n以下是你现在需要处理的两个题目：\n第一道：\n{option_one_input}\n答案：{option_one_output}\n第二道：\n{question_one_input}\n答案：{question_one_output}\n第一道题的答案和第二题的问题所涉及到的考点和概念经过初步判断是相似的，分别是{option_one_subject}|{question_one_subject}。可以融合时，output部分不仅仅输出最后的答案，还要体现推理的过程，你应该按照两道题目中相关联的知识点的角度写出思考和推理，但是不要具体拿出第一题第二题这样的说法来，也就是这个推理不是基于具体题目的，而是着重于题目中所涉及的知识/概念的关系，分析和推理的最后用Choice: [[具体选项]]给出最终答案。'
    while True:
        try:
            merge_test = generate_response_text(model, query, model_name=MODEL_NAME)
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)
    try:
        # Use regular expressions to extract content within '{}'
        json_strs = re.findall(r'\{(.*?)\}', merge_test)
        
        # Attempt to parse each matched string as JSON
        json_str = json_strs[0]
        try:
            parsed_json = json.loads('{' + json_str + '}')  # Restore complete JSON format and parse
            return parsed_json
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            return False
    except Exception as e:
        return False
    
unmatched_record_dict = {}
matched_list = []
    
for index, matching in enumerate(matching_result_list):
    base = matching['base']
    similar_list = matching['similar']
    if similar_list:
        check = 0
        for similar in similar_list:
            merge_test = try_merge(base, similar)
            if merge_test:
                if merge_test['question'] == '无' or merge_test['output'] == '无' or merge_test['options'] == '无':
                    if similar['index'] not in unmatched_record_dict:
                        unmatched_record_dict[similar['index']] = 0
                else:
                    check = 1
                    matched_list.append(merge_test)
                    if base['index'] in unmatched_record_dict:
                        unmatched_record_dict[base['index']] = 1
                    if similar['index'] in unmatched_record_dict:
                        unmatched_record_dict[similar['index']] = 1
            else:
                if similar['index'] not in unmatched_record_dict:
                    unmatched_record_dict[similar['index']] = 0
                    
        if check == 0:
            if base['index'] not in unmatched_record_dict:
                unmatched_record_dict[base['index']] = 0
    else:
        if base['index'] not in unmatched_record_dict:
            unmatched_record_dict[base['index']] = 0
            
    print(f"Progress: {index + 1}/{len(matching_result_list)}")
        
def find_all_uppercase_letters(s):
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    found_letters = []
    
    for letter in alphabet:
        if letter in s:
            found_letters.append(letter)
    
    return found_letters
  
processed_data = []  
    
for item in matched_list:
    quesion = item['question']  
    options = item['options']
    item['input'] = f'{quesion}\n{options}'
    if len(find_all_uppercase_letters(str(options))) >= 2:
        processed_data.append(item)
        
for d in processed_data:  
    del d['question']
    del d['options']

extract_answer_data = []

for d in processed_data:
    match = re.search(r'\[\[([A-Z]+)\]\]', d['output'])
    if match:
        answer = match.group(1)
        d['output'] = answer
        extract_answer_data.append(d)
    
# Load the model
model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

data = extract_answer_data

# Extract all texts and vectorize them
texts = [entry['input'] + "\n" + entry['output'] for entry in data]
embeddings = model.encode(texts)

# Apply DBSCAN for clustering
dbscan = DBSCAN(eps=0.01, min_samples=1, metric="cosine")
labels = dbscan.fit_predict(embeddings)

# Select the center point of each cluster
unique_labels = set(labels)
filtered_data = []
noise_data = []  # To store noise data points

for label in unique_labels:
    if label == -1:
        # If it's a noise point, store it in noise_data
        noise_data.extend([data[i] for i in range(len(labels)) if labels[i] == -1])
        continue  # Skip noise points
    # Select cluster center
    cluster_indices = [i for i, l in enumerate(labels) if l == label]
    cluster_embeddings = embeddings[cluster_indices]
    center = cluster_embeddings.mean(axis=0)
    distances = cdist([center], cluster_embeddings, metric="cosine")
    closest_index = cluster_indices[np.argmin(distances)]
    filtered_data.append(data[closest_index])
    
merge = filtered_data + noise_data

filtered_merge = []
for item in merge:
    if len(item['output']) > 50:
        filtered_merge.append(item)

def find_all_uppercase_letters(s):
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    found_letters = []
    
    for letter in alphabet:
        if letter in s:
            found_letters.append(letter)
    
    return found_letters

def extract_answers(options, content):
    # Regular expression to flexibly match option formats
    pattern = r"([A-Z])[\.\)\s]*\s*(.*?)\s*(?=[A-Z][\.\)\s]|$)"  # Match formats like A., A), A (space), etc.

    # Match all options and their content
    matches = re.findall(pattern, content, re.DOTALL)
    
    # Create a dictionary to store each option and its corresponding content
    options_dict = {}
    for match in matches:
        option, option_content = match
        # Clean up extra whitespace and newlines in the content
        clean_content = re.sub(r'\s+', ' ', option_content).strip()
        options_dict[option] = clean_content
    
    # Construct the final answer string
    result = []
    for option in options:
        if option in options_dict:
            result.append(f"{option}. {options_dict[option]}")
        else:
            # If an option cannot find corresponding content, return False directly
            return False
    
    return '\n'.join(result)

output_file = 'hard_mc.json'
        
for question in filtered_merge:
    input = question['input']
    output = question['output']
    answer_list = find_all_uppercase_letters(output)
    question['answer'] = answer_list
            
with open(output_file, 'w') as f:
    json.dump(filtered_merge, f, ensure_ascii = False, indent = 4)
