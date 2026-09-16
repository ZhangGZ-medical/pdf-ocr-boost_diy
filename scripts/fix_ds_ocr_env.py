# -*- coding: utf-8 -*-
"""DeepSeek-OCR 环境诊断与依赖修复
本机 D:/ai-ocr/venv_ds 环境的已知问题:
  1. 缺依赖: PIL/addict/matplotlib/requests/einops/torchvision
     (2026-08-18 已补装: pillow, addict, matplotlib, requests, einops, torchvision 0.28.0+cpu)
  2. transformers 版本冲突: venv_ds 装的是 5.15.0, 但 DeepSeek-OCR 的
     modeling_deepseekv2.py 引用 transformers.models.llama.modeling_llama 的
     LlamaFlashAttention2 —— 该类在 transformers >= 4.46 已移除。
     报错: ImportError: cannot import name 'LlamaFlashAttention2'

用法:
  python fix_ds_ocr_env.py --check   # 诊断(只读)
  python fix_ds_ocr_env.py --fix     # 补装缺失依赖(清华源)
  python fix_ds_ocr_env.py --fix-transformers   # 尝试降级 transformers(需确认兼容性)
"""
import os, subprocess, sys, argparse

PY_DS = r'D:/ai-ocr/venv_ds/Scripts/python.exe'
MODELING = r'D:/ai-ocr/models/hf/modules/transformers_modules/DeepSeek_hyphen_OCR'
PIP_INDEX = 'https://pypi.tuna.tsinghua.edu.cn/simple'

REQUIRED = ['PIL', 'addict', 'matplotlib', 'requests', 'einops', 'torchvision']

def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)

def check_imports():
    print('=== 依赖检查 ===')
    missing = []
    for mod in REQUIRED:
        r = run([PY_DS, '-c', f'import {mod}'], timeout=60)
        print(f'  {"OK" if r.returncode == 0 else "缺"} {mod}')
        if r.returncode != 0:
            missing.append(mod)
    print('=== transformers 版本 ===')
    r = run([PY_DS, '-c', 'import transformers; print(transformers.__version__)'], timeout=60)
    ver = r.stdout.strip()
    print(f'  {ver}')
    print('=== modeling 文件引用检查 ===')
    found = []
    for root, dirs, files in os.walk(MODELING):
        for f in files:
            if f == 'modeling_deepseekv2.py':
                p = os.path.join(root, f)
                content = open(p, encoding='utf-8', errors='ignore').read()
                if 'LlamaFlashAttention2' in content:
                    found.append(p)
    if found:
        print(f'  以下文件引用 LlamaFlashAttention2(已在新版 transformers 移除):')
        for p in found:
            print(f'    - {p}')
        print(f'  结论: transformers {ver} 与模型代码不兼容, 需降级或打补丁')
    else:
        print('  未发现 LlamaFlashAttention2 引用')
    return missing

def fix_deps():
    print('=== 补装缺失依赖 ===')
    r = run([PY_DS, '-m', 'pip', 'install', 'pillow', 'addict', 'matplotlib',
             'requests', 'einops', '-i', PIP_INDEX], timeout=600)
    print(r.stdout[-300:])
    print(r.stderr[-300:])
    # torchvision 需与 torch 匹配, 用 --no-deps 防连带升级 torch
    r = run([PY_DS, '-m', 'pip', 'install', 'torchvision', '--no-deps', '-i', PIP_INDEX], timeout=600)
    print(r.stdout[-200:])
    print(r.stderr[-200:])

def fix_transformers():
    """降级 transformers 到支持 LlamaFlashAttention2 的版本(4.44/4.45 系列)
    注意: 降级可能影响其他依赖, 执行前确认; 若模型有官方要求版本以官方为准"""
    print('=== 尝试降级 transformers ===')
    print('DeepSeek-OCR 官方要求 transformers>=4.38; LlamaFlashAttention2 在 4.45 仍存在')
    r = run([PY_DS, '-m', 'pip', 'install', 'transformers==4.45.2', '-i', PIP_INDEX], timeout=600)
    print(r.stdout[-300:])
    print(r.stderr[-300:])
    print('降级后重跑 deepseek_ocr.py 验证; 若报其他 API 不兼容, 改试 4.44.2')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='只诊断')
    ap.add_argument('--fix', action='store_true', help='补装缺失依赖')
    ap.add_argument('--fix-transformers', action='store_true', help='尝试降级 transformers')
    args = ap.parse_args()

    if not os.path.exists(PY_DS):
        print(f'!! DeepSeek-OCR 环境不存在: {PY_DS}')
        print('   参见 pdf-ocr-pipeline/README.md 部署 D:/ai-ocr/venv_ds')
        sys.exit(1)

    if args.check:
        check_imports()
    if args.fix:
        fix_deps()
    if args.fix_transformers:
        fix_transformers()
    if not (args.check or args.fix or args.fix_transformers):
        print('用法: python fix_ds_ocr_env.py [--check] [--fix] [--fix-transformers]')
        check_imports()

if __name__ == '__main__':
    main()
