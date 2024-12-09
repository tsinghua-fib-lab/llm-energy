import json
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN

paper_list = [
                'questions_电力交易大赛.json',
                'questions_电力交易员.json',
                'questions_电力市场交易员选拔题库.json',
                'questions_电力市场竞赛题库.json',
                'questions_电力市场培训.json',
                'questions_电力政策.json'
            ]

template_path = './extract_multi_choice_from_text/test_multi_choice_abcd.json'
with open(template_path, 'r') as f:
    total_test = json.load(f)

for paper in paper_list:
    file_path = paper
    with open(f'./original_questions/{file_path}', 'r') as f:
        temp = json.load(f)
        
    for q in temp:
        q['question'] = q.pop('question_text')
        q['answer'] = q.pop('right_ans')
        q['answer'] = sorted([char for char in q['answer'] if char.isupper()])
        total_test.append(q)
        
random.shuffle(total_test)

data = total_test

# Extract question text
questions = [item['question'] for item in data]

# Vectorization
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(questions)

# DBSCAN clustering
db = DBSCAN(eps=0.5, min_samples=1, metric='cosine').fit(X)
labels = db.labels_

# Deduplicate questions based on cluster labels
unique_labels = set(labels)
clustered_questions = {}

for i, label in enumerate(labels):
    if label not in clustered_questions:
        clustered_questions[label] = data[i]
    else:
        # You can choose how to merge data as needed, here we only keep the first occurrence
        pass

deduplicated_data = list(clustered_questions.values())
random.shuffle(deduplicated_data)

# Augmentation
for data in deduplicated_data:
    if 'question_type' not in data:
        len_of_answer = len(data['answer'])
        if len_of_answer == 2:
            data['question_type'] = 'True/False'
        elif len_of_answer > 2:
            data['question_type'] = 'Multiple Choice'
        else:
            data['question_type'] = 'Single Choice'
            
    q_type = data['question_type']
    q = data['question']
    options = data['options']
    ans = data['answer']
    options_str = ''.join(f'{opt}\n' for opt in options)
    
    input = f'{q_type}\n{q}\n{options_str}'
    output = ' '.join(ans)
    
    data['input'] = input
    data['output'] = output

output = deduplicated_data[:1000]
rest_of = deduplicated_data[1000:]
with open('easy_mc.json', 'w') as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

        