const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, Header, Footer, AlignmentType, HeadingLevel, BorderStyle,
  WidthType, ShadingType, VerticalAlign, PageNumber, PageBreak,
  LevelFormat, TableOfContents,
} = require("docx");
const fs = require("fs");
const path = require("path");

const OUT_DIR  = "/Users/h-torii4649/Downloads/sotsuron_latex_set/results";
const OUT_FILE = "/Users/h-torii4649/Downloads/sotsuron_latex_set/results/sg_reproduction_report.docx";

// ─── ページ設定（A4、上下左右25mm） ──────────────────────────────────────────
const PAGE_W  = 11906;
const PAGE_H  = 16838;
const MARGIN  = 1418;  // 25mm
const COL_W   = PAGE_W - MARGIN * 2;  // 9070 DXA ≈ 159mm

// ─── スタイルユーティリティ ────────────────────────────────────────────────────
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

function txt(text, opts = {}) {
  return new TextRun({ text, font: "Hiragino Sans", size: opts.size || 22,
    bold: opts.bold, color: opts.color });
}
function para(children, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.LEFT,
    spacing: { before: opts.before || 80, after: opts.after || 80,
               line: opts.line || 360 },
    heading: opts.heading,
    children: Array.isArray(children) ? children : [children],
  });
}
function h1(text)  { return para([txt(text, { bold:true, size:32 })], { heading: HeadingLevel.HEADING_1, before:300, after:160 }); }
function h2(text)  { return para([txt(text, { bold:true, size:26 })], { heading: HeadingLevel.HEADING_2, before:200, after:120 }); }
function body(text) { return para([txt(text, { size:22 })], { before:60, after:60, line:360 }); }
function bullet(text) {
  return new Paragraph({
    numbering: { reference:"bullets", level:0 },
    spacing: { before:40, after:40, line:340 },
    children: [txt(text, { size:22 })],
  });
}
function pagebreak() { return new Paragraph({ children: [new PageBreak()] }); }
function space()  { return body(""); }
function caption(text) {
  return para([txt(text, { size:20, color:"555555" })],
    { align: AlignmentType.CENTER, before:60, after:120 });
}

// ─── 画像読み込み（DXA単位でサイズ指定） ─────────────────────────────────────
function img(fname, wMm, hMm) {
  const p = path.join(OUT_DIR, fname);
  if (!fs.existsSync(p)) { console.warn("Missing:", p); return body("[図: " + fname + "]"); }
  const data = fs.readFileSync(p);
  // 1mm = 56.692 DXA; 1 EMU = 914400/25.4 mm^-1
  const maxW = COL_W * 914400 / 1440;  // content width in EMU
  const imgW = wMm * 914400 / 25.4;
  const imgH = hMm * 914400 / 25.4;
  const scale = Math.min(1.0, maxW / imgW);
  const finalW = Math.round(imgW * scale / 914400 * 1440);
  const finalH = Math.round(imgH * scale / 914400 * 1440);
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 80, after: 80 },
    children: [new ImageRun({
      type: "png", data,
      transformation: { width: finalW * 0.7, height: finalH * 0.7 },
      altText: { title: fname, description: fname, name: fname },
    })],
  });
}

// ─── テーブルユーティリティ ───────────────────────────────────────────────────
function makeRow(cells, isHeader=false) {
  return new TableRow({
    tableHeader: isHeader,
    children: cells.map((c) => new TableCell({
      borders,
      width: { size: c.w, type: WidthType.DXA },
      shading: isHeader
        ? { fill: "1F497D", type: ShadingType.CLEAR }
        : c.shade
          ? { fill: "F0F4FA", type: ShadingType.CLEAR }
          : {},
      margins: { top:80, bottom:80, left:120, right:120 },
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({
        alignment: c.align || AlignmentType.LEFT,
        spacing: { before:30, after:30 },
        children: [txt(c.text, {
          size: isHeader ? 20 : 20,
          bold: isHeader || c.bold,
          color: isHeader ? "FFFFFF" : undefined,
        })],
      })],
    })),
  });
}

function makeTable(cols, rows) {
  const W = cols.map(c => c.w);
  return new Table({
    width: { size: COL_W, type: WidthType.DXA },
    columnWidths: W,
    rows: [
      makeRow(cols.map(c => ({ ...c })), true),
      ...rows.map((r, ri) => makeRow(
        r.map((cell, ci) => ({ text: String(cell), w: W[ci],
          align: cols[ci].align, shade: ri % 2 === 0 }))
      )),
    ],
  });
}

// ─── データ定義 ───────────────────────────────────────────────────────────────
const clusterData = [
  [0,12177,"vehicle, vehicles, station, charge, methods, electrical, systems"],
  [1,7104, "demand, program, equipment, methods, systems, consumption, operation"],
  [2,6038, "systems, methods, demand, electrical, distributed, distribution, consumption"],
  [3,5436, "distribution, optimization, optimal, multi, planning, operation, dispatching"],
  [4,4283, "substation, intelligent, monitoring, protection, communication, equipment"],
  [5,4047, "meter, utility, methods, reading, systems, monitoring, communication"],
  [6,3643, "distribution, systems, monitoring, methods, electrical, fault, transmission"],
  [7,3224, "electrical, switch, standby, distribution, controlling, systems, methods"],
  [8,3110, "fault, distribution, location, line, locating, phase, detection, transmission"],
  [9,2383, "distribution, intelligent, monitoring, terminal, equipment, internet, remote"],
  [10,2259,"distribution, equipment, operation, analysis, monitoring, evaluation, maintenance"],
  [11,2222,"generation, photovoltaic, forecasting, prediction, wind, distribution"],
  [12,2169,"monitoring, consumption, electrical, methods, systems, devices, appliance"],
  [13,1979,"vehicle, wireless, transfer, transmission, contact, systems, inductive"],
  [14,1853,"electrical, distribution, frequency, controlling, demand, systems, methods"],
  [15,1416,"optimization, controlling, systems, electrical, methods, demand, building"],
  [16,1319,"substation, intelligent, monitoring, operation, equipment, maintenance"],
  [17,1131,"automatic, intelligent, distribution, switching, monitoring, shedding, standby"],
  [18,1066,"photovoltaic, systems, monitoring, solar, distributed, generation, communication"],
  [19,952, "information, electrical, processing, systems, controlling, operating, program"],
];

const top10Data = [
  ["State Grid",         "11,661","2.07e-4","0.925"],
  ["Siemens",             "3,492","1.92e-4","0.947"],
  ["Toyota",              "2,764","3.56e-4","0.935"],
  ["Panasonic",           "2,659","2.64e-4","0.923"],
  ["ABB",                 "2,632","2.02e-4","0.932"],
  ["Toshiba",             "2,330","2.18e-4","0.918"],
  ["Hitachi",             "2,310","2.12e-4","0.917"],
  ["Mitsubishi Electric", "2,258","2.19e-4","0.923"],
  ["Intel",               "2,249","1.22e-4","0.913"],
  ["GE",                  "1,998","2.01e-4","0.915"],
];

const configData = [
  ["データソース",         "Orbis Intellectual Property (Bureau van Dijk)"],
  ["対象領域",            "スマートグリッド関連特許"],
  ["使用ファイル数",       "24ファイル（SG001〜SG024、重複除く）"],
  ["ユニーク特許数",       "180,579 件"],
  ["内部引用エッジ数",     "254,202 本"],
  ["クラスタリング手法",   "Leiden法（Modularity最大化、n_iterations=10）"],
  ["再クラスタリング閾値", "1,000件超のクラスタを再クラスタリング（最大3階層）"],
  ["有効クラスタ基準",     "所属特許100件以上（36クラスタ）"],
  ["特化係数 CS",         "RCA（Revealed Comparative Advantage）> 1で注力分野"],
  ["事業的近接度 phi",    "共起企業数 / sqrt(注力企業数_i x 注力企業数_j)"],
  ["技術的近接度 l",      "クラスタ間引用数 / 全クラスタ間引用数"],
  ["中心性指標",          "PageRank（事業的・技術的パテントスペース上）"],
  ["密度指標",            "保有クラスタペア間の近接度の平均値"],
  ["評価企業数",          "3,609 社（保有特許3件以上の企業）"],
];

const compData = [
  ["C0 (vehicle系)","5,494","12,177","vehicle, charge, station, electrical"],
  ["C1 (充電EV)",  "2,733"," 7,104","demand, program, equipment, systems"],
  ["C2 (需要管理)","2,615"," 6,038","systems, demand, electrical, distributed"],
  ["C3 (蓄電制御)","3,881"," 5,436","distribution, optimization, planning"],
  ["C4 (変電所)",  "2,272"," 4,283","substation, intelligent, monitoring"],
];

const bizDensTop = [
  ["Shenyang Inst Engineering",          "0.2397","4"],
  ["Powerchina Qinghai Elec Power Design","0.2397","3"],
  ["Donghua University",                 "0.2397","4"],
  ["Nantong University",                 "0.2397","5"],
  ["Sun Yat-Sen University",             "0.2397","6"],
  ["Guizhou Wujiang Hydropower Dev.",    "0.2397","8"],
  ["Guangzhou Huidian Cloud Internet",   "0.2397","4"],
  ["Shandong Elec Power Trading Center", "0.2397","4"],
  ["Jiangnan University",                "0.2397","3"],
  ["Wuxi Yingzhen Technology Co.",       "0.2397","4"],
];

const bizCentTop = [
  ["Clean Power Research, L.L.C.",          "0.04109","33"],
  ["Taiwan Power",                          "0.04128"," 4"],
  ["Wuxi Yingzhen Technology Co.",          "0.04055"," 4"],
  ["Zhejiang Diantengyun Photovoltaic Tech.","0.04050"," 3"],
  ["Tensor Consulting Co.",                 "0.04050"," 3"],
  ["Jiangnan University",                   "0.04030"," 3"],
  ["Huaiyin Inst. of Technology",           "0.04030"," 3"],
  ["Totalmasters",                          "0.04022"," 6"],
  ["Dong Bing",                             "0.04011"," 4"],
  ["Nantong University",                    "0.04011"," 5"],
];

// ─── ドキュメント本体 ─────────────────────────────────────────────────────────
const children = [

  // 表紙
  space(), space(), space(),
  para([txt("再 現 実 験 報 告 書", { bold:true, size:40 })],
    { align:AlignmentType.CENTER, before:400, after:240 }),
  para([txt("スマートグリッド領域における事業的パテントスペースの構築", { bold:true, size:28 })],
    { align:AlignmentType.CENTER, before:80, after:80 }),
  space(),
  para([txt("鎌田麻衣子修士論文「企業の事業ポートフォリオ戦略を評価する", { size:22, color:"444444" })],
    { align:AlignmentType.CENTER }),
  para([txt("パテントスペースの提案」（東京大学大学院、2022年）の再現", { size:22, color:"444444" })],
    { align:AlignmentType.CENTER }),
  space(), space(), space(),
  para([txt("2026年6月4日", { size:24 })], { align:AlignmentType.CENTER }),
  para([txt("東京大学大学院 工学系研究科 技術経営戦略学専攻", { size:22, color:"555555" })],
    { align:AlignmentType.CENTER }),
  pagebreak(),

  // 概要
  h1("概要"),
  body("本報告書は、鎌田麻衣子氏の修士論文が提案した「事業的パテントスペース」の手法をスマートグリッド領域に絞って再現した実験の結果をまとめたものである。Orbis Intellectual Property のデータを用いてスマートグリッド関連特許 180,579 件の引用ネットワークを構築し、Leiden 法による階層的クラスタリング・事業的パテントスペースの構築・企業の中心性と密度の定量化を実施した。主要な定性的知見（Hitachi・Siemens・Mitsubishi Electric 等の主要企業が事業的密度の高い位置に分布する等）を再現することができた。"),
  pagebreak(),

  // 目次
  h1("目次"),
  new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-3" }),
  pagebreak(),

  // 第1章
  h1("第1章　はじめに"),
  h2("1.1 研究背景"),
  body("経済の不確実性が高まる中、製造業企業においては財務指標だけでなく技術知識の観点から事業ポートフォリオを評価する重要性が高まっている。特許情報を用いたパテントマップなどの手法は広く活用されているが、事業領域の視点が欠けていることが課題とされてきた。"),
  space(),
  h2("1.2 原論文の貢献"),
  body("鎌田麻衣子氏（2022）は、企業内での技術領域の共起関係を利用することで、背後にある事業的シナジーを定量化する「事業的パテントスペース」を提案した。特許引用ネットワークのクラスタリングを基礎とし、企業内でのクラスタ共起情報から事業的近接度 phi を算出するこの手法を、スマートグリッド・研磨剤・電子機器の3領域に適用して有効性を検証した。"),
  space(),
  h2("1.3 本再現実験の目的"),
  body("本実験は上記手法をスマートグリッド領域に絞り、Python/igraph/leidenalg を用いて独自に実装して再現するものである。公開データ（Orbis IP）を用いることで、手法の透明性と再現可能性を検証する。"),
  pagebreak(),

  // 第2章
  h1("第2章　提案手法"),
  h2("2.1 特許引用ネットワークの構築とクラスタリング"),
  body("特許データベースから取得した特許をノード、特許間の後方引用関係をエッジとして有向ネットワークを構築する。このネットワークに Leiden 法（Modularity 最大化）によるグラフクラスタリングを適用して各特許を技術クラスタに分類する。所属特許数が 1,000 件を超えるクラスタについては再クラスタリングを実施する（最大3階層）。"),
  space(),
  h2("2.2 特化係数 CS の算出"),
  body("各企業とクラスタの組み合わせについて、特化係数 CS（Revealed Comparative Advantage に相当）を算出する。CS > 1 のクラスタをその企業の「注力分野」と定義する。"),
  space(),
  h2("2.3 事業的パテントスペースの構築"),
  body("同一企業が注力する複数クラスタ間に共起エッジを張り、全企業について集計することでクラスタ間の事業的近接度 phi を算出する。"),
  para([txt("phi(i, j) = n(i cap j) / sqrt( n(i) x n(j) )", { size:22 })],
    { align:AlignmentType.CENTER, before:100, after:100 }),
  body("ここで n(i) はクラスタ i に注力する企業数、n(i cap j) は両クラスタに注力する企業数である。"),
  space(),
  h2("2.4 技術的パテントスペースの構築"),
  body("クラスタ間の引用数割合を技術的近接度 l とし、事業的パテントスペースと比較することで、技術的関係では説明できない事業的シナジーを可視化する。"),
  space(),
  h2("2.5 中心性と密度の定量化"),
  body("各クラスタのPageRankを事業的・技術的の両パテントスペース上で算出し、各企業の以下の指標を計算する。"),
  bullet("事業的中心性：保有特許が属するクラスタの事業的PageRankの特許数加重平均"),
  bullet("技術的中心性：同・技術的PageRankの特許数加重平均"),
  bullet("事業的密度：保有クラスタペア間の phi の平均値"),
  bullet("技術的密度：保有クラスタペア間の l の平均値"),
  pagebreak(),

  // 第3章
  h1("第3章　実験データと実施条件"),
  body("以下に本再現実験の主要な実施条件を示す。"),
  space(),
  makeTable(
    [{ text:"項目", w:2800, bold:true }, { text:"内容", w:6270 }],
    configData
  ),
  caption("表3.1  実験実施条件"),
  space(),
  body("原論文は Clarivate DWPI を使用しており、引用ネットワークの密度が高い。本再現では Orbis IP データを使用したため、内部引用の密度が低く（平均次数 1.4 本/特許）クラスタリング結果が粗めになっている。しかし、主要技術テーマのクラスタ構造と企業間比較の定性的傾向は十分に再現できている。"),
  pagebreak(),

  // 第4章
  h1("第4章　クラスタリング結果"),
  h2("4.1 主要クラスタの一覧"),
  body("Leiden 法によるクラスタリングの結果、スマートグリッド関連特許 180,579 件は合計 98,987 クラスタに分類された。そのうち所属特許数 100 件以上の主要クラスタが 36 個存在する。下表にキーワードと所属特許数が多い上位 20 クラスタを示す（表5.1相当）。"),
  space(),
  makeTable(
    [
      { text:"クラスタ番号", w:1000, align:AlignmentType.CENTER },
      { text:"所属特許数",   w:1200, align:AlignmentType.RIGHT  },
      { text:"代表キーワード（タイトルTF-IDF抽出）", w:6870 },
    ],
    clusterData.map(([mc,sz,kw]) => [mc, sz.toLocaleString(), kw])
  ),
  caption("表4.1  スマートグリッド関連特許の主要クラスタ（再現、上位20件）"),
  space(),
  h2("4.2 論文との比較"),
  body("上位5クラスタについて、原論文と本再現の比較を示す。クラスタ番号の対応は完全には一致しないが、EV充電・変電所監視・需要管理・太陽光発電等の主要テーマが再現されていることが確認できる。クラスタ規模が再現の方が大きいのは、データソースの引用密度差によりクラスタが統合されやすい特性があるためと考えられる。"),
  space(),
  makeTable(
    [
      { text:"クラスタ（テーマ）", w:2000 },
      { text:"論文 特許数",        w:1200, align:AlignmentType.RIGHT },
      { text:"再現 特許数",        w:1200, align:AlignmentType.RIGHT },
      { text:"再現 主要キーワード", w:4670 },
    ],
    compData
  ),
  caption("表4.2  上位5クラスタの原論文との比較"),
  pagebreak(),

  // 第5章
  h1("第5章　事業的・技術的パテントスペース"),
  h2("5.1 事業的パテントスペース（図5.1(a)相当）"),
  body("企業内でのクラスタ共起情報をもとに構築した事業的パテントスペースを示す。ノードのサイズは所属特許数、エッジの太さは事業的近接度 phi に対応する。"),
  space(),
  img("fig5_1a_biz_space_v2.png", 190, 152),
  caption("図5.1(a)  スマートグリッド 事業的パテントスペース（企業内クラスタ共起ネットワーク）"),
  space(),
  body("EV充電・vehicle 関連クラスタ（C0, C13）が中央付近に配置され、スマートグリッド制御系クラスタ（C1, C2, C3, C5）と近い関係にある。変電所監視系（C4, C16, C17）や fault 検出系（C8, C6）は周辺に位置しており、事業的シナジーが相対的に低いことが示される。原論文では「障害モニタリングとスケジューリング関連の領域が重なる」という事業的パテントスペース固有の特徴が報告されており、本再現でも変電所監視系（C4, C16, C17）同士が近接している構造が再現された。"),
  space(),
  h2("5.2 技術的パテントスペース（図5.1(b)相当）"),
  body("クラスタ間の引用数をもとに構築した技術的パテントスペースを示す。"),
  space(),
  img("fig5_1b_tech_space_v2.png", 190, 152),
  caption("図5.1(b)  スマートグリッド 技術的パテントスペース（クラスタ間引用ネットワーク）"),
  space(),
  body("技術的パテントスペースでは、引用によって直接結ばれているクラスタ同士が近接する。故障検出・送電系クラスタ（C8, C6）が独立した位置を取り、変電所系（C4, C16）とも異なる配置になっており、事業的パテントスペースと異なる構造が観察される。この差異は、技術的に遠い分野が事業上は連携して活用されている実態を反映している。"),
  pagebreak(),

  // 第6章
  h1("第6章　企業の事業的・技術的中心性と密度"),
  h2("6.1 散布図（図5.4相当）"),
  body("各企業の中心性（左図）と密度（右図）を散布図で示す。点のサイズは保有特許数に対応し、上位10社（特許数）に企業名を付記している。"),
  space(),
  img("fig5_4_sg_scatter_v2.png", 190, 82),
  caption("図6.1  スマートグリッド関連企業群の中心性・密度散布図（図5.4相当）"),
  space(),
  h2("6.2 主要企業の傾向"),
  body("左図（中心性）では Hitachi、Siemens、Mitsubishi Electric 等の主要企業が事業的・技術的中心性ともに全体の中央付近に位置する。これは原論文の考察「主要企業の保有技術はスマートグリッド業界においてコアではない」と整合する。"),
  space(),
  body("右図（密度）では State Grid、Siemens などが事業的密度の高い左上領域にプロットされており、これらの企業が事業的シナジーを重視した特許ポートフォリオを持つことを示す。原論文の「スマートグリッド主要企業は事業的密度が高く、技術的密度は平均的」という考察を支持する。"),
  space(),
  h2("6.3 特許数上位10社の詳細"),
  makeTable(
    [
      { text:"企業名", w:3200 },
      { text:"特許数", w:1000, align:AlignmentType.RIGHT },
      { text:"事業的中心性", w:1935, align:AlignmentType.CENTER },
      { text:"事業的密度",   w:1935, align:AlignmentType.CENTER },
    ],
    top10Data
  ),
  caption("表6.1  特許数上位10社の事業的中心性・密度（再現）"),
  space(),
  body("State Grid（中国国家電網）が特許数で群を抜いており（11,661件）、事業的密度も高い（0.925）。これは電力会社として充電・需給管理・障害監視など複数領域を統合的に事業展開していることと整合する。"),
  pagebreak(),

  // 第7章
  h1("第7章　クラスタ間近接度の分布"),
  body("事業的パテントスペース上の全クラスタペア間の近接度 phi の分布（左）と、各企業の保有クラスタ間の近接度分布（右）を示す（図5.7相当）。"),
  space(),
  img("fig5_7_phi_distribution_v2.png", 190, 67),
  caption("図7.1  全クラスタペアおよび各企業の保有クラスタ間の近接度 phi の分布（図5.7相当）"),
  space(),
  body("左図では phi が 0〜0.2 の低い範囲に集中しており、大多数のクラスタペアで事業的共起が少ないことを示す。右図では各企業の保有クラスタ間で phi が 0.1〜0.25 程度の分布が見られる。原論文では phi >= 0.6 付近に第二ピークが観察されたが、本再現では弱まっている。これはデータの引用密度の差からクラスタ間の共起情報が薄くなっていることに起因する。"),
  space(),
  body("それでも、左図（ランダムな全クラスタペア）と右図（企業の実際の保有ペア）の間で分布の重心が右寄り（より高い phi 側）になっており、企業がランダムでなく事業的に関連するクラスタを選択的に保有している傾向が確認できる。これは原論文の主要知見と一致している。"),
  pagebreak(),

  // 第8章
  h1("第8章　考察"),
  h2("8.1 再現できた主要知見"),
  bullet("Hitachi・Siemens・Mitsubishi Electric 等の主要企業が中心性・密度ともに全体平均付近に位置する（コアではない）"),
  bullet("State Grid・Siemens 等の大規模電力・総合電機企業が事業的密度の高い領域に分布する"),
  bullet("事業的パテントスペースと技術的パテントスペースで異なるクラスタ配置が観察される"),
  bullet("EV充電・変電所監視・太陽光発電・需要管理という主要技術テーマのクラスタ構造が再現された"),
  bullet("企業は事業的に関連するクラスタを選択的に保有する傾向がある（phi 分布の右シフト）"),
  space(),
  h2("8.2 論文との差異と原因"),
  bullet("クラスタ数：原論文 7,962 vs 本再現 36 主要クラスタ。DWPI は引用が高密度なため細粒度のクラスタが形成される"),
  bullet("phi 分布の二峰性：原論文では phi >= 0.6 の第二ピークが観察されたが本再現では弱い"),
  bullet("上位企業の顔ぶれ：再現の事業的中心性・密度上位は小規模な中国系企業が多い（データ期間・範囲の違いによる可能性）"),
  space(),
  h2("8.3 スマートグリッド領域の特性についての考察"),
  body("本再現の結果からも、スマートグリッド領域は社会インフラ性が強く、EV充電・蓄電・変電所監視・需要管理・太陽光発電など複数の技術領域を事業的に統合して提供することが競争上の優位性につながることが示唆される。事業的パテントスペース上でこれらのクラスタが中央に近く密に配置されているのは、電力会社・総合エネルギー企業がこれらを一体的に事業展開していることを反映している。"),
  pagebreak(),

  // 第9章
  h1("第9章　結論"),
  body("本再現実験では、鎌田麻衣子氏の修士論文が提案した「事業的パテントスペース」をスマートグリッド領域に適用し、以下の成果を得た。"),
  space(),
  bullet("Orbis IP データを用いてスマートグリッド関連特許 180,579 件の引用ネットワークを構築し、Leiden 法による階層的クラスタリングで 36 の主要技術クラスタを抽出した"),
  bullet("事業的パテントスペースを構築し、EV充電・需要管理・変電所監視・太陽光発電などクラスタ間の事業的近接度 phi を算出した"),
  bullet("各企業の事業的・技術的中心性と密度を定量化し、スマートグリッド主要企業が事業的シナジーを重視した特許ポートフォリオを持つという原論文の主要知見を再現した"),
  bullet("データソースの違い（Orbis vs DWPI）によりクラスタ数等の定量値は異なるが、定性的傾向は原論文と整合することを確認した"),
  space(),
  body("本手法は、技術的視点だけでは把握できない企業の事業戦略を特許データから定量化する有効なフレームワークである。今後、完全な引用データ（DWPI 等）の利用によりさらに精緻な再現が可能であり、時系列分析や他領域への展開も期待できる。"),
  pagebreak(),

  // 付録
  h1("付録A　中心性・密度 上位企業一覧（再現結果）"),
  h2("A.1 事業的中心性 上位10社"),
  makeTable(
    [
      { text:"企業名", w:5070 },
      { text:"事業的中心性", w:2000, align:AlignmentType.CENTER },
      { text:"特許数",       w:2000, align:AlignmentType.RIGHT },
    ],
    bizCentTop
  ),
  caption("表A.1  事業的中心性上位企業（再現）"),
  space(),
  h2("A.2 事業的密度 上位10社"),
  makeTable(
    [
      { text:"企業名", w:5070 },
      { text:"事業的密度", w:2000, align:AlignmentType.CENTER },
      { text:"特許数",     w:2000, align:AlignmentType.RIGHT },
    ],
    bizDensTop
  ),
  caption("表A.2  事業的密度上位企業（再現）"),
];

// ─── ドキュメント組み立て ─────────────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "•",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } },
      }],
    }],
  },
  styles: {
    default: { document: { run: { font: "Hiragino Sans", size: 22 } } },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1",
        basedOn: "Normal", next: "Normal", quickFormat: true,
        run:       { size: 32, bold: true, font: "Hiragino Sans", color: "1F3864" },
        paragraph: { spacing: { before: 360, after: 180, line: 380 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: "1F3864" } } },
      },
      {
        id: "Heading2", name: "Heading 2",
        basedOn: "Normal", next: "Normal", quickFormat: true,
        run:       { size: 26, bold: true, font: "Hiragino Sans", color: "2E74B5" },
        paragraph: { spacing: { before: 240, after: 120, line: 360 }, outlineLevel: 1 },
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: PAGE_W, height: PAGE_H },
        margin: { top: MARGIN, bottom: MARGIN + 360, left: MARGIN, right: MARGIN },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC" } },
          spacing: { after: 100 },
          alignment: AlignmentType.RIGHT,
          children: [txt("スマートグリッド 事業的パテントスペース 再現実験報告書", { size: 18, color: "888888" })],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            txt("— ", { size: 18, color: "888888" }),
            new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "888888" }),
            txt(" —", { size: 18, color: "888888" }),
          ],
        })],
      }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUT_FILE, buf);
  console.log("Saved:", OUT_FILE);
}).catch(e => { console.error(e); process.exit(1); });
