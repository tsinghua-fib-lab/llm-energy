import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
import random

source_path = 'total_test_shuffled.json'
with open(source_path, 'r') as f:
    data = json.load(f)

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
with open('test_1000_new.json', 'w') as f:
    json.dump(output, f, ensure_ascii=False, indent=4)
