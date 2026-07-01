# LLM Prompt: Patent Problem-Solution Context Extraction

## Purpose

This prompt extracts a patent's problem context and solution context from `Title`, `Abstract`, and `Claims`.
The output is used for separate embedding of problem-side text and solution-side text in a cross-domain technology candidate screening pipeline.

## Prompt

あなたは特許文書を分析する研究補助者である。入力された特許の `Title`、`Abstract`、`Claims` を読み、発明が扱う「課題文脈」と、その課題に対する「解決手段文脈」を分けて抽出せよ。

本研究では、課題文脈と解決手段文脈を別々にベクトル化する。そのため、`problem_context` には解決手段を混ぜず、`solution_context` には課題説明を混ぜないこと。

### Input

```json
{
  "title": "Patent title",
  "abstract": "Patent abstract",
  "claims": "Patent claims"
}
```

### Output

JSON のみを出力すること。説明文、Markdown、コードブロックは出力しない。

```json
{
  "problem_context": "",
  "solution_context": "",
  "technical_means": [],
  "target_object": "",
  "effect_context": "",
  "application_field": "",
  "problem_evidence": "",
  "solution_evidence": "",
  "confidence": "high"
}
```

## Field Definitions

### problem_context

発明が解決しようとする技術的課題を、日本語で1〜3文に要約する。

含める内容：
- 従来技術の問題点
- 精度、効率、コスト、安定性、検出漏れ、誤検出、残渣、ノイズなどの課題
- 解決したい目的、必要性、制約

含めてはいけない内容：
- 提案された装置構成、処理手順、モデル構造、材料組成
- 「U-Netを用いる」「学習モデルを用いる」などの解決手段

### solution_context

課題を解決するために提案された技術的手段を、日本語で1〜3文に要約する。

含める内容：
- システム、方法、装置、モデル、材料、アルゴリズム、処理フロー
- Claims に記載された構成要素や処理ステップ
- U-Net、CNN、GAN、Transformer、洗浄剤組成物、基板処理方法などの具体的な手段

含めてはいけない内容：
- 従来技術の問題点だけの説明
- 効果だけの説明

### technical_means

本文に明示されている具体的な技術手段を、原則として1〜5個の配列で出力する。
U-NetやCNNのような明示的な手法名がない場合でも、Claimsやsolution_contextから、装置構成、処理方法、学習方式、検出方式、分類方式、撮像方式、材料、組成物、洗浄方法などを抽出する。
ただし、本文に根拠がない内容は推測しない。

よい例：
- `"U-Net"`
- `"encoder-decoder network"`
- `"attention mechanism"`
- `"defect candidate image generation"`
- `"substrate cleaning composition"`
- `"image processing apparatus"`
- `"defect detection method"`
- `"cleaning method"`

避ける例：
- `"AI"`
- `"deep learning"` だけ
- `"method"` だけ

### target_object

処理、検出、分類、洗浄、分析などの対象を具体的に書く。

例：
- 医療画像
- CT画像中の腫瘍領域
- 鋼材表面の欠陥
- 半導体ウェハ
- 基板上の残渣

### effect_context

本文に根拠がある場合のみ、発明による効果を日本語で1文に要約する。
不明な場合は空文字にする。

### application_field

用途分野を簡潔に書く。

例：
- 医療画像解析
- 製造欠陥検出
- 半導体洗浄
- 表面検査

### problem_evidence

`problem_context` の根拠となる原文の短い抜粋を入れる。
入力文に根拠がない場合は空文字にする。

### solution_evidence

`solution_context` の根拠となる原文の短い抜粋を入れる。
入力文に根拠がない場合は空文字にする。

### confidence

抽出の確信度を `"high"`、`"medium"`、`"low"` のいずれかで出力する。

- `"high"`: 課題と解決手段が明示的に分かれている。
- `"medium"`: どちらか一方がやや暗示的だが、本文から妥当に抽出できる。
- `"low"`: 情報が不足している、または課題と解決手段の分離が難しい。

## Rules

1. `Title`、`Abstract`、`Claims` をすべて根拠として使ってよい。
2. `Claims` は主に解決手段の根拠として扱う。ただし、課題が明示されている場合は課題文脈にも使ってよい。
3. `Abstract` に「課題」「解決手段」「効果」が明示されている場合は、その区別を優先する。
4. 課題文脈と解決手段文脈を混ぜない。
5. 本文にない内容を推測しない。
6. 入力が英語・日本語・中国語などの場合でも、出力の要約文は日本語に統一する。
7. 原文抜粋の `problem_evidence` と `solution_evidence` は、入力文の表現を短く残す。
8. `technical_means` は、solution_contextまたはClaimsに根拠がある限り、できるだけ空配列にしない。
9. 該当情報が本当にないフィールドは、空文字 `""` または空配列 `[]` にする。
10. JSON として機械的に解析できる形式で出力する。

## Example

### Input

```json
{
  "title": "Automated segmentation of liver tumors in CT images using modified U-Net",
  "abstract": "Accurate delineation of liver tumors in computed tomography images is crucial for treatment planning but remains challenging due to low contrast and irregular tumor boundaries. The invention proposes a modified U-Net architecture incorporating attention gates and deep supervision to improve segmentation accuracy.",
  "claims": "A medical image processing system comprising an encoder-decoder neural network, skip connections, attention gates, and an output layer configured to generate a tumor segmentation mask from a CT image."
}
```

### Output

```json
{
  "problem_context": "CT画像における肝腫瘍領域の正確な抽出は治療計画に重要であるが、低コントラストや不規則な腫瘍境界により困難である。",
  "solution_context": "エンコーダ・デコーダ型の修正U-Netにスキップ接続、attention gate、deep supervisionを組み込み、CT画像から腫瘍セグメンテーションマスクを生成する。",
  "technical_means": ["U-Net", "encoder-decoder neural network", "skip connections", "attention gates", "deep supervision"],
  "target_object": "CT画像中の肝腫瘍領域",
  "effect_context": "肝腫瘍セグメンテーションの精度向上を目的とする。",
  "application_field": "医療画像解析",
  "problem_evidence": "remains challenging due to low contrast and irregular tumor boundaries",
  "solution_evidence": "modified U-Net architecture incorporating attention gates and deep supervision",
  "confidence": "high"
}
```

## Use in This Thesis

The `problem_context` field is embedded as the problem-side vector.
The `solution_context` field is embedded as the solution-side vector.
The method does not prove technical adoptability; it screens candidates that should be reviewed by experts.
