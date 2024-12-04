import json
import random

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

with open('total_test_shuffled.json', 'w', encoding='utf-8') as f:
    json.dump(total_test, f, ensure_ascii=False, indent=4)
        