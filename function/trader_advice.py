# =============================================================================
# function/trader_advice.py
# Rule-based NLG engine — Bahasa Indonesia trader advice templates.
# NO LLM dependency. Pure template lookup table.
# =============================================================================
 
ADVICE_TEMPLATES = {
    ("GLUT", "HIGH"): (
        "Sinyal SURPLUS TINGGI terdeteksi. Pasokan beras kemungkinan berlebih "
        "dalam 2–3 minggu ke depan. "
        "→ Tunda pembelian stok besar hingga harga turun. "
        "→ Negosiasi harga supplier lebih rendah sekarang sebelum harga pasar turun. "
        "→ Prioritaskan menjual sisa stok lama sebelum harga anjlok."
    ),
    ("GLUT", "MEDIUM"): (
        "Potensi kelebihan pasokan sedang terdeteksi. "
        "→ Beli stok secukupnya saja, hindari overstock minggu ini. "
        "→ Pantau harga Pasar Induk 2–3 hari ke depan sebelum pembelian besar."
    ),
    ("GLUT", "LOW"): (
        "Sinyal surplus lemah. Situasi relatif normal dengan sedikit "
        "kecenderungan kelebihan pasokan. "
        "→ Lanjutkan operasi normal, pertahankan stok standar."
    ),
    ("SHORTAGE", "HIGH"): (
        "Sinyal KEKURANGAN PASOKAN TINGGI terdeteksi. "
        "Risiko kenaikan harga signifikan dalam 2–3 minggu ke depan. "
        "→ Amankan stok dari pemasok sekarang sebelum harga naik. "
        "→ Pertimbangkan naikkan margin jual 3–5% secara bertahap. "
        "→ Siapkan 2–3 alternatif pemasok sebagai cadangan."
    ),
    ("SHORTAGE", "MEDIUM"): (
        "Risiko kekurangan pasokan sedang terdeteksi. "
        "→ Pertahankan stok di atas level normal minggu ini. "
        "→ Siapkan alternatif pemasok jika harga naik lebih dari 10%."
    ),
    ("SHORTAGE", "LOW"): (
        "Sinyal kekurangan lemah. Sedikit tekanan kenaikan harga mungkin terjadi. "
        "→ Stok normal sudah cukup. Waspadai perkembangan harga minggu ini."
    ),
    ("NEUTRAL", "LOW"): (
        "Pasar stabil. Tidak ada sinyal ekstrem yang terdeteksi saat ini. "
        "→ Lanjutkan operasi pembelian dan penjualan normal."
    ),
}
 
REASON_TEMPLATES = {
    "harvest_near":        "musim panen mendekati — potensi surplus gabah di pasar",
    "lean_season":         "memasuki musim paceklik — pasokan biasanya menurun",
    "prod_above_normal":   "produksi padi di atas rata-rata musiman (data BPS Jatim)",
    "prod_below_normal":   "produksi padi di bawah rata-rata musiman (data BPS Jatim)",
    "price_falling":       "harga menunjukkan tren turun dalam 3 bulan terakhir",
    "price_rising":        "harga menunjukkan tren naik dalam 3 bulan terakhir",
    "default":             "pola harga dan pasokan historis musiman Jawa Timur",
}
 
 
def get_trader_advice(
    dominant_signal: str,
    intensity: str,
    features: dict = {}
) -> dict:
    """
    Returns structured advice dict for the dashboard.
 
    Parameters:
        dominant_signal : "GLUT" | "SHORTAGE" | "NEUTRAL"
        intensity       : "HIGH" | "MEDIUM" | "LOW"
        features        : dict of latest feature values (for reason generation)
 
    Returns:
        {
            "action_text"  : str,
            "reason"       : str,
            "horizon_days" : int
        }
    """
    key = (dominant_signal, intensity)
    action_text = ADVICE_TEMPLATES.get(key, ADVICE_TEMPLATES[("NEUTRAL", "LOW")])
    reason      = _build_reason(dominant_signal, features or {})
 
    # Horizon: how many days ahead the signal is reliable
    horizon_days = {"HIGH": 14, "MEDIUM": 21, "LOW": 30}.get(intensity, 21)
 
    return {
        "action_text":  action_text,
        "reason":       reason,
        "horizon_days": horizon_days,
    }
 
 
def _build_reason(dominant_signal: str, features: dict) -> str:
    prod_dev = features.get("production_dev_pct", 0) or 0
    mom_3m   = features.get("price_mom_3m", 0) or 0
    harvest  = features.get("harvest_window", 0) or 0
    lean     = features.get("lean_season", 0) or 0
 
    if dominant_signal == "GLUT":
        if harvest:
            return REASON_TEMPLATES["harvest_near"]
        if prod_dev > 0.10:
            return REASON_TEMPLATES["prod_above_normal"]
        if mom_3m < -0.03:
            return REASON_TEMPLATES["price_falling"]
 
    elif dominant_signal == "SHORTAGE":
        if lean:
            return REASON_TEMPLATES["lean_season"]
        if prod_dev < -0.10:
            return REASON_TEMPLATES["prod_below_normal"]
        if mom_3m > 0.03:
            return REASON_TEMPLATES["price_rising"]
 
    return REASON_TEMPLATES["default"]
 