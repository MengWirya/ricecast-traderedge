import zipfile
import re
from pathlib import Path

fp = Path(r'c:/Users/mengw/OneDrive/Documents/Profesional Work/ricecast-traderedge/data/raw/Tabel Harga Berdasarkan Daerah.xlsx')
with zipfile.ZipFile(fp) as z:
    ss = []
    if 'xl/sharedStrings.xml' in z.namelist():
        x = z.open('xl/sharedStrings.xml').read().decode('utf-8', 'ignore')
        ss = re.findall(r'<t>([^<]+)</t>', x)
    sheet = z.open('xl/worksheets/sheet1.xml').read().decode('utf-8', 'ignore')
    cells = re.findall(r'<c [^>]*r="([A-Z]+[0-9]+)"[^>]*>(.*?)</c>', sheet, re.S)
    cellmap = {}
    for ref, content in cells:
        text = ''
        if 't="s"' in content:
            idx = re.search(r'<v>(\d+)</v>', content)
            if idx:
                text = ss[int(idx.group(1))]
        else:
            v = re.search(r'<v>([^<]+)</v>', content)
            if v:
                text = v.group(1)
        cellmap[ref] = text
    rows = {}
    for cell, value in cellmap.items():
        col = re.sub('[0-9]', '', cell)
        row = int(re.sub('[A-Z]', '', cell))
        rows.setdefault(row, {})[col] = value
    for row in range(1, 15):
        rowvals = [rows.get(row, {}).get(col, '') for col in ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O']]
        print(row, rowvals)
