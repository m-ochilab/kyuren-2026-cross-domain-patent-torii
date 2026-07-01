"use strict";
const pptxgen = require("pptxgenjs");
const path = require("path");

const BASE = path.join(__dirname);
const FIGS = path.join(BASE, "figures");

// --- Color palette (Midnight Executive + accent) ---
const C = {
  NAVY:       "1E2761",
  ICE:        "C8D8F0",
  WHITE:      "FFFFFF",
  LGRAY:      "F2F5FA",
  DTEXT:      "1A1A2E",
  MTEXT:      "4A5568",
  CAPTION:    "718096",
  ACCENT:     "2563EB",
  ACCENT2:    "0EA5E9",
  HIGHLIGHT:  "F59E0B",
  GREEN:      "10B981",
  RED:        "EF4444",
  BORDER:     "CBD5E0",
};

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10" × 5.625"
pres.title = "特許文書を用いたクロスドメイン技術候補抽出";
pres.author = "";

// ─── helpers ─────────────────────────────────────────────────────────────────

function slideTitle(slide, text, opts = {}) {
  const color = opts.dark ? C.WHITE : C.NAVY;
  slide.addText(text, {
    x: 0.5, y: 0.22, w: 9.0, h: 0.7,
    fontSize: 26, bold: true, color,
    fontFace: "Hiragino Kaku Gothic ProN",
    valign: "middle",
    margin: 0,
  });
}

function slideSubtitle(slide, text, opts = {}) {
  const color = opts.dark ? "A0B8E0" : C.MTEXT;
  slide.addText(text, {
    x: 0.5, y: 0.9, w: 9.0, h: 0.4,
    fontSize: 13, color,
    fontFace: "Hiragino Kaku Gothic ProN",
    valign: "middle",
    margin: 0,
  });
}

function hRule(slide, opts = {}) {
  const color = opts.dark ? "3B5A9A" : C.ICE;
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 0.94, w: 9.0, h: 0.03,
    fill: { color }, line: { color, width: 0 },
  });
}

function bullet(text, sub = false) {
  return { text, options: { bullet: true, indentLevel: sub ? 1 : 0, breakLine: true } };
}

function imgPath(name) { return path.join(FIGS, name); }

// ─── SLIDE 1 · Title ─────────────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.NAVY };

  // top accent bar
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.18,
    fill: { color: C.ACCENT2 }, line: { color: C.ACCENT2, width: 0 },
  });

  // main title
  sl.addText("特許文書を用いたクロスドメイン技術候補抽出", {
    x: 0.7, y: 1.3, w: 8.6, h: 1.0,
    fontSize: 32, bold: true, color: C.WHITE,
    fontFace: "Hiragino Kaku Gothic ProN",
    align: "center", valign: "middle",
  });

  // subtitle
  sl.addText("課題・解決手段分離型アプローチによるU-Net応用事例の後ろ向き検証", {
    x: 0.7, y: 2.45, w: 8.6, h: 0.55,
    fontSize: 16, color: "CADCF8",
    fontFace: "Hiragino Kaku Gothic ProN",
    align: "center", valign: "middle",
  });

  // divider
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 3.5, y: 3.15, w: 3.0, h: 0.04,
    fill: { color: C.ACCENT2 }, line: { color: C.ACCENT2, width: 0 },
  });

  // author placeholder
  sl.addText("氏名：_______________", {
    x: 0.7, y: 3.35, w: 8.6, h: 0.4,
    fontSize: 14, color: "8AAAD0",
    fontFace: "Hiragino Kaku Gothic ProN",
    align: "center",
  });

  sl.addText("2026年 卒業論文 発表", {
    x: 0.7, y: 3.85, w: 8.6, h: 0.35,
    fontSize: 12, color: "6688B8",
    fontFace: "Hiragino Kaku Gothic ProN",
    align: "center",
  });

  // bottom bar
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.43, w: 10, h: 0.195,
    fill: { color: "162050" }, line: { color: "162050", width: 0 },
  });
}

// ─── SLIDE 2 · 研究背景 ───────────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.LGRAY };

  // Navy left stripe
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.NAVY }, line: { color: C.NAVY, width: 0 },
  });

  slideTitle(sl, "研究背景");
  hRule(sl);

  // Left column - main content
  sl.addText([
    bullet("特許文書は技術動向・R&D活動を反映する重要な情報源"),
    bullet("異なる技術分野でも「取り組む課題」が類似する場合がある"),
    bullet("例：医療画像解析と製造欠陥検出", true),
    bullet("→ 「異常領域の高精度検出・分割」という課題構造が近い", true),
    bullet("近年はBERT/Sentence-BERTによる特許埋め込みが進展"),
    bullet("しかし——課題文脈と解決手段文脈が混在する問題がある"),
  ], {
    x: 0.6, y: 1.1, w: 5.8, h: 4.1,
    fontSize: 14, color: C.DTEXT,
    fontFace: "Hiragino Kaku Gothic ProN",
    paraSpaceAfter: 6,
  });

  // Right column - example box
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 6.7, y: 1.05, w: 3.0, h: 4.15,
    fill: { color: C.WHITE },
    shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.10 },
    line: { color: C.BORDER, width: 1 },
  });

  sl.addText("技術分野間の類似性", {
    x: 6.75, y: 1.12, w: 2.9, h: 0.35,
    fontSize: 11, bold: true, color: C.ACCENT,
    fontFace: "Hiragino Kaku Gothic ProN",
    align: "center",
  });

  // Domain A box
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 6.8, y: 1.52, w: 2.8, h: 0.9,
    fill: { color: "EBF5FB" }, line: { color: "90BDD9", width: 1 },
  });
  sl.addText("医療画像解析（参照分野）\n腫瘍・病変の検出・分割", {
    x: 6.8, y: 1.52, w: 2.8, h: 0.9,
    fontSize: 11, color: C.NAVY,
    fontFace: "Hiragino Kaku Gothic ProN",
    align: "center", valign: "middle",
  });

  // Arrow
  sl.addText("↕ 課題構造が近い", {
    x: 6.8, y: 2.48, w: 2.8, h: 0.35,
    fontSize: 11, bold: true, color: C.HIGHLIGHT,
    fontFace: "Hiragino Kaku Gothic ProN",
    align: "center",
  });

  // Domain B box
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 6.8, y: 2.85, w: 2.8, h: 0.9,
    fill: { color: "E8F6EF" }, line: { color: "7DBBA5", width: 1 },
  });
  sl.addText("製造欠陥検出（対象分野）\n管路・鋼材表面の欠陥検出", {
    x: 6.8, y: 2.85, w: 2.8, h: 0.9,
    fontSize: 11, color: "1A5E3A",
    fontFace: "Hiragino Kaku Gothic ProN",
    align: "center", valign: "middle",
  });

  sl.addText("→ 参照分野の技術が対象分野に転用できる可能性", {
    x: 6.8, y: 3.82, w: 2.8, h: 0.75,
    fontSize: 10, color: C.MTEXT, italic: true,
    fontFace: "Hiragino Kaku Gothic ProN",
    align: "center", valign: "middle",
  });

  // page number
  sl.addText("2", { x: 9.5, y: 5.35, w: 0.4, h: 0.2, fontSize: 9, color: C.CAPTION, align: "right", margin: 0 });
}

// ─── SLIDE 3 · 問題意識 ───────────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.LGRAY };
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.NAVY }, line: { color: C.NAVY, width: 0 },
  });

  slideTitle(sl, "問題意識");
  hRule(sl);

  // Problem box
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.1, w: 9.0, h: 1.15,
    fill: { color: "FEF3C7" }, line: { color: "F59E0B", width: 2 },
  });
  sl.addText("既存研究の課題", {
    x: 0.6, y: 1.13, w: 2.0, h: 0.3,
    fontSize: 11, bold: true, color: C.HIGHLIGHT,
    fontFace: "Hiragino Kaku Gothic ProN", margin: 0,
  });
  sl.addText("既存の特許埋め込み研究では、特許全文を「1つのベクトル」として扱う。\nそのため、課題文脈（何を解決しようとしているか）と解決手段文脈（どう解決しているか）が混在してしまう。", {
    x: 0.6, y: 1.44, w: 8.8, h: 0.75,
    fontSize: 13, color: C.DTEXT,
    fontFace: "Hiragino Kaku Gothic ProN",
  });

  // Explanation cards
  const cards = [
    { x: 0.5, label: "問題①", text: "「なぜこの候補が選ばれたか」\nが説明しにくい", bg: "FEF2F2", border: "FECACA", tc: "991B1B" },
    { x: 3.6, label: "問題②", text: "課題の近さ vs 解決手段の近さ\nの区別ができない", bg: "FEF2F2", border: "FECACA", tc: "991B1B" },
    { x: 6.7, label: "問題③", text: "対象分野で低出現かどうかを\n独立に確認できない", bg: "FEF2F2", border: "FECACA", tc: "991B1B" },
  ];

  for (const c of cards) {
    sl.addShape(pres.shapes.RECTANGLE, {
      x: c.x, y: 2.45, w: 2.9, h: 1.2,
      fill: { color: c.bg }, line: { color: c.border, width: 1.5 },
    });
    sl.addText(c.label, {
      x: c.x + 0.08, y: 2.48, w: 2.7, h: 0.3,
      fontSize: 11, bold: true, color: c.tc,
      fontFace: "Hiragino Kaku Gothic ProN", margin: 0,
    });
    sl.addText(c.text, {
      x: c.x + 0.08, y: 2.79, w: 2.74, h: 0.82,
      fontSize: 12, color: C.DTEXT,
      fontFace: "Hiragino Kaku Gothic ProN", valign: "top",
    });
  }

  // Solution hint
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 3.85, w: 9.0, h: 1.4,
    fill: { color: "EFF6FF" }, line: { color: "BFDBFE", width: 1.5 },
  });
  sl.addText("本研究のアプローチ", {
    x: 0.65, y: 3.9, w: 3.0, h: 0.3,
    fontSize: 11, bold: true, color: C.ACCENT,
    fontFace: "Hiragino Kaku Gothic ProN", margin: 0,
  });
  sl.addText([
    bullet("特許文書を「課題文脈」と「解決手段文脈」に分けて抽出・ベクトル化"),
    bullet("課題の近さと解決手段の出現率差（手法ギャップ）を分離して評価"),
    bullet("→ クロスドメイン技術候補の抽出理由を説明可能にする"),
  ], {
    x: 0.65, y: 4.22, w: 8.7, h: 0.95,
    fontSize: 12.5, color: C.DTEXT,
    fontFace: "Hiragino Kaku Gothic ProN",
  });

  sl.addText("3", { x: 9.5, y: 5.35, w: 0.4, h: 0.2, fontSize: 9, color: C.CAPTION, align: "right", margin: 0 });
}

// ─── SLIDE 4 · 研究目的・研究課題 ────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.LGRAY };
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.NAVY }, line: { color: C.NAVY, width: 0 },
  });

  slideTitle(sl, "研究目的・研究課題");
  hRule(sl);

  // Objective box
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.1, w: 9.0, h: 1.1,
    fill: { color: C.NAVY }, line: { color: C.NAVY, width: 0 },
  });
  sl.addText("研究目的", {
    x: 0.65, y: 1.13, w: 1.8, h: 0.3,
    fontSize: 11, bold: true, color: C.ICE,
    fontFace: "Hiragino Kaku Gothic ProN", margin: 0,
  });
  sl.addText(
    "特許文書から課題文脈と解決手段文脈を分離・抽出し、課題が近い異分野間において、\n対象分野では低出現の技術手法を専門家確認候補として抽出できるかを検討する。",
    {
      x: 0.65, y: 1.42, w: 8.7, h: 0.72,
      fontSize: 13, color: C.WHITE,
      fontFace: "Hiragino Kaku Gothic ProN",
    }
  );

  // RQ cards
  const rqs = [
    {
      id: "RQ1", color: "2563EB",
      title: "候補抽出理由の説明可能性",
      text: "課題文脈と解決手段文脈を分離することで、異分野技術候補の抽出理由を説明可能にできるか？",
    },
    {
      id: "RQ2", color: "7C3AED",
      title: "過去期間での低出現候補抽出",
      text: "2015–2018年の過去期間において、U-Netを製造欠陥検出分野の低出現候補として抽出できるか？",
    },
    {
      id: "RQ3", color: "0D9488",
      title: "将来期間での出現・増加との対応",
      text: "過去期間に抽出した候補が、2019–2024年の将来評価期間での出現・増加と対応するか？",
    },
  ];

  const rqY = 2.35;
  const rqW = 2.8;
  const rqGap = 0.18;
  for (let i = 0; i < rqs.length; i++) {
    const rq = rqs[i];
    const x = 0.5 + i * (rqW + rqGap);
    sl.addShape(pres.shapes.RECTANGLE, {
      x, y: rqY, w: rqW, h: 2.9,
      fill: { color: C.WHITE },
      shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 135, opacity: 0.10 },
      line: { color: C.BORDER, width: 1 },
    });
    // Top accent
    sl.addShape(pres.shapes.RECTANGLE, {
      x, y: rqY, w: rqW, h: 0.28,
      fill: { color: rq.color }, line: { color: rq.color, width: 0 },
    });
    sl.addText(rq.id, {
      x: x + 0.08, y: rqY + 0.01, w: rqW - 0.16, h: 0.26,
      fontSize: 14, bold: true, color: C.WHITE,
      fontFace: "Hiragino Kaku Gothic ProN",
      align: "center", valign: "middle", margin: 0,
    });
    sl.addText(rq.title, {
      x: x + 0.1, y: rqY + 0.32, w: rqW - 0.2, h: 0.55,
      fontSize: 12, bold: true, color: rq.color,
      fontFace: "Hiragino Kaku Gothic ProN",
      valign: "top",
    });
    sl.addText(rq.text, {
      x: x + 0.1, y: rqY + 0.92, w: rqW - 0.2, h: 2.2,
      fontSize: 12, color: C.DTEXT,
      fontFace: "Hiragino Kaku Gothic ProN",
      valign: "top",
    });
  }

  sl.addText("4", { x: 9.5, y: 5.35, w: 0.4, h: 0.2, fontSize: 9, color: C.CAPTION, align: "right", margin: 0 });
}

// ─── SLIDE 5 · 提案フレームワーク ────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.LGRAY };
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.NAVY }, line: { color: C.NAVY, width: 0 },
  });

  slideTitle(sl, "提案フレームワーク");
  hRule(sl);

  // Figure: aspect ratio 1272/623 ≈ 2.04
  const figH = 3.5;
  const figW = figH * (1272 / 623);
  const figX = (10 - figW) / 2;
  sl.addImage({ path: imgPath("fig01_framework.png"), x: figX, y: 1.05, w: figW, h: figH });

  sl.addText("課題ベクトル・解決手段ベクトルを分離して計算し、手法ギャップから専門家確認候補を抽出するフレームワーク", {
    x: 0.5, y: 4.65, w: 9.0, h: 0.4,
    fontSize: 11, italic: true, color: C.CAPTION,
    fontFace: "Hiragino Kaku Gothic ProN",
    align: "center",
  });

  sl.addText("5", { x: 9.5, y: 5.35, w: 0.4, h: 0.2, fontSize: 9, color: C.CAPTION, align: "right", margin: 0 });
}

// ─── SLIDE 6 · 課題文脈・解決手段文脈の定義 ──────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.LGRAY };
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.NAVY }, line: { color: C.NAVY, width: 0 },
  });

  slideTitle(sl, "課題・解決手段文脈の定義と抽出");
  hRule(sl);

  // Left: definitions
  const defs = [
    { label: "課題文脈", color: "2563EB", text: "従来技術の問題点・解決したい課題・目的・必要性\n(problem, issue, difficulty, challenge など)" },
    { label: "解決手段文脈", color: "0D9488", text: "課題を解く構成・方法・材料・アルゴリズム\n(method, system, network, comprises など)" },
    { label: "技術手段", color: "7C3AED", text: "具体的な手法名（U-Net, YOLO, GAN …）\n→ 候補ラベル化に使用" },
  ];

  for (let i = 0; i < defs.length; i++) {
    const d = defs[i];
    const y = 1.08 + i * 1.15;
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 0.22, h: 0.9,
      fill: { color: d.color }, line: { color: d.color, width: 0 },
    });
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0.72, y, w: 4.4, h: 0.9,
      fill: { color: C.WHITE }, line: { color: C.BORDER, width: 1 },
    });
    sl.addText(d.label, {
      x: 0.75, y: y + 0.05, w: 4.3, h: 0.28,
      fontSize: 13, bold: true, color: d.color,
      fontFace: "Hiragino Kaku Gothic ProN", margin: 0,
    });
    sl.addText(d.text, {
      x: 0.75, y: y + 0.34, w: 4.3, h: 0.52,
      fontSize: 11, color: C.MTEXT,
      fontFace: "Hiragino Kaku Gothic ProN", valign: "top",
    });
  }

  sl.addText("抽出方法：ルールベース（トリガーキーワード） + LLM補完（GPT-4等、オプション）", {
    x: 0.5, y: 4.5, w: 5.4, h: 0.35,
    fontSize: 11, italic: true, color: C.CAPTION,
    fontFace: "Hiragino Kaku Gothic ProN",
  });

  // Right: figure  1147×623 ≈ 1.84
  const figH = 3.5;
  const figW = figH * (1147 / 623);
  sl.addImage({ path: imgPath("fig02_problem_solution_split.png"), x: 5.35, y: 1.05, w: figW, h: figH });
  sl.addText("課題文脈・解決手段文脈の分離イメージ", {
    x: 5.35, y: 4.65, w: figW, h: 0.3,
    fontSize: 9, italic: true, color: C.CAPTION,
    fontFace: "Hiragino Kaku Gothic ProN", align: "center",
  });

  sl.addText("6", { x: 9.5, y: 5.35, w: 0.4, h: 0.2, fontSize: 9, color: C.CAPTION, align: "right", margin: 0 });
}

// ─── SLIDE 7 · 手法ギャップの定義 ────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.LGRAY };
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.NAVY }, line: { color: C.NAVY, width: 0 },
  });

  slideTitle(sl, "手法ギャップ（Method Gap）と候補抽出モード");
  hRule(sl);

  // Gap formula box
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.08, w: 5.5, h: 1.35,
    fill: { color: C.WHITE }, line: { color: C.ICE, width: 1.5 },
  });
  sl.addText("手法ギャップの定義", {
    x: 0.65, y: 1.12, w: 5.2, h: 0.3,
    fontSize: 12, bold: true, color: C.NAVY,
    fontFace: "Hiragino Kaku Gothic ProN", margin: 0,
  });
  sl.addText("Gap(m; A, B)  =  rateₐ(m) − rate⸮(m)", {
    x: 0.65, y: 1.44, w: 5.2, h: 0.45,
    fontSize: 18, bold: true, color: C.ACCENT,
    fontFace: "Courier New",
    align: "center",
  });
  sl.addText("rateₐ: 参照分野Aでの出現率  ／  rate⸮: 対象分野Bでの出現率", {
    x: 0.65, y: 1.93, w: 5.2, h: 0.4,
    fontSize: 11, color: C.MTEXT,
    fontFace: "Hiragino Kaku Gothic ProN",
    align: "center",
  });

  // GapScore box
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 2.56, w: 5.5, h: 1.3,
    fill: { color: "EFF6FF" }, line: { color: "BFDBFE", width: 1.5 },
  });
  sl.addText("GapScore（スクリーニング指標）", {
    x: 0.65, y: 2.6, w: 5.2, h: 0.3,
    fontSize: 12, bold: true, color: C.ACCENT,
    fontFace: "Hiragino Kaku Gothic ProN", margin: 0,
  });
  sl.addText("課題類似度 × 正規化Gap × log(1+Nₐ) × 低出現ボーナス", {
    x: 0.65, y: 2.93, w: 5.2, h: 0.35,
    fontSize: 12.5, color: C.DTEXT,
    fontFace: "Hiragino Kaku Gothic ProN",
    align: "center",
  });
  sl.addText("※ 技術導入可能性を断定しない。専門家確認候補の絞り込み指標として使用する。", {
    x: 0.65, y: 3.3, w: 5.2, h: 0.45,
    fontSize: 10, italic: true, color: C.CAPTION,
    fontFace: "Hiragino Kaku Gothic ProN",
  });

  // Candidate modes - right side
  const modes = [
    {
      label: "近接解決策型",
      cond: "課題類似度 高\n解決手段類似度 高",
      text: "似た課題を似た解決方向で解いている他分野から、対象分野で低出現の手法を候補として抽出\n（U-Netが典型例）",
      bg: "EFF6FF", bc: "BFDBFE", tc: C.ACCENT,
    },
    {
      label: "異質解決策型",
      cond: "課題類似度 高\n解決手段の方向が異なる",
      text: "似た課題に対して異なる解決方向を取る他分野から、新しい発想候補を得る（補助ケース）",
      bg: "F0FDF4", bc: "BBF7D0", tc: "059669",
    },
  ];

  for (let i = 0; i < modes.length; i++) {
    const m = modes[i];
    const y = 1.08 + i * 1.9;
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 6.25, y, w: 3.45, h: 1.7,
      fill: { color: m.bg }, line: { color: m.bc, width: 1.5 },
    });
    sl.addText(m.label, {
      x: 6.35, y: y + 0.06, w: 3.25, h: 0.3,
      fontSize: 13, bold: true, color: m.tc,
      fontFace: "Hiragino Kaku Gothic ProN", margin: 0,
    });
    sl.addText(m.cond, {
      x: 6.35, y: y + 0.38, w: 3.25, h: 0.45,
      fontSize: 11, bold: true, color: C.DTEXT,
      fontFace: "Hiragino Kaku Gothic ProN",
    });
    sl.addText(m.text, {
      x: 6.35, y: y + 0.84, w: 3.25, h: 0.8,
      fontSize: 11, color: C.MTEXT,
      fontFace: "Hiragino Kaku Gothic ProN",
    });
  }

  sl.addText("本研究では近接解決策型（U-Net）を主分析とする", {
    x: 0.5, y: 5.06, w: 9.2, h: 0.3,
    fontSize: 11, bold: true, color: C.NAVY, italic: true,
    fontFace: "Hiragino Kaku Gothic ProN",
    align: "center",
  });

  sl.addText("7", { x: 9.5, y: 5.35, w: 0.4, h: 0.2, fontSize: 9, color: C.CAPTION, align: "right", margin: 0 });
}

// ─── SLIDE 8 · 後ろ向き評価設計 ──────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.LGRAY };
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.NAVY }, line: { color: C.NAVY, width: 0 },
  });

  slideTitle(sl, "後ろ向き評価設計");
  hRule(sl);

  // Text left
  sl.addText([
    bullet("過去期間（2015–2018年）"),
    bullet("候補抽出に使用", true),
    bullet("参照分野(A0)で先行出現・対象分野(B0)で低出現の手法を特定", true),
    bullet("将来評価期間（2019–2024年）"),
    bullet("過去に抽出した候補が対象分野で出現・増加するかを確認", true),
    bullet("理由：U-Netは既知のクロスドメイン応用事例 → 後ろ向き検証に最適"),
    bullet("注：技術移転の因果を証明するものではなく、枠組みの妥当性を確認する設計"),
  ], {
    x: 0.5, y: 1.08, w: 4.7, h: 4.0,
    fontSize: 13, color: C.DTEXT,
    fontFace: "Hiragino Kaku Gothic ProN",
    paraSpaceAfter: 5,
  });

  // Figure: 1147×536 ≈ 2.14
  const figH = 3.5;
  const figW = figH * (1147 / 536);
  sl.addImage({ path: imgPath("fig03_evaluation_design.png"), x: 5.35, y: 1.05, w: figW, h: figH });
  sl.addText("過去期間・将来評価期間を用いた後ろ向き評価設計", {
    x: 5.35, y: 4.65, w: figW, h: 0.3,
    fontSize: 9, italic: true, color: C.CAPTION,
    fontFace: "Hiragino Kaku Gothic ProN", align: "center",
  });

  sl.addText("8", { x: 9.5, y: 5.35, w: 0.4, h: 0.2, fontSize: 9, color: C.CAPTION, align: "right", margin: 0 });
}

// ─── SLIDE 9 · データセット定義 ──────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.LGRAY };
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.NAVY }, line: { color: C.NAVY, width: 0 },
  });

  slideTitle(sl, "データセット定義");
  hRule(sl);

  // Table
  const header = [
    { text: "ラベル", options: { bold: true, color: C.WHITE, fill: { color: C.NAVY }, fontSize: 12 } },
    { text: "内容", options: { bold: true, color: C.WHITE, fill: { color: C.NAVY }, fontSize: 12 } },
    { text: "Publication数", options: { bold: true, color: C.WHITE, fill: { color: C.NAVY }, fontSize: 12 } },
    { text: "Family ID数", options: { bold: true, color: C.WHITE, fill: { color: C.NAVY }, fontSize: 12 } },
    { text: "役割", options: { bold: true, color: C.WHITE, fill: { color: C.NAVY }, fontSize: 12 } },
  ];
  const rows = [
    [
      { text: "A0", options: { bold: true, color: C.ACCENT, fill: { color: "EFF6FF" } } },
      "医療画像解析（全体）",
      "15,167", "8,513",
      "参照分野の母集団",
    ],
    [
      { text: "A1", options: { bold: true, color: C.ACCENT, fill: { color: "EFF6FF" } } },
      "医療画像解析 × U-Net",
      "804", "577",
      "参照分野のU-Net関連集合",
    ],
    [
      { text: "B0", options: { bold: true, color: "059669", fill: { color: "F0FDF4" } } },
      "製造欠陥検出（全体）",
      "12,212", "8,898",
      "対象分野の母集団",
    ],
    [
      { text: "B1", options: { bold: true, color: "059669", fill: { color: "F0FDF4" } } },
      "製造欠陥検出 × U-Net",
      "72", "49",
      "対象分野のU-Net関連集合",
    ],
  ];
  sl.addTable([header, ...rows], {
    x: 0.5, y: 1.08, w: 5.6, h: 2.5,
    border: { pt: 1, color: C.BORDER },
    fontSize: 12,
    fontFace: "Hiragino Kaku Gothic ProN",
    colW: [0.7, 2.0, 1.05, 1.05, 1.6],
  });

  sl.addText("データ取得元：Orbis IP｜期間：Filing date 2015–2024年\nU-Net関連はTitle/Abstractに「U-Net」「UNet」「U Net」を含むものを抽出", {
    x: 0.5, y: 3.65, w: 5.6, h: 0.65,
    fontSize: 11, italic: true, color: C.CAPTION,
    fontFace: "Hiragino Kaku Gothic ProN",
  });

  // Figure: 1185×732 ≈ 1.62
  const figH = 2.9;
  const figW = figH * (1185 / 732);
  sl.addImage({ path: imgPath("fig07_dataset_overview.png"), x: 6.3, y: 1.05, w: figW, h: figH });
  sl.addText("データセット別Publication数", {
    x: 6.3, y: 4.02, w: figW, h: 0.3,
    fontSize: 9, italic: true, color: C.CAPTION,
    fontFace: "Hiragino Kaku Gothic ProN", align: "center",
  });

  sl.addText("9", { x: 9.5, y: 5.35, w: 0.4, h: 0.2, fontSize: 9, color: C.CAPTION, align: "right", margin: 0 });
}

// ─── SLIDE 10 · 結果① 全期間U-Net出現率 (RQ1) ───────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.LGRAY };
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.NAVY }, line: { color: C.NAVY, width: 0 },
  });

  slideTitle(sl, "結果① 全期間U-Net出現率　〔RQ1〕");
  hRule(sl);

  // Large stat callouts
  const stats = [
    { label: "医療画像解析\n（参照分野 A0）", pub: "5.30%", fam: "6.78%", color: C.ACCENT, bg: "EFF6FF", bc: "BFDBFE" },
    { label: "製造欠陥検出\n（対象分野 B0）", pub: "0.59%", fam: "0.55%", color: "059669", bg: "F0FDF4", bc: "BBF7D0" },
  ];

  for (let i = 0; i < stats.length; i++) {
    const s = stats[i];
    const x = 0.5 + i * 4.6;
    sl.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.08, w: 4.3, h: 3.2,
      fill: { color: s.bg }, line: { color: s.bc, width: 1.5 },
    });
    sl.addText(s.label, {
      x: x + 0.15, y: 1.12, w: 4.0, h: 0.55,
      fontSize: 13, bold: true, color: s.color,
      fontFace: "Hiragino Kaku Gothic ProN",
      align: "center",
    });
    // Publication rate big
    sl.addText("Publication率", {
      x: x + 0.15, y: 1.73, w: 4.0, h: 0.3,
      fontSize: 11, color: C.MTEXT,
      fontFace: "Hiragino Kaku Gothic ProN",
      align: "center",
    });
    sl.addText(s.pub, {
      x: x + 0.15, y: 2.0, w: 4.0, h: 0.85,
      fontSize: 52, bold: true, color: s.color,
      fontFace: "Hiragino Kaku Gothic ProN",
      align: "center",
    });
    // Family rate
    sl.addText("Family ID率", {
      x: x + 0.15, y: 2.85, w: 4.0, h: 0.25,
      fontSize: 11, color: C.MTEXT,
      fontFace: "Hiragino Kaku Gothic ProN",
      align: "center",
    });
    sl.addText(s.fam, {
      x: x + 0.15, y: 3.1, w: 4.0, h: 0.45,
      fontSize: 22, bold: true, color: s.color,
      fontFace: "Hiragino Kaku Gothic ProN",
      align: "center",
    });
  }

  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.43, w: 9.0, h: 0.8,
    fill: { color: "FEF3C7" }, line: { color: "F59E0B", width: 1 },
  });
  sl.addText("▶ 医療画像解析分野は製造欠陥検出分野と比べてU-Net出現率が約9倍高く、手法ギャップが明確に存在する。\nPublication・Family IDの両ベースで同様の傾向が確認され、重複の影響を除いても結果は整合する。", {
    x: 0.65, y: 4.47, w: 8.7, h: 0.7,
    fontSize: 11.5, color: C.DTEXT,
    fontFace: "Hiragino Kaku Gothic ProN",
  });

  sl.addText("10", { x: 9.4, y: 5.35, w: 0.5, h: 0.2, fontSize: 9, color: C.CAPTION, align: "right", margin: 0 });
}

// ─── SLIDE 11 · 結果② 期間別比較 (RQ2) ──────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.LGRAY };
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.NAVY }, line: { color: C.NAVY, width: 0 },
  });

  slideTitle(sl, "結果② 期間別比較　〔RQ2〕");
  hRule(sl);

  // Period table
  const hdr = [
    { text: "期間", options: { bold: true, color: C.WHITE, fill: { color: C.NAVY }, fontSize: 11 } },
    { text: "医療画像解析 (A0)", options: { bold: true, color: C.WHITE, fill: { color: C.NAVY }, fontSize: 11 } },
    { text: "製造欠陥検出 (B0)", options: { bold: true, color: C.WHITE, fill: { color: C.NAVY }, fontSize: 11 } },
    { text: "手法ギャップ", options: { bold: true, color: C.WHITE, fill: { color: C.NAVY }, fontSize: 11 } },
  ];
  const r1 = [
    "2015–2018（過去期間）",
    { text: "0.99%（25件）", options: { color: C.ACCENT, bold: true } },
    { text: "0.00%（0件）", options: { color: C.RED, bold: true } },
    { text: "≈ 0.99%", options: { color: C.HIGHLIGHT, bold: true } },
  ];
  const r2 = [
    "2019–2024（将来評価期間）",
    { text: "6.16%（779件）", options: { color: C.ACCENT, bold: true } },
    { text: "0.71%（72件）", options: { color: "059669", bold: true } },
    { text: "≈ 5.45%", options: { color: C.MTEXT } },
  ];
  sl.addTable([hdr, r1, r2], {
    x: 0.5, y: 1.08, w: 5.3, h: 1.7,
    border: { pt: 1, color: C.BORDER },
    fontSize: 11.5,
    fontFace: "Hiragino Kaku Gothic ProN",
    colW: [1.75, 1.3, 1.3, 0.95],
  });

  // Family table
  const hdr2 = [
    { text: "期間", options: { bold: true, color: C.WHITE, fill: { color: "4A5568" }, fontSize: 11 } },
    { text: "A0 Family率", options: { bold: true, color: C.WHITE, fill: { color: "4A5568" }, fontSize: 11 } },
    { text: "B0 Family率", options: { bold: true, color: C.WHITE, fill: { color: "4A5568" }, fontSize: 11 } },
  ];
  const rf1 = [
    "2015–2018（過去期間）",
    { text: "1.24%（14件）", options: { color: C.ACCENT } },
    { text: "0.00%（0件）", options: { color: C.RED, bold: true } },
  ];
  const rf2 = [
    "2019–2024（将来評価期間）",
    { text: "7.62%（563件）", options: { color: C.ACCENT } },
    { text: "0.66%（49件）", options: { color: "059669", bold: true } },
  ];
  sl.addText("Family IDベース（重複除去後も同傾向）", {
    x: 0.5, y: 2.85, w: 5.3, h: 0.28,
    fontSize: 11, bold: true, color: C.MTEXT,
    fontFace: "Hiragino Kaku Gothic ProN", margin: 0,
  });
  sl.addTable([hdr2, rf1, rf2], {
    x: 0.5, y: 3.15, w: 5.3, h: 1.4,
    border: { pt: 1, color: C.BORDER },
    fontSize: 11,
    fontFace: "Hiragino Kaku Gothic ProN",
    colW: [1.75, 1.77, 1.78],
  });

  // Figure: 1034×659 ≈ 1.57
  const figH = 3.0;
  const figW = figH * (1034 / 659);
  sl.addImage({ path: imgPath("fig05_unet_period_publication.png"), x: 5.9, y: 1.05, w: figW, h: figH });
  sl.addText("期間別U-Net出現率（Publication）", {
    x: 5.9, y: 4.12, w: figW, h: 0.28,
    fontSize: 9, italic: true, color: C.CAPTION,
    fontFace: "Hiragino Kaku Gothic ProN", align: "center",
  });

  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.55, w: 5.3, h: 0.7,
    fill: { color: "FEF3C7" }, line: { color: "F59E0B", width: 1 },
  });
  sl.addText("▶ RQ2 確認：過去期間にU-Netを「A0で先行・B0で低出現」の候補として抽出できる。", {
    x: 0.65, y: 4.59, w: 5.1, h: 0.6,
    fontSize: 11.5, color: C.DTEXT,
    fontFace: "Hiragino Kaku Gothic ProN",
  });

  sl.addText("11", { x: 9.4, y: 5.35, w: 0.5, h: 0.2, fontSize: 9, color: C.CAPTION, align: "right", margin: 0 });
}

// ─── SLIDE 12 · 結果③ 年次推移 (RQ3) ────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.LGRAY };
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.NAVY }, line: { color: C.NAVY, width: 0 },
  });

  slideTitle(sl, "結果③ 年次推移　〔RQ3〕");
  hRule(sl);

  // Figure: 1334×659 ≈ 2.02
  const figH = 3.3;
  const figW = figH * (1334 / 659);
  const figX = (10 - figW) / 2;
  sl.addImage({ path: imgPath("fig04_unet_publication_rate.png"), x: figX, y: 1.05, w: figW, h: figH });

  // Key points
  const kps = [
    { x: 0.5, text: "医療画像解析：2017年から出現→2019年以降急増", color: C.ACCENT, bg: "EFF6FF", bc: "BFDBFE" },
    { x: 5.2, text: "製造欠陥検出：2015–18年はほぼ0件→2019年から出現・増加", color: "059669", bg: "F0FDF4", bc: "BBF7D0" },
  ];
  for (const kp of kps) {
    sl.addShape(pres.shapes.RECTANGLE, {
      x: kp.x, y: 4.5, w: 4.5, h: 0.55,
      fill: { color: kp.bg }, line: { color: kp.bc, width: 1 },
    });
    sl.addText(kp.text, {
      x: kp.x + 0.1, y: 4.53, w: 4.3, h: 0.5,
      fontSize: 11.5, bold: true, color: kp.color,
      fontFace: "Hiragino Kaku Gothic ProN",
      valign: "middle",
    });
  }

  sl.addText("▶ RQ3 確認：過去に候補として抽出されたU-Netは、後年にB0分野で出現・増加と対応する。", {
    x: 0.5, y: 5.1, w: 9.2, h: 0.3,
    fontSize: 11.5, bold: true, color: C.NAVY, italic: true,
    fontFace: "Hiragino Kaku Gothic ProN",
    align: "center",
  });

  sl.addText("12", { x: 9.4, y: 5.35, w: 0.5, h: 0.2, fontSize: 9, color: C.CAPTION, align: "right", margin: 0 });
}

// ─── SLIDE 13 · 結果④ 代表特許の目視確認 ────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.LGRAY };
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.NAVY }, line: { color: C.NAVY, width: 0 },
  });

  slideTitle(sl, "結果④ 代表特許の目視確認");
  hRule(sl);

  sl.addText("語の一致だけでなく、U-Net系構造が技術的手段として用いられていることを確認した。", {
    x: 0.5, y: 1.0, w: 9.2, h: 0.35,
    fontSize: 13, color: C.MTEXT,
    fontFace: "Hiragino Kaku Gothic ProN",
  });

  // Two columns
  const cols = [
    {
      x: 0.5, label: "医療画像解析側 (A1)", color: C.ACCENT, bg: "EFF6FF", bc: "BFDBFE",
      items: ["腫瘍・生物医学画像のセグメンテーション", "対象物：人体画像、腫瘍画像、細胞画像", "U-Net系構造が画像分割の主要手段として使用"],
    },
    {
      x: 5.1, label: "製造欠陥検出側 (B1)", color: "059669", bg: "F0FDF4", bc: "BBF7D0",
      items: ["管路・鋼材・金属表面欠陥の検出・分割", "対象物：製造物画像、鋼材表面、管路断面", "U-Net系構造が欠陥セグメンテーション手段として使用"],
    },
  ];

  for (const c of cols) {
    sl.addShape(pres.shapes.RECTANGLE, {
      x: c.x, y: 1.43, w: 4.4, h: 2.35,
      fill: { color: c.bg }, line: { color: c.bc, width: 1.5 },
    });
    sl.addText(c.label, {
      x: c.x + 0.1, y: 1.47, w: 4.2, h: 0.32,
      fontSize: 13, bold: true, color: c.color,
      fontFace: "Hiragino Kaku Gothic ProN", margin: 0,
    });
    sl.addText(c.items.map(t => ({ text: t, options: { bullet: true, breakLine: true } })), {
      x: c.x + 0.1, y: 1.8, w: 4.2, h: 1.9,
      fontSize: 12.5, color: C.DTEXT,
      fontFace: "Hiragino Kaku Gothic ProN",
    });
  }

  // Verification table
  sl.addText("確認観点", {
    x: 0.5, y: 3.88, w: 9.2, h: 0.3,
    fontSize: 12, bold: true, color: C.NAVY,
    fontFace: "Hiragino Kaku Gothic ProN", margin: 0,
  });
  const vHeader = [
    { text: "確認観点", options: { bold: true, color: C.WHITE, fill: { color: C.NAVY }, fontSize: 11 } },
    { text: "確認内容", options: { bold: true, color: C.WHITE, fill: { color: C.NAVY }, fontSize: 11 } },
  ];
  const vRows = [
    ["技術手段としての利用", "U-Netが単なる語ではなく、画像分割・欠陥検出の構成として使われているか"],
    ["対象物", "医療画像・腫瘍画像・管路・鋼材・金属表面などが確認できるか"],
    ["課題文脈", "高精度な領域分割、欠陥検出、異常領域抽出などの課題が確認できるか"],
  ];
  sl.addTable([vHeader, ...vRows], {
    x: 0.5, y: 4.2, w: 9.2, h: 1.05,
    border: { pt: 1, color: C.BORDER },
    fontSize: 10.5,
    fontFace: "Hiragino Kaku Gothic ProN",
    colW: [2.0, 7.2],
  });

  sl.addText("13", { x: 9.4, y: 5.35, w: 0.5, h: 0.2, fontSize: 9, color: C.CAPTION, align: "right", margin: 0 });
}

// ─── SLIDE 14 · 本研究の貢献 ─────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.LGRAY };
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.NAVY }, line: { color: C.NAVY, width: 0 },
  });

  slideTitle(sl, "本研究の貢献");
  hRule(sl);

  const contribs = [
    {
      num: "01",
      title: "候補抽出の説明可能化",
      text: "特許文書を課題文脈・解決手段文脈に分離し、候補抽出理由を「課題の近さ」と「解決手段の低出現性」として整理した。全文類似では説明できなかった抽出根拠を明示できる。",
      color: "2563EB",
    },
    {
      num: "02",
      title: "後ろ向き評価設計の提示",
      text: "U-Netを対象に、医療画像解析と製造欠陥検出の特許データを比較し、過去の手法ギャップと将来の出現増加を用いた後ろ向き評価設計を示した。",
      color: "7C3AED",
    },
    {
      num: "03",
      title: "語一致を超えた評価",
      text: "Publication/Family ID両ベースで傾向を確認し、代表特許の目視確認を組み合わせることで、単なる語の一致に留まらない、専門家確認候補としての妥当性評価を実施した。",
      color: "0D9488",
    },
  ];

  for (let i = 0; i < contribs.length; i++) {
    const c = contribs[i];
    const y = 1.08 + i * 1.38;
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 9.2, h: 1.22,
      fill: { color: C.WHITE },
      shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.08 },
      line: { color: C.BORDER, width: 1 },
    });
    // Accent circle-ish
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 0.62, h: 1.22,
      fill: { color: c.color }, line: { color: c.color, width: 0 },
    });
    sl.addText(c.num, {
      x: 0.5, y: y + 0.35, w: 0.62, h: 0.5,
      fontSize: 20, bold: true, color: C.WHITE,
      fontFace: "Hiragino Kaku Gothic ProN",
      align: "center", valign: "middle",
    });
    sl.addText(c.title, {
      x: 1.22, y: y + 0.06, w: 8.35, h: 0.32,
      fontSize: 14, bold: true, color: c.color,
      fontFace: "Hiragino Kaku Gothic ProN", margin: 0,
    });
    sl.addText(c.text, {
      x: 1.22, y: y + 0.42, w: 8.35, h: 0.76,
      fontSize: 12, color: C.DTEXT,
      fontFace: "Hiragino Kaku Gothic ProN",
    });
  }

  sl.addText("14", { x: 9.4, y: 5.35, w: 0.5, h: 0.2, fontSize: 9, color: C.CAPTION, align: "right", margin: 0 });
}

// ─── SLIDE 15 · 限界と今後の展望 ─────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.LGRAY };
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.NAVY }, line: { color: C.NAVY, width: 0 },
  });

  slideTitle(sl, "限界と今後の展望");
  hRule(sl);

  // Limitations
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.08, w: 4.4, h: 3.8,
    fill: { color: "FEF2F2" }, line: { color: "FECACA", width: 1.5 },
  });
  sl.addText("本研究の限界", {
    x: 0.65, y: 1.12, w: 4.1, h: 0.32,
    fontSize: 13, bold: true, color: C.RED,
    fontFace: "Hiragino Kaku Gothic ProN", margin: 0,
  });
  sl.addText([
    bullet("特許データの重複"),
    bullet("同一発明の複数国出願が重複計上される", true),
    bullet("出現率の傾向は整合するが絶対数は異なる", true),
    bullet("キーワードマッチングの限界"),
    bullet("表記揺れ（例：U-Netの変種）の未捕捉", true),
    bullet("関連構造（マルチスケールエンコーダ）は非対象", true),
    bullet("特許データの限界"),
    bullet("U-Netは論文・OSSで広く利用", true),
    bullet("特許出現率の低さ ≠ 技術未利用", true),
  ], {
    x: 0.65, y: 1.47, w: 4.1, h: 3.3,
    fontSize: 12, color: C.DTEXT,
    fontFace: "Hiragino Kaku Gothic ProN",
    paraSpaceAfter: 3,
  });

  // Future work
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.08, w: 4.6, h: 3.8,
    fill: { color: "F0FDF4" }, line: { color: "BBF7D0", width: 1.5 },
  });
  sl.addText("今後の展望", {
    x: 5.25, y: 1.12, w: 4.3, h: 0.32,
    fontSize: 13, bold: true, color: "059669",
    fontFace: "Hiragino Kaku Gothic ProN", margin: 0,
  });
  sl.addText([
    bullet("補助ケースの追加検証"),
    bullet("YOLO、GAN、Domain Adaptation等", true),
    bullet("提案枠組みの一般性を評価", true),
    bullet("異質解決策型分析への拡張"),
    bullet("花王の洗浄技術→半導体洗浄など", true),
    bullet("単一手法名に依存しない候補抽出へ", true),
    bullet("論文×特許データの接続"),
    bullet("科学知識が産業応用へ展開する経路分析", true),
    bullet("K2P（知識→産業）経路の可視化", true),
  ], {
    x: 5.25, y: 1.47, w: 4.3, h: 3.3,
    fontSize: 12, color: C.DTEXT,
    fontFace: "Hiragino Kaku Gothic ProN",
    paraSpaceAfter: 3,
  });

  sl.addText("15", { x: 9.4, y: 5.35, w: 0.5, h: 0.2, fontSize: 9, color: C.CAPTION, align: "right", margin: 0 });
}

// ─── SLIDE 16 · 結論 ─────────────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.NAVY };

  // Top accent
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.18,
    fill: { color: C.ACCENT2 }, line: { color: C.ACCENT2, width: 0 },
  });

  sl.addText("結　論", {
    x: 0.5, y: 0.25, w: 9.0, h: 0.6,
    fontSize: 28, bold: true, color: C.WHITE,
    fontFace: "Hiragino Kaku Gothic ProN",
    align: "center",
  });

  // Summary box
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 0.98, w: 9.0, h: 0.75,
    fill: { color: "243585" }, line: { color: "3B5A9A", width: 1 },
  });
  sl.addText(
    "U-Netの医療画像解析→製造欠陥検出への展開を対象に、課題・解決手段分離型クロスドメイン技術候補抽出枠組みを検討した。",
    {
      x: 0.65, y: 0.98, w: 8.7, h: 0.75,
      fontSize: 13, color: C.ICE,
      fontFace: "Hiragino Kaku Gothic ProN",
      valign: "middle",
    }
  );

  // Three key results
  const results = [
    {
      label: "手法ギャップ",
      text: "過去期間（2015–18年）\nA0: 0.99%、B0: 0.00%\n→ 明確なギャップを確認",
      color: C.ACCENT2, bg: "243585",
    },
    {
      label: "将来期間での出現",
      text: "2019–2024年\nB0: 72件・0.71%へ増加\n→ RQ3の後ろ向き根拠",
      color: C.HIGHLIGHT, bg: "2A3070",
    },
    {
      label: "目視確認",
      text: "代表特許の確認により\nU-Netが技術的手段として\n使用されていることを確認",
      color: "6EE7B7", bg: "1E3A5F",
    },
  ];

  for (let i = 0; i < results.length; i++) {
    const r = results[i];
    const x = 0.5 + i * 3.05;
    sl.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.9, w: 2.85, h: 2.1,
      fill: { color: r.bg }, line: { color: r.color, width: 1.5 },
    });
    sl.addText(r.label, {
      x: x + 0.1, y: 1.94, w: 2.65, h: 0.35,
      fontSize: 13, bold: true, color: r.color,
      fontFace: "Hiragino Kaku Gothic ProN", margin: 0,
    });
    sl.addText(r.text, {
      x: x + 0.1, y: 2.32, w: 2.65, h: 1.64,
      fontSize: 12, color: "CADCF8",
      fontFace: "Hiragino Kaku Gothic ProN",
    });
  }

  // Final statement
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.13, w: 9.0, h: 0.82,
    fill: { color: C.ACCENT }, line: { color: C.ACCENT, width: 0 },
  });
  sl.addText(
    "提案枠組みは、既知のクロスドメイン応用事例（U-Net）を過去時点のデータから\n専門家確認候補として抽出できる可能性を示した。",
    {
      x: 0.65, y: 4.14, w: 8.7, h: 0.8,
      fontSize: 13, color: C.WHITE,
      fontFace: "Hiragino Kaku Gothic ProN",
      valign: "middle",
      align: "center",
    }
  );

  // Bottom bar
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.43, w: 10, h: 0.195,
    fill: { color: "162050" }, line: { color: "162050", width: 0 },
  });

  sl.addText("16", { x: 9.4, y: 5.35, w: 0.5, h: 0.2, fontSize: 9, color: "3B5A9A", align: "right", margin: 0 });
}

// ─── write ────────────────────────────────────────────────────────────────────
pres.writeFile({ fileName: path.join(BASE, "research_presentation.pptx") })
  .then(() => console.log("✓ research_presentation.pptx を生成しました"))
  .catch(err => { console.error("ERROR:", err); process.exit(1); });
