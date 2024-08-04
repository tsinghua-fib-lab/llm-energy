# Rapid Layout

**工作流的入口，需将其他几个模型启动后再运行**

**用来识别PDF布局并联合其他几个模型**

**改写自Rapid-Layout**

## 环境
- python 3.11
- cuda 12.1
- cudnn 8.9.0.6
- 依赖包见同目录下 requirements.txt

## Rapid-Layout

1. 新增 `./parse_policy_layout.py`

## 运行

1. 运行 `TexTeller` 和 `PaddleParse`
2. 修改 `./parse_policy_layout.py` 最后一行的 `input_dir=` 和 `output_dir`
2. python ./parse_policy_layout.py