# Where State Accountancy Boards Stand on AI: the data

This is the data behind the article "Where State Accountancy Boards Stand on AI," covering the public records of all 55 state and territorial accountancy boards, January 2023 to November 2026. The article describes the method.

## How to check any claim

Every claim about a board rests on one row of `data/tier1_board_ai_guidance.csv`. To check it:

1. Find the board's row. Each row has a document title, date, summary, an exact quote, a source link (`source_url`) and the path of a saved copy (`raw_file`, relative to `data/`).
2. Open the source link, or open the saved copy at that path. The saved copies are the boards' own files, unchanged.
3. Find the quoted text in the document.

**Worked example (Texas).** Line 84 of `data/tier1_board_ai_guidance.csv` is the Texas State Board of Public Accountancy's August 2026 Board Report, "AI and the Texas CPA." Its `binding_status` is `guidance`. Open `data/sources/first_pass/tier1/texas/br_082026_web_final.pdf` and search for the quote. It begins "While the Texas Public Accountancy Act and the Texas State Board of Public Accountancy Rules of Professional Conduct do not specifically address generative AI, existing professional obligations apply."

**Check every quote at once:** `python scripts/quotecheck.py` searches each Tier 1 quote in its saved copy. NASBA and AICPA documents are not saved here, so those rows are reported as "no saved copy"; use their `source_url`. Seven quotes (lines 60, 61, 62, 107, 108, 128 and 130: Ohio, Virginia, New Mexico, Wyoming) are on scanned pages with no text layer, so the script reports them as "NOT FOUND"; read them by eye in the saved PDF. The script needs `pip install beautifulsoup4 lxml pymupdf`.

## Where each number in the article comes from

| Number | Where |
|---|---|
| 55 boards | `data/jurisdictions.csv`: 55 distinct values in `jurisdiction` (Illinois has two board rows). |
| 50 of 55 with meeting records | `data/tracker_55_boards.csv`: 50 rows with `meeting_records_status` = "files collected". |
| Map 2 / 28 / 20 / 5 | `docs/figures/fig1_map.csv`: count of rows by `category` (1 to 4). |
| 30 | `docs/figures/fig2_funnel.csv`, level 2: boards with a Tier 1 document dated 2023 or later (`data/tier1_coding.csv`, NASBA and AICPA rows left out). |
| 16 | Level 3: of those, the board itself is speaking (`speaker` is `board_authored`, `board_discussion` or `individual_statement`). |
| 10 | Level 4: of those, the topic is CPAs using AI (`topic` = `cpa_use_of_ai`). |
| 1 (plus Virginia's draft) | Level 5: `binding_status` = `guidance` and `speaker` = `board_authored` (Texas). Virginia has `draft_own_guidance` = `yes`. |
| 0 | Level 6: no row has `binding_status` = `rule`. |
| 3.0%, 6.0%, 8.8%, 10.2% | `data/ai_trend_by_year.csv`, column `pct_files_with_ai` (2023, 2024, 2025, 2026). Files with a reviewed AI mention (`data/ai_hits_reviewed.csv`) divided by meeting files in `data/tier2_meeting_index.csv` and `data/tier2_intake_index.csv`. |

## Files

**`data/`**

| File or folder | What it is |
|---|---|
| `tier1_board_ai_guidance.csv` | Every document found that discusses AI (130 rows): date, binding status, summary, exact quote, source link, saved copy. |
| `tier1_coding.csv` | For each Tier 1 document: who is speaking, the topic, and the binding status. |
| `tier1_jurisdiction_summary.csv` | One row per jurisdiction: whether any AI document was found, how many, and what was searched. |
| `tier2_meeting_index.csv` | Meeting agendas, minutes and packets from the first collection pass (1,216 files). |
| `tier2_keyword_hits.csv` | Passages in those files that contain AI, outsourcing or cybersecurity terms. |
| `tier2_intake_index.csv` | Meeting files from the second pass, November 2026 (897 files); `collection_pass` says whether a file was collected from the website or in a browser. |
| `tier2_intake_keyword_hits.csv` | Keyword passages in the second-pass files. |
| `ai_hits_reviewed.csv` | Every AI keyword passage, read and marked as a real AI mention or a false match. |
| `ai_trend_by_year.csv` | Share of meeting files that mention AI, by year. |
| `tracker_55_boards.csv` | One row per board: what was collected and what is missing. |
| `coverage_classes.csv` | For boards whose sites were hard to reach: what blocked access. |
| `failures.csv` | Pages or files that could not be fetched, and why. |
| `jurisdictions.csv` | The 55 boards, with their website links. |
| `FREEZE_MANIFEST.csv` | Size and SHA-256 hash of every other file in `data/`. |
| `sources/first_pass/` | Saved copies of board records, first pass (Tier 1 documents and Tier 2 meeting files), exactly as published. |
| `sources/second_pass/` | Saved copies, second pass, collected from board websites. |
| `sources/second_pass_browser/` | Saved copies, second pass, collected in a browser (including archived copies of one board page). |

**`docs/figures/`**: `fig1_map` (the map) and `fig2_funnel` (the funnel), each as PNG, SVG and CSV.

**`scripts/`**: `figures/fig1_map.py`, `figures/fig2_funnel.py`, `ai_trend.py`, `quotecheck.py`.

## How to confirm nothing was changed

`data/FREEZE_MANIFEST.csv` lists the size and SHA-256 hash of every file in `data/` except itself. This command prints how many files differ from the list (it stops with an error if a file is missing):

```
python -c "import csv,hashlib; bad=[r['path'] for r in csv.DictReader(open('data/FREEZE_MANIFEST.csv')) if hashlib.sha256(open('data/'+r['path'],'rb').read()).hexdigest()!=r['sha256']]; print(len(bad),'files differ',bad[:5])"
```

## Rebuild the figures and the trend

With Python 3, from this folder:

```
pip install matplotlib plotly-geo pyshp beautifulsoup4 lxml pymupdf
python scripts/figures/fig1_map.py
python scripts/figures/fig2_funnel.py
python scripts/ai_trend.py
python scripts/quotecheck.py
```

The map script uses U.S. Census state shapes that come with the `plotly-geo` package, so nothing is downloaded. Run it before the funnel script, because the funnel checks its second level against the map.

## Known gaps

- **Five boards have no meeting records:** Guam, Kentucky, the Northern Mariana Islands, the U.S. Virgin Islands and Puerto Rico (`coverage_classes.csv` says why).
- **Montana** keeps only about a year of meeting records online.
- **Scanned pages have no extracted text,** so they cannot be searched: one West Virginia scan, and the seven pages named under "Check every quote at once."
- **Arizona's one source link is incomplete;** use the saved copy.
- **A collection log lists 70 Arizona, Iowa and Massachusetts files that are not here.** Only the files present are counted.

## License

The data and text are licensed under CC BY 4.0, and the code under the MIT License. See `LICENSE`.
