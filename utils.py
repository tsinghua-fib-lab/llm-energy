import json
from openai import OpenAI

def config_model(api_key, base_url):
    if not api_key:
        raise ValueError("API key must be specified")
    if not base_url:
        raise ValueError("Base URL must be specified")
    model = OpenAI(api_key=api_key, base_url=base_url)
    return model
    
def generate_response_text(model, query, top_p = 0.95, max_output_tokens = 2000, temperature = 0.5, model_name = None):
    # OpenAI style API by default
    if not model_name:
        raise ValueError("Model name must be specified")
    response = model.chat.completions.create(
        model= model_name,
        messages=[
            {'role': 'user', 'content': f"{query}"}
        ],
        stream=False,  
        top_p = top_p,
        temperature = temperature,
        max_tokens = max_output_tokens
    )

    output = response.choices[0].message.content
    return output

def save_json(content, path, isstr = True):
    try:
        if isstr:
            content_to_json = json.loads(content)
        else:
            content_to_json = content
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(content_to_json, f, ensure_ascii=False, indent=4)
        print(f"Content has been written to {path}")
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
