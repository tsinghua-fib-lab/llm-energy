import xmindparser
import json

# Specify the path to the XMind file
xmind_file = ''

# Parse the XMind file
content = xmindparser.xmind_to_dict(xmind_file)

content = content[0]['topic']['topics']

with open('xmind.json', 'w', encoding='utf-8') as f:
    json.dump(content, f, ensure_ascii=False, indent=4)
