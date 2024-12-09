import json

def map_number_to_letter(number):
    number = int(number)
    if 1 <= number <= 26:
        return chr(64 + number)
    else:
        return None

def convert_answer_list(answer_list):
    for i in range(len(answer_list)):
        answer_list[i] = map_number_to_letter(answer_list[i])

def convert_option_list(option_list):
    for index in range(len(option_list)):
        opt = map_number_to_letter(index + 1)
        option_list[index] = opt + '. ' + option_list[index]

# usage sample
with open('test_multi_choice.json', 'r') as f:
    paper = json.load(f)
    
for qa in paper:
    answer_list = qa['answer']
    convert_answer_list(answer_list)
    option_list = qa['options']
    convert_option_list(option_list)
    
with open('test_multi_choice_abcd.json', 'w') as f:
    json.dump(paper, f, ensure_ascii=False, indent=4)