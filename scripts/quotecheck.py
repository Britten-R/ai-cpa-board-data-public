"""Check that each Tier 1 quote appears word for word in its saved copy.

Run from the repository root:
    python scripts/quotecheck.py                    check every row of data/tier1_board_ai_guidance.csv
    python scripts/quotecheck.py FILE "some quote"  check one quote against one saved file

For each row, the quote is searched for in the text of the file named in the raw_file column (a path under data/).
Differences in spacing, line breaks, curly quotes, dashes and words split by a hyphen at a line end are ignored.
Court-reporter transcripts print line numbers inside the text, so a second pass ignores one- and two-digit numbers.

A row is reported as "no saved copy" when the file is not in this repository (the NASBA and AICPA documents are
not saved here; their links are in source_url). It is not counted as a failure.

Needs: Python 3, beautifulsoup4 and lxml (for HTML files) and pymupdf (for PDF files). If pdftotext (poppler) is
installed it is used as a second reading of each PDF. Scanned PDFs have no text layer; for those the script uses text
recognition when rapidocr-onnxruntime is also installed (it is slow: about a minute per 10 pages). Without it,
a quote on a scanned page is reported as NOT FOUND and has to be read by eye in the saved PDF.
Install: pip install beautifulsoup4 lxml pymupdf rapidocr-onnxruntime
"""
import csv
import os
import re
import subprocess
import sys
import unicodedata
import zipfile

from bs4 import BeautifulSoup

_cache = {}

# typographic characters that are replaced before comparing
REPLACE = (('’', "'"), ('‘', "'"), ('“', '"'), ('”', '"'), ('–', '-'), ('—', '-'),
           ('­', ''), ('•', ' '), ('', ' '), (' ', ' '))


def pdf_texts(path):
    """Text of a PDF as read by pymupdf and by pdftotext (each one that works)."""
    out = []
    try:
        import pymupdf
        out.append(' '.join(page.get_text() for page in pymupdf.open(path)))
    except Exception:
        pass
    try:
        out.append(subprocess.run(['pdftotext', path, '-'], capture_output=True, timeout=120).stdout.decode('utf-8', 'replace'))
    except Exception:
        pass
    return out


def ocr_text(path):
    """Text recognition for a scanned PDF; '' if the optional packages are not installed."""
    try:
        import pymupdf
        from rapidocr_onnxruntime import RapidOCR
    except Exception:
        return ''
    engine = RapidOCR()
    parts = []
    for page in pymupdf.open(path):
        result, _ = engine(page.get_pixmap(dpi=130).tobytes('png'))
        parts.append(' '.join(line[1] for line in (result or [])))
    return ' '.join(parts)


def file_texts(path):
    """Candidate texts for a file (more than one reading for PDFs)."""
    low = path.lower()
    if low.endswith('.pdf'):
        texts = pdf_texts(path)
        if not any(len(t.strip()) >= 200 for t in texts):      # scanned: no text layer
            texts.append(ocr_text(path))
        return texts
    if low.endswith('.docx'):
        xml = zipfile.ZipFile(path).read('word/document.xml').decode('utf-8', 'replace')
        return [re.sub(r'<[^>]+>', ' ', xml.replace('</w:p>', '\n'))]
    soup = BeautifulSoup(open(path, 'rb').read(), 'lxml')
    for t in soup(['script', 'style', 'noscript', 'nav', 'header', 'footer']):
        t.decompose()
    return [soup.get_text('\n')]


def norm(s):
    s = unicodedata.normalize('NFKC', s)
    for bad, good in REPLACE:
        s = s.replace(bad, good)
    s = re.sub(r'(\w)-\s+(\w)', r'\1\2', s)          # re-join words hyphenated across lines
    return ' '.join(s.split())


def strip_linenums(s):
    return ' '.join(w for w in s.split() if not re.match(r'\d{1,2}$', w))


def texts_of(path):
    if path not in _cache:
        _cache[path] = [norm(t) for t in file_texts(path)]
    return _cache[path]


def quote_in(path, quote):
    """Returns 'exact', 'exact_ignoring_line_numbers', 'exact_ignoring_spaces', or '' (not found)."""
    q = norm(quote)
    for t in texts_of(path):
        if q in t:
            return 'exact'
    for t in texts_of(path):
        if strip_linenums(q) in strip_linenums(t):
            return 'exact_ignoring_line_numbers'
    for t in texts_of(path):
        if q.replace(' ', '') in t.replace(' ', ''):      # text extraction sometimes drops a space
            return 'exact_ignoring_spaces'
    return ''


def check_all():
    rows = list(csv.DictReader(open('data/tier1_board_ai_guidance.csv', encoding='utf-8', newline='')))
    found, missing, nocopy = 0, [], []
    for i, r in enumerate(rows, start=2):               # i = line number in the CSV
        path = os.path.join('data', r['raw_file']) if r['raw_file'] else ''
        if not path or not os.path.exists(path):
            nocopy.append((i, r['jurisdiction'], r['raw_file']))
            continue
        how = quote_in(path, r['quote'])
        if how:
            found += 1
        else:
            missing.append((i, r['jurisdiction'], r['raw_file']))
    print(f'{len(rows)} rows: {found} quotes found in the saved copy, {len(missing)} not found, '
          f'{len(nocopy)} with no saved copy')
    for i, j, f in missing:
        print(f'  NOT FOUND  line {i}  {j}  {f}')
    for i, j, f in nocopy:
        print(f'  no saved copy  line {i}  {j}  {f}')
    return 1 if missing else 0


if __name__ == '__main__':
    if len(sys.argv) == 3:
        print(quote_in(sys.argv[1], sys.argv[2]) or 'not found')
    else:
        sys.exit(check_all())
