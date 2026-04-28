# Quick Reference — How to Use These Files with an AI Coding Assistant

## File order — always follow this sequence

```
00_PROJECT_CONTEXT.md   ← Feed this FIRST in every new chat session
01_DATA_PIPELINE.md     ← Build notebooks 01 and 02
02_MODEL.md             ← Build notebooks 03 and 04
03_FUNCTION.md          ← Build the Azure Function backend
04_DASHBOARD.md         ← Build the Streamlit dashboard
```

---

## Prompt templates

### Starting a new module

```
Here is the project context:
[paste 00_PROJECT_CONTEXT.md]

Now here is the module I want to build:
[paste the specific module MD]

Build all the files described. Ask me if anything is unclear about
the data or environment before writing code.
```

### Fixing a bug

```
Here is my project context:
[paste 00_PROJECT_CONTEXT.md]

I am on Module [X]. Here is the error I am getting:
[paste error + stack trace]

Here is the relevant code:
[paste the file with the bug]

Fix the bug without changing the architecture described in the context file.
```

### Asking for a specific file only

```
Context: [paste 00_PROJECT_CONTEXT.md]

From Module 03, write only the file `function/supply_pressure_scorer.py`.
Use exactly the function signatures described in the module file.
```

---

## Recommended AI tools for this project

| Task | Best tool | Why |
|---|---|---|
| Building code from these MD files | **Claude** (claude.ai) or **Claude Code** | Best at following multi-file architectural constraints |
| Debugging Prophet model errors | Claude or ChatGPT-4o | Both handle pandas/statsmodels well |
| Azure deployment issues | **GitHub Copilot** in VS Code | Azure extension + inline suggestions |
| Searching for dataset columns | **Perplexity** or this Claude chat | Web search needed |

---

## Common pitfalls — tell your AI to avoid these

1. **Do not use Azure ML managed endpoints** — pkl loaded directly in Azure Functions
2. **Do not use Azure OpenAI** — all text is rule-based templates
3. **Do not generate exact price predictions** in the dashboard — show ranges only
4. **Do not use annual BPS production data as a Prophet regressor** — use deviation from seasonal mean
5. **All user-facing text must be in Bahasa Indonesia**
6. **Do not add a farmer view** — single trader view only
7. **Do not hide confidence intervals** — always show CI bands in the chart

---

## Folder creation commands

```bash
mkdir -p ricecast-traderedge/{notebooks,function,dashboard/components,data/{raw,processed,sample},models,tests,scripts}

touch ricecast-traderedge/.gitignore
touch ricecast-traderedge/.env.example
touch ricecast-traderedge/README.md
touch ricecast-traderedge/requirements-dev.txt
```

## `.gitignore` content

```
# Never commit these
data/raw/
data/processed/
models/prophet_model.pkl
function/local.settings.json
.env
__pycache__/
*.pyc
.ipynb_checkpoints/
```

## `requirements-dev.txt`

```
jupyter==7.1.0
pytest==8.1.0
black==24.3.0
python-dotenv==1.0.0
prophet==1.1.5
pandas==2.2.0
numpy==1.26.4
matplotlib==3.8.0
plotly==5.20.0
scikit-learn==1.4.0
joblib==1.3.2
azure-storage-blob==12.19.0
streamlit==1.33.0
requests==2.31.0
```
