import os
import argparse
import cv2
from pathlib import Path
import numpy as np
from models.ocr_model.utils.to_katex import to_katex
from models.ocr_model.utils.inference import inference as latex_inference
from models.ocr_model.model.TexTeller import TexTeller
import loguru

def load_model(model_path:str = None, use_onnx:bool = False, onnx_provider:str|None = None):
    """加载模型
    """
    os.chdir(Path(__file__).resolve().parent)
    
    # You can use your own checkpoint and tokenizer path.
    loguru.logger.info('Loading model and tokenizer...')
    latex_rec_model = TexTeller.from_pretrained(model_path, use_onnx, onnx_provider)
    tokenizer = TexTeller.get_tokenizer()
    loguru.logger.info('Model and tokenizer loaded.')
    return latex_rec_model, tokenizer


def infer(img:bytes, latex_rec_model, tokenizer, inference_mode='cpu') -> str:
    """包装原来的代码，用于调用。
    """
    
    img = cv2.imdecode(np.frombuffer(img, dtype=np.uint8), 1)
    inf = latex_inference(latex_rec_model, tokenizer, [img], inference_mode, 1)
    katex = to_katex(inf[0])
    if katex.startswith("\\boxed{"):
        katex = katex[7:-1]
        flag = False
        for i in range(len(katex)):
            end_i = len(katex) - i - 1
            if katex[end_i] == "}":
                if flag:
                    katex = katex[:end_i] + katex[end_i+1:]
                    break
                else:
                    flag = True 
    return katex


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-img', 
        type=str, 
        required=True,
        help='path to the input image'
    )
    
    args = parser.parse_args()
    
    with open(args.img, mode='rb') as f:
        img = f.read()
    model, tokenizer = load_model(None, True, 'cuda')
    print(infer(img, model, tokenizer, 'cuda'))