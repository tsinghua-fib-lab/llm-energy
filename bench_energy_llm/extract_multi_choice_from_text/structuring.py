import json

def process_text_block(block):
    # Split the block into a list of lines
    lines = block.strip().split('\n')
    
    # The first line is the question
    question = lines[0].strip()
    answer = lines[1].strip()
    answer_list = answer.split(' ')
    # The remaining lines are the options
    options = [line.strip() for line in lines[2:]]
    
    return question, answer_list, options

def process_txt_file(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Split the content into blocks by two newline characters
    blocks = content.strip().split('\n\n')
    
    # Process each block
    processed_data = []
    for block in blocks:
        question, answer_list, options = process_text_block(block)
        processed_data.append({
            'question': question,
            'answer': answer_list,
            'options': options
        })
    
    return processed_data

# Usage example
filename = 'test_multi_choice.txt'
processed_data = process_txt_file(filename)
with open('test_multi_choice.json', 'w') as f:
    json.dump(processed_data, f, ensure_ascii=False, indent=4)
