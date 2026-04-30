# RiceCast TraderEdge

Machine Learning Decision Support untuk Stabilitas Pasokan & Harga Beras
**Important: Projects currently around 80% done. Bug fixing still needed (Not fatal) and also user improvement is really needed**
**If you're interested, Help me by contributing this repo! Every help will be remembered!**

---

![Status](https://img.shields.io/badge/status-in%20development-yellow)
![Tech](https://img.shields.io/badge/tech-ML%20%7C%20Streamlit%20%7C%20Python-blue)

---

## Ringkasan Eksekutif

Ketahanan pangan di Indonesia sangat dipengaruhi oleh stabilitas harga dan distribusi beras. Namun, pelaku utama di lapangan seperti pedagang pasar induk sering kali mengambil keputusan tanpa dukungan data yang memadai, terutama dalam menghadapi fluktuasi produksi, cuaca, dan pola musiman.

Data BPS menunjukkan bahwa produksi padi bersifat musiman, sementara BMKG menunjukkan variabilitas curah hujan yang tinggi. Ketidakseimbangan ini sering menyebabkan kondisi **surplus atau kekurangan pasokan**, yang berdampak langsung pada harga di pasar.

**Problem Statement:**
Bagaimana membantu pedagang beras mengambil keputusan pembelian dan penjualan secara tepat berdasarkan kondisi pasokan yang dinamis?

**Research Questions:**

* Bagaimana produksi dan cuaca mempengaruhi harga beras?
* Bisakah kita mendeteksi surplus/kekurangan lebih awal?
* Bagaimana mengubah data kompleks menjadi keputusan sederhana?

**Solusi:**
RiceCast TraderEdge menggunakan pendekatan **Machine Learning berbasis time-series dan feature engineering** untuk mendeteksi **Supply Pressure** dan menerjemahkannya menjadi sinyal sederhana:

> **BELI — TAHAN — JUAL**

---

## Deskripsi Proyek

**RiceCast TraderEdge** adalah platform berbasis Machine Learning yang membantu pedagang beras memahami arah pasar dalam 7–30 hari ke depan.

Alih-alih memprediksi harga secara absolut, sistem ini:

* Mendeteksi kondisi **surplus / shortage**
* Memberikan **rekomendasi tindakan langsung**
* Menjelaskan **alasan berbasis data**

🎯 Fokus utama: **membantu pengambilan keputusan, bukan sekadar analisis**

---

## Fitur Utama & Teknologi

### Fitur Utama

* 📊 **Sinyal Keputusan Langsung**

  * Output: BELI / TAHAN / JUAL

* ⚖️ **Supply Pressure Detection**

  * Klasifikasi kondisi pasar:

    * Surplus
    * Netral
    * Shortage

* 🔍 **Explainable Insight**

  * Contoh:

    * Produksi naik +15%
    * Musim panen aktif
    * Curah hujan stabil

* 📈 **Visualisasi Harga (Pendukung)**

  * Tren historis
  * Proyeksi jangka pendek

---

### Teknologi yang Digunakan

* **Python (Pandas, NumPy)**
* **Prophet (Time-Series Forecasting)**
* **Streamlit (Web App)**
* **Dataset:**

  * WFP
  * BPS
  * BMKG
  * PIHPS

* Azure Functions
* Azure Machine Learning

---

## Cara Penggunaan Website

1. Buka dashboard TraderEdge
2. Atur horizon prediksi (bulan)
3. Klik **Perbarui Sinyal**
4. Perhatikan output utama:

   * Status pasar
   * Rekomendasi tindakan
5. Gunakan untuk:

   * Menentukan waktu pembelian
   * Menjual stok lama
   * Negosiasi harga

---

## Preview Produk

📸 Screenshot

> *Coming soon*

🎥 Demo Video

> *Coming soon*

---

## Studi Kasus Pengguna

**Skenario: Pedagang Pasar Induk Malang**

| Kondisi      | Tanpa Sistem | Dengan TraderEdge        |
| ------------ | ------------ | ------------------------ |
| Saat surplus | Tetap beli   | Menunda pembelian        |
| Harga turun  | Rugi stok    | Sudah menjual lebih awal |
| Keputusan    | Intuisi      | Berbasis data            |

---

## Roadmap

* [ ] Memperbaiki deploy

---

## Tim & Kontributor

👥 Tim Pengembang

* [Mengwirya - Wiryateja Pamungkas](https://github.com/mengwirya)
* [Mavenhay - Maven Helios Agathon Yesstian](https://github.com/mavenhay)
* [Saktizaman-wq - Sakti Mahayana Zaman](https://github.com/saktizaman-wq)

---

### 🔗 Kontributor Repository

[![Contributors](https://contrib.rocks/image?repo=USERNAME/REPO_NAME)](https://github.com/USERNAME/REPO_NAME/graphs/contributors)

---

## Dokumentasi & Link

* 📂 GitHub Repo: *[(On Progress)](https://github.com/MengWirya/ricecast-traderedge)*
* 🌐 Live Demo: *[(On Progress)](https://ricecast-dashboard-bhh9dvgnfqfmazfp.southeastasia-01.azurewebsites.net/)*
* 🎥 Video Demo: *(On Progress)*

---

## Penutup

RiceCast TraderEdge dirancang sebagai **alat bantu keputusan nyata**, bukan sekadar eksperimen Machine Learning.

Dengan mengubah data kompleks menjadi sinyal sederhana, sistem ini membantu pelaku distribusi beras:

> Mengurangi risiko, meningkatkan timing, dan mengambil keputusan lebih percaya diri.
