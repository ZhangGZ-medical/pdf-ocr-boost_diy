---
name: pdf-ocr-boost_diy
description: 本机图片型 PDF OCR 增强层技能，是 pdf-ocr-pipeline 的补丁与兜底。适用于：(1) pipeline 双栏/多栏检测失效导致版面错乱时，用坐标级版面重建（按 OCR box 坐标分栏、聚类成行、续行合并）恢复正确阅读顺序；(2) 引擎选型决策——RapidOCR/PaddleOCR/DeepSeek-OCR 三引擎在本机 CPU 环境的实测精度速度基准与选择矩阵；(3) DeepSeek-OCR 环境故障修复（缺依赖补装、transformers 5.x 版本冲突诊断）；(4) OCR 质量评估与降级策略（置信度阈值、DPI 调整、二值化回退）。触发词：OCR双栏错乱、坐标重建、OCR引擎选型、DeepSeek-OCR报错、OCR质量评估、扫描件版面恢复、OCR环境修复。
agent_created: true
---

# pdf-ocr-boost_diy — 本机图片型 PDF OCR 增强层

`pdf-ocr-pipeline` 的标准 5 阶段流程覆盖"渲染→预处理→OCR→版面→清洗"主链路；
本技能覆盖其**薄弱环节**：引擎选型、双栏坐标重建、DeepSeek-OCR 环境修复、质量评估。

## 何时使用本技能

| 症状 | 用本技能 |
|---|---|
| 执行 pipeline 后 `manifest.json` 中 `two_column=false` 但文档实际是双栏，`document.md` 左右栏错乱/压成乱行 | scripts/rebuild_columns.py 坐标重建 |
| 不确定用哪个引擎（rapid/paddle/DeepSeek-OCR） | 查 references/engine_benchmarks.md 选择矩阵 |
| `D:/ai-ocr/venv_ds` 跑 DeepSeek-OCR 报 ImportError（缺依赖或 transformers 版本冲突） | scripts/fix_ds_ocr_env.py |
| OCR 置信度低（<0.85）或结果质量存疑 | 查 references/quality_guide.md 降级策略 |

## 本机环境矩阵（2026-08 实测）

| 环境 | 路径 | 引擎 | 精度 | 速度（CPU i5-1340P） |
|---|---|---|---|---|
| default venv | `C:/Users/G1381/.workbuddy/binaries/python/envs/default/Scripts/python.exe` | RapidOCR | 中（实测置信度 0.73-0.87） | 每页 8-40 秒 |
| D 盘 paddle | `D:/ai-ocr/venv/Scripts/python.exe` | PP-OCRv4 Server | 高 | 每页 1-23 分钟（表格页极慢） |
| D 盘 DeepSeek-OCR | `D:/ai-ocr/venv_ds/Scripts/python.exe` | DeepSeek-OCR（VLM） | 最高（版面语义理解） | 每页 20-90 秒（修复后理论值） |

**引擎选择速记**：大字/词典/规整版面 → rapid；表格/复杂/低清 → paddle；少量高价值页或版面语义要求高 → DeepSeek-OCR。

## 工作流程

### 1. 环境体检（可选）

```bash
"C:/Users/G1381/.workbuddy/binaries/python/envs/default/Scripts/python.exe" \
  scripts/ocr_env_probe.py
```

探测三个环境的存在性、关键包版本、DeepSeek-OCR 模型文件完整性，输出体检报告。

### 2. 标准 OCR（pdf-ocr-pipeline）

```bash
PY="C:/Users/G1381/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"$PY" "C:/Users/G1381/.workbuddy/skills/pdf-ocr-pipeline/scripts/pipeline.py" \
  "输入.pdf" -o "输出目录" --engine rapid --dpi 300 --keep-images
```

**只消费其坐标产物** `work/ocr/page_XXX.ocr.json`（items: box+text+score）；不依赖其版面结构化。

### 3. 双栏坐标重建（当 pipeline 版面错乱时）

```bash
"$PY" scripts/rebuild_columns.py \
  --ocr-dir "输出目录/work/ocr" \
  --out "重建结果.txt" \
  --split-x 1050 --y-tol 40
```

算法：按 box 中心 x 分栏 → 栏内 y 聚类成行 → 行内 x 排序拼接 → 输出左右栏各自的正确阅读顺序。
参数说明与算法细节见 references/column_rebuild.md。

### 4. DeepSeek-OCR 精读（少量高价值页）

```bash
"D:/ai-ocr/venv_ds/Scripts/python.exe" scripts/fix_ds_ocr_env.py --check   # 先体检
"D:/ai-ocr/venv_ds/Scripts/python.exe" D:/ai-ocr/scripts/deepseek_ocr.py \
  "输入.pdf" -o "输出.md" --dpi 200 --resume
```

### 5. 质量评估

对照 `manifest.json` 平均置信度与 references/quality_guide.md 阈值表，决定接受、提 DPI 重跑或换引擎。

## 关键约束（踩坑结论）

1. **不要用 x 间隙拆分**（拆散"中文+英文"同行结构）；相邻行合并产生的混行交给下游技能人工修正
2. **y 聚类容差勿 <30px**（OCR 会把英文首字母单独成框，"a"+"ngiotensin" 会被拆行）
3. 坐标重建脚本只读 OCR JSON + 写文本文件，无网络、无删除操作，可放心运行
4. DeepSeek-OCR 的 transformers 需与 `D:/ai-ocr/models/.../modeling_deepseekv2.py` 兼容（当前 5.15.0 缺 `LlamaFlashAttention2`，见 scripts/fix_ds_ocr_env.py 注释）

## 与其他技能协同

- 标准流程 → `pdf-ocr-pipeline`
- OCR 后词条结构化提取 → `med-term-extractor_diy`
- 医学内容审核 → `biomed-review-pipeline_diy`、`reference_review_diy`
- 纯文本层 PDF → `pdf` / `pdfkit-py`（无需 OCR）
