#!/usr/bin/env python3
"""
CSV出力から統計を計算し、グラフと論文用LaTeXテーブルを生成する
"""
import csv, json, sys
from collections import Counter
from pathlib import Path

WORKDIR = Path('/Users/h-torii4649/Downloads/sotsuron_latex_set')
FIGDIR  = WORKDIR / 'figures'
FIGDIR.mkdir(exist_ok=True)

def load_csv(path):
    records = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = int(row['year']) if row['year'] else None
            records.append({
                'year': year,
                'family_idx': row['family_idx'],
                'is_unet': row['is_unet'] == '1'
            })
    return records

def compute_stats(records):
    total = len(records)
    unet_n = sum(1 for r in records if r['is_unet'])
    all_fam  = {r['family_idx'] for r in records if r['family_idx']}
    unet_fam = {r['family_idx'] for r in records if r['is_unet'] and r['family_idx']}

    yr_total = Counter(r['year'] for r in records if r['year'] and 2015 <= r['year'] <= 2024)
    yr_unet  = Counter(r['year'] for r in records if r['is_unet'] and r['year'] and 2015 <= r['year'] <= 2024)

    # Period stats
    past   = [r for r in records if r['year'] and 2015 <= r['year'] <= 2018]
    future = [r for r in records if r['year'] and 2019 <= r['year'] <= 2024]
    # Filter to valid range
    total_valid = len([r for r in records if r['year'] and 2015 <= r['year'] <= 2024])
    unet_valid  = sum(1 for r in records if r['is_unet'] and r['year'] and 2015 <= r['year'] <= 2024)

    return {
        'total': total,
        'total_valid': total_valid,
        'unet': unet_n,
        'unet_valid': unet_valid,
        'families': len(all_fam),
        'unet_families': len(unet_fam),
        'yr_total': dict(yr_total),
        'yr_unet': dict(yr_unet),
        'past_total': len(past),
        'past_unet': sum(1 for r in past if r['is_unet']),
        'future_total': len(future),
        'future_unet': sum(1 for r in future if r['is_unet']),
        'past_fam_total': len({r['family_idx'] for r in past if r['family_idx']}),
        'past_fam_unet': len({r['family_idx'] for r in past if r['is_unet'] and r['family_idx']}),
        'future_fam_total': len({r['family_idx'] for r in future if r['family_idx']}),
        'future_fam_unet': len({r['family_idx'] for r in future if r['is_unet'] and r['family_idx']}),
    }

def print_stats(label, s):
    print(f'\n{label}:')
    print(f'  全期間: total={s["total_valid"]}, unet={s["unet_valid"]}, rate={s["unet_valid"]/s["total_valid"]*100:.2f}%')
    print(f'  Family: total={s["families"]}, unet_fam={s["unet_families"]}, rate={s["unet_families"]/s["families"]*100:.2f}%')
    print(f'  2015-2018: total={s["past_total"]}, unet={s["past_unet"]}, rate={s["past_unet"]/max(s["past_total"],1)*100:.2f}%')
    print(f'  2019-2024: total={s["future_total"]}, unet={s["future_unet"]}, rate={s["future_unet"]/max(s["future_total"],1)*100:.2f}%')
    print(f'  年次: {dict(sorted((k,v) for k,v in s["yr_total"].items()))}')
    print(f'  U-Net年次: {dict(sorted((k,v) for k,v in s["yr_unet"].items()))}')

def make_charts(a0, b0):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import numpy as np

    import matplotlib.font_manager as fm
    fm.fontManager.addfont('/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc')
    plt.rcParams['font.family'] = ['Hiragino Sans', 'DejaVu Sans']
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.spines.right'] = False

    years = list(range(2015, 2025))

    # ---------- Figure 1: Annual U-Net rate (Publication-based) ----------
    a0_rate = [a0['yr_unet'].get(y, 0) / a0['yr_total'].get(y, 1) * 100 for y in years]
    b0_rate = [b0['yr_unet'].get(y, 0) / b0['yr_total'].get(y, 1) * 100 for y in years]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(years, a0_rate, 'o-', color='#2196F3', linewidth=2, markersize=6, label='医療画像解析 (A0)')
    ax.plot(years, b0_rate, 's--', color='#FF5722', linewidth=2, markersize=6, label='製造欠陥検出 (B0)')
    ax.axvspan(2014.5, 2018.5, alpha=0.08, color='gray', label='過去期間 (2015-2018)')
    ax.axvspan(2018.5, 2024.5, alpha=0.05, color='blue', label='将来評価期間 (2019-2024)')
    ax.set_xlabel('Filing Year', fontsize=11)
    ax.set_ylabel('U-Net出現率 (%)', fontsize=11)
    ax.set_title('U-Net出現率の年次推移（Publication numberベース）', fontsize=12, fontweight='bold')
    ax.legend(fontsize=9, loc='upper left')
    ax.set_xticks(years)
    ax.set_xlim(2014.5, 2024.5)
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f%%'))
    fig.tight_layout()
    fig.savefig(str(FIGDIR / 'fig04_unet_publication_rate.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('  Saved fig04_unet_publication_rate.png')

    # ---------- Figure 2: Period comparison bar chart (Publication) ----------
    periods = ['2015-2018\n(過去期間)', '2019-2024\n(将来評価期間)']
    a0_vals = [a0['past_unet']/max(a0['past_total'],1)*100,
               a0['future_unet']/max(a0['future_total'],1)*100]
    b0_vals = [b0['past_unet']/max(b0['past_total'],1)*100,
               b0['future_unet']/max(b0['future_total'],1)*100]

    x = np.arange(len(periods))
    w = 0.35
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars1 = ax.bar(x - w/2, a0_vals, w, label='医療画像解析 (A0)', color='#2196F3', alpha=0.85)
    bars2 = ax.bar(x + w/2, b0_vals, w, label='製造欠陥検出 (B0)', color='#FF5722', alpha=0.85)
    ax.set_xlabel('期間', fontsize=11)
    ax.set_ylabel('U-Net出現率 (%)', fontsize=11)
    ax.set_title('期間別U-Net出現率（Publication numberベース）', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(periods, fontsize=10)
    ax.legend(fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f%%'))
    for bar in [*bars1, *bars2]:
        h = bar.get_height()
        ax.annotate(f'{h:.2f}%', xy=(bar.get_x()+bar.get_width()/2, h),
                    xytext=(0, 3), textcoords='offset points', ha='center', va='bottom', fontsize=9)
    fig.tight_layout()
    fig.savefig(str(FIGDIR / 'fig05_unet_period_publication.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('  Saved fig05_unet_period_publication.png')

    # ---------- Figure 3: Period comparison (Family ID) ----------
    a0f_vals = [a0['past_fam_unet']/max(a0['past_fam_total'],1)*100,
                a0['future_fam_unet']/max(a0['future_fam_total'],1)*100]
    b0f_vals = [b0['past_fam_unet']/max(b0['past_fam_total'],1)*100,
                b0['future_fam_unet']/max(b0['future_fam_total'],1)*100]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars1 = ax.bar(x - w/2, a0f_vals, w, label='医療画像解析 (A0)', color='#2196F3', alpha=0.85)
    bars2 = ax.bar(x + w/2, b0f_vals, w, label='製造欠陥検出 (B0)', color='#FF5722', alpha=0.85)
    ax.set_xlabel('期間', fontsize=11)
    ax.set_ylabel('U-Net出現率 (%)', fontsize=11)
    ax.set_title('期間別U-Net出現率（Family IDベース）', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(periods, fontsize=10)
    ax.legend(fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f%%'))
    for bar in [*bars1, *bars2]:
        h = bar.get_height()
        ax.annotate(f'{h:.2f}%', xy=(bar.get_x()+bar.get_width()/2, h),
                    xytext=(0, 3), textcoords='offset points', ha='center', va='bottom', fontsize=9)
    fig.tight_layout()
    fig.savefig(str(FIGDIR / 'fig06_unet_period_family.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('  Saved fig06_unet_period_family.png')

    # ---------- Figure 4: Dataset overview (pub counts) ----------
    a1_total = a0['unet_valid']
    b1_total = b0['unet_valid']
    datasets = ['A0\n医療画像解析\n全体', 'A1\n医療画像解析\n×U-Net',
                'B0\n製造欠陥検出\n全体', 'B1\n製造欠陥検出\n×U-Net']
    counts   = [a0['total_valid'], a1_total, b0['total_valid'], b1_total]
    colors   = ['#2196F3', '#64B5F6', '#FF5722', '#FF8A65']

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(datasets, counts, color=colors, alpha=0.85, width=0.5)
    ax.set_ylabel('Publication数', fontsize=11)
    ax.set_title('データセット別Publication数 (2015-2024)', fontsize=12, fontweight='bold')
    for bar, cnt in zip(bars, counts):
        ax.annotate(f'{cnt:,}', xy=(bar.get_x()+bar.get_width()/2, bar.get_height()),
                    xytext=(0, 4), textcoords='offset points', ha='center', va='bottom',
                    fontsize=10, fontweight='bold')
    fig.tight_layout()
    fig.savefig(str(FIGDIR / 'fig07_dataset_overview.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('  Saved fig07_dataset_overview.png')

    # ---------- Figure 5: U-Net annual count stacked ----------
    a0_unet_annual = [a0['yr_unet'].get(y, 0) for y in years]
    b0_unet_annual = [b0['yr_unet'].get(y, 0) for y in years]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5), sharey=False)
    ax1.bar(years, a0_unet_annual, color='#2196F3', alpha=0.85)
    ax1.set_title('医療画像解析 (A0)\nU-Net関連特許数', fontsize=11, fontweight='bold')
    ax1.set_xlabel('Filing Year'); ax1.set_ylabel('Publication数')
    ax1.set_xticks(years); ax1.tick_params(axis='x', rotation=45)

    ax2.bar(years, b0_unet_annual, color='#FF5722', alpha=0.85)
    ax2.set_title('製造欠陥検出 (B0)\nU-Net関連特許数', fontsize=11, fontweight='bold')
    ax2.set_xlabel('Filing Year'); ax2.set_ylabel('Publication数')
    ax2.set_xticks(years); ax2.tick_params(axis='x', rotation=45)

    fig.tight_layout()
    fig.savefig(str(FIGDIR / 'fig08_unet_annual_count.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print('  Saved fig08_unet_annual_count.png')

if __name__ == '__main__':
    WORKDIR = Path('/Users/h-torii4649/Downloads/sotsuron_latex_set')
    FIGDIR  = WORKDIR / 'figures'
    FIGDIR.mkdir(exist_ok=True)

    print('Loading A0 data...')
    a0_records = load_csv(WORKDIR / 'A0_data.csv')
    print('Loading B0 data...')
    b0_records = load_csv(WORKDIR / 'B0_data.csv')

    a0_stats = compute_stats(a0_records)
    b0_stats = compute_stats(b0_records)

    print_stats('A0 (医療画像解析)', a0_stats)
    print_stats('B0 (製造欠陥検出)', b0_stats)

    # Save JSON summary
    summary = {'A0': a0_stats, 'B0': b0_stats}
    with open(WORKDIR / 'experiment_summary.json', 'w') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print('\nSaved experiment_summary.json')

    print('\nGenerating charts...')
    make_charts(a0_stats, b0_stats)

    # Print key results for verification
    print('\n=== 卒論との照合 ===')
    a0s, b0s = a0_stats, b0_stats
    print(f'A0 全体 Publication: {a0s["total_valid"]}  (論文: 15,167)')
    print(f'A0 U-Net Publication: {a0s["unet_valid"]}  (論文: 804)')
    print(f'A0 出現率: {a0s["unet_valid"]/a0s["total_valid"]*100:.2f}%  (論文: 5.30%)')
    print(f'B0 全体 Publication: {b0s["total_valid"]}  (論文: 12,212)')
    print(f'B0 U-Net Publication: {b0s["unet_valid"]}  (論文: 72)')
    print(f'B0 出現率: {b0s["unet_valid"]/b0s["total_valid"]*100:.2f}%  (論文: 0.59%)')
    print(f'A0 Family: {a0s["families"]}  (論文: 8,513)')
    print(f'A0 U-Net Family: {a0s["unet_families"]}  (論文: 577)')
    print(f'B0 Family: {b0s["families"]}  (論文: 8,898)')
    print(f'B0 U-Net Family: {b0s["unet_families"]}  (論文: 49)')
