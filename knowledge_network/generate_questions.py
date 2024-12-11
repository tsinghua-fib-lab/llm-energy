import json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from utils import config_model, generate_response_text, save_json
import itertools
import random

API_KEY = 'DEFINE_API_SERVICE_KEY'
BASE_URL = 'DEFINE_API_BASE_URL'
MODEL_NAME = 'DEFINE_MODEL_NAME'
model = config_model(API_KEY, BASE_URL)

def list_subdirectories(directory):
    return [name for name in os.listdir(directory) if os.path.isdir(os.path.join(directory, name))]

def generate_basic_questions(class_session, concepts, syllabus):
    # Single strategy: randomly select 1 to 5 concepts from a single class session to generate a question
    num_concepts = random.randint(2, min(5, len(concepts)))
    selected_concepts = random.sample(concepts, num_concepts)
    concepts_text = "、".join(selected_concepts)
    query = f'class session为{class_session},涉及到的key concept有{concepts_text},课程的syllabus为{syllabus},请根据上面的信息给出一个assignment questions,只需要一条问题即可不需要再具体分点，输出就只是一条问题，不要有别的，中文提问'
    question = generate_response_text(model, query, model_name=MODEL_NAME)
    return question

def generate_combined_questions(class_session1, concepts1, class_session2, concepts2, syllabus):
    # Combination strategy: select concepts from two different class sessions to generate a question
    num_concepts1 = random.randint(1, min(5, len(concepts1)))
    num_concepts2 = random.randint(1, min(5, len(concepts2)))
    selected_concepts1 = random.sample(concepts1, num_concepts1)
    selected_concepts2 = random.sample(concepts2, num_concepts2)
    concepts_text1 = "、".join(selected_concepts1)
    concepts_text2 = "、".join(selected_concepts2)
    query = f'class session1为{class_session1}, key concept有{concepts_text1}, class session2为{class_session2}, key concept有{concepts_text2}, 课程的syllabus为{syllabus},请根据上面的信息给出一个assignment questions,只需要一条问题即可不需要再具体分点，输出就只是一条问题，不要有别的，中文提问'
    question = generate_response_text(model, query, model_name=MODEL_NAME)
    return question

def append_tuning_list(question, list):
    dict = {}
    dict['input'] = question
    list.append(dict)

# Example usage
directory = './output'  # Replace this with the target output folder path
subdirectories = list_subdirectories(directory)

SINGLE = 5 # Number of questions generated for each single class session
DOUBLE = 10 # Number of questions generated for each combination of two class sessions
question_file_name = 'tuning_set.json'

for index, sub in enumerate(subdirectories):
    with open(f'./output/{sub}/class_key.json', 'r') as f:
        class_keyConcept_json = json.load(f)
        
    with open(f'./output/{sub}/syllabus.txt', 'r') as f:
        syllabus = f.read()    

    output_path = f'./output/{sub}/{question_file_name}'
    if os.path.exists(output_path):
        with open(output_path, 'r') as f:
            question_json = json.load(f)
    else:
        # If the file does not exist, assign an empty list
        question_json = []

    # for single class_session
    for cls in class_keyConcept_json:
        class_session = list(cls.keys())[0]
        concept_list = cls[class_session]
        for _ in range(SINGLE):
            question = generate_basic_questions(class_session, concept_list, syllabus)
            append_tuning_list(question, question_json)
            
    # for double class_session
    combinations = list(itertools.combinations(class_keyConcept_json, 2))
    
    for combo in combinations:
        dict1, dict2 = combo
        key1, key2 = list(dict1.keys())[0], list(dict2.keys())[0]
        concept1, concept2 = dict1[key1], dict2[key2]
        for _ in range(DOUBLE):
            question = generate_combined_questions(key1, concept1, key2, concept2, syllabus)
            append_tuning_list(question, question_json)

    save_json(question_json, output_path, isstr=False)
    print(f'{index} finished')