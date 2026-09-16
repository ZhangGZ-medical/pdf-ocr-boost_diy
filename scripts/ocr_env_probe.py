# -*- coding: utf-8 -*-
"""本机 OCR 环境体检
探测三个 OCR 环境(rapid/paddle/DeepSeek-OCR)的存在性、关键包、模型完整性。
只读检查, 无副作用。
"""
import os, subprocess, sys, json

ENVS = {
    'rapid (default venv)': {
        'python': r'C:/Users/G1381/.workbuddy/binaries/python/envs/default/Scripts/python.exe',
        'checks': ['import rapidocr_onnxruntime, pymupdf, PIL, numpy; print("ok")'],
        'note': 'pdf-ocr-pipeline 默认轻量引擎环境',
    },
    'paddle (D盘)': {
        'python': r'D:/ai-ocr/venv/Scripts/python.exe',
        'checks': ['import paddle, paddleocr; print("ok")'],
        'note': 'PP-OCRv4 Server 高精度引擎环境',
    },
    'DeepSeek-OCR (D盘)': {
        'python': r'D:/ai-ocr/venv_ds/Scripts/python.exe',
        'checks': [
            'import torch, transformers, PIL, addict, matplotlib, requests, einops, torchvision; print("ok")',
            'import transformers; print("transformers", transformers.__version__)',
        ],
        'note': 'VLM 级 OCR, 依赖多, 需 transformers 与模型 modeling 文件版本兼容',
    },
}

MODEL_DIR = r'D:/ai-ocr/models/DeepSeek-OCR'
DS_SCRIPT = r'D:/ai-ocr/scripts/deepseek_ocr.py'

def run(py, code):
    try:
        r = subprocess.run([py, '-c', code], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=120)
        return (r.returncode == 0, (r.stdout + r.stderr).strip()[-200:])
    except Exception as e:
        return (False, str(e)[:200])

def main():
    print('===== 本机 OCR 环境体检 =====')
    for name, cfg in ENVS.items():
        py = cfg['python']
        exists = os.path.exists(py)
        print(f'\n[{name}] python 存在: {"是" if exists else "否"} -> {py}')
        if not exists:
            print('  !! 环境缺失, 参见 pdf-ocr-pipeline/README.md 安装说明')
            continue
        for code in cfg['checks']:
            ok, out = run(py, code)
            print(f'  {"✓" if ok else "✗"} {code[:50]}...')
            if not ok:
                print(f'    输出: {out}')
        print(f'  说明: {cfg["note"]}')
    print('\n===== DeepSeek-OCR 模型与脚本 =====')
    print(f'模型目录: {"存在" if os.path.isdir(MODEL_DIR) else "缺失"} -> {MODEL_DIR}')
    if os.path.isdir(MODEL_DIR):
        items = os.listdir(MODEL_DIR)
        print(f'  内容(前8): {items[:8]}')
    print(f'精读脚本: {"存在" if os.path.exists(DS_SCRIPT) else "缺失"} -> {DS_SCRIPT}')
    print('\n提示: DeepSeek-OCR 缺依赖 → fix_ds_ocr_env.py --fix; 报 LlamaFlashAttention2 ImportError → fix_ds_ocr_env.py --fix-transformers')

if __name__ == '__main__':
    main()
