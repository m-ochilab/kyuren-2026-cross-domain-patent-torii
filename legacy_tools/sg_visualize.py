"""
鎌田麻衣子修士論文 再現実験 v3 — 可視化・分析（キャッシュ利用）
前回のラベルキャッシュを再利用し、グラフ品質を向上させる
"""

# ── openpyxlパッチ ────────────────────────────────────────────────────────────
import openpyxl.descriptors.serialisable as _s
_orig_ft = _s.Serialisable.from_tree.__func__
@classmethod
def _safe_from_tree(cls, node):
    try:
        return _orig_ft(cls, node)
    except TypeError:
        import inspect
        valid = set(inspect.signature(cls.__init__).parameters) - {'self'}
        return cls(**{k: v for k, v in node.attrib.items() if k in valid})
_s.Serialisable.from_tree = _safe_from_tree

import os, re, json, math, time, warnings
from collections import defaultdict
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

warnings.filterwarnings('ignore')

# ── 日本語フォント設定 ────────────────────────────────────────────────────────
_jp = [f.name for f in fm.fontManager.ttflist if 'Hiragino Sans' in f.name]
plt.rcParams['font.family'] = _jp[0] if _jp else 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# ── 設定 ──────────────────────────────────────────────────────────────────────
DATA_DIR   = "/Users/h-torii4649/Downloads"
OUT_DIR    = "/Users/h-torii4649/Downloads/sotsuron_latex_set/results"
CACHE_PATH = os.path.join(OUT_DIR, "labels_cache.json")
MIN_CLUSTER_SIZE = 100   # 100件未満のクラスタは「その他」扱い

SG_FILES = [
    "SG001.xlsx", "SG002 (1).xlsx", "SG003.xlsx", "SG004.xlsx",
    "SG006.xlsx", "SG007.xlsx", "SG008.xlsx", "SG009.xlsx",
    "SG010.xlsx", "SG011.xlsx", "SG012.xlsx", "SG013.xlsx",
    "SG014.xlsx", "SG015.xlsx", "SG016.xlsx", "SG017.xlsx",
    "SG018.xlsx", "SG019.xlsx", "SG020.xlsx", "SG021.xlsx",
    "SG022.xlsx", "SG023.xlsx", "SG024.xlsx",
]

os.makedirs(OUT_DIR, exist_ok=True)

# ── ユーティリティ ────────────────────────────────────────────────────────────
def normalize_applicant(name):
    if not name or str(name) == 'nan':
        return "UNKNOWN"
    name = str(name).upper().strip()
    name = re.sub(r'\s+(LTD\.?|INC\.?|CORP\.?|CO\.?|LLC|GMBH|AG|SA|NV|BV|SE|SPA|PLC|KK|KG|AS|AB|OY|PTY|PRIVATE|LIMITED|INCORPORATED|CORPORATION|COMPANY)\b\.?\s*$', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    for key, val in [
        ('HITACHI', 'Hitachi'), ('SIEMENS', 'Siemens'),
        ('MITSUBISHI ELECTRIC', 'Mitsubishi Electric'),
        ('MITSUBISHI DENKI', 'Mitsubishi Electric'),
        ('GENERAL ELECTRIC', 'GE'), ('STATE GRID', 'State Grid'),
        ('CHINA ELECTRIC POWER', 'China Elec Power'), ('ABB', 'ABB'),
        ('SCHNEIDER', 'Schneider'), ('TOSHIBA', 'Toshiba'),
        ('PANASONIC', 'Panasonic'), ('SHARP', 'Sharp'),
        ('SAMSUNG', 'Samsung'), ('LG ELECTRONICS', 'LG Electronics'),
        ('SONY', 'Sony'), ('NEC', 'NEC'), ('FUJITSU', 'Fujitsu'),
        ('MICROSOFT', 'Microsoft'), ('APPLE', 'Apple'),
        ('GOOGLE', 'Google'), ('AMAZON', 'Amazon'),
        ('FORD', 'Ford'), ('NISSAN', 'Nissan'), ('TOYOTA', 'Toyota'),
        ('HONDA', 'Honda'), ('INTEL', 'Intel'), ('BOSCH', 'Bosch'),
        ('PHILIPS', 'Philips'), ('HONEYWELL', 'Honeywell'),
    ]:
        if key in name:
            return val
    return name.title()[:50]


# ── データ再読み込み（タイトル込み） ──────────────────────────────────────────
def load_xlsx_with_title(path):
    df = pd.read_excel(
        path, sheet_name=1, header=None, skiprows=2,
        usecols=[1, 2, 8, 13, 16, 26, 27],  # B,C,I(title),N,Q,AA,AB
    )
    df.columns = ['pub_id', 'date', 'title', 'family_id', 'applicant', 'bwd_cnt', 'bwd_cit']
    main_mask = df['pub_id'].notna()
    df['pub_id_fill']    = df['pub_id'].where(main_mask).ffill()
    df['applicant_fill'] = df['applicant'].where(main_mask).ffill()
    df['family_fill']    = df['family_id'].where(main_mask).ffill()
    df['title_fill']     = df['title'].where(main_mask).ffill()
    df['year_fill']      = pd.to_datetime(df['date'], errors='coerce').dt.year.where(main_mask).ffill()

    main_df = df[main_mask][['pub_id','year_fill','applicant_fill','family_fill','title_fill']].copy()
    main_df.columns = ['pub_id','year','applicant','family_id','title']
    main_df = main_df.dropna(subset=['pub_id'])

    cit_df = df[df['bwd_cit'].notna()][['pub_id_fill','bwd_cit']].copy()
    cit_df.columns = ['pub_id','cited_id']
    cit_df = cit_df.dropna()

    return main_df, cit_df


def load_all_data():
    patents  = {}
    all_cits = []
    seen_sz  = set()
    for fname in SG_FILES:
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            continue
        sz = os.path.getsize(path)
        if sz in seen_sz:
            continue
        seen_sz.add(sz)
        t0 = time.time()
        main_df, cit_df = load_xlsx_with_title(path)
        new = 0
        for _, row in main_df.iterrows():
            pid = str(row['pub_id']).strip()
            if pid and pid not in patents:
                patents[pid] = {
                    'year':      int(row['year']) if pd.notna(row['year']) else None,
                    'applicant': normalize_applicant(row['applicant']),
                    'family_id': str(row['family_id']) if pd.notna(row['family_id']) else None,
                    'title':     str(row['title']) if pd.notna(row['title']) else '',
                }
                new += 1
        for _, row in cit_df.iterrows():
            all_cits.append((str(row['pub_id']).strip(), str(row['cited_id']).strip()))
        print(f"  {fname}: +{new} ({len(patents)} total) {time.time()-t0:.1f}s")

    pub_set = set(patents.keys())
    edges = [(s, d) for s, d in all_cits if s in pub_set and d in pub_set]
    return patents, edges


# ── クラスタラベル読み込み＋フィルタリング ────────────────────────────────────
def load_labels_and_filter(patents):
    """キャッシュからラベルを読み込み、小クラスタを除去して主要クラスタのみ残す"""
    print(f"  キャッシュ読み込み: {CACHE_PATH}")
    with open(CACHE_PATH) as f:
        raw_labels = json.load(f)

    # メインクラスタ（L1）ごとの件数を集計
    mc_counts = defaultdict(int)
    for pid, label in raw_labels.items():
        mc = label.split('-')[0]
        mc_counts[mc] += 1

    # MIN_CLUSTER_SIZE 以上のメインクラスタのみ採用
    valid_mcs = {mc for mc, cnt in mc_counts.items() if cnt >= MIN_CLUSTER_SIZE}
    print(f"  有効メインクラスタ数（≥{MIN_CLUSTER_SIZE}件）: {len(valid_mcs)}")

    # 有効クラスタに属する特許のみフィルタ
    filtered = {}
    for pid, label in raw_labels.items():
        if pid in patents:
            mc = label.split('-')[0]
            if mc in valid_mcs:
                filtered[pid] = mc   # ← メインクラスタIDを使用

    print(f"  有効クラスタに含まれる特許: {len(filtered):,} / {len(raw_labels):,}")
    return filtered, dict(mc_counts)


# ── キーワード抽出 ────────────────────────────────────────────────────────────
STOP_WORDS = {
    'the','a','an','of','for','in','to','and','or','with','by','on','is','are',
    'at','from','as','be','this','that','it','its','using','system','method',
    'device','apparatus','based','control','power','management','network','grid',
    'smart','energy','electric','data','signal','circuit','unit','module','mode',
    'battery','storage','charging','supply','voltage','output','input','user',
    'load','high','low','time','value','first','second','type','number','node',
}


def extract_keywords(titles, top_n=8):
    from collections import Counter
    wc = Counter()
    for t in titles:
        for w in re.findall(r'[a-z]{4,}', str(t).lower()):
            if w not in STOP_WORDS:
                wc[w] += 1
    return [w for w, _ in wc.most_common(top_n)]


def make_cluster_info(patents, mc_labels, mc_counts):
    """クラスタ番号 → {size, keywords, members} を返す"""
    mc_titles = defaultdict(list)
    for pid, mc in mc_labels.items():
        t = patents.get(pid, {}).get('title', '')
        if t:
            mc_titles[mc].append(t)

    info = {}
    for mc in set(mc_labels.values()):
        info[mc] = {
            'size':     mc_counts.get(mc, 0),
            'keywords': extract_keywords(mc_titles[mc]),
            'members':  [],
        }
    return info


# ── 特化係数 CS ───────────────────────────────────────────────────────────────
def compute_cs(patents, mc_labels):
    comp_mc = defaultdict(lambda: defaultdict(int))
    mc_tot  = defaultdict(int)
    grand   = 0
    for pid, mc in mc_labels.items():
        comp = patents[pid]['applicant']
        comp_mc[comp][mc] += 1
        mc_tot[mc]        += 1
        grand             += 1

    cs = {}
    for comp, mcs in comp_mc.items():
        n_comp = sum(mcs.values())
        for mc, cnt in mcs.items():
            if n_comp > 0 and mc_tot[mc] > 0:
                cs[(comp, mc)] = (cnt / n_comp) / (mc_tot[mc] / grand)
    return cs, dict(comp_mc), dict(mc_tot)


# ── パテントスペース ──────────────────────────────────────────────────────────
def build_biz_space(cs):
    cc = defaultdict(set)
    for (comp, mc), v in cs.items():
        if v > 1:
            cc[mc].add(comp)
    clusters = list(cc.keys())
    phi = {}
    for i in range(len(clusters)):
        for j in range(i+1, len(clusters)):
            ci, cj = clusters[i], clusters[j]
            shared = len(cc[ci] & cc[cj])
            denom  = math.sqrt(len(cc[ci]) * len(cc[cj]))
            if denom > 0 and shared > 0:
                p = shared / denom
                phi[(ci, cj)] = phi[(cj, ci)] = p
    return phi, dict(cc)


def build_tech_space(patents, mc_labels, edges):
    cit = defaultdict(int)
    mc_set = set(mc_labels.values())
    for src, dst in edges:
        sc = mc_labels.get(src)
        dc = mc_labels.get(dst)
        if sc and dc and sc != dc and sc in mc_set and dc in mc_set:
            cit[(sc, dc)] += 1
            cit[(dc, sc)] += 1
    return dict(cit)


def pagerank_dict(weight_dict, nodes):
    G = nx.Graph()
    G.add_nodes_from(nodes)
    for (s, d), w in weight_dict.items():
        if s in G and d in G and s != d:
            if G.has_edge(s, d):
                G[s][d]['weight'] += w
            else:
                G.add_edge(s, d, weight=w)
    if G.number_of_edges() == 0:
        return {n: 1/len(nodes) for n in nodes}
    return nx.pagerank(G, weight='weight')


# ── 企業メトリクス ────────────────────────────────────────────────────────────
def compute_metrics(cs, comp_mc, biz_phi, biz_pr, tech_pr, tech_cit):
    total_tech = sum(tech_cit.values()) or 1
    tech_l = {pair: v/total_tech for pair, v in tech_cit.items()}
    results = {}
    for comp, mc_cnts in comp_mc.items():
        total = sum(mc_cnts.values())
        if total < 3:
            continue
        mcs = list(mc_cnts.keys())
        bc  = sum(biz_pr.get(m, 0)*n for m, n in mc_cnts.items()) / total
        tc  = sum(tech_pr.get(m, 0)*n for m, n in mc_cnts.items()) / total
        bphi, tl = [], []
        for i in range(len(mcs)):
            for j in range(i+1, len(mcs)):
                bphi.append(biz_phi.get((mcs[i],mcs[j]), 0.0))
                tl.append(tech_l.get((mcs[i],mcs[j]), 0.0))
        results[comp] = {
            'biz_centrality':  bc,
            'tech_centrality': tc,
            'biz_density':     float(np.mean(bphi)) if bphi else 0.0,
            'tech_density':    float(np.mean(tl))   if tl   else 0.0,
            'total_patents':   total,
            'n_clusters':      len(mcs),
        }
    return results


# ── 可視化 ────────────────────────────────────────────────────────────────────
CMAP = plt.cm.tab20


def plot_scatter(metrics):
    comps = [c for c, m in metrics.items() if m['total_patents'] >= 10]
    if not comps:
        print("[plot] 散布図: データ不足")
        return
    bc  = np.array([metrics[c]['biz_centrality']  for c in comps])
    tc  = np.array([metrics[c]['tech_centrality'] for c in comps])
    bd  = np.array([metrics[c]['biz_density']     for c in comps])
    td  = np.array([metrics[c]['tech_density']    for c in comps])
    sz  = np.array([metrics[c]['total_patents']   for c in comps])

    top10 = sorted(comps, key=lambda c: metrics[c]['total_patents'], reverse=True)[:10]

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle("図5.4 スマートグリッド関連企業群保有特許の中心性・密度散布図（再現）",
                 fontsize=13, fontweight='bold')

    for ax, xv, yv, xl, yl, sub, col in [
        (axes[0], tc, bc, '技術的中心性', '事業的中心性', '(a) 事業的・技術的中心性', 'steelblue'),
        (axes[1], td, bd, '技術的密度',   '事業的密度',   '(b) 事業的・技術的密度',   'darkorange'),
    ]:
        msz = np.clip(np.log10(sz+1)*20, 5, 200)
        ax.scatter(xv, yv, s=msz, alpha=0.4, c=col, edgecolors='none')
        for c in top10:
            idx = comps.index(c)
            ax.annotate(c, (xv[idx], yv[idx]), fontsize=8,
                        ha='center', va='bottom',
                        xytext=(0, 5), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.7, ec='none'))
        # 平均線
        ax.axhline(np.median(yv), color='gray', lw=0.8, ls='--', alpha=0.5)
        ax.axvline(np.median(xv), color='gray', lw=0.8, ls='--', alpha=0.5)
        ax.set_xlabel(xl, fontsize=11)
        ax.set_ylabel(yl, fontsize=11)
        ax.set_title(sub, fontsize=11)
        ax.grid(True, ls='--', alpha=0.3)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "fig5_4_sg_scatter_v2.png")
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[plot]  {out}")


def plot_network(weight_dict, cluster_info, title, fname, top_n=20, edge_scale=1.0):
    top_cls = sorted(cluster_info.items(), key=lambda x: x[1]['size'], reverse=True)[:top_n]
    top_ids = [c for c, _ in top_cls]
    top_set = set(top_ids)

    G = nx.Graph()
    for mc, info in top_cls:
        kw = ', '.join(info['keywords'][:3]) if info['keywords'] else '(N/A)'
        G.add_node(mc, size=info['size'],
                   label=f"C{mc}\n({info['size']:,}件)\n{kw}")

    vals = [v for (a,b),v in weight_dict.items() if a in top_set and b in top_set and a < b]
    thresh = np.percentile(vals, 30) if vals else 0
    for (a, b), w in weight_dict.items():
        if a in top_set and b in top_set and a < b and w > thresh:
            G.add_edge(a, b, weight=w)

    pos = nx.spring_layout(G, seed=42, weight='weight', k=3.5)
    fig, ax = plt.subplots(figsize=(15, 12))

    node_szs   = [math.sqrt(cluster_info[n]['size']) * 15 for n in G.nodes()]
    node_cols  = [CMAP(i % 20) for i, _ in enumerate(G.nodes())]
    edge_ws    = [G[u][v]['weight'] * edge_scale for u, v in G.edges()]

    nx.draw_networkx_edges(G, pos, width=edge_ws, alpha=0.45, edge_color='#888', ax=ax)
    nx.draw_networkx_nodes(G, pos, node_size=node_szs, node_color=node_cols, alpha=0.88, ax=ax)
    labels = {n: G.nodes[n]['label'] for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=7, ax=ax)

    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.axis('off')
    plt.tight_layout()
    out = os.path.join(OUT_DIR, fname)
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[plot]  {out}")


def plot_phi_dist(biz_phi, comp_mc, mc_labels):
    all_phi = list(biz_phi.values())
    company_phi = []
    for comp, mc_cnts in comp_mc.items():
        mcs = list(mc_cnts.keys())
        for i in range(len(mcs)):
            for j in range(i+1, len(mcs)):
                v = biz_phi.get((mcs[i], mcs[j]), 0.0)
                company_phi.append(v)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("図5.7 クラスタ間近接度φの分布（スマートグリッド・再現）", fontsize=12)

    bins = np.linspace(0, 1, 51)
    axes[0].hist(all_phi, bins=bins, color='steelblue', alpha=0.8, edgecolor='none')
    axes[0].set_xlabel("近接度 φ", fontsize=11)
    axes[0].set_ylabel("頻度", fontsize=11)
    axes[0].set_title("(a) 全クラスタペア間の近接度φの分布", fontsize=10)
    axes[0].grid(True, ls='--', alpha=0.35)

    axes[1].hist(company_phi, bins=bins, color='darkorange', alpha=0.8, edgecolor='none')
    axes[1].set_xlabel("近接度 φ", fontsize=11)
    axes[1].set_ylabel("頻度", fontsize=11)
    axes[1].set_title("(b) 各企業の保有クラスタ間の近接度φの分布", fontsize=10)
    axes[1].grid(True, ls='--', alpha=0.35)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "fig5_7_phi_distribution_v2.png")
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[plot]  {out}")


# ── テーブル出力 ──────────────────────────────────────────────────────────────
def save_table5_1(cluster_info):
    top20 = sorted(cluster_info.items(), key=lambda x: x[1]['size'], reverse=True)[:20]
    lines = [
        "表5.1: スマートグリッド関連特許の主要クラスタ（再現）\n",
        f"{'クラスタ番号':<14}  {'所属特許数':>10}  代表的なキーワード",
        "-" * 90,
    ]
    for mc, info in top20:
        kws = ','.join(info['keywords']) if info['keywords'] else '(N/A)'
        lines.append(f"{mc:<14}  {info['size']:>10}  {kws}")

    # 論文の表と並べて比較
    thesis = [
        (0, 5494, 'substation,fault,module,distribution,monitoring,intelligent'),
        (1, 2733, 'charging,vehicle,electric,power,battery,station,supply,user'),
        (2, 2615, 'consumption,demand,system,management,block,storage,generation'),
        (3, 3881, 'storage,control,management,system,diagram,value,operation'),
        (4, 2272, 'scheduling,control,distribution,wind,storage'),
    ]
    lines += ["\n\n--- 論文との比較（上位5クラスタ） ---",
              f"{'クラスタ':<6}  {'論文件数':>10}  論文キーワード",
              "-" * 80]
    for mc, sz, kws in thesis:
        lines.append(f"{mc:<6}  {sz:>10}  {kws}")

    out = os.path.join(OUT_DIR, "table5_1_sg_clusters_v2.txt")
    with open(out, "w") as f:
        f.write("\n".join(lines))
    print(f"[table] {out}")
    print("\n" + "\n".join(lines[:28]))
    return top20


def save_table_a1(metrics):
    lines = ["表A.1: スマートグリッド関連領域 中心性・密度上位20企業（再現）\n"]
    for key, label in [
        ('biz_centrality',  '事業的中心性'),
        ('tech_centrality', '技術的中心性'),
        ('biz_density',     '事業的密度'),
        ('tech_density',    '技術的密度'),
    ]:
        top = sorted(metrics.items(), key=lambda x: x[1][key], reverse=True)[:20]
        lines += [f"\n  {label} 上位20社:",
                  f"  {'企業名':<50}  {'値':>12}  {'特許数':>8}",
                  "  " + "-" * 75]
        for comp, m in top:
            lines.append(f"  {comp:<50}  {m[key]:>12.6f}  {m['total_patents']:>8}")
    out = os.path.join(OUT_DIR, "table_a1_sg_top20_v2.txt")
    with open(out, "w") as f:
        f.write("\n".join(lines))
    print(f"[table] {out}")
    # コンソール: 事業的中心性上位のみ表示
    print("\n事業的密度 上位15社:")
    top_bd = sorted(metrics.items(), key=lambda x: x[1]['biz_density'], reverse=True)[:15]
    for comp, m in top_bd:
        print(f"  {comp:<42} {m['biz_density']:.4f}  ({m['total_patents']}件)")


# ── メイン ────────────────────────────────────────────────────────────────────
def main():
    print("="*60)
    print("再現実験 v3 (キャッシュ利用・可視化改善)")
    print("="*60)

    # 1. データ読み込み（タイトル込み）
    print("\n[Step 1] 特許データ（タイトル込み）再読み込み...")
    patents, edges = load_all_data()

    # 2. ラベルキャッシュ読み込み + フィルタリング
    print("\n[Step 2] クラスタラベル読み込み...")
    mc_labels, mc_counts_all = load_labels_and_filter(patents)

    # 3. クラスタ情報（キーワード抽出）
    print("\n[Step 3] クラスタキーワード抽出...")
    cluster_info = make_cluster_info(patents, mc_labels, mc_counts_all)
    print(f"  有効クラスタ数: {len(cluster_info)}")
    top5 = sorted(cluster_info.items(), key=lambda x: x[1]['size'], reverse=True)[:5]
    for mc, info in top5:
        print(f"  C{mc}: {info['size']}件 | {','.join(info['keywords'][:5])}")

    # 4. CS計算
    print("\n[Step 4] 特化係数 CS 計算...")
    cs, comp_mc, mc_tot = compute_cs(patents, mc_labels)
    print(f"  企業数: {len(comp_mc):,}, CS>1ペア: {sum(1 for v in cs.values() if v>1):,}")

    # 5. パテントスペース
    print("\n[Step 5] パテントスペース構築...")
    biz_phi, cluster_comps = build_biz_space(cs)
    tech_cit = build_tech_space(patents, mc_labels, edges)
    print(f"  φ>0 ペア: {len(biz_phi)//2:,}, 技術的引用ペア: {len(tech_cit)//2:,}")

    # 6. PageRank
    print("\n[Step 6] PageRank...")
    nodes = list(cluster_info.keys())
    biz_pr  = pagerank_dict(biz_phi, nodes)
    tech_pr = pagerank_dict(tech_cit, nodes)

    # 7. 企業メトリクス
    print("\n[Step 7] 企業メトリクス...")
    metrics = compute_metrics(cs, comp_mc, biz_phi, biz_pr, tech_pr, tech_cit)
    print(f"  評価企業数: {len(metrics):,}")

    # 8. 出力
    print("\n[Step 8] グラフ・表出力...")
    save_table5_1(cluster_info)
    save_table_a1(metrics)
    plot_scatter(metrics)
    plot_network(biz_phi, cluster_info,
                 "図5.1(a) スマートグリッド 事業的パテントスペース\n（企業内クラスタ共起ネットワーク）",
                 "fig5_1a_biz_space_v2.png", edge_scale=8.0)
    plot_network(tech_cit, cluster_info,
                 "図5.1(b) スマートグリッド 技術的パテントスペース\n（クラスタ間引用ネットワーク）",
                 "fig5_1b_tech_space_v2.png", edge_scale=300.0)
    plot_phi_dist(biz_phi, comp_mc, mc_labels)

    print(f"\n出力先: {OUT_DIR}")
    print("完了")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"\n総実行時間: {(time.time()-t0)/60:.1f} 分")
