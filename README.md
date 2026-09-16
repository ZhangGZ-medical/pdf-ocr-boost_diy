# pdf-ocr-boost_diy — 本机图片型 PDF OCR 增强层

`pdf-ocr-pipeline` 的增强补丁：引擎选型实测基准、双栏坐标重建、DeepSeek-OCR 环境修复、质量评估降级策略。全部能力源自本机实战（《常用临床医学名词（2023年版）》多份图片型 PDF 的 OCR 任务）。

## 定位（与 pdf-ocr-pipeline 的关系）

```
pdf-ocr-pipeline（标准流程）           pdf-ocr-boost_diy（增强层）
├── 渲染 → 预处理 → OCR → 清洗        ├── 引擎选型决策矩阵（实测基准）
├── 双栏中缝检测（常失效）◄──兜底──   ├── 坐标级双栏重建 rebuild_columns.py
├── DeepSeek-OCR 引用                ├── 环境诊断修复 fix_ds_ocr_env.py
└── manifest 置信度报告               └── 质量阈值与降级决策 quality_guide.md
```

两个技能互补：先跑 pipeline 拿 OCR 坐标产物，版面错乱/引擎存疑/环境报错时用本技能兜底。

## 目录结构

```
pdf-ocr-boost_diy/
├── SKILL.md                      # 技能定义
├── README.md                     # 本文件
├── scripts/
│   ├── ocr_env_probe.py          # 三环境体检（rapid/paddle/DeepSeek-OCR）
│   ├── rebuild_columns.py        # OCR 坐标级双栏/多栏版面重建
│   └── fix_ds_ocr_env.py         # DeepSeek-OCR 依赖补装 + transformers 冲突诊断
└── references/
    ├── engine_benchmarks.md      # 实测速度/精度基准 + 引擎选择矩阵
    └── quality_guide.md          # 置信度阈值、降级决策树、交付规范
```

## 安装

无额外安装。依赖本机已有的三个环境（均由 `pdf-ocr-pipeline` 的 install.py 部署）：

| 环境 | 用途 |
|---|---|
| `~/.workbuddy/binaries/python/envs/default` | RapidOCR（本技能脚本的运行环境） |
| `D:/ai-ocr/venv` | PaddleOCR Server（可选） |
| `D:/ai-ocr/venv_ds` | DeepSeek-OCR（可选，本技能提供修复脚本） |

```bash
# 验证环境
"C:/Users/G1381/.workbuddy/binaries/python/envs/default/Scripts/python.exe" \
  "C:/Users/G1381/.workbuddy/skills/pdf-ocr-boost_diy/scripts/ocr_env_probe.py"
```

## 快速开始

**场景 1：OCR 结果版面错乱（双栏检测失效）**

```bash
# 1. 标准 OCR（拿坐标产物）
"$PY" .../pdf-ocr-pipeline/scripts/pipeline.py "输入.pdf" -o "_work" --engine rapid --dpi 300

# 2. 坐标重建
"$PY" .../pdf-ocr-boost_diy/scripts/rebuild_columns.py \
  --ocr-dir "_work/work/ocr" --out "重建.txt" --split-x 1050 --y-tol 40
```

**场景 2：引擎怎么选** → 查 `references/engine_benchmarks.md` 选择矩阵。
简记：规整大字 → rapid；表格复杂 → paddle；少量关键页 → DeepSeek-OCR。

**场景 3：DeepSeek-OCR 报错**

```bash
"$PY" .../pdf-ocr-boost_diy/scripts/fix_ds_ocr_env.py --check       # 诊断
"$PY" .../pdf-ocr-boost_diy/scripts/fix_ds_ocr_env.py --fix         # 补缺依赖
# 若报 LlamaFlashAttention2 ImportError（transformers 版本冲突）:
"$PY" .../pdf-ocr-boost_diy/scripts/fix_ds_ocr_env.py --fix-transformers
```

## 参数说明（rebuild_columns.py）

| 参数 | 默认 | 说明 |
|---|---|---|
| `--split-x` | 1050 | 双栏中缝 x。300DPI A4 图宽 2292，中缝约在 1/2 处；可通过查看 items box 分布调整 |
| `--y-tol` | 40 | 行聚类容差。**勿 <30**：OCR 常把英文首字母单独成框 |
| `--page-range` | 空 | 只重建指定页，如 `1-3` |

## 常见问题

**Q1：重建后相邻两行内容还是混在一起？**
行高小于 `--y-tol` 时相邻词条会被聚类合并。本脚本只保证栏内阅读顺序；合并行的拆分需按内容语义在下游处理（词条场景见 `med-term-extractor_diy` 的拉丁簇状态机）。

**Q2：三栏或多栏排版怎么办？**
当前脚本固定双栏。三栏需扩展 `--split-x` 为多个切割点（如 `--split-x "700,1400"`），栏序按 x 排序输出。可自行改造或反馈补充。

**Q3：DeepSeek-OCR 降级 transformers 有风险吗？**
有。`--fix-transformers` 会改写 venv_ds 的 transformers 版本（4.45.2），可能影响该环境其他依赖。执行后须重跑验证；仅当 `--check` 确认是 LlamaFlashAttention2 冲突时才用。

## 局限性

- 坐标重建面向**词典/正文类版面**；复杂图文混排、跨栏图片、艺术字仍需人工
- 引擎基准为 i5-1340P 纯 CPU 实测，换硬件后速度数据仅作参考（精度结论不变）
- DeepSeek-OCR 的 transformers 兼容问题截至 2026-08 未最终解决（已定位根因，降级方案待验证）
