\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{my_bthesis}[2025/12/27 Oita Univ Thesis Class]


\LoadClass[12pt]{ltjsreport}

% --- 1. 大学指定の余白設定 (左30, 右20, 上25, 下30) ---
\RequirePackage[left=30mm, right=20mm, top=25mm, bottom=30mm]{geometry}

% --- 2. パッケージ  ---
\RequirePackage{graphicx}
\RequirePackage{amsmath, amssymb}
\RequirePackage{cite}
\RequirePackage{setspace}
\RequirePackage{enumitem}


% --- 3. 大学指定の「30文字/行、30行/ページ」の設定 ---
\setstretch{1.7} % 30行/ページにするための行間調整
\RequirePackage{luatexja}
\ltjsetparameter{kanjiskip=0.5pt, xkanjiskip=1pt} % 30文字/行への微調整

% --- 4. 表紙 ---
\newcommand{\etitle}[1]{\def\@etitle{#1}} % 英語タイトル用のコマンドを定義
\renewcommand{\maketitle}{
  \begin{titlepage}
    \begin{center}
      % --- 上部：論文の種類 ---
      \vspace*{10mm}
      {\Large 学士論文 \par}
      
      % --- 中央：題目（ここがページの上寄りに配置されます） ---
      \vspace*{20mm}
      {\Large \@title \par}

      \vspace*{5mm}
      {\large \@etitle \par}
      
      % --- 空白調整（ここから下の項目をページ下部へ押し下げる） ---
      \vfill 
      
      % --- 下部：所属・氏名・指導教員（ここにまとまります） ---
      {\large 大規模ネットワークサイエンス研究室 \par}
      
      \vspace*{1mm}
      {\large \@author \par}
      
      \vspace*{1mm}
      {\large 指導教員 大知 正直 准教授 \par}

      \vspace*{1mm}
      {\large \@date \par}

      % --- 所属 ---
      {\large 大分大学 理工学部 共創理工学科 知能情報システムコース \par}
      
      \vspace*{15mm} % ページの一番下からの距離
    \end{center}
  \end{titlepage}
}
\pagestyle{plain}


% --- 5. 目次のカスタマイズ ---
\RequirePackage{tocloft}

% 「目次」という見出しを左寄せ・大きく・太字にする
\renewcommand{\contentsname}{\huge \textbf{目 次}} % サイズを \huge に変更
\renewcommand{\listfigurename}{\huge \textbf{図 目 次}} % 図目次の見出し
\renewcommand{\listtablename}{\huge \textbf{表 目 次}}  % 表目次の見出し
\renewcommand{\cftaftertoctitle}{} % 後ろの \hfill を消して左寄せにする
\renewcommand{\cftafterloftitle}{}
\renewcommand{\cftafterlottitle}{}
\setlength{\cftaftertoctitleskip}{20pt} % 見出しと中身の間の余白を調整
\setlength{\cftafterloftitleskip}{20pt}
\setlength{\cftafterlottitleskip}{20pt}

% 章（Chapter）の前に「第」、後に「章」を付ける
\renewcommand{\cftchapleader}{\cftdotfill{\cftdotsep}} % 章にもドット線を引く
\renewcommand{\cftfigleader}{\cftdotfill{\cftdotsep}}
\renewcommand{\cfttableader}{\cftdotfill{\cftdotsep}}
\renewcommand{\cftchappresnum}{}
\renewcommand{\cftchapaftersnum}{}
\setlength{\cftchapnumwidth}{4em} % 「第X章」の幅を確保

% 章のフォントを太字にする（画像に合わせる）
\renewcommand{\cftchapfont}{\normalfont\bfseries}
\renewcommand{\cftchappagefont}{\normalfont\bfseries}

% --- 6. 章見出し（Chapter）のレイアウト変更 ---
\RequirePackage{titlesec}

% 「第1章」と「タイトル」を1行に並べる設定
\titleformat{\chapter}[hang]
  {\huge\bfseries} % フォントの設定
  {第\thechapter 章\hspace{1em}} % 「第」と「章」を直接書き込みます
  {0pt}
  {}

% 章見出し前後の余白調整（お好みに合わせて）
\titlespacing{\chapter}{0pt}{0pt}{20pt}


% --- 7. レイアウト計算用の内部命令 ---
\makeatletter
% 文字数指定（日本語n文字 ＝ 英語2n文字 分の幅に調整）
\def\mojiparline#1{
    \@tempdima=\linewidth
    \advance\@tempdima by -#1\zw
    \divide\@tempdima by #1
    \ltjsetparameter{kanjiskip=\@tempdima}
    \parindent=1\zw
    \advance\parindent by \@tempdima
}

% 行数指定
\def\linesparpage#1{
    \@tempdima=\textheight
    \divide\@tempdima by #1
    \baselineskip=\@tempdima
}
\makeatother

% --- 8. 要旨・Abstract用 (和40/英80文字, 45行) ---
\newcommand{\startabstractpage}{
  \clearpage
  % 45行入れるために上下の余白を少し調整
  \newgeometry{left=30mm, right=20mm, top=20mm, bottom=25mm, footskip=10mm}
  \selectfont
  \mojiparline{40}  % 和文40字 = 英文80字
  \linesparpage{45} % 45行
}

% --- 9. 本文用 (30文字, 30行) ---
\newcommand{\startmaintext}{
  \clearpage
  % 大学指定の標準余白を再適用
  \newgeometry{left=30mm, right=20mm, top=25mm, bottom=30mm, footskip=10mm}
  \selectfont
  \mojiparline{30}  % 30文字
  \linesparpage{30} % 30行
}