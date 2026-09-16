# -*- coding: utf-8 -*-
"""OCR 坐标级双栏/多栏版面重建
当 pdf-ocr-pipeline 双栏检测失效(two_column=false)导致版面错乱时,
基于 OCR items 的 box 坐标重建正确阅读顺序。

算法:
  1. 按 box 中心 x 与 --split-x 分左右栏
  2. 栏内按 y 聚类成行(y_tol), 行内按 x 排序拼接
  3. 左栏从上到下 → 右栏从上到下, 逐页输出
不依赖 pipeline 的版面结构化, 只消费 work/ocr/page_XXX.ocr.json。

用法:
  python rebuild_columns.py --ocr-dir <work/ocr目录> --out <输出txt> \
      [--split-x 1050] [--img-w 2292] [--y-tol 40] [--page-range 1-3]
"""
import json, os, re, argparse

def center(box):
    return sum(p[0] for p in box) / 4, sum(p[1] for p in box) / 4

def cluster_lines(items, y_tol=40):
    """按 y 聚类成行, 返回行文本列表"""
    items = sorted(items, key=lambda t: (t[0], t[1]))
    lines, cur, cur_y = [], [], None
    for cy, cx, text in items:
        if cur_y is None or abs(cy - cur_y) <= y_tol:
            cur.append((cx, text))
            cur_y = cy if cur_y is None else (cur_y + cy) / 2
        else:
            lines.append(cur)
            cur = [(cx, text)]
            cur_y = cy
    if cur:
        lines.append(cur)
    out = []
    for ln in lines:
        ln.sort(key=lambda t: t[0])
        out.append(' '.join(t[1] for t in ln))
    return out

def main():
    ap = argparse.ArgumentParser(description='OCR坐标级双栏版面重建')
    ap.add_argument('--ocr-dir', required=True, help='pdf-ocr-pipeline 的 work/ocr 目录')
    ap.add_argument('--out', required=True, help='输出文件路径')
    ap.add_argument('--split-x', type=float, default=1050.0, help='双栏中缝 x (默认1050; 300DPI A4 图宽2292)')
    ap.add_argument('--img-w', type=float, default=2292.0, help='页面渲染宽度px')
    ap.add_argument('--y-tol', type=float, default=40.0, help='行聚类 y 容差 (勿<30, 会拆散英文首字母)')
    ap.add_argument('--page-range', default='', help='页码范围 如 1-3')
    ap.add_argument('--dump-lines', action='store_true', help='同时输出行级坐标(调试用)')
    args = ap.parse_args()

    pg_min = pg_max = None
    if args.page_range:
        m = re.match(r'(\d+)-(\d+)', args.page_range)
        if m:
            pg_min, pg_max = int(m.group(1)), int(m.group(2))

    files = sorted(f for f in os.listdir(args.ocr_dir) if re.match(r'page_\d+\.ocr\.json$', f))
    out_lines = []
    for fn in files:
        pg = int(re.search(r'(\d+)', fn).group(1))
        if pg_min is not None and not (pg_min <= pg <= (pg_max or pg_min)):
            continue
        d = json.load(open(os.path.join(args.ocr_dir, fn), encoding='utf-8'))
        items = []
        for it in d['items']:
            cx, cy = center(it['box'])
            items.append((cy, cx, it['text']))
        left = [t for t in items if t[1] < args.split_x]
        right = [t for t in items if t[1] >= args.split_x]
        out_lines.append(f'===== 第{pg}页 左栏 =====')
        for l in cluster_lines(left, args.y_tol):
            out_lines.append(l)
        out_lines.append(f'===== 第{pg}页 右栏 =====')
        for l in cluster_lines(right, args.y_tol):
            out_lines.append(l)

    with open(args.out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines) + '\n')
    print(f'重建完成: {len(files)} 页 -> {args.out}')
    print('注意: 相邻行被聚类合并的情况(表格行高<y_tol)需要下游按内容语义再拆; 本脚本只保证栏内阅读顺序')

if __name__ == '__main__':
    main()
