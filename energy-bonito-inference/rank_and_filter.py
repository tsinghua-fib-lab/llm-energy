import torch
from torch.utils.data import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch.nn.functional as F
import json
import os
import json

# check GPU availability
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

model_name = 'qwen-7B-instruct' # define model directory
model = AutoModelForCausalLM.from_pretrained(model_name, load_in_8bit=True)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# define dataset class
class TextDataset(Dataset):
    def __init__(self, texts):
        self.texts = texts
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        inputs = self.tokenizer(self.texts[idx], return_tensors='pt', truncation=True, padding=True)
        return inputs.input_ids.squeeze(), inputs.attention_mask.squeeze()

def calculate_perplexity(model, inputs, attention_mask):
    inputs, attention_mask = inputs.to(device), attention_mask.to(device)
    with torch.no_grad():
        outputs = model(input_ids=inputs, attention_mask=attention_mask, labels=inputs)
        loss = outputs.loss
        perplexity = torch.exp(loss)
    return perplexity.item()

def calculate_el2n_score(model, inputs, attention_mask):
    inputs, attention_mask = inputs.to(device), attention_mask.to(device)
    with torch.no_grad():
        logits = model(input_ids=inputs, attention_mask=attention_mask).logits
        predicted_logits = logits.argmax(dim=-1)
        true_labels = inputs
        el2n_score = F.mse_loss(predicted_logits.float(), true_labels.float())
    return el2n_score.item()

def custom_quality_score(text):
    words = text.split()
    unique_words = set(words)
    score = len(unique_words) / len(words)  # vocabulary richness
    return score

def cal_score(dataset, model, metrics_weights):
    total_score_list = []
    for i, (inputs, attention_mask) in enumerate(dataset):
        text = tokenizer.decode(inputs)
        perplexity = calculate_perplexity(model, inputs.unsqueeze(0), attention_mask.unsqueeze(0))
        el2n_score = calculate_el2n_score(model, inputs.unsqueeze(0), attention_mask.unsqueeze(0))
        quality_score = custom_quality_score(text)

        # Calculate the total score (weighted sum of multiple metrics)
        # Set a very small non-zero number to avoid division by zero
        epsilon = 1e-9

        total_score = metrics_weights['perplexity'] * (1 / max(perplexity, epsilon)) + \
                    metrics_weights['el2n'] * (1 / max(el2n_score, epsilon)) + \
                    metrics_weights['quality'] * quality_score
        total_score_list.append(total_score)
        print(f'{i} calculated')
    
    return total_score_list

def rerank(data_list, score_list):
    # Sort according to the score list and adjust the order of the data list
    sorted_score_data = sorted(zip(score_list, data_list), reverse=True)

    # Get the sorted score list and data list separately
    sorted_score_list, sorted_data_list = zip(*sorted_score_data)

    # Convert to list form
    sorted_score_list = list(sorted_score_list)
    sorted_data_list = list(sorted_data_list)
    
    return sorted_data_list, sorted_score_list


if __name__ == '__main__':
    current_directory = os.getcwd()

    # Iterate through all *.json files in the current directory
    json_files = [f for f in os.listdir(current_directory) if f.endswith('.json')]

    for json_file in json_files:
        file_path = os.path.join(current_directory, json_file)
    
        with open(file_path, 'r') as f:
            try:
                json_data = json.load(f)
                
                texts = []
                    
                for j in json_data:
                    input = j['input'][:2048] if len(j['input']) > 2048 else j['input']
                    output = j['output'][:2048] if len(j['output']) > 2048 else j['output']
                    combine_text = f"{input}\n{output}"
                    texts.append(combine_text)

                dataset = TextDataset(texts)
                
                # Set the weights for the metrics (can be adjusted as needed)
                metrics_weights = {
                    'perplexity': 0.5,
                    'el2n': 0.4,
                    'quality': 0.1
                }

                score_list = cal_score(dataset, model, metrics_weights)
                
                # store score list
                with open(f'{json_file.split('.')[0]}_score.json', 'w') as f:
                    json.dump(score_list, f, ensure_ascii=False, indent=4)

                json_data, _ = rerank(json_data, score_list)
                
                # store rerank_json
                with open(f'{json_file.split('.')[0]}_rerank.json', 'w') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=4)
                            
            except json.JSONDecodeError:
                print(f"Error decoding {json_file}")
    
