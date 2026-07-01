# 提案手法の説明

## 研究目的

本研究は、特許文書の課題文脈と解決手段文脈を分離して抽出し、異なる応用分野（ドメイン）間でクロスドメイン技術候補をスクリーニングする手法を提案する。専門家が確認すべき候補の絞り込みを目的としており、候補抽出の可能性を示すことを研究成果とする。

---

## 1. 問題設定

技術の応用可能性をドメイン横断的に探索する際、研究者や企業は大量の特許文書を精査する必要がある。しかし、特許文書には技術的課題の記述と解決手段の記述が混在しており、機械的な類似度計算では両者を区別できない。

本研究では、次の問いに取り組む：

> 「あるドメインAで広く用いられている技術手法は、類似した課題構造を持つドメインBにおいて、将来的に出現増加する候補となりうるか？」

---

## 2. データセット定義

| データセット | 内容 | 備考 |
|---|---|---|
| A0 | 医療画像解析分野の特許群 | 参照元ドメイン（技術供給源） |
| B0 | 製造欠陥検出分野の特許群 | 対象ドメイン（技術候補探索先） |

分析期間を以下の2区間に分割する：

- **過去期間（Past）**：2015年〜2018年（候補抽出に使用）
- **将来期間（Future）**：2019年〜2024年（後ろ向き評価に使用）

---

## 3. 課題・解決手段文脈の分離

### 3.1 ルールベース抽出

特許テキスト（タイトル・要約・クレーム）を文単位で分割し、キーワードマッチングにより以下の文脈を抽出する：

**課題文脈（Problem Context）**：
- トリガーワード：*problem, issue, difficulty, challenge, drawback, disadvantage, improve, detect, defect, lesion, tumor, abnormality* など
- 技術的課題・改善が必要な状態を記述した文を抽出

**解決手段文脈（Solution Context）**：
- トリガーワード：*method, system, apparatus, model, network, comprises, configured to, training, segmentation* など
- 提案された技術的アプローチを記述した文を抽出

**技術手段（Technical Means）**：
- 手法名辞書（U-Net, YOLO, GAN, Transformer など）とのマッチング
- 文書中に出現する具体的な手法名のリスト

### 3.2 LLMによる補完（オプション）

`prompts/problem_solution_extraction_prompt.md` に示すプロンプトを用いて、GPT-4などのLLMで高精度な構造抽出を行うことができる。LLM抽出結果はルールベース結果と比較・補完する位置づけとする。

---

## 4. PatentSBERTaによるベクトル化

抽出された各文脈テキストを事前学習済み特許特化型言語モデル **PatentSBERTa**（Sentence-BERT の特許ドメインファインチューニング版）でベクトル化する。

$$\mathbf{e}_{i}^{\text{problem}} = \text{PatentSBERTa}(\text{problem\_context}_i) \in \mathbb{R}^{768}$$

$$\mathbf{e}_{i}^{\text{solution}} = \text{PatentSBERTa}(\text{solution\_context}_i) \in \mathbb{R}^{768}$$

PatentSBERTaが利用できない場合は、`sentence-transformers/all-MiniLM-L6-v2` をフォールバックとして使用する。

**ドメイン代表ベクトル**は各ドメインの平均ベクトルとして定義する：

$$\bar{\mathbf{e}}_{\text{A0}}^{\text{problem}} = \frac{1}{|A_0|}\sum_{i \in A_0} \mathbf{e}_{i}^{\text{problem}}$$

**コサイン類似度**によってドメイン間の課題構造の類似性を定量化する：

$$\text{sim}(A_0, B_0) = \cos\!\left(\bar{\mathbf{e}}_{\text{A0}}^{\text{problem}},\; \bar{\mathbf{e}}_{\text{B0}}^{\text{problem}}\right)$$

---

## 5. GapScore の定義と計算

### 5.1 Method Gap

各技術手法 $m$ について、A0とB0の**過去期間における出現率差**（Method Gap）を計算する：

$$\text{rate}_{A,m} = \frac{|\{d \in A_0^{\text{past}} : m \in d\}|}{|A_0^{\text{past}}|}$$

$$\text{rate}_{B,m} = \frac{|\{d \in B_0^{\text{past}} : m \in d\}|}{|B_0^{\text{past}}|}$$

$$\text{gap}_m = \text{rate}_{A,m} - \text{rate}_{B,m}$$

### 5.2 GapScore（埋め込みあり版）

$$\text{GapScore}_m = \underbrace{\text{sim}^{\text{prob}}(A_0^{\text{unet}}, B_0)}_{\text{課題類似度}} \times \underbrace{\frac{\text{gap}_m}{\max_j \text{gap}_j}}_{\text{正規化Gap}} \times \underbrace{\log(1 + N_{A,m})}_{\text{頻度重み}} \times \underbrace{\min\!\left(\frac{1}{\text{rate}_{B,m} + \varepsilon},\; C\right)}_{\text{低出現ボーナス}}$$

各項の意味：

| 項 | 記号 | 意味 |
|---|---|---|
| 課題類似度 | $\text{sim}^{\text{prob}}$ | A0のU-Net特許群の課題ベクトルとB0全体の課題ベクトルのコサイン類似度 |
| 正規化Gap | normalized\_gap | A0-B0の出現率差を最大値で正規化 |
| 頻度重み | $\log(1 + N_{A,m})$ | A0での出現件数の対数（稀すぎる手法にペナルティ） |
| 低出現ボーナス | low\_presence\_bonus | B0での出現が少ない手法ほど高いスコア（探索価値が高い） |
| $\varepsilon$ | epsilon | ゼロ除算回避定数（$10^{-6}$） |
| $C$ | cap | ボーナス上限（10.0） |

### 5.3 GapScore_simple（埋め込みなし版）

埋め込みが利用できない場合は以下のシンプル版を使用する：

$$\text{GapScore\_simple}_m = \text{gap}_m \times \log(1 + N_{A,m}) \times \text{low\_presence\_bonus}_m$$

---

## 6. 分析の解釈上の注意点

- 本手法は「専門家が確認すべき候補を抽出する」ためのスクリーニング手法である。
- GapScoreが高い手法が将来的にドメインBで出現増加する候補として浮上することを、後ろ向き評価で確認する。
- 候補抽出の可能性を示すものであり、技術的・経済的な実現可能性や事業化の可能性を主張するものではない。
- 候補リストは専門家のレビューを経て活用することが前提となる。
