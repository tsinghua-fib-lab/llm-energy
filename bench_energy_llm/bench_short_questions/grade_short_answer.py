import os
import json
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from bert_score import score as bert_score

input_file = input('input your inference result file name: ')
model = SentenceTransformer('microsoft/deberta-v3-large')

def calculate_similarity(reference_answer, model_answer):
    # Convert sentences to vectors
    reference_embedding = model.encode([reference_answer])
    model_embedding = model.encode([model_answer])
    
    # Calculate cosine similarity
    similarity = cosine_similarity(reference_embedding, model_embedding)
    score = float(similarity[0][0])  # Extract similarity value
    
    return score

def calculate_bertscore(reference_answer, model_answer):
    P, R, F1 = bert_score([model_answer], [reference_answer], model_type='microsoft/deberta-v3-large', device='cuda')
    return float(F1[0])

source_file = f'../extract_short_questions/{input_file}'
file_name = 'short_answer_bertscore.json'

with open(source_file, 'r') as f:
    short_answer = json.load(f)
    
bert_score_dict = {'new-energy-llm': 0}

# Iterate through each question to score
for question in short_answer:
    ref_anwer = question['answer']
    llm_list = ['new-energy-llm']
    
    for key in llm_list:
        if key != 'question' and key != 'answer' and not key.endswith('_score') and not key.endswith('_rank'):
            answer = question[key]
            
            # Calculate BERTScore
            bert_similarity_score = calculate_bertscore(ref_anwer, answer)
            question[key + '_bertscore'] = bert_similarity_score
            bert_score_dict[key] += bert_similarity_score

# Calculate average score
for key in bert_score_dict.keys():
    bert_score_dict[key] = bert_score_dict[key] / len(short_answer)

# Rank each question's scores
for question in short_answer:
    llm_list = []
    
    # Sort by BERTScore
    llm_bertscore_list = []
    for key in question.keys():
        if key.endswith('_bertscore'):
            llm_bertscore_list.append(key)
    
    llm_bertscore_list.sort(key=lambda x: question[x], reverse=True)
    for i, key in enumerate(llm_bertscore_list):
        question[key + '_bertscore_rank'] = i + 1

# Save results to json file
with open(file_name, 'w') as f:
    json.dump(short_answer, f, ensure_ascii=False, indent=4)

print(bert_score_dict)
