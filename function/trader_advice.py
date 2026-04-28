"""
trader_advice.py

Rule-based NLG engine for RiceCast TraderEdge.
Generates Bahasa Indonesia advice for pasar induk UMKM traders.
"""

from typing import Dict

ADVICE_TEMPLATES = {
    ('GLUT', 'HIGH'): (
        "⚠️ SINYAL SURPLUS TINGGI\n\n"
        "Perkiraan harga turun {price_change_pct:.1f}% dalam 30 hari ke depan. "
        "Pasokan beras diperkirakan melebihi permintaan normal.\n\n"
        "Rekomendasi untuk pedagang pasar induk:\n"
        "• Tunda pembelian stok besar. Tunggu harga menyentuh level terendah dulu.\n"
        "• Negosiasi harga beli dari pemasok sekarang — mereka juga ingin jual.\n"
        "• Prioritaskan menjual sisa stok lama sebelum harga turun lebih jauh.\n"
        "• Faktor utama: {top_feature_text}"
    ),
    ('GLUT', 'MEDIUM'): (
        "⚡ Potensi Kelebihan Pasokan (Sedang)\n\n"
        "Ada indikasi tekanan harga turun. Perubahan harga diperkirakan "
        "{price_change_pct:.1f}% — masih dalam rentang normal tapi perlu diperhatikan.\n\n"
        "Rekomendasi:\n"
        "• Beli secukupnya — hindari overstock minggu ini.\n"
        "• Pantau harga pasar 2–3 hari ke depan sebelum beli besar.\n"
        "• Faktor utama: {top_feature_text}"
    ),
    ('SHORTAGE', 'HIGH'): (
        "🔴 SINYAL KEKURANGAN PASOKAN TINGGI\n\n"
        "Tekanan kenaikan harga terdeteksi. Perkiraan harga naik {price_change_pct:.1f}% "
        "dalam 30 hari ke depan. Pasokan beras diperkirakan lebih ketat dari normal.\n\n"
        "Rekomendasi untuk pedagang pasar induk:\n"
        "• Amankan stok dari pemasok sekarang, sebelum harga naik.\n"
        "• Pertimbangkan naikkan margin jual 3–5% secara bertahap.\n"
        "• Siapkan alternatif pemasok jika supplier utama kehabisan stok.\n"
        "• Faktor utama: {top_feature_text}"
    ),
    ('SHORTAGE', 'MEDIUM'): (
        "⚡ Potensi Kekurangan Pasokan (Sedang)\n\n"
        "Ada indikasi tekanan naik harga. Perubahan harga diperkirakan "
        "{price_change_pct:.1f}%.\n\n"
        "Rekomendasi:\n"
        "• Pertahankan stok normal atau sedikit di atas normal.\n"
        "• Siapkan kontak alternatif pemasok sebagai backup.\n"
        "• Faktor utama: {top_feature_text}"
    ),
    ('NEUTRAL', 'LOW'): (
        "✅ Pasar Stabil\n\n"
        "Tidak ada sinyal ekstrem terdeteksi. Harga diperkirakan bergerak "
        "{price_change_pct:+.1f}% — dalam batas normal musiman.\n\n"
        "Rekomendasi:\n"
        "• Lanjutkan operasi pembelian/penjualan seperti biasa.\n"
        "• Tidak ada tindakan khusus diperlukan saat ini."
    ),
    ('_DEFAULT', '_DEFAULT'): (
        "ℹ️ Sinyal Tidak Jelas\n\n"
        "Model tidak mendeteksi tekanan dominan yang kuat. "
        "Pantau kondisi pasar secara manual."
    ),
}

FEATURE_TEXT = {
    'price_momentum': 'momentum harga 3 bulan terakhir',
    'harvest_timing': 'siklus musim panen Jawa Timur',
    'production_signal': 'deviasi produksi padi dari rata-rata musiman',
    'rainfall_deficit': 'defisit curah hujan di sentra produksi',
}


def _confidence_qualifier(ci_width_pct: float) -> str:
    if ci_width_pct < 10:
        return 'Tingkat keyakinan: Cukup tinggi'
    elif ci_width_pct < 20:
        return 'Tingkat keyakinan: Sedang — gunakan sebagai panduan, bukan kepastian'
    return 'Tingkat keyakinan: Rendah — interval perkiraan lebar, pantau pasar langsung'


def generate_trader_advice(pressure_result: Dict) -> Dict:
    dominant = pressure_result['dominant_signal']
    intensity = pressure_result['intensity']
    pct = pressure_result['price_change_pct']
    ci = pressure_result['ci_width_pct']
    top_feat = pressure_result.get('top_driving_feature', 'price_momentum')
    top_feature_text = FEATURE_TEXT.get(top_feat, top_feat)
    key = (dominant, intensity)
    template = ADVICE_TEMPLATES.get(key, ADVICE_TEMPLATES[('_DEFAULT', '_DEFAULT')])
    try:
        full_advice = template.format(
            price_change_pct=pct,
            top_feature_text=top_feature_text,
        )
    except KeyError:
        full_advice = template
    full_advice += f"\n\n_{_confidence_qualifier(ci)}_"
    headlines = {
        ('GLUT', 'HIGH'): '🔻 Risiko Surplus Tinggi — Tunda pembelian',
        ('GLUT', 'MEDIUM'): '↘ Potensi Surplus — Pantau harga',
        ('SHORTAGE', 'HIGH'): '🔺 Risiko Kekurangan Tinggi — Amankan stok',
        ('SHORTAGE', 'MEDIUM'): '↗ Potensi Kekurangan — Siapkan backup',
        ('NEUTRAL', 'LOW'): '✅ Pasar Stabil',
    }
    headline = headlines.get(key, 'ℹ️ Sinyal Tidak Jelas')
    colors = {
        ('GLUT', 'HIGH'): '#EF9F27',
        ('GLUT', 'MEDIUM'): '#F59E0B',
        ('SHORTAGE', 'HIGH'): '#E24B4A',
        ('SHORTAGE', 'MEDIUM'): '#F97316',
        ('NEUTRAL', 'LOW'): '#1D9E75',
    }
    signal_color = colors.get(key, '#6B7280')
    if dominant == 'GLUT':
        gauge_value = -pressure_result['glut_score']
    elif dominant == 'SHORTAGE':
        gauge_value = pressure_result['shortage_score']
    else:
        gauge_value = 0.0
    return {
        'headline': headline,
        'full_advice': full_advice,
        'confidence': _confidence_qualifier(ci),
        'signal_color': signal_color,
        'gauge_value': gauge_value,
        'dominant_signal': dominant,
        'intensity': intensity,
    }
