"""AI in board meeting records by year, on confirmed hits only.

Meeting files: every row of data/tier2_meeting_index.csv, plus every file in data/tier2_intake_index.csv that is not a
duplicate of a Tier 2 file, is dated 2023-2026, and is not a rule, statute, newsletter, CPE list, snapshot or recording.
Files whose type is search, notice, rule_text or blank are left out (they are not meeting records). Intake files with
the same bytes (sha256) are counted once.

Confirmed hit: an AI keyword hit (artificial intelligence, AI, machine learning, generative, ChatGPT, large language
model) that a person read and marked genuine_ai in data/ai_hits_reviewed.csv, in a meeting record, dated
2023-01-01 to 2026-11-15.

The share of files is the measure to read: the number of mentions depends on how long the documents are.
Writes data/ai_trend_by_year.csv. Run: python scripts/ai_trend.py
"""
import collections
import csv
import os
import re

os.chdir('data')
SKIP = re.compile(r'rule|ilcs|nycrr|arsd|admin-rules|newsletter|cpe-subject|/snapshots/|recording', re.I)
DROP_TYPES = {'search', 'notice', 'rule_text', ''}
YEARS = ['2023', '2024', '2025', '2026']
rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8', newline='')))  # noqa: E731

files = {}
for r in rd('tier2_meeting_index.csv'):
    files[r['raw_file']] = (r['jurisdiction'].title(), r['meeting_date'], r['doc_type'])
sha_seen = set()
for r in rd('tier2_intake_index.csv'):
    if r['duplicate_of_tier2'] or SKIP.search(r['raw_file']) or not re.match(r'20(2[3-6])', r['date'] or ''):
        continue
    if r['sha256'] in sha_seen:
        continue
    sha_seen.add(r['sha256'])
    files[r['raw_file']] = (r['jurisdiction'].replace('_', ' ').title(), r['date'], r['doc_type'])
den = {f: v for f, v in files.items() if v[1][:4] in YEARS and v[2] not in DROP_TYPES}

hits = [h for h in rd('ai_hits_reviewed.csv') if h['verdict'] == 'genuine_ai' and h['is_meeting_record'] == 'yes'
        and h['file_id'] in den and '2023-01-01' <= h['date'] <= '2026-11-15']

rows = []
for y in YEARS:
    fs = {f: v for f, v in den.items() if v[1][:4] == y}
    ch = [h for h in hits if h['file_id'] in fs]
    fwa = {h['file_id'] for h in ch}
    bwf = {v[0] for v in fs.values()}
    bwa = {fs[f][0] for f in fwa}
    rows.append(dict(year=y, meeting_files=len(fs), files_with_ai=len(fwa), pct_files_with_ai=round(100 * len(fwa) / len(fs), 1),
                     boards_with_files=len(bwf), boards_with_ai=len(bwa), confirmed_ai_mentions=len(ch),
                     note='2026 runs to November 15' if y == '2026' else ''))
with open('ai_trend_by_year.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
for r in rows:
    print(r)
