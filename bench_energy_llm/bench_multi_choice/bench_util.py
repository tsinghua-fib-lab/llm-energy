def check(answer_list, response, test):
    response = response.strip()
    response_list = find_all_uppercase_letters(response)
    if response_list == answer_list:
        test['llm_result'] = 'True ' + str(response)
        return True
    else:
        test['llm_result'] = 'False ' + str(response)
        return False
    
def direct_check(answer_list, response, test):
    response = response.strip()
    answer_list = find_all_uppercase_letters(answer_list)
    response_list = find_all_uppercase_letters(response)
    if response_list == answer_list:
        test['llm_result'] = 'True ' + str(response)
        return True
    else:
        test['llm_result'] = 'False ' + str(response)
        return False

def find_all_uppercase_letters(s):
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    found_letters = []
    
    for letter in alphabet:
        if letter in s:
            found_letters.append(letter)
    
    return found_letters
