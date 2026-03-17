"""
sensitivity.py
Modul sensitivity analysis untuk CEOE — re-run solver per titik variasi.

Insight yang dihasilkan (6 total, semuanya kuantitatif):

Sensitivity MB:
  1. Trade-off     — best_mb vs best_cost, selisih Rp konkret
  2. Elastisitas   — rata-rata Δcost per Δspread 0.05
  3. Sweet spot    — normalized weighted score (0.6 biaya + 0.4 Mb)

Sensitivity Durasi:
  4. Risiko molor  — total cost tambahan kalau +10 hari (apple to apple)
  5. Titik transisi— durasi berapa unit alat berubah + naik berapa Rp/hari
  6. Break-even    — total_cost_aktual vs total_cost_cepat (apple to apple)
"""

from engine import solve_ceoe, run_iterasi, pilih_rekomendasi


# ============================================
# SENSITIVITY: MATCH BALANCE
# ============================================

def sensitivity_mb(biaya, produkt, co2_per_jam, max_unit,
                   volume_bank, volume_loose, volume_compact,
                   waktu_max, T, skema,
                   spreads=None):
    """
    Re-run solver untuk setiap spread interval MB.
    spread = setengah lebar interval di kiri dan kanan center 1.0
    Contoh: spread=0.10 → interval (0.90, 1.10)
    """
    if spreads is None:
        spreads = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]

    results = []
    for spread in spreads:
        mb_lo = round(1.0 - spread, 2)
        mb_hi = round(1.0 + spread, 2)

        r = solve_ceoe(
            biaya, produkt, co2_per_jam, max_unit,
            volume_bank, volume_loose, volume_compact,
            waktu_max, T, mb_lo, mb_hi, skema
        )

        if r:
            unit_exc   = r["solution"][1] + r["solution"][2]
            unit_dt    = r["solution"][3] + r["solution"][4]
            unit_bd    = r["solution"][5] + r["solution"][6]
            unit_vr    = r["solution"][7] + r["solution"][8]
            unit_total = unit_exc + unit_dt + unit_bd + unit_vr

            results.append({
                "spread":        spread,
                "mb_lo":         mb_lo,
                "mb_hi":         mb_hi,
                "label":         f"{mb_lo:.2f}–{mb_hi:.2f}",
                "cost_per_hari": r["cost_per_hari"],
                "co2_per_hari":  r["co2_per_hari"],
                "mb_aktual":     r["mb_aktual"],
                "unit_exc":      unit_exc,
                "unit_dt":       unit_dt,
                "unit_bd":       unit_bd,
                "unit_vr":       unit_vr,
                "unit_total":    unit_total,
                "solution":      r["solution"],
                "score":         None,
                "feasible":      True,
            })
        else:
            results.append({
                "spread":        spread,
                "mb_lo":         mb_lo,
                "mb_hi":         mb_hi,
                "label":         f"{mb_lo:.2f}–{mb_hi:.2f}",
                "cost_per_hari": None,
                "co2_per_hari":  None,
                "mb_aktual":     None,
                "unit_exc":      None,
                "unit_dt":       None,
                "unit_bd":       None,
                "unit_vr":       None,
                "unit_total":    None,
                "solution":      None,
                "score":         None,
                "feasible":      False,
            })

    return results


def _hitung_sweetspot(feasible):
    """
    Tambahkan normalized score ke setiap titik feasible.
    score = 0.6 * score_cost + 0.4 * score_mb

    Bobot 60/40 dipertahankan karena:
    - objective ILP adalah minimize cost → cost lebih prioritas
    - MB adalah constraint bukan objective → bobotnya lebih kecil
    """
    if len(feasible) < 2:
        if feasible:
            feasible[0]["score"] = 1.0
        return feasible

    costs      = [r["cost_per_hari"] for r in feasible]
    max_cost   = max(costs)
    min_cost   = min(costs)
    cost_range = max_cost - min_cost

    for r in feasible:
        # makin murah → score_cost mendekati 1.0
        score_cost = (max_cost - r["cost_per_hari"]) / cost_range \
                     if cost_range > 0 else 1.0

        # makin dekat Mb=1.0 → score_mb mendekati 1.0
        score_mb = 1.0 - abs(r["mb_aktual"] - 1.0)

        r["score"] = round(0.6 * score_cost + 0.4 * score_mb, 4)

    return feasible


def generate_insight_mb(results, existing_cost, skema_label):
    """
    Return: list of insight dict
    [{"text": str, "severity": "success"|"warning"|"info", "type": str}]
    """
    feasible = [r for r in results if r["feasible"]]
    if not feasible:
        return [{
            "text":     "Tidak ditemukan solusi feasible pada range MB yang diuji.",
            "severity": "warning",
            "type":     "no_feasible",
        }]

    feasible   = _hitung_sweetspot(feasible)
    best_cost  = min(feasible, key=lambda r: r["cost_per_hari"])
    best_mb    = min(feasible, key=lambda r: abs(r["mb_aktual"] - 1.0))
    sweet_spot = max(feasible, key=lambda r: r["score"])
    insights   = []

    # ── 1. Trade-off ─────────────────────────────────────────────────────
    if best_cost["label"] != best_mb["label"]:
        selisih_rp  = abs(best_mb["cost_per_hari"] - best_cost["cost_per_hari"])
        selisih_pct = selisih_rp / best_cost["cost_per_hari"] * 100
        insights.append({
            "text": (
                f"Trade-off terdeteksi: interval paling seimbang "
                f"({best_mb['label']}, Mb={best_mb['mb_aktual']:.4f}) "
                f"lebih mahal Rp {selisih_rp:,.0f}/hari ({selisih_pct:.2f}%) "
                f"dibanding interval termurah ({best_cost['label']})."
            ),
            "severity": "warning",
            "type":     "trade_off",
        })
    else:
        saving_pct = (existing_cost - best_cost["cost_per_hari"]) / existing_cost * 100
        insights.append({
            "text": (
                f"Tidak ada trade-off: interval {best_cost['label']} "
                f"sekaligus termurah (hemat {saving_pct:.2f}%) dan "
                f"paling seimbang (Mb={best_mb['mb_aktual']:.4f})."
            ),
            "severity": "success",
            "type":     "trade_off",
        })

    # ── 2. Elastisitas ────────────────────────────────────────────────────
    deltas = []
    for i in range(1, len(feasible)):
        prev     = feasible[i - 1]
        curr     = feasible[i]
        d_spread = curr["spread"] - prev["spread"]
        d_cost   = prev["cost_per_hari"] - curr["cost_per_hari"]  # positif = turun
        if d_spread > 0:
            deltas.append(d_cost / d_spread * 0.05)

    if deltas:
        avg_delta     = sum(deltas) / len(deltas)
        avg_delta_pct = abs(avg_delta) / existing_cost * 100
        arah          = "turun" if avg_delta >= 0 else "naik"
        insights.append({
            "text": (
                f"Elastisitas: setiap pelonggaran spread 0.05, "
                f"biaya rata-rata {arah} Rp {abs(avg_delta):,.0f}/hari "
                f"({avg_delta_pct:.2f}% dari eksisting)."
            ),
            "severity": "info",
            "type":     "elastisitas",
        })

    # ── 3. Sweet spot ─────────────────────────────────────────────────────
    saving_ss = (existing_cost - sweet_spot["cost_per_hari"]) / existing_cost * 100
    insights.append({
        "text": (
            f"Sweet spot: interval {sweet_spot['label']} "
            f"(score={sweet_spot['score']:.2f}) — "
            f"hemat {saving_ss:.2f}% dari eksisting, "
            f"Mb={sweet_spot['mb_aktual']:.4f}. "
            f"Paling balance antara efisiensi biaya (bobot 60%) "
            f"dan keseimbangan operasional (bobot 40%)."
        ),
        "severity": "success",
        "type":     "sweet_spot",
    })

    return insights


# ============================================
# SENSITIVITY: DURASI PROYEK
# ============================================

def sensitivity_durasi(biaya, produkt, co2_per_jam, max_unit,
                        volume_bank, volume_loose, volume_compact,
                        T, skema, total_days_base,
                        hari_range=None):
    """
    Re-run solver per variasi durasi.
    waktu_max = T × hari → constraint produktivitas minimum ikut berubah.
    """
    if hari_range is None:
        start = max(1, total_days_base - 30)
        end   = total_days_base + 31
        hari_range = list(range(start, end, 5))
        if total_days_base not in hari_range:
            hari_range.append(total_days_base)
            hari_range.sort()

    results = []
    for hari in hari_range:
        waktu_var = T * hari
        iterasi   = run_iterasi(
            biaya, produkt, co2_per_jam, max_unit,
            volume_bank, volume_loose, volume_compact,
            waktu_var, T, skema
        )
        rek = pilih_rekomendasi(iterasi, skema)

        if rek:
            unit_exc   = rek["solution"][1] + rek["solution"][2]
            unit_dt    = rek["solution"][3] + rek["solution"][4]
            unit_bd    = rek["solution"][5] + rek["solution"][6]
            unit_vr    = rek["solution"][7] + rek["solution"][8]
            unit_total = unit_exc + unit_dt + unit_bd + unit_vr

            results.append({
                "hari":          hari,
                "is_aktual":     hari == total_days_base,
                "cost_per_hari": rek["cost_per_hari"],
                "total_cost":    rek["cost_per_hari"] * hari,
                "co2_per_hari":  rek["co2_per_hari"],
                "mb_aktual":     rek["mb_aktual"],
                "unit_exc":      unit_exc,
                "unit_dt":       unit_dt,
                "unit_bd":       unit_bd,
                "unit_vr":       unit_vr,
                "unit_total":    unit_total,
                "feasible":      True,
            })
        else:
            results.append({
                "hari":      hari,
                "is_aktual": hari == total_days_base,
                "feasible":  False,
                **{k: None for k in [
                    "cost_per_hari", "total_cost", "co2_per_hari",
                    "mb_aktual", "unit_exc", "unit_dt",
                    "unit_bd", "unit_vr", "unit_total"
                ]}
            })

    return results


def generate_insight_durasi(results, existing_cost, total_days_base, skema_label):
    """
    Return: list of insight dict
    [{"text": str, "severity": "success"|"warning"|"info", "type": str}]
    """
    feasible = [r for r in results if r["feasible"]]
    if not feasible:
        return [{
            "text":     "Tidak ditemukan solusi feasible pada range durasi yang diuji.",
            "severity": "warning",
            "type":     "no_feasible",
        }]

    aktual   = next((r for r in feasible if r["is_aktual"]), None)
    insights = []

    # ── 1. Risiko molor — total cost apple to apple ───────────────────────
    if aktual:
        ref_molor = next(
            (r for r in feasible if r["hari"] == total_days_base + 10),
            next((r for r in feasible if r["hari"] == total_days_base + 5), None)
        )
        if ref_molor:
            delta_hari  = ref_molor["hari"] - total_days_base
            delta_total = ref_molor["total_cost"] - aktual["total_cost"]
            unit_berubah = ref_molor["unit_total"] != aktual["unit_total"]
            insights.append({
                "text": (
                    f"Risiko keterlambatan {delta_hari} hari: "
                    f"total biaya proyek bertambah Rp {delta_total:,.0f} "
                    f"(Rp {aktual['total_cost']:,.0f} → Rp {ref_molor['total_cost']:,.0f})."
                    + (" Konfigurasi alat tidak berubah." if not unit_berubah
                       else " Konfigurasi alat juga berubah pada durasi ini.")
                ),
                "severity": "warning",
                "type":     "risiko_molor",
            })

    # ── 2. Titik transisi konfigurasi ─────────────────────────────────────
    transitions = []
    for i in range(1, len(feasible)):
        prev = feasible[i - 1]
        curr = feasible[i]
        if curr["unit_total"] != prev["unit_total"]:
            naik_cost = curr["cost_per_hari"] - prev["cost_per_hari"]
            arah      = "naik" if naik_cost > 0 else "turun"
            transitions.append(
                f"{prev['hari']}→{curr['hari']} hari "
                f"({prev['unit_total']}→{curr['unit_total']} unit, "
                f"cost/hari {arah} Rp {abs(naik_cost):,.0f})"
            )

    if transitions:
        insights.append({
            "text": (
                f"Titik transisi konfigurasi di {len(transitions)} titik: "
                f"{'; '.join(transitions[:3])}. "
                f"Perubahan ini tidak terlihat pada analisis linear biasa."
            ),
            "severity": "info",
            "type":     "titik_transisi",
        })
    else:
        insights.append({
            "text": (
                f"Konfigurasi alat stabil di seluruh range durasi — "
                f"tidak ada perubahan jumlah unit."
            ),
            "severity": "info",
            "type":     "titik_transisi",
        })

    # ── 3. Break-even percepatan — total cost apple to apple ──────────────
    if aktual:
        lebih_cepat = [r for r in feasible if r["hari"] < total_days_base]
        if lebih_cepat:
            ref_cepat = next(
                (r for r in lebih_cepat if r["hari"] == total_days_base - 10),
                next((r for r in lebih_cepat if r["hari"] == total_days_base - 5), None)
            )
            if ref_cepat:
                delta_hari    = total_days_base - ref_cepat["hari"]
                delta_total   = aktual["total_cost"] - ref_cepat["total_cost"]
                naik_per_hari = ref_cepat["cost_per_hari"] - aktual["cost_per_hari"]
                worth_it      = delta_total > 0

                insights.append({
                    "text": (
                        f"Break-even percepatan {delta_hari} hari: "
                        f"cost/hari {'naik' if naik_per_hari > 0 else 'turun'} "
                        f"Rp {abs(naik_per_hari):,.0f}, "
                        f"total biaya proyek "
                        f"{'turun' if worth_it else 'naik'} "
                        f"Rp {abs(delta_total):,.0f} "
                        f"(Rp {aktual['total_cost']:,.0f} → "
                        f"Rp {ref_cepat['total_cost']:,.0f}). "
                        f"{'Percepatan worth it secara finansial.' if worth_it else 'Percepatan tidak menguntungkan secara finansial.'}"
                    ),
                    "severity": "success" if worth_it else "warning",
                    "type":     "break_even",
                })
        else:
            insights.append({
                "text": (
                    f"Tidak ada durasi lebih pendek yang feasible — "
                    f"analisis break-even tidak dapat dilakukan."
                ),
                "severity": "info",
                "type":     "break_even",
            })

    return insights
