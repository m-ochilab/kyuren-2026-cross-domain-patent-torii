"""
鎌田麻衣子修士論文 - スマートグリッド再現実験 v2
高速版: pandas + openpyxlパッチ
"""

# ── openpyxlのapplyNumFmtバグをパッチ（必ず最初に） ──────────────────────────
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

# ── ライブラリ ────────────────────────────────────────────────────────────────
import os, re, math, json, time, warnings
from collections import defaultdict
import numpy as np
import pandas as pd
import igraph as ig
import leidenalg
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
warnings.filterwarnings('ignore')

# 日本語フォント（macOS）
jp_fonts = [f.name for f in fm.fontManager.ttflist if 'Hiragino' in f.name or 'Noto' in f.name]
if jp_fonts:
    plt.rcParams['font.family'] = jp_fonts[0]
else:
    plt.rcParams['font.family'] = 'DejaVu Sans'

# ── 設定 ──────────────────────────────────────────────────────────────────────
DATA_DIR   = "/Users/h-torii4649/Downloads"
OUT_DIR    = "/Users/h-torii4649/Downloads/sotsuron_latex_set/results"
LEIDEN_SEED = 42
RECLUSTER_THRESHOLD = 1000

SG_FILES = [
    "SG001.xlsx", "SG002 (1).xlsx", "SG003.xlsx", "SG004.xlsx",
    "SG006.xlsx", "SG007.xlsx",  "SG007-2.xlsx",
    "SG008.xlsx", "SG009.xlsx", "SG010.xlsx", "SG011.xlsx",
    "SG012.xlsx", "SG013.xlsx", "SG014.xlsx", "SG015.xlsx",
    "SG016.xlsx", "SG017.xlsx", "SG018.xlsx", "SG019.xlsx",
    "SG020.xlsx", "SG021.xlsx", "SG022.xlsx", "SG023.xlsx", "SG024.xlsx",
]

os.makedirs(OUT_DIR, exist_ok=True)

# ── Step 1: 全ファイル読み込み ────────────────────────────────────────────────
def normalize_applicant(name: str) -> str:
    if not name or str(name) == 'nan':
        return "UNKNOWN"
    name = str(name).upper().strip()
    name = re.sub(r'\s+(LTD\.?|INC\.?|CORP\.?|CO\.?|LLC|GMBH|AG|SA|NV|BV|SE|SPA|PLC|KK|KG|AS|AB|OY|PTY|SRO|LTDA|SDN BHD|PVT|PRIVATE|LIMITED|INCORPORATED|CORPORATION|COMPANY)\b\.?\s*$', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    mappings = {
        'HITACHI': 'Hitachi', 'SIEMENS': 'Siemens',
        'MITSUBISHI ELECTRIC': 'Mitsubishi Electric', 'MITSUBISHI DENKI': 'Mitsubishi Electric',
        'MITSUBISHI JIDOSHA': 'Mitsubishi Motors', 'GENERAL ELECTRIC': 'GE',
        'ABB': 'ABB', 'SCHNEIDER': 'Schneider', 'TOSHIBA': 'Toshiba',
        'PANASONIC': 'Panasonic', 'SHARP': 'Sharp',
        'SAMSUNG': 'Samsung', 'LG ELECTRONICS': 'LG Electronics',
        'SONY': 'Sony', 'NEC': 'NEC', 'FUJITSU': 'Fujitsu',
        'STATE GRID': 'State Grid', 'CHINA ELECTRIC POWER': 'China Electric Power',
        'MICROSOFT': 'Microsoft', 'APPLE': 'Apple', 'GOOGLE': 'Google',
        'AMAZON': 'Amazon', 'FORD': 'Ford', 'NISSAN': 'Nissan',
        'TOYOTA': 'Toyota', 'HONDA': 'Honda', 'INTEL': 'Intel',
        'QUALCOMM': 'Qualcomm', 'BOSCH': 'Bosch', 'PHILIPS': 'Philips',
        'HONEYWELL': 'Honeywell', 'ABB RES': 'ABB',
    }
    for key, val in mappings.items():
        if key in name:
            return val
    return name.title()[:50]


def load_xlsx_patents(path: str) -> pd.DataFrame:
    """1ファイルを読んで特許DataFrame（pub_id, year, applicant, family_id, citations）を返す"""
    df = pd.read_excel(
        path, sheet_name=1, header=None, skiprows=2,
        usecols=[0, 1, 2, 13, 16, 26, 27],  # A,B,C,N,Q,AA,AB
    )
    df.columns = ['row_no', 'pub_id', 'date', 'family_id', 'applicant', 'bwd_cnt', 'bwd_cit']

    # 行番号でメイン行を判定（A列に数字.があるのがメイン行）
    main_mask = df['pub_id'].notna() & (df['pub_id'].astype(str) != 'nan')
    # 年の抽出
    df['year'] = pd.to_datetime(df['date'], errors='coerce').dt.year

    # pub_id・applicant・family_idを継続行に前方伝搬
    df['pub_id_fill']   = df['pub_id'].where(main_mask).ffill()
    df['applicant_fill'] = df['applicant'].where(main_mask).ffill()
    df['family_fill']    = df['family_id'].where(main_mask).ffill()
    df['year_fill']      = df['year'].where(main_mask).ffill()

    # 引用のある行だけ抽出し、pub_idごとに集約
    cit_rows = df[df['bwd_cit'].notna()][['pub_id_fill', 'bwd_cit']].copy()
    cit_rows.columns = ['pub_id', 'cited_id']
    cit_rows = cit_rows.dropna()

    # メイン行だけ抽出（特許情報）
    main_df = df[main_mask][['pub_id', 'year_fill', 'applicant_fill', 'family_fill']].copy()
    main_df.columns = ['pub_id', 'year', 'applicant', 'family_id']
    main_df = main_df.dropna(subset=['pub_id'])

    return main_df, cit_rows


def load_all_data():
    """全ファイルを読み込み、重複排除して特許dictと引用edgelistを返す"""
    patents    = {}       # pub_id -> {year, applicant, family_id}
    all_cits   = []       # [(src_pub, dst_pub), ...]
    seen_sizes = set()

    for fname in SG_FILES:
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            print(f"  [skip] {fname}")
            continue
        sz = os.path.getsize(path)
        if sz in seen_sizes:
            print(f"  [dup]  {fname} (skipped)")
            continue
        seen_sizes.add(sz)

        t0 = time.time()
        main_df, cit_df = load_xlsx_patents(path)

        new = 0
        for _, row in main_df.iterrows():
            pid = str(row['pub_id']).strip()
            if pid and pid not in patents:
                patents[pid] = {
                    'year':      int(row['year']) if pd.notna(row['year']) else None,
                    'applicant': normalize_applicant(row['applicant']),
                    'family_id': str(row['family_id']) if pd.notna(row['family_id']) else None,
                }
                new += 1

        # 引用エッジを追加
        for _, row in cit_df.iterrows():
            src = str(row['pub_id']).strip()
            dst = str(row['cited_id']).strip()
            if src and dst:
                all_cits.append((src, dst))

        print(f"  [ok]  {fname}: +{new} patents ({len(patents)} total) | {time.time()-t0:.1f}s")

    # 内部引用のみ抽出
    pub_set = set(patents.keys())
    edges = [(s, d) for s, d in all_cits if s in pub_set and d in pub_set]
    print(f"\n  合計ユニーク特許: {len(patents):,}, 内部引用エッジ: {len(edges):,}")
    return patents, edges


# ── Step 2: Leiden クラスタリング ─────────────────────────────────────────────
def leiden_once(pub_ids: list, edges: list, seed: int = LEIDEN_SEED) -> dict:
    if len(pub_ids) <= 1:
        return {p: 0 for p in pub_ids}
    id2i = {p: i for i, p in enumerate(pub_ids)}
    idx_edges = list({(id2i[s], id2i[t]) for s, t in edges if s in id2i and t in id2i})
    g = ig.Graph(n=len(pub_ids), edges=idx_edges, directed=False)
    part = leidenalg.find_partition(g, leidenalg.ModularityVertexPartition,
                                    seed=seed, n_iterations=10)
    return {pub_ids[i]: part.membership[i] for i in range(len(pub_ids))}


def hierarchical_leiden(patents: dict, edges: list) -> dict:
    pubs = list(patents.keys())
    edge_set = list({(min(s,t), max(s,t)) for s, t in edges})  # undirected unique

    print(f"\n[Leiden L1] {len(pubs):,} 特許 ...")
    t0 = time.time()
    l1 = leiden_once(pubs, edge_set)
    print(f"  -> {len(set(l1.values()))} clusters ({time.time()-t0:.1f}s)")

    by_c1 = defaultdict(list)
    for pid, c in l1.items():
        by_c1[c].append(pid)

    edge_by_pub = defaultdict(list)
    for s, t in edge_set:
        edge_by_pub[s].append(t)
        edge_by_pub[t].append(s)

    labels = {}
    for c1, members in by_c1.items():
        if len(members) <= RECLUSTER_THRESHOLD:
            for p in members:
                labels[p] = str(c1)
            continue
        mem_set = set(members)
        sub_edges = [(s, t) for s in members for t in edge_by_pub[s] if t in mem_set]
        print(f"  [L2] cluster {c1}: {len(members)} members ...")
        l2 = leiden_once(members, sub_edges, seed=LEIDEN_SEED + c1)
        by_c2 = defaultdict(list)
        for p, c in l2.items():
            by_c2[c].append(p)
        for c2, sub in by_c2.items():
            if len(sub) <= RECLUSTER_THRESHOLD:
                for p in sub:
                    labels[p] = f"{c1}-{c2}"
                continue
            sub_set = set(sub)
            sub2_edges = [(s, t) for s in sub for t in edge_by_pub[s] if t in sub_set]
            print(f"    [L3] cluster {c1}-{c2}: {len(sub)} members ...")
            l3 = leiden_once(sub, sub2_edges, seed=LEIDEN_SEED + c1 + c2)
            for p, c3 in l3.items():
                labels[p] = f"{c1}-{c2}-{c3}"

    # 引用なし孤立ノード
    for p in pubs:
        if p not in labels:
            labels[p] = l1.get(p, "99")

    n_total = len(set(labels.values()))
    n_main  = len(set(l.split('-')[0] for l in labels.values()))
    print(f"  総クラスタ数: {n_total:,} (メインクラスタ: {n_main})")
    return labels


# ── Step 3: 特化係数 CS ───────────────────────────────────────────────────────
def compute_cs(patents: dict, labels: dict):
    comp_mc = defaultdict(lambda: defaultdict(int))   # comp -> mc -> count
    mc_total = defaultdict(int)
    grand_total = 0

    for pid, pat in patents.items():
        mc = labels.get(pid, '99').split('-')[0]
        comp = pat['applicant']
        comp_mc[comp][mc] += 1
        mc_total[mc] += 1
        grand_total += 1

    cs = {}   # (comp, mc) -> CS
    for comp, mc_counts in comp_mc.items():
        n_comp = sum(mc_counts.values())
        for mc, cnt in mc_counts.items():
            if n_comp > 0 and mc_total[mc] > 0 and grand_total > 0:
                cs[(comp, mc)] = (cnt / n_comp) / (mc_total[mc] / grand_total)

    return cs, dict(comp_mc), dict(mc_total)


# ── Step 4: パテントスペース構築 ─────────────────────────────────────────────
def build_biz_space(cs: dict):
    """φ(i,j) = co-occurrence / sqrt(|comp_i| * |comp_j|)"""
    cluster_comps = defaultdict(set)
    for (comp, mc), val in cs.items():
        if val > 1:
            cluster_comps[mc].add(comp)

    clusters = list(cluster_comps.keys())
    phi = {}
    for i in range(len(clusters)):
        for j in range(i+1, len(clusters)):
            ci, cj = clusters[i], clusters[j]
            shared = len(cluster_comps[ci] & cluster_comps[cj])
            denom  = math.sqrt(len(cluster_comps[ci]) * len(cluster_comps[cj]))
            if denom > 0 and shared > 0:
                p = shared / denom
                phi[(ci, cj)] = phi[(cj, ci)] = p

    return phi, dict(cluster_comps)


def build_tech_space(patents: dict, labels: dict, edges: list) -> dict:
    """技術的近接度: クラスタ間引用数"""
    cit = defaultdict(int)
    for src, dst in edges:
        sc = labels.get(src, '').split('-')[0]
        dc = labels.get(dst, '').split('-')[0]
        if sc and dc and sc != dc:
            cit[(sc, dc)] += 1
            cit[(dc, sc)] += 1
    return dict(cit)


# ── Step 5: PageRank ──────────────────────────────────────────────────────────
def pagerank_from_dict(weight_dict: dict, nodes: list) -> dict:
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


# ── Step 6: 企業メトリクス ────────────────────────────────────────────────────
def compute_metrics(cs, comp_mc, biz_phi, biz_pr, tech_pr, tech_cit):
    total_tech = sum(tech_cit.values()) or 1
    tech_l = {pair: v/total_tech for pair, v in tech_cit.items()}

    results = {}
    for (comp, mc) in cs:
        pass  # just to get all companies

    all_comps = set(comp for comp, _ in cs)
    for comp in all_comps:
        mc_cnts = comp_mc.get(comp, {})
        if not mc_cnts:
            continue
        total = sum(mc_cnts.values())
        if total == 0:
            continue

        # 中心性（特許数加重平均PageRank）
        bc = sum(biz_pr.get(mc, 0)*n for mc, n in mc_cnts.items()) / total
        tc = sum(tech_pr.get(mc, 0)*n for mc, n in mc_cnts.items()) / total

        # 密度（クラスタペア間の平均近接度）
        mcs = list(mc_cnts.keys())
        bphi, tl = [], []
        for i in range(len(mcs)):
            for j in range(i+1, len(mcs)):
                bphi.append(biz_phi.get((mcs[i], mcs[j]), 0.0))
                tl.append(tech_l.get((mcs[i], mcs[j]), 0.0))

        results[comp] = {
            'biz_centrality':  bc,
            'tech_centrality': tc,
            'biz_density':     float(np.mean(bphi)) if bphi else 0.0,
            'tech_density':    float(np.mean(tl))   if tl   else 0.0,
            'total_patents':   total,
            'n_clusters':      len(mcs),
        }

    return results


# ── Step 7: テーブル出力 ──────────────────────────────────────────────────────
def make_cluster_summary(patents: dict, labels: dict) -> dict:
    """メインクラスタ番号 -> {size, words} の辞書を返す"""
    mc_data = defaultdict(lambda: {'size': 0, 'words': defaultdict(int)})
    stop = {'the','a','an','of','for','in','to','and','or','with','by','on',
            'is','are','at','from','as','be','this','that','it','its','using',
            'system','method','device','apparatus','based','control','power',
            'management','network','grid','smart','energy','electric','data'}
    for pid, label in labels.items():
        mc = label.split('-')[0]
        mc_data[mc]['size'] += 1
        title = patents.get(pid, {}).get('title', '')
        if title:
            for w in re.findall(r'[a-z]{4,}', title.lower()):
                if w not in stop:
                    mc_data[mc]['words'][w] += 1
    return dict(mc_data)


def save_table5_1(mc_summary: dict):
    top20 = sorted(mc_summary.items(), key=lambda x: x[1]['size'], reverse=True)[:20]
    lines = ["表5.1: スマートグリッド関連特許の主要クラスタ（再現）\n",
             f"{'クラスタ':^8}  {'所属特許数':>10}  代表的なキーワード",
             "-"*80]
    for mc, info in top20:
        kws = ','.join(w for w, _ in sorted(info['words'].items(), key=lambda x:-x[1])[:8])
        lines.append(f"{mc:<8}  {info['size']:>10}  {kws}")

    out = os.path.join(OUT_DIR, "table5_1_sg_clusters.txt")
    with open(out, "w") as f:
        f.write("\n".join(lines))
    print(f"[table] {out}")

    # コンソール表示
    print("\n" + "\n".join(lines[:25]))
    return top20


def save_table_a1(metrics: dict):
    lines = ["表A.1: スマートグリッド関連領域 中心性・密度上位20企業（再現）\n"]
    for key, label in [('biz_centrality','事業的中心性'),
                        ('tech_centrality','技術的中心性'),
                        ('biz_density','事業的密度'),
                        ('tech_density','技術的密度')]:
        top = sorted(metrics.items(), key=lambda x: x[1][key], reverse=True)[:20]
        lines.append(f"\n  {label}:")
        lines.append(f"  {'企業名':<50}  {'値':>12}")
        lines.append("  " + "-"*65)
        for comp, m in top:
            lines.append(f"  {comp:<50}  {m[key]:>12.6f}  ({m['total_patents']}件)")
    out = os.path.join(OUT_DIR, "table_a1_sg_top20.txt")
    with open(out, "w") as f:
        f.write("\n".join(lines))
    print(f"[table] {out}")


# ── Step 8: グラフ出力 ────────────────────────────────────────────────────────
def plot_scatter(metrics: dict):
    comps  = [c for c, m in metrics.items() if m['total_patents'] >= 5]
    if not comps:
        return
    bc  = [metrics[c]['biz_centrality']  for c in comps]
    tc  = [metrics[c]['tech_centrality'] for c in comps]
    bd  = [metrics[c]['biz_density']     for c in comps]
    td  = [metrics[c]['tech_density']    for c in comps]
    sz  = [metrics[c]['total_patents']   for c in comps]

    top10 = sorted(comps, key=lambda c: metrics[c]['total_patents'], reverse=True)[:10]

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle("図5.4 スマートグリッド関連企業群保有特許の中心性・密度散布図（再現）",
                 fontsize=13, fontweight='bold')

    for ax, xvals, yvals, xlabel, ylabel, subtitle, color in [
        (axes[0], tc, bc, '技術的中心性', '事業的中心性', '(a) 中心性', 'steelblue'),
        (axes[1], td, bd, '技術的密度',   '事業的密度',   '(b) 密度',   'darkorange'),
    ]:
        marker_sz = [max(10, math.log10(max(s,1)) * 30) for s in sz]
        ax.scatter(xvals, yvals, s=marker_sz, alpha=0.45, c=color, edgecolors='none')
        for c in top10:
            xi = comps.index(c)
            ax.annotate(c, (xvals[xi], yvals[xi]), fontsize=7, ha='center',
                        xytext=(0, 5), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.6, ec='none'))
        ax.set_xlabel(xlabel, fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(subtitle, fontsize=11)
        ax.grid(True, linestyle='--', alpha=0.35)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "fig5_4_sg_scatter.png")
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[plot]  {out}")


def plot_biz_network(biz_phi: dict, mc_summary: dict):
    top20 = sorted(mc_summary.items(), key=lambda x: x[1]['size'], reverse=True)[:20]
    top_ids = [mc for mc, _ in top20]
    top_set = set(top_ids)

    G = nx.Graph()
    for mc, info in top20:
        kws = ','.join(w for w, _ in sorted(info['words'].items(), key=lambda x:-x[1])[:3])
        G.add_node(mc, size=info['size'], label=f"C{mc}\n{kws}")

    for (a, b), phi in biz_phi.items():
        if a in top_set and b in top_set and phi > 0.03:
            G.add_edge(a, b, weight=phi)

    if G.number_of_nodes() == 0:
        return

    pos = nx.spring_layout(G, seed=42, weight='weight', k=3.0)
    fig, ax = plt.subplots(figsize=(14, 11))

    node_sizes = [mc_summary[n]['size'] / 80 for n in G.nodes()]
    cmap = plt.cm.tab20
    node_colors = [cmap(i % 20) for i, _ in enumerate(G.nodes())]

    edge_widths = [G[u][v]['weight'] * 8 for u, v in G.edges()]
    nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.45, edge_color='#999', ax=ax)
    nx.draw_networkx_nodes(G, pos, node_size=[s*3 for s in node_sizes],
                           node_color=node_colors, alpha=0.85, ax=ax)

    labels_map = {n: G.nodes[n]['label'] for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels_map, font_size=7, ax=ax)

    ax.set_title("図5.1(a) スマートグリッド: 事業的パテントスペース\n"
                 "（企業内クラスタ共起ネットワーク）", fontsize=12)
    ax.axis('off')
    plt.tight_layout()
    out = os.path.join(OUT_DIR, "fig5_1a_biz_space.png")
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[plot]  {out}")


def plot_tech_network(tech_cit: dict, mc_summary: dict):
    top20 = sorted(mc_summary.items(), key=lambda x: x[1]['size'], reverse=True)[:20]
    top_ids = [mc for mc, _ in top20]
    top_set = set(top_ids)

    G = nx.Graph()
    for mc, info in top20:
        kws = ','.join(w for w, _ in sorted(info['words'].items(), key=lambda x:-x[1])[:3])
        G.add_node(mc, size=info['size'], label=f"C{mc}\n{kws}")

    total_cit = sum(tech_cit.values()) or 1
    for (a, b), cnt in tech_cit.items():
        if a in top_set and b in top_set and a < b:
            w = cnt / total_cit
            if w > 0.001:
                G.add_edge(a, b, weight=w)

    pos = nx.spring_layout(G, seed=42, weight='weight', k=3.0)
    fig, ax = plt.subplots(figsize=(14, 11))

    node_sizes = [mc_summary[n]['size'] / 80 for n in G.nodes()]
    cmap = plt.cm.tab20
    node_colors = [cmap(i % 20) for i, _ in enumerate(G.nodes())]

    edge_widths = [G[u][v]['weight'] * 500 for u, v in G.edges()]
    nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.45, edge_color='#999', ax=ax)
    nx.draw_networkx_nodes(G, pos, node_size=[s*3 for s in node_sizes],
                           node_color=node_colors, alpha=0.85, ax=ax)
    labels_map = {n: G.nodes[n]['label'] for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels_map, font_size=7, ax=ax)

    ax.set_title("図5.1(b) スマートグリッド: 技術的パテントスペース\n"
                 "（クラスタ間引用ネットワーク）", fontsize=12)
    ax.axis('off')
    plt.tight_layout()
    out = os.path.join(OUT_DIR, "fig5_1b_tech_space.png")
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[plot]  {out}")


def plot_phi_distribution(biz_phi: dict, comp_mc: dict, cs: dict, mc_summary: dict):
    """図5.7: 全クラスタペアおよび企業の新規進出領域との近接度分布"""
    all_phi = list(biz_phi.values())
    if not all_phi:
        return

    # 論文では「CS>1の注力分野と新規注力分野の近接度」だが
    # ここでは「各企業の保有クラスタ間の近接度」を使用
    company_phi = []
    for comp, mc_cnts in comp_mc.items():
        mcs = list(mc_cnts.keys())
        for i in range(len(mcs)):
            for j in range(i+1, len(mcs)):
                v = biz_phi.get((mcs[i], mcs[j]), 0.0)
                company_phi.append(v)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("図5.7 クラスタ間近接度φの分布（スマートグリッド・再現）", fontsize=12)

    axes[0].hist(all_phi, bins=50, color='steelblue', alpha=0.8, edgecolor='none')
    axes[0].set_xlabel("近接度 φ", fontsize=11)
    axes[0].set_ylabel("頻度", fontsize=11)
    axes[0].set_title("(a) 全クラスタペア間の近接度φの分布", fontsize=10)
    axes[0].grid(True, linestyle='--', alpha=0.35)

    axes[1].hist(company_phi, bins=50, color='darkorange', alpha=0.8, edgecolor='none')
    axes[1].set_xlabel("近接度 φ", fontsize=11)
    axes[1].set_ylabel("頻度", fontsize=11)
    axes[1].set_title("(b) 各企業の保有クラスタ間の近接度φの分布", fontsize=10)
    axes[1].grid(True, linestyle='--', alpha=0.35)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "fig5_7_phi_distribution.png")
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[plot]  {out}")


# ── メインパイプライン ─────────────────────────────────────────────────────────
def main():
    print("="*60)
    print("スマートグリッド 事業的パテントスペース 再現実験 v2")
    print("="*60)

    # 1. データ読み込み
    print("\n[Step 1] 全SGファイル読み込み...")
    patents, edges = load_all_data()

    if len(patents) == 0:
        print("ERROR: 特許データが読み込めませんでした")
        return

    # 2. Leiden クラスタリング
    print("\n[Step 2] Leiden クラスタリング...")
    labels = hierarchical_leiden(patents, edges)

    # キャッシュ保存
    cache = os.path.join(OUT_DIR, "labels_cache.json")
    with open(cache, "w") as f:
        json.dump(labels, f)
    print(f"  キャッシュ保存: {cache}")

    # 3. クラスタサマリー
    print("\n[Step 3] クラスタサマリー生成...")
    mc_summary = make_cluster_summary(patents, labels)
    print(f"  メインクラスタ数: {len(mc_summary)}")

    # 4. 特化係数 CS
    print("\n[Step 4] 特化係数 (CS) 計算...")
    cs, comp_mc, mc_total = compute_cs(patents, labels)
    n_comps = len(set(c for c, _ in cs))
    print(f"  企業数: {n_comps:,}, CS>1 ペア数: {sum(1 for v in cs.values() if v>1):,}")

    # 5. パテントスペース
    print("\n[Step 5] パテントスペース構築...")
    biz_phi, cluster_comps = build_biz_space(cs)
    tech_cit = build_tech_space(patents, labels, edges)
    print(f"  φ>0 ペア数: {len(biz_phi)//2:,}, 技術的引用ペア: {len(tech_cit)//2:,}")

    # 6. PageRank
    print("\n[Step 6] PageRank 計算...")
    main_clusters = list(mc_summary.keys())
    biz_pr  = pagerank_from_dict(biz_phi,  main_clusters)
    tech_pr = pagerank_from_dict(tech_cit, main_clusters)

    # 7. 企業メトリクス
    print("\n[Step 7] 企業メトリクス計算...")
    metrics = compute_metrics(cs, comp_mc, biz_phi, biz_pr, tech_pr, tech_cit)
    print(f"  評価企業数: {len(metrics):,}")

    # 8. 出力
    print("\n[Step 8] 表・グラフ出力...")
    top20_clusters = save_table5_1(mc_summary)
    save_table_a1(metrics)
    plot_scatter(metrics)
    plot_biz_network(biz_phi, mc_summary)
    plot_tech_network(tech_cit, mc_summary)
    plot_phi_distribution(biz_phi, comp_mc, cs, mc_summary)

    # サマリーテキスト
    summary_lines = [
        "=" * 60,
        "再現実験結果サマリー",
        "=" * 60,
        f"総ユニーク特許数: {len(patents):,}",
        f"内部引用エッジ数: {len(edges):,}",
        f"総クラスタ数:     {len(set(labels.values())):,}",
        f"メインクラスタ数: {len(mc_summary)}",
        f"評価企業数:       {len(metrics):,}",
        "",
        "上位10社（特許数）:",
    ]
    top10 = sorted(metrics.items(), key=lambda x: x[1]['total_patents'], reverse=True)[:10]
    for comp, m in top10:
        summary_lines.append(
            f"  {comp:<40} {m['total_patents']:>6}件  "
            f"biz_C={m['biz_centrality']:.4e}  biz_D={m['biz_density']:.4f}"
        )
    summary_lines.append(f"\n出力先: {OUT_DIR}")
    summary = "\n".join(summary_lines)
    print("\n" + summary)
    with open(os.path.join(OUT_DIR, "summary.txt"), "w") as f:
        f.write(summary)


if __name__ == "__main__":
    t_start = time.time()
    main()
    print(f"\n総実行時間: {(time.time()-t_start)/60:.1f} 分")
