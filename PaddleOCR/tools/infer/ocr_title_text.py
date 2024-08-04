import os
import sys
import subprocess

from more_itertools import unzip

__dir__ = os.path.dirname(os.path.abspath(__file__))
sys.path.append(__dir__)
sys.path.insert(0, os.path.abspath(os.path.join(__dir__, "../..")))

os.environ["FLAGS_allocator_strategy"] = "auto_growth"

import cv2
import copy
import numpy as np
import json
import time
import logging
from PIL import Image
import tools.infer.utility as utility
import tools.infer.predict_rec as predict_rec
import tools.infer.predict_det as predict_det
import tools.infer.predict_cls as predict_cls
from ppocr.utils.utility import get_image_file_list, check_and_read
from ppocr.utils.logging import get_logger
from tools.infer.utility import (
    draw_ocr_box_txt,
    get_rotate_crop_image,
    get_minarea_rect_crop,
    slice_generator,
    merge_fragmented,
)
import loguru

logger = get_logger()


class TextSystem(object):
    def __init__(self, args):
        if not args.show_log:
            logger.setLevel(logging.INFO)

        self.text_detector = predict_det.TextDetector(args)
        self.text_recognizer = predict_rec.TextRecognizer(args)
        self.use_angle_cls = args.use_angle_cls
        self.drop_score = args.drop_score
        if self.use_angle_cls:
            self.text_classifier = predict_cls.TextClassifier(args)

        self.args = args
        self.crop_image_res_index = 0

    def draw_crop_rec_res(self, output_dir, img_crop_list, rec_res):
        os.makedirs(output_dir, exist_ok=True)
        bbox_num = len(img_crop_list)
        for bno in range(bbox_num):
            cv2.imwrite(
                os.path.join(
                    output_dir, f"mg_crop_{bno+self.crop_image_res_index}.jpg"
                ),
                img_crop_list[bno],
            )
            logger.debug(f"{bno}, {rec_res[bno]}")
        self.crop_image_res_index += bbox_num

    def __call__(self, img, cls=True, slice={}):
        time_dict = {"det": 0, "rec": 0, "cls": 0, "all": 0}

        if img is None:
            logger.debug("no valid image provided")
            return None, None, time_dict

        start = time.time()
        ori_im = img.copy()
        if slice:
            slice_gen = slice_generator(
                img,
                horizontal_stride=slice["horizontal_stride"],
                vertical_stride=slice["vertical_stride"],
            )
            elapsed = []
            dt_slice_boxes = []
            for slice_crop, v_start, h_start in slice_gen:
                dt_boxes, elapse = self.text_detector(slice_crop)
                if dt_boxes.size:
                    dt_boxes[:, :, 0] += h_start
                    dt_boxes[:, :, 1] += v_start
                    dt_slice_boxes.append(dt_boxes)
                    elapsed.append(elapse)
            dt_boxes = np.concatenate(dt_slice_boxes)

            dt_boxes = merge_fragmented(
                boxes=dt_boxes,
                x_threshold=slice["merge_x_thres"],
                y_threshold=slice["merge_y_thres"],
            )
            elapse = sum(elapsed)
        else:
            dt_boxes, elapse = self.text_detector(img)

        time_dict["det"] = elapse

        if dt_boxes is None:
            logger.debug("no dt_boxes found, elapsed : {}".format(elapse))
            end = time.time()
            time_dict["all"] = end - start
            return None, None, time_dict
        else:
            # logger.debug(
            #     "dt_boxes num : {}, elapsed : {}".format(len(dt_boxes), elapse)
            # )
            pass
        img_crop_list = []

        dt_boxes = sorted_boxes(dt_boxes)

        for bno in range(len(dt_boxes)):
            tmp_box = copy.deepcopy(dt_boxes[bno])
            if self.args.det_box_type == "quad":
                img_crop = get_rotate_crop_image(ori_im, tmp_box)
            else:
                img_crop = get_minarea_rect_crop(ori_im, tmp_box)
            img_crop_list.append(img_crop)
        if self.use_angle_cls and cls:
            img_crop_list, angle_list, elapse = self.text_classifier(img_crop_list)
            time_dict["cls"] = elapse
            logger.debug(
                "cls num  : {}, elapsed : {}".format(len(img_crop_list), elapse)
            )
        if len(img_crop_list) > 1000:
            logger.debug(
                f"rec crops num: {len(img_crop_list)}, time and memory cost may be large."
            )

        rec_res, elapse = self.text_recognizer(img_crop_list)
        time_dict["rec"] = elapse
        # logger.debug("rec_res num  : {}, elapsed : {}".format(len(rec_res), elapse))
        if self.args.save_crop_res:
            self.draw_crop_rec_res(self.args.crop_res_save_dir, img_crop_list, rec_res)
        filter_boxes, filter_rec_res = [], []
        for box, rec_result in zip(dt_boxes, rec_res):
            text, score = rec_result[0], rec_result[1]
            if score >= self.drop_score:
                filter_boxes.append(box)
                filter_rec_res.append(rec_result)
        end = time.time()
        time_dict["all"] = end - start
        return filter_boxes, filter_rec_res, time_dict


def sorted_boxes(dt_boxes):
    """
    Sort text boxes in order from top to bottom, left to right
    args:
        dt_boxes(array):detected text boxes with shape [4, 2]
    return:
        sorted boxes(array) with shape [4, 2]
    """
    num_boxes = dt_boxes.shape[0]
    sorted_boxes = sorted(dt_boxes, key=lambda x: (x[0][1], x[0][0]))
    _boxes = list(sorted_boxes)

    for i in range(num_boxes - 1):
        for j in range(i, -1, -1):
            if abs(_boxes[j + 1][0][1] - _boxes[j][0][1]) < 10 and (
                _boxes[j + 1][0][0] < _boxes[j][0][0]
            ):
                tmp = _boxes[j]
                _boxes[j] = _boxes[j + 1]
                _boxes[j + 1] = tmp
            else:
                break
    return _boxes


def load_model(
    args = None,
    det_model_dir: str  = "tools/inference/ch_PP-OCRv4_det_server_infer",
    rec_model_dir: str  = "tools/inference/ch_PP-OCRv4_rec_server_infer",
    use_angle_cls: bool = False
):
    if args is None:
        parser = utility.init_args()
        args = parser.parse_args([])
        args.det_model_dir = det_model_dir
        args.rec_model_dir = rec_model_dir
        args.use_angle_cls = use_angle_cls
        loguru.logger.info("Loading models...")
        text_sys = TextSystem(args)
        loguru.logger.info("Models loaded.")
        return text_sys


def main(
    args,
    text_sys: TextSystem
):
    img = cv2.imdecode(np.frombuffer(args.img, dtype=np.uint8), 1)
    dt_boxes, rec_res, time_dict = text_sys(img)
    # for text, score in rec_res:
        # logger.debug("{}, {:.3f}".format(text, score))
    
    if args.is_title:
        return ''.join(unzip(rec_res)[0])
    elif args.is_text:
        texts = list(unzip(rec_res)[0])
        res = texts[0] if texts else ""
        if texts:
            for i in range(1, len(texts)):
                box, box_pre = dt_boxes[i].tolist(), dt_boxes[i-1].tolist()
                [x1, y1], [x2, y2] = box[0], box[2]
                [x1_pre, y1_pre], [x2_pre, y2_pre] = box_pre[0], box_pre[2]
                res += ('\n' if y1 - y1_pre > (y2-y1) / 2 else '') + texts[i]
                # res += ("\n" if texts[i-1][-1] in "!;:?。！；：？……" or texts[i][0] == "第" else "") + texts[i]
            return res
    else:
        return dt_boxes, rec_res, time_dict
        

def infer(
    img: bytes,
    text_sys: TextSystem,
    is_title: bool = False,
    is_text: bool = False,
    args = None,
    det_model_dir: str = "tools/inference/ch_PP-OCRv4_det_server_infer",
    rec_model_dir: str = "tools/inference/ch_PP-OCRv4_rec_server_infer",
    use_angle_cls: bool = False
):
    if not args:
        parser = utility.init_args()
        parser.add_argument("--is_title", type=bool, default=False)
        parser.add_argument("--is_text", type=bool, default=False)
        args = parser.parse_args([])
        args.is_title = is_title
        args.is_text = is_text
        args.det_model_dir = det_model_dir
        args.rec_model_dir = rec_model_dir
        args.use_angle_cls = use_angle_cls
        args.img = img
    return main(args, text_sys)
    

if __name__ == "__main__":
    # args = utility.parse_args()
    
    # with open(args.image_dir, "rb") as f:
    #     args.img = f.read()
    
    # text_sys = load_model(args)
    # print(main(args, text_sys))
    
    with open(r'./0.png', mode='rb') as f:
        img = f.read()
        text_sys = load_model()
        print(infer(img, text_sys))
