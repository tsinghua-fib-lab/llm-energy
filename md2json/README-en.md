## Dependency Installation
Run the following command to install the openai library:
```bash
pip install openai
```


## Modify the Program
Open `md2json.py`;  
Change line 12 from `"Your-api-key"` to your api key;  
Change line 14 to update `example_path` to the path where `example.json` is located;  
Change line 494 to update `/path/to/your/directory` to the path of the directory containing the files to be processed;  
On line 355, you can change `THUDM/glm-4-9b-chat` to the name of another large language model.

## Run the Program
Run the following command:
```bash
python md2json.py
```
