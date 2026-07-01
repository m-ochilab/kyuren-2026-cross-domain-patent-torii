from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

from lxml import etree


NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKGREL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"main": NS_MAIN, "rel": NS_REL, "pkgrel": NS_PKGREL}


SOURCE = Path("/Users/h-torii4649/Downloads/公募要領･申請書類フォーマット(第２回用)/第2回_様式1_研究計画調書.xlsx")
OUT_DIR = Path("application_work/output")
OUTPUT = OUT_DIR / "第2回_様式1_研究計画調書_要入力あり_Torii_Harukaze_草案.xlsx"


def col_row(cell: str) -> tuple[str, int]:
    m = re.fullmatch(r"([A-Z]+)([0-9]+)", cell)
    if not m:
        raise ValueError(cell)
    return m.group(1), int(m.group(2))


def col_to_num(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + ord(ch) - 64
    return n


def cell_sort_key(cell: str) -> tuple[int, int]:
    col, row = col_row(cell)
    return row, col_to_num(col)


def workbook_map(zf: zipfile.ZipFile) -> dict[str, str]:
    wb = etree.fromstring(zf.read("xl/workbook.xml"))
    rels = etree.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_by_id = {r.get("Id"): r.get("Target") for r in rels.findall("pkgrel:Relationship", NS)}
    out = {}
    for s in wb.findall("main:sheets/main:sheet", NS):
        rid = s.get(f"{{{NS_REL}}}id")
        target = rel_by_id[rid]
        if not target.startswith("xl/"):
            target = "xl/" + target
        out[s.get("name")] = target
    return out


def inline_text_cell(cell_ref: str, value: str, style: str | None):
    c = etree.Element(f"{{{NS_MAIN}}}c", r=cell_ref, t="inlineStr")
    if style is not None:
        c.set("s", style)
    is_node = etree.SubElement(c, f"{{{NS_MAIN}}}is")
    t = etree.SubElement(is_node, f"{{{NS_MAIN}}}t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = value
    return c


def numeric_cell(cell_ref: str, value: int | float, style: str | None):
    c = etree.Element(f"{{{NS_MAIN}}}c", r=cell_ref)
    if style is not None:
        c.set("s", style)
    v = etree.SubElement(c, f"{{{NS_MAIN}}}v")
    v.text = str(value)
    return c


def set_text(root, cell_ref: str, value: str) -> None:
    set_cell(root, cell_ref, value, is_number=False)


def set_number(root, cell_ref: str, value: int | float) -> None:
    set_cell(root, cell_ref, value, is_number=True)


def set_cell(root, cell_ref: str, value, is_number: bool) -> None:
    sheet_data = root.find("main:sheetData", NS)
    _, row_num = col_row(cell_ref)
    row = sheet_data.find(f"main:row[@r='{row_num}']", NS)
    if row is None:
        row = etree.Element(f"{{{NS_MAIN}}}row", r=str(row_num))
        rows = sheet_data.findall("main:row", NS)
        insert_at = next((i for i, r in enumerate(rows) if int(r.get("r")) > row_num), len(rows))
        sheet_data.insert(insert_at, row)

    existing = row.find(f"main:c[@r='{cell_ref}']", NS)
    style = existing.get("s") if existing is not None else None
    new_cell = numeric_cell(cell_ref, value, style) if is_number else inline_text_cell(cell_ref, str(value), style)
    if existing is not None:
        row.replace(existing, new_cell)
    else:
        cells = row.findall("main:c", NS)
        insert_at = next((i for i, c in enumerate(cells) if cell_sort_key(c.get("r")) > cell_sort_key(cell_ref)), len(cells))
        row.insert(insert_at, new_cell)


def set_formula_cached_value(root, cell_ref: str, value: int | float) -> None:
    c = root.find(f".//main:c[@r='{cell_ref}']", NS)
    if c is None:
        set_number(root, cell_ref, value)
        return
    v = c.find("main:v", NS)
    if v is None:
        v = etree.SubElement(c, f"{{{NS_MAIN}}}v")
    v.text = str(value)


def update_calc_mode(workbook_xml: bytes) -> bytes:
    root = etree.fromstring(workbook_xml)
    calc_pr = root.find("main:calcPr", NS)
    if calc_pr is None:
        calc_pr = etree.SubElement(root, f"{{{NS_MAIN}}}calcPr")
    calc_pr.set("calcMode", "auto")
    calc_pr.set("fullCalcOnLoad", "1")
    calc_pr.set("forceFullCalc", "1")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def build() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = OUT_DIR / "work.xlsx"
    shutil.copyfile(SOURCE, tmp)

    with zipfile.ZipFile(tmp, "r") as zin:
        files = {name: zin.read(name) for name in zin.namelist()}
        sheet_targets = workbook_map(zin)

    s1 = etree.fromstring(files[sheet_targets["研究計画調書_1枚目"]])
    s2 = etree.fromstring(files[sheet_targets["研究計画調書_2枚目"]])
    s3 = etree.fromstring(files[sheet_targets["研究計画調書_3枚目"]])
    s4 = etree.fromstring(files[sheet_targets["研究計画調書_4枚目"]])

    # Sheet 1: basic/applicant information. Unknown personal/institutional data is left explicit.
    for cell, value in {
        "C8": "[要入力] e-Rad研究者番号",
        "C10": "[要入力] 所属機関発行メールアドレス",
        "D12": "トリイ ハルカゼ",
        "D13": "鳥井 春風",
        "C15": "[要入力]",
        "F15": "[要入力]",
        "H15": "[要入力]",
        "C16": "[要入力] e-Rad所属機関コード",
        "C18": "[要入力] 所属機関名",
        "C19": "[要入力] 部局名",
        "C20": "[要入力] 職・身分",
        "L20": "Y",
        "C21": "大学",
        "C23": "修士課程学生",
        "C27": "電気工学・電子工学・情報科学・コンピューターサイエンス",
        "C29": "7.発見・設計支援",
        "G33": "Y",
        "I33": "Y",
        "C35": "LLMによる特許文書の課題・解決手段分離に基づく異分野技術候補抽出手法の構築",
        "G39": "Y",
        "I39": "Y",
        "K39": "Y",
        "C40": "Y",
        "E40": "Y",
        "G40": "Y",
        "C42": "特許文書から課題文脈・解決手段文脈をLLMで抽出し、文埋め込みと類似度計算で候補をランキングしている。APIによる抽出、PatentSBERTa等の既存モデルによるベクトル化、結果の可視化・著者確認評価までを研究プロセスに組み込んでいる。",
    }.items():
        set_text(s1, cell, str(value))
    for cell, value in {"H6": 2026, "J6": 6, "L6": 17}.items():
        set_number(s1, cell, value)
    title = "LLMによる特許文書の課題・解決手段分離に基づく異分野技術候補抽出手法の構築"
    set_formula_cached_value(s1, "N35", len(title))
    current_ai = "特許文書から課題文脈・解決手段文脈をLLMで抽出し、文埋め込みと類似度計算で候補をランキングしている。APIによる抽出、PatentSBERTa等の既存モデルによるベクトル化、結果の可視化・著者確認評価までを研究プロセスに組み込んでいる。"
    set_formula_cached_value(s1, "N42", len(current_ai))

    # Sheet 2: research plan.
    plan_fields = {
        "D8": "本研究は、特許文書に含まれる技術課題と解決手段をLLMにより分離し、異なる応用分野間で専門家が確認すべき技術候補を抽出する手法を構築することを目的とする。全文類似や単純なキーワード検索では説明しにくい候補抽出理由を、課題文脈・解決手段文脈・技術手段の関係として整理し、AIを用いた科学技術探索を加速する知見を得る。",
        "D9": "研究は六つの工程で進める。第一に、Orbis IP等から取得した特許のTitle、Abstract、Claimsを公開公報単位およびファミリー単位で整理する。第二に、LLMを用いてproblem_context、solution_context、technical_means、target_object、effect_contextを抽出し、抽出プロンプトと出力形式を固定する。第三に、PatentSBERTa等の特許向け文埋め込みモデルで文脈をベクトル化し、課題文脈の類似度を算出する。第四に、参照分野で高出現し対象分野で低出現の手法をGapScoreでランキングする。第五に、U-Netを対象とした医療画像解析から製造欠陥検出への後ろ向き評価と、洗浄・除去系技術から半導体洗浄への補助分析を実施する。第六に、上位候補をLLM支援付き著者確認で評価し、Hit@k、出現率変化、候補タイプ別の解釈可能性を検証する。",
        "D10": "本研究では、大量の特許文書を人手で読み分けることがボトルネックであり、全文類似だけでは課題、対象物、解決手段、効果が混在するため候補抽出の根拠を説明しにくい。LLMを用いることで、長い特許文書から課題文脈と解決手段文脈を構造化し、人間が確認しやすい中間表現を得られる。さらに文埋め込みモデルを組み合わせることで、分野名や対象物が異なる場合でも、課題の近さに基づく探索が可能になる。既に小規模実験では、医療画像解析で先行したU-Net関連技術が製造欠陥検出分野で後年増加する傾向を確認しており、AI導入による実現可能性は高い。",
        "D11": "最終目標は、特許文書から異分野技術候補を説明可能に抽出するAI支援型スクリーニング手法を確立し、研究者が新しい応用可能性を短時間で探索できる基盤を作ることである。三か月後までに、文脈抽出プロンプト、データ整形、GapScore計算、U-Net後ろ向き評価の再現可能なパイプラインを完成させる。六か月後までに、補助分析を含む候補タイプ別評価、ベースライン比較、ノウハウ整理、公開可能なサンプルコードと報告書を整備する。期間終了時には、研究計画から評価までを他分野の研究者が再利用できる形でまとめる。",
        "D12": "LLM抽出プロンプト、失敗例、評価ラベル、費用対効果、データ管理上の注意を工程別に整理する。最終的に、特許以外の科学技術文書にも転用可能なチェックリスト、プロンプト雛形、再現用サンプルパイプラインとして共有する。",
        "D13": "個人情報・契約上公開できない特許データを除き、サンプルデータ、コード、図表、プロンプト、検証報告書をGitHub等で公開する予定である。",
        "D14": "該当なし（関連する本人業績がある場合は提出前に差し替えてください。）",
        "D15": "該当なし",
        "D16": "該当なし",
        "D17": "該当なし",
        "D18": "該当なし",
    }
    for cell, value in plan_fields.items():
        set_text(s2, cell, value)
    for cell in ["D8", "D9", "D10", "D11", "D12", "D13"]:
        count_cell = "E" + cell[1:]
        set_formula_cached_value(s2, count_cell, len(plan_fields[cell]))

    # Sheet 3: budget details in thousand yen.
    budget_text = {
        "M11": "データ保存用SSD・バックアップ媒体",
        "N11": 150,
        "D34": "特許文書・抽出結果・評価ファイルを安全に保存し、再現実験とバックアップを行うために必要である。",
        "D40": "候補確認・ラベル付け補助謝金",
        "E40": 200,
        "H40": "成果発表・研究打合せ旅費",
        "J40": 300,
        "D63": "抽出候補の妥当性確認と成果発表・研究打合せに必要な経費である。",
        "D69": "生成AI API利用料",
        "E69": 900,
        "D70": "クラウドGPU・計算資源利用料",
        "E70": 1200,
        "D71": "特許データ処理・関連ソフトウェア利用料",
        "E71": 250,
        "D92": "LLMによる文脈抽出、文埋め込み計算、候補ランキング、再実行を伴う評価に必要な経費である。API費用とクラウド計算資源を分けて管理し、処理量と再実行回数に基づき適正に執行する。",
    }
    for cell, value in budget_text.items():
        if isinstance(value, int):
            set_number(s3, cell, value)
        else:
            set_text(s3, cell, value)
    for cell, value in {
        "J31": 0,
        "N31": 150,
        "E60": 200,
        "J60": 300,
        "N60": 0,
        "E89": 2350,
    }.items():
        set_formula_cached_value(s3, cell, value)

    # Sheet 4: API and compute basis.
    for cell, value in {
        "D9": "特許文書の課題・解決手段文脈抽出",
        "E9": 900,
        "F9": "Title/Abstract/Claimsから構造化項目を抽出する。約5,000〜10,000文書相当を複数回実行し、プロンプト改良・再実行・評価用サンプル抽出を含めて算定する。",
        "D22": "クラウドGPU（A10/T4相当または同等環境）",
        "E22": "PatentSBERTa等の文埋め込み計算と候補ランキングを、ローカル環境では処理時間が過大となる規模で実施するため。",
        "F22": 1200,
        "G22": "特許文書の文脈ベクトル化、類似度計算、ベースライン比較、パラメータ変更時の再実行を想定。数十〜百時間程度のGPU/高メモリ計算資源利用として算定する。",
    }.items():
        if isinstance(value, int):
            set_number(s4, cell, value)
        else:
            set_text(s4, cell, value)

    files[sheet_targets["研究計画調書_1枚目"]] = etree.tostring(s1, xml_declaration=True, encoding="UTF-8", standalone=True)
    files[sheet_targets["研究計画調書_2枚目"]] = etree.tostring(s2, xml_declaration=True, encoding="UTF-8", standalone=True)
    files[sheet_targets["研究計画調書_3枚目"]] = etree.tostring(s3, xml_declaration=True, encoding="UTF-8", standalone=True)
    files[sheet_targets["研究計画調書_4枚目"]] = etree.tostring(s4, xml_declaration=True, encoding="UTF-8", standalone=True)
    files["xl/workbook.xml"] = update_calc_mode(files["xl/workbook.xml"])

    # Cached summary values on sheet 1.
    s1 = etree.fromstring(files[sheet_targets["研究計画調書_1枚目"]])
    for cell, value in {
        "D48": 3000,
        "E48": 0,
        "G48": 150,
        "I48": 200,
        "K48": 300,
        "L48": 2350,
    }.items():
        set_formula_cached_value(s1, cell, value)
    files[sheet_targets["研究計画調書_1枚目"]] = etree.tostring(s1, xml_declaration=True, encoding="UTF-8", standalone=True)

    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)

    tmp.unlink(missing_ok=True)
    print(OUTPUT)


if __name__ == "__main__":
    build()
