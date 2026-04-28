# RiceCast TraderEdge

RiceCast TraderEdge adalah project prediksi **tekanan pasokan beras** untuk membantu pedagang mengambil keputusan stok (indikasi glut / shortage), bukan menampilkan prediksi harga absolut sebagai output utama.

## Struktur proyek saat ini

- `md/` → dokumen panduan proyek dan alur kerja.
- `function/` → backend Azure Function (API forecast + scoring).
- `dashboard/` → scaffold Streamlit dashboard.
- `notebooks/` → eksplorasi data, feature engineering, training, dan backtest.
- `data/` → data mentah/olahan/sampel (file data besar tidak dikomit).
- `models/` → metadata model dan artefak model.
- `tests/` → unit test untuk modul scoring dan trader advice.

## Langkah berikutnya

1. Rapikan komponen dashboard (`dashboard/components/`).
2. Sambungkan `dashboard/app.py` ke endpoint Azure Function.
3. Lengkapi pipeline data + training sesuai dokumen di folder `md/`.

## Referensi utama

Mulai dari `md/00_PROJECT_CONTEXT.md` lalu lanjutkan ke file modul lain di folder `md/`.
