## 依赖项安装
运行如下命令安装openai库：
```bash
pip install openai
```

## 修改程序
打开`md2json.py`文件；  
第12行将`“Your-api-key”`修改为您的api key；  
第14行将`example_path`修改为`example.json`所在的路径；  
第494行将`/path/to/your/directory`修改为要处理的文件所在文件夹的路径；  
第355行可将`THUDM/glm-4-9b-chat`修改为其他大模型名称。

## 运行程序
运行如下命令：
```bash
python md2json.py
```
