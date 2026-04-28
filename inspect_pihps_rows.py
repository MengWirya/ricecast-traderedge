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
    cells = re.findall(r'<c ([^>]+)>(.*?)</c>', sheet, re.S)

    def get_attr(text, name):
        m = re.search(rf'{name}="([^"]+)"', text)
        return m.group(1) if m else None

    rows = {}
    for attrs, content in cells:
        ref = get_attr(attrs, 'r')
        t = get_attr(attrs, 't')
        v = None
        if t == 's':
            m = re.search(r'<v>(\d+)</v>', content)
            if m:
                v = ss[int(m.group(1))]
        else:
            m = re.search(r'<v>([^<]+)</v>', content)
            if m:
                v = m.group(1)
        if ref:
            col = ''.join([c for c in ref if c.isalpha()])
            row = int(''.join([c for c in ref if c.isdigit()]))
            rows.setdefault(row, {})[col] = v or ''

    cols = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P']
    for row in range(1, 45):
        if row in rows:
            print(row, [rows[row].get(c, '') for c in cols])
