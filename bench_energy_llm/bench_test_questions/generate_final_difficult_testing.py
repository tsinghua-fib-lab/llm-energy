import json
import re

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

to_do_list = ['cot-test_dedu.json']

for file in to_do_list:
    with open(file, 'r') as f:
        data = json.load(f)
        
    for question in data:
        input = question['input']
        output = question['output']
        answer_list = find_all_uppercase_letters(output)
        question['answer'] = answer_list
                
    with open(f'{file.split(".json")[0]}_fake_transfered.json', 'w') as f:
        json.dump(data, f, ensure_ascii = False, indent = 4)
