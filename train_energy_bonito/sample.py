import json
import os
import random

RATIO = 'DEFINE_SAMPLE_RATIO' # Needs to be modified to the sampling ratio

def collect_contents(directory):
    contents = []

    # Traverse the specified directory
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                if random.random() < RATIO:
                    try:
                        file_path = os.path.join(root, file)
                        subdir_name = os.path.basename(root)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            # Recursively search and extract information
                            extract_contents(data, contents, subdir_name)
                        
                    except (json.JSONDecodeError, FileNotFoundError, IOError) as e:
                        print(f"Error reading {file_path}: {e}")
    
    return contents

def extract_contents(data, contents, sub):
    if isinstance(data, dict):
        # If there is a non-empty subtree
        if "subtree" in data and data["subtree"]:
            for item in data["subtree"]:
                content = item.get("content", "N/A")
                if content.count('|') > 5:
                    continue
                district = item.get("district", "N/A")
                release_time = item.get("release_time", "N/A")
                
                content_info = {
                    "content": content,
                    "district": district,
                    "release_time": release_time,
                    "file_name": sub
                }
                contents.append(content_info)
                
                # Recursively process items in the subtree
                extract_contents(item, contents, sub)
        else:
            # If there is no subtree, ignore
            pass
    elif isinstance(data, list):
        for item in data:
            extract_contents(item, contents, sub)
            
dir = '' # Needs to be modified to the path where the JSON structured files are stored
content_list = collect_contents(dir)
filtered_list = [
    c for c in content_list 
    if c.get('content') not in ['None', 'None error'] and len(c.get('content', '')) >= 5
]

SAVE_FILE_NAME = ''
with open(SAVE_FILE_NAME, 'w', encoding='utf-8') as f:
    json.dump(filtered_list, f, ensure_ascii=False, indent=4)