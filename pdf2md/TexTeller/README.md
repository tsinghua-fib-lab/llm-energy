# TexTeller

**用来OCR表格和文本**

**改写自TexTeller**

## 环境

- python 3.11
- cuda 12.1
- cudnn 8.9.0.6
- 依赖包见同目录下 requirements.txt

## LaTeX OCR

    1. 改写`src/inference.py` 为 `src/ocr_formula.py`
    2. 新增 `src/run_table_api.py`，用于启动 http API

## 运行

```bash
python ./src/run_formula_api.py
```
