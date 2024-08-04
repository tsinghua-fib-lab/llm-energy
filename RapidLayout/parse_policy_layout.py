"""
### 运行环境：
    - python 3.11
    - cuda 12.1
    - cudnn 8.9.0.6
### 依赖库：
    - 见同目录下 requirements.txt
"""

import cv2, fitz
from rapid_layout import RapidLayout, VisLayout
import numpy as np
import tqdm, loguru
import os, json
from functools import cmp_to_key
import requests


def pdf2img_list(pdf_path: str) -> list[np.ndarray]:
    """将PDF转换为图片列表

    ### Args:
        - pdf_path (str): 
            PDF文件路径

    ### Returns:
        - list[np.ndarray]: 
            返回图片列表，其中每个元素为一张cv2.imread读取的图片
    """
    loguru.logger.info(f"Converting PDF to images: {pdf_path}")
    pdf = fitz.open(pdf_path)
    prog_bar = tqdm.tqdm(total=pdf.page_count, desc="Converting PDF to images")
    img_list = []
    for i in range(pdf.page_count):
        page = pdf[i]
        zoom = 2.0
        pix = page.get_pixmap(matrix = fitz.Matrix(zoom, zoom))
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        # Convert the image to RGB format
        if pix.n == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        elif pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_list.append(cv2.imdecode(np.frombuffer(cv2.imencode('.png', img)[1], np.uint8), cv2.IMREAD_COLOR))
        prog_bar.update(1)
    return img_list


def load_model(model_type: str) -> RapidLayout:
    loguru.logger.info(f"Loading model: {model_type}...")
    layout_engine = RapidLayout(conf_thres = 0.3, model_type = model_type, use_cuda = True)
    loguru.logger.info(f"Model loaded.")
    return layout_engine


def parse_img_list(img_list: list[np.ndarray], layout_engine: RapidLayout) -> list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    """识别一组图片中的布局

    ### Args:
        - img_list (list[np.ndarray]): 
            图片列表，其中每个元素为一张cv2.imread读取的图片
        - layout_engine (RapidLayout):
            布局识别模型实例

    ### Returns:
        - list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
            返回识别结果，其中每个元素为一张图片的识别结果，包括原始图片、检测框、置信度、类别名。
            删除置信度低于0.6的公式块、置信度低于0.8的标题块、置信度低于0.7的其他块
    """
    loguru.logger.info(f"Running layout engine on images...")
    prog_bar = tqdm.tqdm(total=len(img_list), desc="Running layout engine on images...")
    res = []
    for img in img_list:
        boxes, scores, class_names = [], [], []
        boxes_tmp, scores_tmp, class_names_tmp, elapse = layout_engine(img)
        for b, s, c in zip(boxes_tmp, scores_tmp, class_names_tmp):
            if c == "equation" and s < 0.6:
                continue
            elif c == "title" and s < 0.8:
                continue
            elif s < 0.7:
                continue
            else:
                boxes.append(b)
                scores.append(s)
                class_names.append(c)
        res.append((img, boxes, scores, class_names))
        prog_bar.update(1)
    return res


def split_image(layouts: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]) -> list[dict[str, list[tuple[np.ndarray, np.ndarray, float, str]]]]:
    """将布局中的检测框分割出来，每个检测框分割成一张图片

    ### Args:
        - layouts (list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]):
            布局识别结果，其中每个元素为一张图片的识别结果，包括原始图片、检测框、置信度、类别名

    ### Returns:
        - list[dict[str, list[np.ndarray]]]: 
            返回分割后的图片，其中每个元素为一张图片的分割结果，为一个字典，键为该图片下识别出来的布局的类别名，值为该类别的图片列表，包括图片、检测框、置信度、类别名
    """
    loguru.logger.info(f"Splitting images...")
    prog_bar = tqdm.tqdm(total=len(layouts), desc="Splitting images")
    res = []
    for img, boxes, scores, class_names in layouts:
        page_res = {}
        x_shape, y_shape = img.shape[1], img.shape[0]
        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = box
            if class_names[i] != "figure":
                y1, y2 = int(y1 - y_shape/110), int(y2 + y_shape/110)
                x1, x2 = 0, x_shape
            else:
                y1, y2 = int(y1), int(y2)
                x1, x2 = int(x1), int(x2)
            sub_img = img[y1:y2, x1:x2]
            if class_names[i] not in page_res:
                page_res[class_names[i]] = []
            page_res[class_names[i]].append((sub_img, box, scores[i], class_names[i]))
        res.append(page_res)
        prog_bar.update(1)
    return res


def save_splited_images(splited_images: list[dict[str, list[tuple[np.ndarray, np.ndarray, float, str]]]], output_dir: str, file_name):
    """将分割后的图片保存到文件夹

    ### Args:
        - splited_images (list[dict[str, list[np.ndarray]]]): 
            分割后的图片，其中每个元素为一张图片的分割结果，为一个字典，键为该图片下识别出来的布局的类别名，值为该类别的图片列表，包括图片、检测框、置信度、类别名
        - output_dir (str): 
            输出文件夹路径
    """
    # Save images
    loguru.logger.info(f"Saving splited images...")
    for page in range(len(splited_images)):
        for class_name, class_obj in splited_images[page].items():
            for i, (sub_img, box, score, class_name) in enumerate(class_obj):
                output_png_dir = os.path.join(output_dir, f"page{page}/{class_name}")
                if not os.path.exists(output_png_dir):
                    os.makedirs(output_png_dir, exist_ok=True)
                cv2.imwrite(os.path.join(output_png_dir, f"{i}.png"), sub_img)
              
    # Save json  
    output_json = {
        "title": file_name,
        "mata": []
    }
    output_json_path = os.path.join(output_dir, "meta.json")
    for page in range(len(splited_images)):
        page_res = {}
        for class_name, class_obj in splited_images[page].items():
            output_png_dir = os.path.join(output_dir, f"page{page}/{class_name}")
            for i, (sub_img, box, score, class_name) in enumerate(class_obj):
                item_res = {
                    "id": i,
                    "class_name": class_name,
                    "box": box.tolist(),
                    "score": score,
                    "path": os.path.join(output_png_dir, f"{i}.png")
                }
                if not class_name in page_res:
                    page_res[class_name] = []
                page_res[class_name].append(item_res)
        output_json["mata"].append(page_res)
    output_json = json.dumps(output_json, indent=4, ensure_ascii=False)
    with open(output_json_path, "w") as f:
        f.write(output_json)


def rend_layout_pdf(layouts: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]) -> fitz.Document:
    """将布局渲染到PDF，体现结果：在原始PDF上用彩色框标出各个区域

    ### Args:
        - layouts (list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]): 
            布局识别结果，其中每个元素为一张图片的识别结果，包括原始图片、检测框、置信度、类别名

    ### Returns:
        - fitz.Document: 
            返回渲染后的PDF
    """
    loguru.logger.info(f"Rendering layout to PDF")
    prog_bar = tqdm.tqdm(total=len(layouts), desc="Rendering layout to PDF")
    output_pdf = fitz.open()
    for img, boxes, scores, class_names in layouts:
        img = VisLayout.draw_detections(img, boxes, scores, class_names)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.imencode('.png', img)[1].tobytes()
        output_pdf.insert_pdf(
            fitz.open("pdf", 
                fitz.open("pdf", img).convert_to_pdf()
            )
        )
        prog_bar.update(1)
    return output_pdf


def get_markdown_from_other_model(img_cv: np.ndarray, classname: str, file_id: int|str) -> str:
    """根据不同的类别，调用不同的模型，获取markdown

    ### Args:
        img (np.ndarray): 图片的二进制数据（cv2形式）
        classname (str): 图片的类别（title、text、equation、table、figure）

    ### Returns:
        str: 返回markdown字符串
        
    ### APIs:
        method: POST
        - equation: "http://localhost:20000/infer"
        - table: "http://localhost:20001/infer"
        - text: "http://localhost:20002/infer/text"
        - title: "http://localhost:20002/infer/title"        
    """
    img_bytes = cv2.imencode('.png', img_cv)[1].tobytes()
    resp = None
    if classname == "equation":
        resp = requests.post(
            url = 'http://localhost:20000/infer',
            files = { 'file': img_bytes }
        ).json()
    elif classname == "table":
        resp = requests.post(
            url = 'http://localhost:20001/infer',
            files = { 'file': img_bytes }
        ).json()
    elif classname == "text":
        resp = requests.post(
            url = 'http://localhost:20002/infer/text',
            files = { 'file': img_bytes }
        ).json()
    elif classname == "title":
        resp = requests.post(
            url = 'http://localhost:20002/infer/title',
            files = { 'file': img_bytes }
        ).json()
    if resp:
        if resp['status'] == 'success':
            return resp['result']
        else:
            loguru.logger.error(f"Failed to get markdown from other model. classname:{classname}, file:{file_id}, error:{resp['error']}")
            return ''
    else:
        loguru.logger.error(f"Classname {classname} is not supported.")
        return ''


def cmp_layout_item(item1, item2):
    box1, box2 = item1[1], item2[1]
    x11, y11, x21, y21 = box1
    x12, y12, x22, y22 = box2
    if y11 < y12:
        return -1
    elif y11 > y12:
        return 1
    else:
        if x11 < x12:
            return -1
        elif x11 > x12:
            return 1
        else:
            return 0

def save_markdown(
        output_dir: str,
        splited_images: list[dict[str, list[tuple[np.ndarray, np.ndarray, float, str]]]]
    ):
    """保存为markdown文件
    
    ### Args:
        output_dir (str): 输出文件夹路径，路径可以以原始 PDF 文件名命名（不要包含 .pdf）
        splited_images (list[dict[str, list[np.ndarray]]]): 分割后的图片，其中每个元素为一张图片的分割结果，为一个字典，键为该图片下识别出来的布局的类别名，值为该类别的图片列表，包括图片、检测框、置信度、类别名

    ### Returns:
        None
    """
    output_md_content = ""
    output_img_dir = os.path.join(output_dir, "images")
    output_md_path = os.path.join(output_dir, "output.md")
    output_figure_cnt = 0
    pre_page_lst_item_is_text = False
    if not os.path.exists(output_img_dir):
        os.makedirs(output_img_dir, exist_ok=True)
    loguru.logger.info(f"Recognizing markdown...")
    prog_bar = tqdm.tqdm(total=len(splited_images), desc="Recognizing markdown")
    
    for page_id, page_layout in enumerate(splited_images):
        item_list = []
        for classname, class_obj in page_layout.items():
            if not classname in ['title', 'text', 'equation', 'table', 'figure']:
                continue
            item_list += class_obj
        item_list.sort(key=cmp_to_key(cmp_layout_item))
        
        for item_id, (sub_img, box, score, classname) in enumerate(item_list):
            if pre_page_lst_item_is_text and classname != 'text':
                pre_page_lst_item_is_text = False
                output_md_content += "\n\n"
            if classname == 'figure':
                output_figure_cnt += 1
                cv2.imwrite(os.path.join(output_img_dir, f"figure{output_figure_cnt}.png"), sub_img)
                output_md_content += f"![figure{output_figure_cnt}](images/figure{output_figure_cnt}.png)\n\n"
                    
            else:
                output_md_content += get_markdown_from_other_model(sub_img, classname, f"{page_id}-{item_id}")
                if item_id == len(item_list) - 1 and classname == 'text':
                    pre_page_lst_item_is_text = True
                else:
                    output_md_content += "\n\n"
        prog_bar.update(1)
        
    with open(output_md_path, "w") as f:
        f.write(output_md_content)


def parse(input_dir: str, output_dir: str):
    layout_engine = load_model("pp_layout_cdla")
    
    file_paths = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            file_paths.append(os.path.join(root, file))
    for i, file in enumerate(file_paths):
        if not file.endswith(".pdf"):
            continue
        input_pdf_path = file
        output_pdf_dir = os.path.join(output_dir, os.path.splitext(file[2:] if file[:2] == './' else file)[0])
        # output_pdf_path = os.path.join(output_dir, file)
        if not os.path.exists(output_pdf_dir):
            os.makedirs(output_pdf_dir, exist_ok=True)
            
        loguru.logger.info(f"Processing PDF: {input_pdf_path}    {i}/{len(file_paths)}...")
        images = pdf2img_list(input_pdf_path)
        layouts = parse_img_list(images, layout_engine)
        splited_images = split_image(layouts) 
        save_markdown(output_pdf_dir, splited_images)
        # save_splited_images(splited_images, output_dir, file) # 当 http 接口封装完成后，就不用向硬盘写入了
        # output_pdf = rend_layout_pdf(layouts) # 查看 layout 识别效果
        # output_pdf.save(output_pdf_path)


if __name__ == '__main__':
    parse(input_dir="./input_pdf", output_dir="./output")
