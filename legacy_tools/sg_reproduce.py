"""
鎌田麻衣子修士論文 - スマートグリッド領域 再現実験スクリプト
事業的パテントスペースの提案（スマートグリッドに絞った再現）
"""

import zipfile
import xml.etree.ElementTree as ET
import os
import re
import json
import math
from collections import defaultdict
import igraph as ig
import leidenalg
import networkx as nx
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime

# ─── 設定 ─────────────────────────────────────────────────────────────────────
SG_FILES = [
    "SG001.xlsx",
    "SG002 (1).xlsx",
    "SG003.xlsx",
    "SG004.xlsx",
    "SG006.xlsx",
    "SG007.xlsx",
    "SG007-2.xlsx",
    "SG008.xlsx",
    "SG009.xlsx",
    "SG010.xlsx",
    "SG011.xlsx",
    "SG012.xlsx",
    "SG013.xlsx",
    "SG014.xlsx",
    "SG015.xlsx",
    "SG016.xlsx",
    "SG017.xlsx",
    "SG018.xlsx",
    "SG019.xlsx",
    "SG020.xlsx",
    "SG021.xlsx",
    "SG022.xlsx",
    "SG023.xlsx",
    "SG024.xlsx",
]
DATA_DIR = "/Users/h-torii4649/Downloads"
OUT_DIR  = "/Users/h-torii4649/Downloads/sotsuron_latex_set/results"
LEIDEN_SEED = 42
RECLUSTER_THRESHOLD = 1000   # 1000件超のクラスタは再クラスタリング

os.makedirs(OUT_DIR, exist_ok=True)


# ─── Step 1: xlsx パーサー ────────────────────────────────────────────────────
def parse_xlsx(path):
    """
    特許データ xlsx から
    {pub_id, date, applicant, family_id, bwd_citations: list, title} を返すイテレータ。
    1特許 = メイン行 + 複数の継続行（引用、IPCなど）。
    """
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    tag_row  = f"{{{ns}}}row"
    tag_cell = f"{{{ns}}}c"
    tag_v    = f"{{{ns}}}v"
    tag_t    = f"{{{ns}}}t"
    tag_si   = f"{{{ns}}}si"

    with zipfile.ZipFile(path) as zf:
        # 共有文字列
        with zf.open("xl/sharedStrings.xml") as f:
            ss_root = ET.parse(f).getroot()
        shared = []
        for si in ss_root.iter(tag_si):
            texts = [t.text or "" for t in si.iter(tag_t)]
            shared.append("".join(texts))

        # sheet2 = データシート
        with zf.open("xl/worksheets/sheet2.xml") as f:
            cur = {}           # 現在の特許
            in_data = False    # ヘッダ行を過ぎたか

            for event, elem in ET.iterparse(f, events=("end",)):
                if elem.tag != tag_row:
                    continue

                row_data = {}
                for cell in elem.findall(tag_cell):
                    ref = cell.get("r", "")
                    col = "".join(c for c in ref if c.isalpha())
                    t   = cell.get("t", "n")
                    v   = cell.find(tag_v)
                    if v is not None and v.text:
                        row_data[col] = shared[int(v.text)] if t == "s" else v.text

                elem.clear()

                a_val = row_data.get("A", "")
                # ヘッダ行スキップ（A="List export" or A="1." etc.? Check B="Publication number")
                if row_data.get("B") == "Publication number":
                    in_data = True
                    continue
                if row_data.get("B") == "Header_PublicationIdentifier":
                    continue
                if not in_data:
                    continue

                # メイン行判定（A列に連番がある）
                is_main = bool(a_val and re.match(r"\d+\.$", a_val.strip()))

                if is_main:
                    if cur and cur.get("pub_id"):
                        yield cur
                    # Excelシリアル日付 → 年
                    date_raw = row_data.get("C", "")
                    try:
                        serial = float(date_raw)
                        # Excel date origin: 1899-12-30
                        year = 1900 + int((serial - 2) / 365.25)
                    except (ValueError, TypeError):
                        year = None

                    cur = {
                        "pub_id":   row_data.get("B", "").strip(),
                        "year":     year,
                        "applicant": row_data.get("Q", "").strip(),
                        "family_id": row_data.get("N", "").strip(),
                        "title":    row_data.get("I", "").strip(),
                        "bwd_citations": [],
                        "fwd_citations": [],
                    }
                    if row_data.get("AB", "").strip():
                        cur["bwd_citations"].append(row_data["AB"].strip())
                    if row_data.get("AE", "").strip():
                        cur["fwd_citations"].append(row_data["AE"].strip())
                else:
                    # 継続行
                    if cur:
                        if row_data.get("AB", "").strip():
                            cur["bwd_citations"].append(row_data["AB"].strip())
                        if row_data.get("AE", "").strip():
                            cur["fwd_citations"].append(row_data["AE"].strip())

            if cur and cur.get("pub_id"):
                yield cur


# ─── Step 2: 全ファイル読み込み ──────────────────────────────────────────────
def normalize_applicant(name: str) -> str:
    """企業名の正規化（略称統一・法的接尾語除去）"""
    name = name.upper().strip()
    # 代表的な正規化ルール
    name = re.sub(r"\s+(LTD\.?|INC\.?|CORP\.?|CO\.?|LLC\.?|GMBH|AG|SA|BV|NV|SPA|PLC|KK|KG|AS|AB|OY|PTY|SE|SRO|SAS|LTDA|SDN BHD|PVT|PRIVATE|LIMITED|INCORPORATED|CORPORATION|COMPANY)\.?\s*$", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    # 有名企業のマッピング
    mappings = {
        "HITACHI": "Hitachi",
        "SIEMENS": "Siemens",
        "MITSUBISHI ELECTRIC": "Mitsubishi Electric",
        "MITSUBISHI DENKI": "Mitsubishi Electric",
        "MITSUBISHI JIDOSHA KOGYO": "Mitsubishi Motors",
        "GENERAL ELECTRIC": "GE",
        "ABB": "ABB",
        "SCHNEIDER ELECTRIC": "Schneider",
        "TOSHIBA": "Toshiba",
        "PANASONIC": "Panasonic",
        "SHARP": "Sharp",
        "SAMSUNG": "Samsung",
        "LG ELECTRONICS": "LG Electronics",
        "SONY": "Sony",
        "NEC": "NEC",
        "FUJITSU": "Fujitsu",
        "NISSAN MOTOR": "Nissan",
        "TOYOTA JIDOSHA": "Toyota",
        "FORD GLOBAL TECHNOLOGIES": "Ford",
        "INTEL": "Intel",
        "MICROSOFT TECHNOLOGY LICENSING": "Microsoft",
        "APPLE": "Apple",
        "GOOGLE": "Google",
        "AMAZON TECHNOLOGIES": "Amazon",
    }
    for key, val in mappings.items():
        if key in name:
            return val
    return name.title()


def load_all_patents():
    """全SG xlsxを読み込み、重複排除して返す"""
    patents    = {}  # pub_id -> patent dict
    seen_files = set()

    for fname in SG_FILES:
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            print(f"  [skip] {fname} not found")
            continue
        # 内容重複ファイルをスキップ（SG002 (1) と SG002 は同一）
        size = os.path.getsize(path)
        if size in seen_files:
            print(f"  [dup]  {fname} ({size} bytes, skipped)")
            continue
        seen_files.add(size)
        print(f"  [read] {fname} ...", end=" ", flush=True)
        n = 0
        for pat in parse_xlsx(path):
            pid = pat["pub_id"]
            if pid and pid not in patents:
                patents[pid] = pat
            n += 1
        print(f"{n} records, {len(patents)} unique total")

    return patents


# ─── Step 3: 引用ネットワーク構築 ────────────────────────────────────────────
def build_citation_network(patents: dict):
    """
    後方引用からエッジを作成（データセット内に存在する特許間のみ）
    """
    pub_set = set(patents.keys())
    edges   = []
    for pid, pat in patents.items():
        for cit in pat["bwd_citations"]:
            cit = cit.strip()
            if cit and cit in pub_set:
                edges.append((pid, cit))
    return edges


# ─── Step 4: Leiden クラスタリング（階層的） ─────────────────────────────────
def leiden_cluster_once(pub_ids: list, edges: list, seed: int = LEIDEN_SEED) -> dict:
    """指定ノード・エッジでLeidenクラスタリング。{pub_id: cluster_label} を返す"""
    if len(pub_ids) == 0:
        return {}
    if len(pub_ids) == 1:
        return {pub_ids[0]: 0}

    id2idx = {pid: i for i, pid in enumerate(pub_ids)}
    idx_edges = [(id2idx[s], id2idx[t]) for s, t in edges
                 if s in id2idx and t in id2idx]

    g = ig.Graph(n=len(pub_ids), edges=idx_edges, directed=False)
    partition = leidenalg.find_partition(
        g,
        leidenalg.ModularityVertexPartition,
        seed=seed,
        n_iterations=5,
    )
    return {pub_ids[i]: partition.membership[i] for i in range(len(pub_ids))}


def hierarchical_leiden(patents: dict, edges: list) -> dict:
    """
    階層的クラスタリング:
    1. 全特許をクラスタリング
    2. 1000件超のクラスタを再クラスタリング
    3. さらに1000件超があれば3回目も実施
    -> {pub_id: "C-C-C"} 形式のクラスタラベル
    """
    pub_ids  = list(patents.keys())
    edge_set = set(tuple(e) for e in edges)

    print(f"\n[Leiden] L1 clustering {len(pub_ids)} patents ...")
    l1 = leiden_cluster_once(pub_ids, list(edge_set))

    # クラスタごとにまとめる
    clusters_l1 = defaultdict(list)
    for pid, c in l1.items():
        clusters_l1[c].append(pid)

    final_labels = {}
    for c1, members in clusters_l1.items():
        if len(members) <= RECLUSTER_THRESHOLD:
            for pid in members:
                final_labels[pid] = str(c1)
            continue

        # L2: 1000件超 → 再クラスタリング
        sub_edges = [(s, t) for s, t in edge_set if s in set(members) and t in set(members)]
        print(f"  [L2] cluster {c1} has {len(members)} members → re-cluster ...")
        l2 = leiden_cluster_once(members, sub_edges, seed=LEIDEN_SEED + c1)
        sub2 = defaultdict(list)
        for pid, c2 in l2.items():
            sub2[c2].append(pid)

        for c2, sub_members in sub2.items():
            if len(sub_members) <= RECLUSTER_THRESHOLD:
                for pid in sub_members:
                    final_labels[pid] = f"{c1}-{c2}"
                continue

            # L3: さらに再クラスタリング
            sub2_edges = [(s, t) for s, t in sub_edges
                          if s in set(sub_members) and t in set(sub_members)]
            print(f"    [L3] cluster {c1}-{c2} has {len(sub_members)} members → re-cluster ...")
            l3 = leiden_cluster_once(sub_members, sub2_edges, seed=LEIDEN_SEED + c1 + c2)
            for pid, c3 in l3.items():
                final_labels[pid] = f"{c1}-{c2}-{c3}"

    print(f"  Total unique clusters: {len(set(final_labels.values()))}")
    return final_labels


# ─── Step 5: メインクラスタ特定 ──────────────────────────────────────────────
def get_main_cluster(label: str) -> str:
    return label.split("-")[0]


def cluster_stats(patents: dict, labels: dict) -> dict:
    """クラスタ番号 -> {size, members, top_titles, main_cluster} を返す"""
    stats = defaultdict(lambda: {"size": 0, "members": [], "titles": []})
    for pid, label in labels.items():
        stats[label]["size"] += 1
        stats[label]["members"].append(pid)
        title = patents[pid].get("title", "")
        if title:
            stats[label]["titles"].append(title)
    return dict(stats)


# ─── Step 6: 特化係数（CS = Specialization Coefficient） ─────────────────────
def compute_cs(patents: dict, labels: dict):
    """
    CS(company, cluster) = (count(company, cluster) / count(company)) / (count(cluster) / count(total))
    RCA (Revealed Comparative Advantage) 相当
    """
    # 会社 -> クラスタ -> 件数
    comp_cluster = defaultdict(lambda: defaultdict(int))
    total_by_cluster = defaultdict(int)
    total_by_comp    = defaultdict(int)
    total = 0

    for pid, pat in patents.items():
        label = labels.get(pid)
        if not label:
            continue
        mc = get_main_cluster(label)  # メインクラスタ単位で集計
        app = normalize_applicant(pat.get("applicant", "UNKNOWN"))
        comp_cluster[app][mc] += 1
        total_by_cluster[mc] += 1
        total_by_comp[app]   += 1
        total += 1

    cs_matrix = {}  # (comp, cluster) -> CS
    for comp, cluster_counts in comp_cluster.items():
        for cluster, cnt in cluster_counts.items():
            if total_by_comp[comp] == 0 or total_by_cluster[cluster] == 0:
                continue
            cs = (cnt / total_by_comp[comp]) / (total_by_cluster[cluster] / total)
            cs_matrix[(comp, cluster)] = cs

    return cs_matrix, dict(comp_cluster), dict(total_by_cluster), dict(total_by_comp)


# ─── Step 7: 技術的パテントスペース（クラスタ間引用） ────────────────────────
def build_tech_space(patents: dict, labels: dict, edges: list) -> dict:
    """クラスタ間の引用数行列を返す"""
    tech_cit = defaultdict(int)
    for src, dst in edges:
        src_c = get_main_cluster(labels.get(src, ""))
        dst_c = get_main_cluster(labels.get(dst, ""))
        if src_c and dst_c and src_c != dst_c:
            tech_cit[(src_c, dst_c)] += 1
    return dict(tech_cit)


# ─── Step 8: 事業的パテントスペース（クラスタ間共起） ────────────────────────
def build_biz_space(cs_matrix: dict, total_by_cluster: dict) -> dict:
    """
    φ(i, j) = # companies with CS>1 in both i and j  / sqrt(#comp_in_i × #comp_in_j)
    """
    # 各クラスタに注力している企業集合
    cluster_companies = defaultdict(set)
    for (comp, cluster), cs in cs_matrix.items():
        if cs > 1:
            cluster_companies[cluster].add(comp)

    clusters = list(cluster_companies.keys())
    phi = {}
    for i in range(len(clusters)):
        for j in range(i + 1, len(clusters)):
            ci, cj = clusters[i], clusters[j]
            shared = len(cluster_companies[ci] & cluster_companies[cj])
            denom  = math.sqrt(len(cluster_companies[ci]) * len(cluster_companies[cj]))
            if denom > 0 and shared > 0:
                p = shared / denom
                phi[(ci, cj)] = p
                phi[(cj, ci)] = p

    return phi, dict(cluster_companies)


# ─── Step 9: PageRank 計算 ────────────────────────────────────────────────────
def compute_pagerank_from_matrix(mat: dict, nodes: list) -> dict:
    """隣接辞書からPageRankを計算"""
    g = nx.DiGraph()
    g.add_nodes_from(nodes)
    for (s, d), w in mat.items():
        if s in set(nodes) and d in set(nodes):
            g.add_edge(s, d, weight=w)
    if g.number_of_edges() == 0:
        return {n: 1.0 / len(nodes) for n in nodes}
    pr = nx.pagerank(g, weight="weight")
    return pr


# ─── Step 10: 中心性・密度の計算 ──────────────────────────────────────────────
def compute_metrics(
    cs_matrix, comp_cluster, biz_phi, tech_pr, biz_pr, tech_cit_dict, cluster_companies
):
    """
    各企業について:
    - 事業的中心性 = 保有特許が属するクラスタのbiz_PR平均（特許数加重）
    - 技術的中心性 = 同・tech_PR平均
    - 事業的密度  = 保有クラスタ間のφ平均
    - 技術的密度  = 保有クラスタ間の技術的近接度平均
    """
    # 技術的近接度（引用割合）
    total_cit = sum(tech_cit_dict.values()) or 1
    tech_l = {pair: v / total_cit for pair, v in tech_cit_dict.items()}

    results = {}
    all_comps = set(comp for comp, _ in cs_matrix.keys())

    for comp in all_comps:
        occupied = {}
        for cluster, cnt in comp_cluster.get(comp, {}).items():
            occupied[cluster] = cnt
        if not occupied:
            continue

        total_pats = sum(occupied.values())
        if total_pats == 0:
            continue

        # 中心性（特許数加重平均）
        biz_cent = sum(biz_pr.get(c, 0) * n for c, n in occupied.items()) / total_pats
        tech_cent = sum(tech_pr.get(c, 0) * n for c, n in occupied.items()) / total_pats

        # 密度（保有クラスタペア間の平均）
        cluster_list = list(occupied.keys())
        phi_vals = []
        tech_l_vals = []
        for i in range(len(cluster_list)):
            for j in range(i + 1, len(cluster_list)):
                ci, cj = cluster_list[i], cluster_list[j]
                phi_vals.append(biz_phi.get((ci, cj), 0.0))
                tech_l_vals.append(tech_l.get((ci, cj), tech_l.get((cj, ci), 0.0)))

        biz_density  = np.mean(phi_vals)  if phi_vals  else 0.0
        tech_density = np.mean(tech_l_vals) if tech_l_vals else 0.0

        results[comp] = {
            "biz_centrality":  biz_cent,
            "tech_centrality": tech_cent,
            "biz_density":     biz_density,
            "tech_density":    tech_density,
            "total_patents":   total_pats,
            "n_clusters":      len(occupied),
        }

    return results


# ─── Step 11: 可視化 ──────────────────────────────────────────────────────────
def plot_scatter(metrics: dict, title_suffix="SG", out_prefix="fig5_4_sg"):
    comps  = list(metrics.keys())
    biz_c  = [metrics[c]["biz_centrality"]  for c in comps]
    tech_c = [metrics[c]["tech_centrality"] for c in comps]
    biz_d  = [metrics[c]["biz_density"]     for c in comps]
    tech_d = [metrics[c]["tech_density"]    for c in comps]
    sizes  = [metrics[c]["total_patents"]   for c in comps]

    # 特許数上位10社のラベル表示
    top10 = sorted(comps, key=lambda c: metrics[c]["total_patents"], reverse=True)[:10]

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle(f"スマートグリッド関連企業群保有特許の中心性・密度散布図 ({title_suffix})",
                 fontsize=13, fontweight="bold")

    # --- (a) 中心性散布図 ---
    ax = axes[0]
    sc = ax.scatter(tech_c, biz_c,
                    s=[max(5, math.log10(max(s, 1)) * 20) for s in sizes],
                    alpha=0.5, c="steelblue", edgecolors="none")
    for comp in top10:
        ax.annotate(
            comp,
            (metrics[comp]["tech_centrality"], metrics[comp]["biz_centrality"]),
            fontsize=7, ha="center",
            xytext=(0, 6), textcoords="offset points",
        )
    ax.set_xlabel("技術的中心性 (Technical Centrality)", fontsize=11)
    ax.set_ylabel("事業的中心性 (Business Centrality)", fontsize=11)
    ax.set_title("(a) 事業的・技術的中心性", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.4)

    # --- (b) 密度散布図 ---
    ax = axes[1]
    ax.scatter(tech_d, biz_d,
               s=[max(5, math.log10(max(s, 1)) * 20) for s in sizes],
               alpha=0.5, c="darkorange", edgecolors="none")
    for comp in top10:
        ax.annotate(
            comp,
            (metrics[comp]["tech_density"], metrics[comp]["biz_density"]),
            fontsize=7, ha="center",
            xytext=(0, 6), textcoords="offset points",
        )
    ax.set_xlabel("技術的密度 (Technical Density)", fontsize=11)
    ax.set_ylabel("事業的密度 (Business Density)", fontsize=11)
    ax.set_title("(b) 事業的・技術的密度", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, f"{out_prefix}.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"[plot] saved → {out}")


def plot_biz_network(biz_phi: dict, cluster_stats_dict: dict, out_name="fig5_1a_biz_space.png"):
    """事業的パテントスペースのネットワーク図（Figure 5.1(a)相当）"""
    # 主要クラスタ（特許数上位20）を使用
    top_clusters = sorted(cluster_stats_dict.items(), key=lambda x: x[1]["size"], reverse=True)[:20]
    top_ids = [c for c, _ in top_clusters]
    top_set = set(top_ids)

    g = nx.Graph()
    for c in top_ids:
        g.add_node(c, size=cluster_stats_dict[c]["size"])

    max_phi = max((v for (a, b), v in biz_phi.items() if a in top_set and b in top_set), default=1)
    for (a, b), phi in biz_phi.items():
        if a in top_set and b in top_set and phi > 0.05:
            g.add_edge(a, b, weight=phi)

    if g.number_of_nodes() == 0:
        return

    pos = nx.spring_layout(g, seed=42, k=2.0)
    fig, ax = plt.subplots(figsize=(12, 10))

    node_sizes = [cluster_stats_dict[c]["size"] / 100 for c in g.nodes()]
    cmap = plt.cm.tab20
    colors = [cmap(i % 20) for i in range(len(g.nodes()))]

    edges_drawn = [(u, v) for u, v, d in g.edges(data=True)]
    weights = [g[u][v]["weight"] * 5 for u, v in edges_drawn]

    nx.draw_networkx_edges(g, pos, edgelist=edges_drawn, width=weights,
                           alpha=0.5, edge_color="gray", ax=ax)
    nx.draw_networkx_nodes(g, pos, node_size=[s * 3 for s in node_sizes],
                           node_color=colors, alpha=0.85, ax=ax)
    nx.draw_networkx_labels(g, pos, {n: f"C{n}" for n in g.nodes()},
                            font_size=8, ax=ax)

    ax.set_title("図5.1(a) スマートグリッド: 事業的パテントスペース\n(企業内クラスタ共起ネットワーク)",
                 fontsize=12)
    ax.axis("off")
    plt.tight_layout()
    out = os.path.join(OUT_DIR, out_name)
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"[plot] saved → {out}")


def plot_tech_network(tech_cit_dict: dict, cluster_stats_dict: dict, out_name="fig5_1b_tech_space.png"):
    """技術的パテントスペースのネットワーク図（Figure 5.1(b)相当）"""
    top_clusters = sorted(cluster_stats_dict.items(), key=lambda x: x[1]["size"], reverse=True)[:20]
    top_ids = [c for c, _ in top_clusters]
    top_set = set(top_ids)

    g = nx.DiGraph()
    for c in top_ids:
        g.add_node(c)

    total_cit = sum(tech_cit_dict.values()) or 1
    for (a, b), cnt in tech_cit_dict.items():
        if a in top_set and b in top_set:
            g.add_edge(a, b, weight=cnt / total_cit)

    ug = g.to_undirected()
    pos = nx.spring_layout(ug, seed=42, k=2.0)
    fig, ax = plt.subplots(figsize=(12, 10))

    cmap = plt.cm.tab20
    colors = [cmap(i % 20) for i in range(len(ug.nodes()))]
    edges_u = list(ug.edges())
    weights_u = [ug[u][v]["weight"] * 200 for u, v in edges_u]

    nx.draw_networkx_edges(ug, pos, edgelist=edges_u, width=weights_u,
                           alpha=0.5, edge_color="gray", ax=ax)
    nx.draw_networkx_nodes(ug, pos,
                           node_size=[cluster_stats_dict[n]["size"] / 100 for n in ug.nodes()],
                           node_color=colors, alpha=0.85, ax=ax)
    nx.draw_networkx_labels(ug, pos, {n: f"C{n}" for n in ug.nodes()},
                            font_size=8, ax=ax)

    ax.set_title("図5.1(b) スマートグリッド: 技術的パテントスペース\n(クラスタ間引用ネットワーク)",
                 fontsize=12)
    ax.axis("off")
    plt.tight_layout()
    out = os.path.join(OUT_DIR, out_name)
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"[plot] saved → {out}")


def save_table5_1(cluster_stats_dict: dict, patents: dict, labels: dict, out_name="table5_1_sg_clusters.txt"):
    """表5.1: スマートグリッド関連特許の主要クラスタ"""
    # メインクラスタの集計
    main_stats = defaultdict(lambda: {"size": 0, "titles": []})
    for pid, label in labels.items():
        mc = get_main_cluster(label)
        main_stats[mc]["size"] += 1
        t = patents[pid].get("title", "")
        if t:
            main_stats[mc]["titles"].append(t)

    top20_main = sorted(main_stats.items(), key=lambda x: x[1]["size"], reverse=True)[:20]

    lines = ["表5.1: スマートグリッド関連特許の主要クラスタ（再現）\n"]
    lines.append(f"{'クラスタ番号':<12}  {'所属特許数':>10}  代表的なキーワード")
    lines.append("-" * 80)

    for mc, info in top20_main:
        # TF-IDF的な単語抽出（簡易）
        from collections import Counter
        word_counts = Counter()
        stop = {"the","a","an","of","for","in","to","and","or","with","by","on",
                "is","are","at","from","as","be","this","that","it","its","using",
                "system","method","device","apparatus","based","control","power",
                "management","network","grid","smart","energy"}
        for title in info["titles"][:200]:
            for w in re.findall(r"[a-z]+", title.lower()):
                if w not in stop and len(w) > 3:
                    word_counts[w] += 1
        keywords = ",".join(w for w, _ in word_counts.most_common(8))
        lines.append(f"{mc:<12}  {info['size']:>10}  {keywords}")

    out = os.path.join(OUT_DIR, out_name)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[table] saved → {out}")
    return top20_main


def save_table_a1(metrics: dict, out_name="table_a1_sg_top20.txt"):
    """表A.1: スマートグリッド領域 中心性・密度上位20企業"""
    lines = ["表A.1: スマートグリッド関連領域 中心性・密度上位20企業（再現）\n"]

    for metric_key, label in [
        ("biz_centrality",  "事業的中心性"),
        ("tech_centrality", "技術的中心性"),
        ("biz_density",     "事業的密度"),
        ("tech_density",    "技術的密度"),
    ]:
        sorted_comps = sorted(metrics.items(), key=lambda x: x[1][metric_key], reverse=True)[:20]
        lines.append(f"\n  {label} 上位20社:")
        lines.append(f"  {'企業名':<45}  {'値':>12}")
        lines.append("  " + "-" * 60)
        for comp, m in sorted_comps:
            lines.append(f"  {comp:<45}  {m[metric_key]:>12.6f}")

    out = os.path.join(OUT_DIR, out_name)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[table] saved → {out}")


# ─── メインパイプライン ────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("スマートグリッド 事業的パテントスペース 再現実験")
    print("=" * 60)

    # 1. データ読み込み
    print("\n[Step 1] 特許データ読み込み ...")
    patents = load_all_patents()
    print(f"  合計ユニーク特許数: {len(patents):,}")

    # 2. 引用ネットワーク構築
    print("\n[Step 2] 引用ネットワーク構築 ...")
    edges = build_citation_network(patents)
    print(f"  エッジ数（内部引用）: {len(edges):,}")

    # 3. Leiden クラスタリング
    print("\n[Step 3] Leiden クラスタリング ...")
    labels = hierarchical_leiden(patents, edges)
    n_clusters = len(set(labels.values()))
    print(f"  総クラスタ数: {n_clusters:,}")

    # 中間保存（再実行の高速化）
    cache_path = os.path.join(OUT_DIR, "labels_cache.json")
    with open(cache_path, "w") as f:
        json.dump(labels, f)
    print(f"  クラスタラベルをキャッシュ: {cache_path}")

    # 4. クラスタ統計
    print("\n[Step 4] クラスタ統計計算 ...")
    stats = cluster_stats(patents, labels)
    print(f"  ユニーククラスタ数: {len(stats)}")

    # 5. 特化係数
    print("\n[Step 5] 特化係数 (CS) 計算 ...")
    cs_matrix, comp_cluster, total_by_cluster, total_by_comp = compute_cs(patents, labels)
    n_comps = len(set(c for c, _ in cs_matrix.keys()))
    print(f"  企業数: {n_comps:,}")
    print(f"  (CS > 1) ペア数: {sum(1 for v in cs_matrix.values() if v > 1):,}")

    # 6. 技術的パテントスペース
    print("\n[Step 6] 技術的パテントスペース構築 ...")
    tech_cit_dict = build_tech_space(patents, labels, edges)
    print(f"  クラスタ間引用ペア数: {len(tech_cit_dict):,}")

    # 7. 事業的パテントスペース
    print("\n[Step 7] 事業的パテントスペース構築 ...")
    biz_phi, cluster_companies = build_biz_space(cs_matrix, total_by_cluster)
    print(f"  φ > 0 のペア数: {len(biz_phi) // 2:,}")

    # PageRank 計算
    main_clusters = list(set(get_main_cluster(l) for l in labels.values()))
    print(f"\n[Step 7b] PageRank 計算 (on {len(main_clusters)} main clusters) ...")
    biz_pr  = compute_pagerank_from_matrix(biz_phi,       main_clusters)
    tech_pr = compute_pagerank_from_matrix(tech_cit_dict, main_clusters)

    # 8. 中心性・密度計算
    print("\n[Step 8] 中心性・密度計算 ...")
    metrics = compute_metrics(
        cs_matrix, comp_cluster, biz_phi, tech_pr, biz_pr, tech_cit_dict, cluster_companies
    )
    print(f"  評価企業数: {len(metrics):,}")

    # 9. 出力
    print("\n[Step 9] グラフ・表の出力 ...")

    # メインクラスタのstatsをまとめる
    main_stats_dict = {}
    for pid, label in labels.items():
        mc = get_main_cluster(label)
        if mc not in main_stats_dict:
            main_stats_dict[mc] = {"size": 0, "titles": []}
        main_stats_dict[mc]["size"] += 1
        t = patents[pid].get("title", "")
        if t:
            main_stats_dict[mc]["titles"].append(t)

    # 表5.1
    save_table5_1(main_stats_dict, patents, labels)

    # 散布図 (Figure 5.4相当)
    plot_scatter(metrics)

    # ネットワーク図 (Figure 5.1相当)
    plot_biz_network(biz_phi, main_stats_dict)
    plot_tech_network(tech_cit_dict, main_stats_dict)

    # 表A.1
    save_table_a1(metrics)

    print("\n" + "=" * 60)
    print("再現実験完了")
    print(f"出力先: {OUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
