def build_explanation(dominant_signal: str, features: dict) -> list:
    """
    Builds 2–3 plain Indonesian bullet reasons tied to real feature values.
    This replaces the generic "pola historis" fallback.
    """
    reasons = []
 
    prod  = features.get("production_dev_pct", 0) or 0
    rain  = features.get("rainfall_dev_pct", 0)   or 0
    harv  = features.get("harvest_window", 0)      or 0
    lean  = features.get("lean_season", 0)         or 0
    mom   = features.get("price_mom_3m", 0)        or 0
 
    # Production signal
    if prod > 0.12:
        reasons.append(f"Produksi padi naik {prod*100:.0f}% di atas rata-rata musiman")
    elif prod < -0.12:
        reasons.append(f"Produksi padi turun {abs(prod)*100:.0f}% di bawah normal")
 
    # Harvest calendar
    if harv:
        reasons.append("Sedang musim panen — pasokan gabah meningkat di pasar")
    elif lean:
        reasons.append("Memasuki musim paceklik — pasokan biasanya berkurang")
 
    # Rainfall
    if rain < -0.20:
        reasons.append(f"Curah hujan turun {abs(rain)*100:.0f}% dari normal — berisiko ganggu panen")
    elif rain > 0.20:
        reasons.append(f"Curah hujan tinggi {rain*100:.0f}% di atas normal — kondisi tanam baik")
 
    # Price momentum
    if mom < -0.04:
        reasons.append("Harga sudah turun konsisten 3 bulan terakhir")
    elif mom > 0.04:
        reasons.append("Harga naik konsisten 3 bulan terakhir")
 
    # Fallback only when nothing fires
    if not reasons:
        reasons.append("Pola musiman normal — tidak ada sinyal ekstrem terdeteksi")
 
    return reasons[:3]   # max 3 bullets on screen
 
 
# ── Advice templates (still used for legacy action_text field) ────────────────
 
ADVICE_TEMPLATES = {
    ("GLUT",     "HIGH"):   (
        "Sinyal surplus tinggi. "
        "→ Tunda pembelian stok besar. "
        "→ Prioritaskan jual sisa stok lama. "
        "→ Negosiasi harga supplier lebih rendah sekarang."
    ),
    ("GLUT",     "MEDIUM"): (
        "Pasokan mulai berlebih. "
        "→ Beli secukupnya saja minggu ini. "
        "→ Pantau harga pasar 2–3 hari sebelum pembelian besar."
    ),
    ("GLUT",     "LOW"):    (
        "Sinyal surplus lemah. "
        "→ Lanjutkan operasi normal, stok standar sudah cukup."
    ),
    ("SHORTAGE", "HIGH"):   (
        "Sinyal kekurangan pasokan tinggi. "
        "→ Amankan stok dari supplier sekarang. "
        "→ Pertimbangkan naikkan margin jual 3–5% bertahap. "
        "→ Siapkan 2–3 supplier alternatif sebagai cadangan."
    ),
    ("SHORTAGE", "MEDIUM"): (
        "Risiko pasokan menipis sedang. "
        "→ Tambah stok di atas level normal minggu ini. "
        "→ Siapkan supplier cadangan jika harga naik lebih dari 10%."
    ),
    ("SHORTAGE", "LOW"):    (
        "Sinyal kekurangan lemah. "
        "→ Stok normal sudah cukup. Waspadai perkembangan harga."
    ),
    ("NEUTRAL",  "LOW"):    (
        "Pasar stabil. Tidak ada sinyal ekstrem saat ini. "
        "→ Lanjutkan operasi pembelian dan penjualan normal."
    ),
}
 
REASON_FALLBACKS = {
    "GLUT":     "musim panen atau produksi di atas normal",
    "SHORTAGE": "musim paceklik atau produksi di bawah normal",
    "NEUTRAL":  "pola musiman Jawa Timur",
}
 
 
def get_trader_advice(dominant: str, intensity: str, features: dict = {}) -> dict:
    key         = (dominant, intensity)
    action_text = ADVICE_TEMPLATES.get(key, ADVICE_TEMPLATES[("NEUTRAL", "LOW")])
    reason      = REASON_FALLBACKS.get(dominant, "pola musiman")
    horizon     = {"HIGH": 14, "MEDIUM": 21, "LOW": 30}.get(intensity, 21)
    return {"action_text": action_text, "reason": reason, "horizon_days": horizon}