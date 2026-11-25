# Flat Information Graphics — 扁平信息圖：數據圖、儀表板與粗野派
---
id: FLAT-INFORMATION-GRAPHICS
name: Flat Information Graphics — 扁平信息圖風格
type: graphic-design
year: '—'
director: '—'
primary_scene: infographic
secondary_scene: dashboard
category: Information Graphic
tags:
  - flat
  - 扁平
  - infographic
  - 信息圖
  - data-viz
  - 數據可視化
  - dashboard
  - 儀表板
  - brutalist
  - 粗野派
  - HUD
  - monochrome
  - 單色
  - network-diagram
  - 網絡圖
techniques:
  typography:
    - 巨字標題加小字標籤
    - 等寬數字
  layout:
    - 網格卡片分區
    - 中心放射網絡
  color:
    - 單色加一個 accent
    - 黑底白字信息圖
    - 淺底黑字信息圖
  charts:
    - 圓餅環形條形
    - 折線加面積
    - 圓點網絡
  data:
    - 數字優先
    - 標籤加單位
    - 來源標註
styles: [flat, infographic, dashboard, brutalist, hud, minimal, data]
scene_relations:
  extra_strong: []
  extra_reference: []
---

## 元信息

| 字段 | 值 |
|------|-----|
| ID | FLAT-INFORMATION-GRAPHICS |
| 名稱 | Flat Information Graphics — 扁平信息圖風格 |
| 類型 | graphic-design（信息圖 / 儀表板） |
| 分類 | Information Graphic（用戶原分類） |
| 年份 | 參考圖未標年份（個別註明來源日期） |
| 關鍵詞 | flat, 扁平, infographic, 信息圖, data-viz, 數據可視化, dashboard, 儀表板, brutalist, 粗野派, HUD, monochrome, 單色, network-diagram, 網絡圖 |
| 主場景 | infographic |
| 輔場景 | dashboard |
| 參考圖 | 14 張（見文末「參考圖」），2026-11-25 由 cristi 批量提供；其中 1 張與上一批重複，只記不重複分析 |

---

## 技法標籤

- **字體**：巨字標題加小字標籤, 等寬數字
- **版式**：網格卡片分區, 中心放射網絡
- **色彩**：單色加一個 accent, 黑底白字信息圖, 淺底黑字信息圖
- **圖表**：圓餅環形條形, 折線加面積, 圓點網絡
- **數據**：數字優先, 標籤加單位, 來源標註

---

## 分類說明

14 張參考圖全部屬於同一風格家族：**扁平信息圖（flat information graphics）**——冇玻璃、冇漸變（個別除外）、硬邊、數據行先。按用途同語氣分四個子變體，寫入同一份 MD，唔分開寫：

| 子變體 | 參考圖 | 底色 | 用途 |
|--------|--------|------|------|
| A. 扁平數據信息圖 | 01、03、04、10、12 | 淺灰 / 黑 / 米 | 數據報道、解釋圖 |
| B. 扁平儀表板 | 05、08、09 | 淺灰 / 深黑 | 醫療、金融、IoT 儀表板 |
| C. 粗野派儀表板 | 07、13 | 白底黑字 + 螢光綠 | SaaS / 金融 / 電商儀表板 |
| D. 技術 HUD 單色 | 02、11、14 | 淺灰 / 白 / 黑白 | 技術圖解、系統圖 |

重複圖：06 號（Management 儀表板）與上一批 08 號相同，已收錄於 glassmorphism MD（單色儀表板玻璃），此批只記不重複分析。

---

## 字體技法（→ Typography）

### 巨字標題加小字標籤——大字講嘢，細字解釋

- **表現**：每張圖都有一個超大標題（"DATA"、"Satellites network"、"BRUTALIST DASH UI"、"IMAGESPELL"、"Network OFF-GRID"、"INFOGRAPHICS"），字重極粗、字號佔版面闊度 60–90%。標題下面或旁邊係一排水細字標籤（全大寫、字號約標題的 1/12）："CLEAN LAYOUTS / BOLD TYPOGRAPHY / RAW AESTHETIC / MAXIMUM IMPACT"、"A VISUAL STUDY / GRID & PATTERNS"、"UI/UX INSPIRATION"。大字係態度，細字係說明。
- **手法**：標題用最粗的字重（800–900）、condensed 或超粗黑體，唔好用普通粗體。細字標籤全部大寫、字母間距放寬、行距鬆，一組最多四行。標題同標籤之間要留白，唔好貼埋。
- **可遷移**：信息圖的標題層——一個巨字標題 + 一組小字標籤，標題講主題，標籤講做法。
- **適用場景**：infographic, dashboard, poster

### 等寬數字——數字要對齊，唔好跳

- **表現**：所有數字都用等寬（tabular）字體：HUD 的 "329"、"206"、DATA 頁的 "79.2%"、"14h"、"7.5%"、Hedging 的 "$24.8M"、"78.6%"、Deerflow 的 "12.4K"、"128"。數字唔會因為 1 同 8 闊度唔同而跳位，對齊晒。
- **手法**：數字一律用 tabular-nums（等寬數字），唔用預設比例數字。小數點後保留相同位數（一位或兩位），單位（%、h、$、M）跟數字用同一字體、細一級。
- **可遷移**：任何數據圖——數字用等寬，小數位數統一，單位細一級。
- **適用場景**：infographic, dashboard

---

## 版式（→ Layout）

### 網格卡片分區——一格一組數據

- **表現**：DATA 頁（01）係 4 欄 × 3 行共 12 格，每格一種圖表（圓餅、環形、條形、數字、地圖）；Deerflow（09）係 3 欄 × 4 行共 12 張卡，每張一個系統（Agent、Claude、Device、Tesla、Pharma、Medical、Bio、Word、Retail、Entertainment、Game、Vision）；Hedging（08）係上中下三區（四張 KPI 卡、折線圖、持倉表）。全部用網格，唔用自由排。
- **手法**：網格要定死欄數（3 或 4 欄最穩），卡片間距均等，唔用線分隔、只用底色或留白分。重要數據放左上（視線起點），次要放右下。卡片唔好大細不一——同級卡片同高。
- **可遷移**：數據頁同儀表板——定死欄數、一格一組數據、重要放左上。
- **適用場景**：infographic, dashboard

### 中心放射網絡——一個中心，全部連出去

- **表現**：Satellites network（03）同 Crypto Wars（04）都係中心放射式：中間一個大圓（"Satellites network"、"THE CRYPTO WARS"），周圍幾十個細圓（國家、機構、用途），用線連住，圓越大數字越大。讀者一眼就知邊個係中心、邊個係分支。
- **手法**：中心圓直徑約版面 25–30%，分支圓按數值比例縮放（唔好全部一樣大）。連線要幼（1px）、顏色淺，唔好搶過圓。分支太多時分組（按軌道/按國家/按用途），每組一個小標題。
- **可遷移**：關係圖、網絡圖——一個中心、分支按數值定大細、連線幼而淺。
- **適用場景**：infographic

---

## 色彩（→ Color）

### 四色體系

| 區域/元素 | 主色 (hex) | 輔色 (hex) | 作用 | 設計理由 |
|-----------|-----------|-----------|------|---------|
| 藍色數據 | `#2E4BFF`（目測） | 黑 `#111111`、白 `#FFFFFF` | 主數據 | DATA 頁（01）的藍——圓餅、條形、數字全部用同一隻藍，唔用第二隻彩色；藍 + 黑 + 白三色行晒成版 |
| 黑底信息圖 | `#0A0A0A` 近黑 | 白 `#FFFFFF` | 底 | Satellites（03）、Blackbox（10）、Hedging（08）、Deerflow（09）——黑底令白字白線浮出嚟，數據感強 |
| 螢光綠 accent | `#C6FF00`（目測） | — | 焦點 | 粗野派（07、13）唯一的 accent——標題 highlight、按鈕、數字升幅，全部同一隻綠，唔用第二隻 |
| 橙色 accent | `#F97316`（目測） | — | 焦點 | Hedging（08）同 Off-Grid（14）的橙——折線、條形、重點詞；一版一個 accent，唔好橙綠齊出 |
| 米色底 | `#C8B89B`（目測） | 黑 `#111111`、白 `#FFFFFF`、棕 `#8A6D4B`（目測） | 底 | Crypto Wars（04）的米色底——檔案感、舊紙感，配合黑白圓做對比 |
| 淺灰底 | `#F4F4F1` 近白（目測） | 黑 `#111111` | 底 | DATA 頁、Imagespell、Off-Grid 的淺底——乾淨、唔搶數據 |
| 紅色警示 | `#E5484D`（目測） | — | 警示 | Deerflow 的 OFFLINE 4%、ALERTS 2、跌幅——紅色只用喺「唔好」的數字，唔好做裝飾 |

### 單色加一個 accent——一版一隻彩色

- **表現**：14 張圖全部守同一條規則：底色（黑/白/淺灰/米）+ 文字色（黑/白）+ **一隻** accent 顏色。DATA 頁係藍、粗野派係螢光綠、Hedging 係橙、Crypto Wars 係棕、Deerflow 係紅（警示）+ 白點。冇一張圖用兩隻或以上 accent。
- **手法**：揀 accent 之前先問：呢版想人望邊度？accent 只畀嗰個位置（主數字、主按鈕、主折線）。其他圖表用黑白灰。accent 飽和度要夠高，否則喺黑白之間唔出。
- **可遷移**：信息圖的配色——底 + 文字 + 一隻 accent，唔好多。
- **適用場景**：infographic, dashboard

### 黑底白字信息圖——數據感來自對比

- **表現**：Satellites（03）、Blackbox（10）、Hedging（08）、Deerflow（09）全部黑底白字白線。黑底唔係裝飾，作用係令數據「浮」出嚟——白圓、白線、白字喺黑底上面，對比最強，遠睇都讀到。黑底亦令 accent（橙、綠、紅）更搶。
- **手法**：黑底要用近黑唔係純黑（`#0A0A0A`–`#14161C`），避免死黑。白字唔好用純白大面積——標題用白，正文用淺灰 `#A0A0A0`，否則黑底白字會刺眼。線用 1px 白，唔好 2px。
- **可遷移**：數據量大、想人一眼掃晒的圖——黑底白字，對比行先。
- **適用場景**：infographic, dashboard

### 淺底黑字信息圖——檔案感來自留白

- **表現**：DATA 頁（01）、Imagespell（12）、Off-Grid（14）係淺底黑字。淺底的感覺係檔案、報告、技術文件——乾淨、冷靜、唔迫人。留白多，線幼，字細，成版好似一張工程圖。
- **手法**：淺底用近白唔係純白（`#F4F4F1`），加少少暖。黑字用近黑唔係純黑。留白至少 20% 版面，唔好填滿。
- **可遷移**：報告式信息圖——淺底、留白、幼線、細字。
- **適用場景**：infographic

---

## 圖表（→ Charts）

### 圓餅環形條形——三種基本圖就夠

- **表現**：DATA 頁（01）一版用齊三種：年齡構成圓餅、男女比大小圓、運動時間橫條、有效取得率大數字、平均殘業時間大數字、入社 3 年以內離職率大數字、出身地點狀地圖、在勤狀況橫條、午餐泡泡圖、服裝環形、學生時代部活方塊圖、休日過法方塊圖。12 格，12 種數據，但圖表類型只係四種：圓餅、環形、橫條、方塊。
- **手法**：一版圖表類型唔好超過四種，否則讀者要重新學習每種圖。圓餅最多五瓣，橫條要對齊基線，方塊圖要用面積唔係邊長表達比例。
- **可遷移**：數據頁——圖表類型封頂四種，圓餅最多五瓣。
- **適用場景**：infographic

### 折線加面積——趨勢圖的兩件套

- **表現**：Hedging（08）的匯率走勢係折線 + 下面淡淡的面積填充；Deerflow（09）的 Retail Analytics 係點線折線 + 圓點標記；Brutalist（07）的 Analytics Overview 係折線 + 下面螢光綠面積。折線講走勢，面積講量。
- **手法**：折線用 accent 色（橙/綠），面積用同一色、透明度 10–15%，唔好實色。最高點加圓點標記 + 數值標籤。X 軸日期要疏（每 5 日一格），唔好每日一格。
- **可遷移**：趨勢圖——折線 accent 色 + 淡面積 + 最高點標記。
- **適用場景**：infographic, dashboard

### 圓點網絡——用圓講比例

- **表現**：Satellites（03）用圓大細講衛星數量（654 LEO、458 GEO、286 Commercial）；Crypto Wars（04）用圓大細講機構重要性（FBI、Apple、Encryption 最大）；DATA 頁（01）的日本地圖用圓點密度講出身地分佈；Deerflow（09）的 Bio Sensor 同 Entertainment 用圓點陣講數值。
- **手法**：圓面積要同數值成正比（唔係直徑）。最大圓同最小圓比例唔好超過 10:1，否則細圓睇唔到。圓上面要標數字，唔好只靠大細估。
- **可遷移**：比例圖——圓面積對應數值，標數字，比例唔超過 10:1。
- **適用場景**：infographic

---

## 數據（→ Data）

### 數字優先——數字就係設計

- **表現**：每張圖最搶眼的都係數字，唔係圖：DATA 頁的 "79.2%"、"14h"、"7.5%" 佔成格一半；HUD 的 "329"、"206" 係成版中心；Hedging 的 "$24.8M"、"78.6%"、"96.2%" 係四張卡的標題；Deerflow 的 "12.4K"、"128"、"1.28K" 係每張卡的標題。數字大到唔使搵，圖表只係配角。
- **手法**：每組數據揀一個主數字，放大到卡片高度的 40–50%，其他數字細一級。主數字用最粗字重 + accent 色或黑白對比最強的位置。
- **可遷移**：數據卡——一個主數字放大，其他細一級。
- **適用場景**：infographic, dashboard

### 標籤加單位——數字唔可以裸跑

- **表現**：每個數字上面或下面都有標籤 + 單位："79.2%" 上面寫「有効取得率」；"14h" 上面寫「平均残業時間」；"$24.8M" 下面寫 "USD Equivalent"；"329" 上面寫 "GEAR EXT"；"12.4K" 下面寫 "TOKENS"。冇一個數字係裸跑。
- **手法**：標籤用全大寫細字、放數字上面；單位跟數字後面、細一級；比較值（↑12.4% vs last 24h）放數字下面、灰字。
- **可遷移**：數字卡——標籤上、單位後、比較值下。
- **適用場景**：infographic, dashboard

### 來源標註——數據要有出處

- **表現**：Satellites（03）底部寫 "Sources: Union of Concerned Scientists, space-track.org. Note: Data to July 2014. SCMP Graphic: Alberto Lucas López"；Crypto Wars（04）頂部寫 "Information gathered from BBC News, New York Times, Motherboard.com, The Hacker News, and TheAtlantic.com" + "CREATED BY YIZZY WU"；DATA 頁（01）每格下面都有細字註明調查期間同對象。
- **手法**：來源放底部、細字、灰色，唔好放大。調查期間同樣要寫（Data to July 2014）。作者署名放角落。
- **可遷移**：任何引用外部數據的圖——底部細字寫來源 + 期間。
- **適用場景**：infographic

---

## 適用提示

- **最佳匹配場景**：數據報道、年度報告、研究解釋圖、SaaS/金融/醫療/IoT 儀表板；想要「冷靜、準確、唔花巧」的數據呈現。
- **不適用場景**：情感類、品牌故事、生活方式（扁平數據風太冷，冇溫度）；需要強烈視覺衝擊的廣告（巨字海報比數據圖啱）；數據量少的頁面（冇數據就唔好硬做信息圖）。
- **引用優先級**：核心引用（做扁平信息圖或儀表板時——數字優先 + 單色加一個 accent 兩者同時需要）；特定技法借用（僅需網絡圖時，只看中心放射網絡一段；僅需粗野派時，只看粗野派儀表板子變體）。

---

## 參考圖

14 張由 cristi 於 2026-11-25 批量提供（分類：Information Graphic），原文件存於 `~/workspace/user/files/`：

| 編號 | 文件 | 內容 |
|------|------|------|
| 01 | 1000017410_10_7a2d.jpg | Metro Ad Agency DATA 頁：日文招聘數據頁，藍黑白，12 格圓餅/環形/條形/地圖 |
| 02 | 1000017409_11_kdds.jpg | 淺灰圓形 HUD 儀表：單色技術錶盤，數字 329 / 206 |
| 03 | 1000017411_12_mey5.jpg | Satellites network：黑底白字衛星網絡圖，中心放射，來源 SCMP |
| 04 | 1000017412_13_z9fm.jpg | THE CRYPTO WARS：米底黑白圓網絡圖，FBI / Apple / 加密，作者 Yizzy Wu |
| 05 | 1000017408_14_em7j.jpg | Cardiology 醫療儀表板：淺灰底、深框、時間線、血壓卡、螢光黃點綴 |
| 06 | 1000017407_15_0wx7.jpg | Management 儀表板——**重複圖，與上一批 08 號相同**，已收錄於 glassmorphism MD，此批不重複分析 |
| 07 | 1000017399_16_i9gk.jpg | BRUTALIST DASH UI：黑白 + 螢光綠粗野派儀表板，XENO |
| 08 | 1000017398_17_akxv.jpg | Hedging Overview 手機金融儀表板：深黑底、橙色折線、持倉表 |
| 09 | 1000017397_18_lfg6.jpg | DEERFLOW AIOT DASHBOARD：深黑 12 卡、點陣圖標、紅白點綴 |
| 10 | 1000017396_19_e14z.jpg | INFOGRAPHICS BLACKBOX GRAFX：黑底白 HUD 元素，圓環、條形、警告標 |
| 11 | 1000017395_20_h7ua.jpg | Design 黑白板：地球儀、內容卡、手機 mockup，黑白對比 |
| 12 | 1000017394_21_6c5e.jpg | IMAGESPELL：淺灰技術圖解，QR 碼、條碼、圖表，中央 OpenAI 標誌 |
| 13 | 1000017393_22_y5uq.jpg | BRUTALIST UI/UX DESIGN：粗野派四屏（DEVORA / 銀行 / 電商 / 旅行健身） |
| 14 | 1000017392_23_936p.jpg | Network OFF-GRID：白底橙黑技術海報，粗字標題、條碼、圓點陣 |

---

## 參考資源

- 搜尋關鍵詞：Pinterest / Behance 搜 "flat infographic design" / "data visualization poster" / "brutalist dashboard ui" / "monochrome HUD interface" / "satellite network infographic"
- 同類參考：SCMP Graphics 的數據新聞圖；Visual Capitalist 的信息圖；Dribbble 的 brutalist dashboard 作品
