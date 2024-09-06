"""
    说明：受限于marker的识别精度，抽取成功率在90%左右，剩下的文件若有必要（指内容尚可使用），考虑等长分割
"""

import re
import os
import json
import traceback
from openai import OpenAI

#定义一些调用大模型要用的常量
client = OpenAI(api_key="sk-azkwfecpuxpjdeyypcdjfzpbsxcohaixlymvhbsjkaoftrpg", base_url="https://api.siliconflow.cn/v1")

example_path = "./output/example.json"

instruction1 = "请读取这个文件的内容，识别它的文章结构，标题和各级子标题，根据这些标题将文章分块。每一块应当含有两个部分：title，subtree。title指这一块文章的标题，subtree则包含title这一标题下的全部子标题及其内容。最终返回的应当是json代码。下面给出的这一段是返回内容的示例，你只需要阅读即可。"

instruction2 = "The following document is the document you need to read and extract a json document from. Make sure to identify all levels of titles and ensure they are accurately segmented without overlap. The title mentioned above is sentences that start with words such as “1、”“一、”“第一章”“第一条”“（一）”.The format of the extracted json document should be the same with the json document given above. You are required to include all the titles included in the document. You are forbidden to add any title that does not appear in the original document and title that is an empty string. Do not add any additional The sequence of the titles should be the same as the original document. The output must be in Chinese."

global count
count = 0
global retry
retry = 0

def decide_type(filedir, filename):
    """
    判断文件格式：
        0: 第xx章，第xx节，第xx条
        1: 一、（一）、1、（1）
        2: 1. 1.1. 1.1.1. 1.1.1.1.
    """
    with open(os.path.join(filedir, filename), mode='r', encoding='utf-8') as f:
        content = f.read()
        z = re.findall(r'^第[一二三四五六七八九零十]+章', content,re.MULTILINE)
        t = re.findall(r'^第[一二三四五六七八九零十]+条', content,re.MULTILINE)
        r = re.findall(r'^[一二三四五六七八九十]+、', content,re.MULTILINE)
        s = re.findall(r'^[(（][一二三四五六七八九十]+[）)]', content,re.MULTILINE)
        n = re.findall(r'^\d+\.\d+\.\d+', content, re.MULTILINE)

        if (len(z)>1 or len(t)>3) and len(n)<5:
          return 0
        elif len(r)>3 and len(n)<5:
          return 1
        else:
          return 2


def parse_Zhang_Jie_Tiao(filedir, filename):
    """
    解析第xx章，第xx节，第xx条格式的文件
    """
    
    # 定义正则表达式
    pattern_Zhang = re.compile(r'第[1234567890.一二三四五六七八九十百千万零〇\s]+章')
    pattern_Jie = re.compile(r'第[1234567890.一二三四五六七八九十百千万零〇\s]+节')
    pattern_Tiao = re.compile(r'第[1234567890.一二三四五六七八九十百千万零〇\s]+条')
    pattern_Noise_Page_Num = re.compile(r'-[\s]+[0-9]+[\s]+—')
    pattern_Title = re.compile(r'[#]+')
    with open(os.path.join(filedir, filename), mode='r', encoding='utf-8') as f:
        content = f.read()
        content = content[content.find('第一章'):]#把第一章前面的东西去除
        # 去除干扰项：pdf中的页码经过marker处理后会变成'- 1 —'这种形式，需要去除
        # 去除标题：marker不能准确将所有标题识别出来，需要去除
        content_Noise_Page_Num = pattern_Noise_Page_Num.findall(content)
        content_Title = pattern_Title.findall(content)
        for t in content_Title:
            content = content.replace(t, '')
        for n in content_Noise_Page_Num:
            content = content.replace(n, '')
        
        # 有些文件不知道为什么没有”第一章“，需要手动添加，以免后面报错
        if content.find("第一章") == -1:
            first_jie = content.find("第一节")
            first_tiao = content.find("第一条")
            if first_jie != -1 and first_jie < first_tiao:
                content = content[:first_jie] + "第一章" + content[first_jie:]
            else:
                content = content[:first_tiao] + "第一章" + content[first_tiao:]
        
        content_Zhang = pattern_Zhang.findall(content)
        content_Jie = pattern_Jie.findall(content)
        content_Tiao = pattern_Tiao.findall(content)      

        # element_list存储章节条目的位置信息：(起始位置，标题)
        element_list = []
        tmp_content = content
        offset_id = 0
        for z in content_Zhang:
            id = tmp_content.find(z)
            tmp_content = tmp_content[id+len(z):]
            element_list.append((id + offset_id, z))
            offset_id += id + len(z)
        tmp_content = content
        offset_id = 0
        for j in content_Jie:
            id = tmp_content.find(j)
            tmp_content = tmp_content[id+len(j):]
            element_list.append((id + offset_id, j))
            offset_id += id + len(j)
        tmp_content = content
        offset_id = 0
        for t in content_Tiao:
            id = tmp_content.find(t)
            tmp_content = tmp_content[id+len(t):]
            element_list.append((id + offset_id, t))
            offset_id += id + len(t)
        element_list.sort(key=lambda x: x[0])
        
        # content_list存储章节条目的内容：(标题，内容)
        content_list = []
        for e in element_list:
            id = e[0]
            title = e[1]
            if e != element_list[-1]:
                next_id = element_list[element_list.index(e)+1][0]
                content_list.append((title, content[id:next_id]))
            else:
                content_list.append((title, content[id:]))

        # content_tree存储章节条目的树形结构
        content_tree = {'title': os.path.splitext(filename)[0], 'subtree': []}
        for c in content_list:
            title = c[0]
            content = c[1]
            if pattern_Zhang.match(title):
                content_tree['subtree'].append({'title': title, 'content': content.replace(title, ''), 'subtree': []})
            elif pattern_Jie.match(title):
                if content_tree['subtree']==[]:
                    content_tree['subtree'].append({'title': title, 'content': content.replace(title, ''),'subtree':[]})
                else:
                    content_tree['subtree'][-1]['subtree'].append({'title': title, 'content': content.replace(title, ''), 'subtree': []})
            elif pattern_Tiao.match(title):
                if content_tree['subtree']==[]:
                    content_tree['subtree'].append({'title': title, 'content': content.replace(title, ''),'subtree':[]})
                elif content_tree['subtree'][-1]['subtree'] == [] or pattern_Tiao.match(content_tree['subtree'][-1]['subtree'][-1]['title']):
                    content_tree['subtree'][-1]['subtree'].append({'title': title, 'content': content.replace(title, ''),'subtree':[]})
                else:
                    content_tree['subtree'][-1]['subtree'][-1]['subtree'].append({'title': title, 'content': content.replace(title, '')})
        
        with open(os.path.join(filedir, os.path.splitext(filename)[0] + '_content_tree.json'), mode='w', encoding='utf-8') as ff:
            json.dump(content_tree, ff, ensure_ascii=False, indent=4)
        
        return content_tree
    
def parse_Yi_Punctuation_Mark(filedir, filename):
    """
    解析一、（一）、1、（1）格式的文件
    大体逻辑与parse_Zhang_Jie_Tiao相同
    """
    pattern_Title = re.compile(r'^[#]+',re.M)
    pattern_big_title = re.compile(r'^[一二三四五六七八九十]+、',re.M)
    pattern_medium_title = re.compile(r'^[(（][一二三四五六七八九十]+[）)]',re.M)
    pattern_little_title = re.compile(r'^[012345789]+\.',re.M)
    pattern_Noise_Page_Num = re.compile(r'-[\s]+[0-9]+[\s]+—')
    with open(os.path.join(filedir, filename), mode='r', encoding='utf-8') as f:
        content = f.read()
        content_Noise_Page_Num = pattern_Noise_Page_Num.findall(content)
        for n in content_Noise_Page_Num:
            content = content.replace(n, '')
        content_Title = pattern_Title.findall(content)
        for t in content_Title:
            content = content.replace(t, '')
        pattern_big_title = re.compile(r'[一二三四五六七八九十]+、')
        pattern_medium_title = re.compile(r'[(（][一二三四五六七八九十]+[）)]')
        pattern_little_title = re.compile(r'[012345789]+\.')
        content_big_title = pattern_big_title.findall(content)
        content_medium_title = pattern_medium_title.findall(content)
        content_little_title = pattern_little_title.findall(content)
        
        element_list = []
        tmp_content = content
        offset_id = 0
        for b in content_big_title:
            id = tmp_content.find(b)
            tmp_content = tmp_content[id+len(b):]
            element_list.append((id + offset_id, b))
            offset_id += id + len(b)
        tmp_content = content
        offset_id = 0
        for m in content_medium_title:
            id = tmp_content.find(m)
            tmp_content = tmp_content[id+len(m):]
            element_list.append((id + offset_id, m))
            offset_id += id + len(m)
        tmp_content = content
        offset_id = 0
        for l in content_little_title:
            id = tmp_content.find(l)
            tmp_content = tmp_content[id+len(l):]
            element_list.append((id + offset_id, l))
            offset_id += id + len(l)
        element_list.sort(key=lambda x: x[0])
        # print(element_list)

        content_list = []
        for e in element_list:
            id = e[0]
            title = e[1]
            if e != element_list[-1]:
                next_id = element_list[element_list.index(e)+1][0]
                content_list.append((title, content[id:next_id]))
            else:
                content_list.append((title, content[id:]))

        content_tree = {'title': os.path.splitext(filename)[0], 'subtree': []}
        for c in content_list:
            title = c[0]
            content = c[1]
            if pattern_big_title.match(title):
                content_tree['subtree'].append({'title': title, 'content': content.replace(title, ''), 'subtree': []})
            elif pattern_medium_title.match(title):
                if content_tree['subtree']==[]:
                    content_tree['subtree'].append({'title': title, 'content': content.replace(title, ''),'subtree':[]})
                else:
                    content_tree['subtree'][-1]['subtree'].append({'title': title, 'content': content.replace(title, ''), 'subtree': []})
            elif pattern_little_title.match(title):
                if content_tree['subtree']==[]:
                    content_tree['subtree'].append({'title': title, 'content': content.replace(title, ''),'subtree':[]})
                elif content_tree['subtree'][-1]['subtree'] == [] or pattern_little_title.match(content_tree['subtree'][-1]['subtree'][-1]['title']):
                    content_tree['subtree'][-1]['subtree'].append({'title': title, 'content': content.replace(title, ''),'subtree':[]})
                else:
                    content_tree['subtree'][-1]['subtree'][-1]['subtree'].append({'title': title, 'content': content.replace(title, '')})
        
        with open(os.path.join(filedir, os.path.splitext(filename)[0] + '_content_tree.json'), mode='w', encoding='utf-8') as ff:
            json.dump(content_tree, ff, ensure_ascii=False, indent=4)
    
        return content_tree

def parse_1_1_1_1(filedir, filename):
    """
    解析1. 1.1. 1.1.1. 格式的文件
    marker基本上能把所有序号识别出来，所以可以大致按照markdown标题的格式来解析
    """
    def find(l:list[object], e:object):
        i=l.index(e)
        return i
        
    pattern_Noise_Page_Num = re.compile(r'-[\s]+[0-9]+[\s]+—')
    pattern_Num_Title = re.compile(r'[0-9.]+')
    with open(os.path.join(filedir, filename), mode='r', encoding='utf-8') as f:
        content = f.read()

        content_Noise_Page_Num = pattern_Noise_Page_Num.findall(content)
        for n in content_Noise_Page_Num:
            content = content.replace(n, '')
        content = content[content.find('## 1'):] # 将第一大条之前的内容去除，如目录、通知等
        lines_tmp = content.split('\n')
        lines = []
        titles = []
        for l in lines_tmp: # 去除空行
            if l == '' or l == '\n' or l == '\r\n' or l == '\r' or l == '\t' or l == ' ':
                continue
            lines.append(l)
        for l in lines:
            if '##' in l:
                title_line = pattern_Num_Title.findall(l)
                for t in title_line:
                    if ('.' in t or l.find(t) < 5) and not (l[l.find(t) + len(t)] == ')' or l[l.find(t) + len(t)] == '）'):
                        titles.append(t)
                        
        content = content[content.find('## 1'):]
        content = content.replace('##', '')
        
        element_list = []
        content_tmp = content
        offset_id = 0
        for t in titles:
            id = content_tmp.find(t)
            content_tmp = content_tmp[id + len(t):]
            element_list.append((id + offset_id, t if t[-1] == '.' else t + '.'))
            offset_id += id + len(t)
        
        content_list = []
        
        for e in element_list:
            if e != element_list[-1]:
                content_list.append((e[1], content[e[0]:element_list[element_list.index(e) + 1][0]]))
            else:
                content_list.append((e[1], content[e[0]:]))
        
        content_tree = {'title': filename, 'subtree': []}
        for c in content_list:
            title = c[0]
            # 分析属于哪一层
            idxs = title.split('.')
            if idxs[-1] == '':
                idxs = idxs[:-1]
            idx = ''
            father_element = content_tree
            for i in range(len(idxs) - 1):
                idx += idxs[i] + '.'
                try:
                # 检查 father_element['subtree'] 是否为空或是否包含匹配的元素
                    if not father_element['subtree'] or father_element['subtree'][-1]['title'] != idx:
                        break
                    father_element = father_element['subtree'][-1]
                except (KeyError, IndexError):
                # 处理可能出现的 KeyError 或 IndexError
                    break
                # 如果找到匹配的元素，继续构建内容树
                if father_element and 'subtree' in father_element:
                    father_element['subtree'].append({'title': title, 'content': c[1].replace(title, '').replace(title[:-1], ''), 'subtree': []})
        
        with open(os.path.join(filedir, os.path.splitext(filename)[0] + '_content_tree.json'), mode='w', encoding='utf-8') as f:
            f.write(json.dumps(content_tree, ensure_ascii=False, indent=4))
            
        return content_tree 

def parse_llm(filedir,filename,example):
    global retry
    retry = 0
    with open(os.path.join(filedir, filename), 'r') as f:
        content = f.read()
        """
        modified_content = ''
        i = 0
        while i < len(content):
            if content[i] == '.':
                modified_content += '.'
                # 检查“.”后面是否是空格或字符串的末尾
                if i + 1 < len(content) and content[i + 1] != ' ':
                    modified_content += ' '
            elif content[i] == ',':
                modified_content += ','
                # 检查“.”后面是否是空格或字符串的末尾
                if i + 1 < len(content) and content[i + 1] != ' ':
                    modified_content += ' '
            else:
                modified_content += content[i]
            i += 1
        content = modified_content#给每个点和逗号后面加个空格
        """
    with open(example,'r') as f:   
        example_content= f.read()
        
    new_title_file_path = os.path.join(filedir, os.path.splitext(filename)[0] + '_title_tree.json')
    
    pattern_Noise_Page_Num = re.compile(r'-[\s]+[0-9]+[\s]+—')
    pattern_Title = re.compile(r'^[#]+',re.M)
    pattern_Quote = re.compile(r'"')
    content_Noise_Page_Num = pattern_Noise_Page_Num.findall(content)
    for n in content_Noise_Page_Num:
        content = content.replace(n, '')
    content_Title = pattern_Title.findall(content)
    for t in content_Title:
        content = content.replace(t, '')
    content_Quote = pattern_Quote.findall(content)
    for q in content_Quote:
        content = content.replace(q,'“')
    
    print("LLM processing...")
    json_load_success = False
    while(json_load_success == False and retry<6):
        response = client.chat.completions.create(
        model='THUDM/glm-4-9b-chat',
        messages=[
            {'role': 'user', 'content': instruction1},
            {'role': 'user', 'content': example_content},
            {'role': 'user', 'content': instruction2},
            {'role': 'user', 'content': content}
        ],
        stream=True  # 如果你想实时接收响应，可以保留 stream=True
        )

        with open(new_title_file_path, 'w') as json_title_file:
            for chunk in response:
                title_content = str(chunk.choices[0].delta.content)
                json_title_file.write(title_content)
    
    
        # 打开原始文件并读取所有行，跳过头两行和最后一行
        with open(new_title_file_path, 'r') as file:
            lines = file.readlines()[2:-1]

        # 将剩余的行写回文件
        with open(new_title_file_path, 'w') as file:
            file.writelines(lines)

        with open(new_title_file_path, 'r') as json_title_file:
            try:
                content_tree = json.load(json_title_file)
                json_load_success = True
            except Exception as e:
                retry = retry + 1
                print("Retrying...")
                print(retry)
            
    print("LLM process complete.")
    title_list = []
    
    def extract_titles(tree, title_list):
        if "title" in tree:
            # 打印当前标题及其位置
            title_list.append(tree["title"])
            # 递归调用子标题
            if "subtree" in tree:
                for subtree in tree["subtree"]:
                    extract_titles(subtree, title_list)
                    
    extract_titles(content_tree, title_list)

    def extract_content(content, end_str):
        end_index = content.find(end_str)
        if(len(end_str)==0):
            return "None"
        elif end_index == -1:
            new_end_str = end_str[:-1]
            return extract_content(content, new_end_str)
        else:
            return content[:end_index]#如果找不到这个标题，就删掉标题的首个字符继续查，因为标题查找出问题一般是因为编号的问题
    
    def content_find(content, tar_str):
        index = content.find(tar_str)
        if(len(tar_str)==0):
            return content
        elif index == -1:
            new_tar_str = tar_str[:-1]
            return content_find(content,new_tar_str)
        else:
            return content[index:]
            
    content_list = []        
    for i in range (len(title_list) - 1):
        content_list.append(extract_content(content, title_list[i+1]))
        content = content_find(content,title_list[i+1])
    content = content_find(content,title_list[-1])
    content_list.append(content)
    global count
    count = 0
    
    def insert_contents(tree, content):
        global count
        if "title" in tree:
            tree["contents"] = content[count]
            count = count + 1
            if count == len(content):
                count = 0
            if "subtree" in tree:
                for subtree in tree["subtree"]:
                    insert_contents(subtree, content)
    
    insert_contents(content_tree, content_list)

    with open(os.path.join(filedir, os.path.splitext(filename)[0] + '_content_tree.json'), mode='w', encoding='utf-8') as f:
        f.write(json.dumps(content_tree, ensure_ascii=False, indent=4))
    """
    os.remove(new_title_file_path) 
    """     
    return content_tree  
    
def create_appendix(filedir,filename,tree):
    tmp_title_path = os.path.join(filedir, os.path.splitext(filename)[0] + '_tmp_tree.json')
    with open("./output/example.json",'r') as f:   
        example_content= f.read()
    json_load = False
    if "content" in tree:
        content_after_attachment = tree["content"]
        with open(os.path.join(filedir, os.path.splitext(filename)[0] + '_appendix_tree.json'),'w') as f:
            f.write(content_after_attachment)
        tree["content"] = ""
        return parse_llm(filedir,os.path.splitext(filename)[0] + '_appendix_tree.json',example_path)
            


def find_appendix(filedir,filename,content_tree):
    if isinstance(content_tree, str):
        tree = json.loads(content_tree)
    else:
        tree = content_tree     
    if "content" in tree:
        if "附件" in tree["title"]:
            try:
                if "subtree" not in tree:
                    tree["subtree"] = []
                appendix = create_appendix(filedir,filename,tree)
                os.remove(os.path.join(filedir, os.path.splitext(filename)[0] + '_appendix_tree.json'))
                print("appendix：",appendix)
                tree["subtree"].append(appendix)
            except Exception as e:
                traceback.print_exc()
    if "subtree" in tree:
        for subtree in tree["subtree"]:
            if isinstance(subtree, dict):
                find_appendix(filedir,filename,subtree)

if __name__ == '__main__':
    error=0
    done=0
    un=0
    type0=0
    type1=0
    type2=0
    #global retry
    for root, dirs, files in os.walk(r'./test'):
        for file in files:
            if file.endswith('.md'):
                print('parse %s' % os.path.join(root, file), end='...   ')
                file_type = decide_type(root, file)
                if file_type == 0:
                    type0 = type0 + 1
                    try:
                        parse_Zhang_Jie_Tiao(root, file)
                        print('done')
                        done = done + 1
                        print(done)
                    except Exception as e:
                        traceback.print_exc()
                        with open('error.log', mode='a', encoding='utf-8') as f:
                            f.write('parse %s type=0 error: %s\n' % (os.path.join(root, file), e))
                        print('error')
                        error = error + 1
                elif file_type == 1:
                    type1 = type1 + 1

                    try:
                        parse_Yi_Punctuation_Mark(root, file)
                        print('done')
                        done=done+1
                    except Exception as e:
                        traceback.print_exc()
                        with open('error.log', mode='a', encoding='utf-8') as f:
                            f.write('parse %s type=1 error: %s\n' % (os.path.join(root, file), e))
                        print('error')
                        error=error+1
                elif file_type == 2:
                    type2=type2+1
                    retry = 0
                    try:
                        parse_llm(root,file,example_path)
                        print('done')
                        done = done + 1
                        print(done)
                    except Exception as e:
                        traceback.print_exc()
                        with open('error.log', mode='a', encoding='utf-8') as f:
                            f.write('parse %s type=1 error: %s\n' % (os.path.join(root, file), e))
                        print('error')
                        error = error + 1
                    
                else:
                        with open('error.log', mode='a', encoding='utf-8') as f:
                            f.write('parse %s type=3 error: unable to categorize\n' % (os.path.join(root, file),))
                        un=un+1
            elif file.endswith('content_tree.json'):
                #print("json start")
                with open(os.path.join(root, os.path.splitext(file)[0] + '.json'), 'r') as json_tmp_file:
                    print('parse %s' % os.path.join(root, file), end='...   ')
                    content_tree = json.load(json_tmp_file)
                    find_appendix(root,file,content_tree)
                with open(os.path.join(root, os.path.splitext(file)[0] + '.json'), 'w') as f:
                    f.write(json.dumps(content_tree, ensure_ascii=False, indent=4))

    print('done:')
    print(done)
    print('error:')
    print(error)
    print(type0)
    print(type1)
    print(type2)
    """
                elif file_type == 1:
                    type1 = type1 + 1

                    try:
                        parse_Yi_Punctuation_Mark(root, file)
                        print('done')
                        done=done+1
                    except Exception as e:
                        traceback.print_exc()
                        with open('error.log', mode='a', encoding='utf-8') as f:
                            f.write('parse %s type=1 error: %s\n' % (os.path.join(root, file), e))
                        print('error')
                        error=error+1
    """
