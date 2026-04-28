import json
from pathlib import Path
path = Path(r'c:/Users/mengw/OneDrive/Documents/Profesional Work/ricecast-traderedge/notebooks/01_eda.ipynb')
nb = json.loads(path.read_text(encoding='utf-8'))
print('cells:', len(nb.get('cells', [])))
for i, cell in enumerate(nb.get('cells', [])):
    print(i, cell.get('cell_type'), len(cell.get('source', [])), cell.get('source')[:5])
