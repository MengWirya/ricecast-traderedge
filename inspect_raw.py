import zipfile
import re
from pathlib import Path

fp = Path(r'c:/Users/mengw/OneDrive/Documents/Profesional Work/ricecast-traderedge/data/raw/Tabel Harga Berdasarkan Daerah.xlsx')
with zipfile.ZipFile(fp) as z:
    names = z.namelist()
    print('--- XL files ---')
    for n in names:
        if n.startswith('xl/'):
            print(n)
    print('--- sheets ---')
    txt = z.open('xl/workbook.xml').read().decode('utf-8', 'ignore')
    sheets = re.findall(r'<sheet[^>]*name="([^"]+)"', txt)
    print(sheets)
    if 'xl/sharedStrings.xml' in names:
        ss = z.open('xl/sharedStrings.xml').read().decode('utf-8', 'ignore')
        strings = re.findall(r'<t>([^<]+)</t>', ss)
        print('--- shared strings sample ---')
        print(strings[:40])
