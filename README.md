# RiceCast TraderEdge

AI-powered **decision support tool** for rice traders at pasar induk.

---

## What this project does

RiceCast TraderEdge helps rice traders answer one simple question:

> **Should I buy, hold, or sell rice stock right now?**

Instead of predicting exact prices, this system analyzes:

* market prices
* production levels
* rainfall patterns
* seasonal harvest cycles

and outputs a **Supply Signal** that indicates whether the market is likely entering:

* **Surplus (prices likely to go down)**
* **Shortage (prices likely to go up)**
* **Neutral**

---

## Why this matters

Rice traders operate with thin margins and high uncertainty.

A wrong decision can lead to:

* overstock during price drops
* missed profit during shortages

This tool provides **early signals (7–30 days ahead)** to support better decisions.

---

## Key Features

### 1. Decision-First Signal

Clear, actionable output:

* BUY / HOLD / SELL guidance
* No technical interpretation required

---

### 2. Supply Pressure Detection

Detects imbalance using:

* production deviation (BPS)
* rainfall anomaly (BMKG)
* historical price patterns (WFP / PIHPS)

---

### 3. Explainable AI

Every signal includes reasons, for example:

* “Produksi naik +15% dari normal”
* “Sedang musim panen”
* “Curah hujan stabil”

---

### 4. Price Context (Supporting Only)

* Historical price trends
* Short-term projection (NOT the main output)

---

## Example Output

> 🔴 **SURPLUS — TINGGI**
> Harga kemungkinan turun dalam 2–3 minggu ke depan

**Rekomendasi:**

* Tunda pembelian stok besar
* Negosiasi harga supplier
* Jual stok lama sebelum harga turun

---

## Data Sources

* WFP Food Prices (Indonesia)
* BPS (Produksi Padi Bulanan)
* BMKG (Curah Hujan)
* PIHPS (Harga Pasar Lokal)

> ⚠️ All data used is publicly available and non-copyright restricted.

---

## Project Structure

```
data/
  raw/
  processed/

notebooks/
  01_data_cleaning.ipynb
  02_feature_engineering.ipynb
  03_modeling.ipynb
  04_insight_analysis.ipynb

app/
  streamlit_app.py

models/
  (to be added)

outputs/
  signals/
```

---

## Methodology (Simplified)

1. Collect multi-source data (price, production, weather)
2. Convert to monthly time series
3. Create features:

   * seasonal indicators
   * deviation metrics
4. Generate **Supply Pressure Score**
5. Translate score → actionable signal

---

## Model

🚧 *Currently in development*

Current approach:

* Time series modeling (Prophet)
* Feature-based signal generation

Planned improvements:

* Better supply-demand modeling
* More robust signal classification
* Improved uncertainty estimation

---

## Limitations

* Signal is **indicative**, not a guaranteed prediction
* Data availability may affect accuracy
* Model currently relies on historical patterns

---

## Demo

📸 Screenshot: *(add later)*
🎥 Video demo: *(add later)*

---

## How to Run

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

---

## Roadmap

### Short Term

* Improve signal clarity (BUY / HOLD / SELL)
* Enhance explanation layer
* Clean UI for real users

### Mid Term

* Add real-time data updates
* Improve model robustness
* Backtesting & evaluation

### Long Term

* Mobile-friendly interface
* Integration with market data APIs
* Personalized trader recommendations

---

## Target Users

* Pedagang beras (pasar induk)
* Distributor beras
* Small-scale supply chain decision makers

---

## Competition Context

Built for:
**Datathon AI Challenge (Microsoft Elevate Training Center)**

Requirements fulfilled:

* AI-based solution
* Uses public datasets
* Deployable digital product
* Ready for Azure integration

---

## Future Azure Integration

Planned:

* Azure Functions → signal generation API
* Azure Storage → dataset pipeline
* Azure ML → model training & deployment

---

## Contributors

* *Hello*

---

## License

*(To be decided)*

---

## Final Note

This is not a price prediction tool.

This is a **decision support system** designed to reduce uncertainty and improve timing in rice trading.

> Simple signal. Real impact.