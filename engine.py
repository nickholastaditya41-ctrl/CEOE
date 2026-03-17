import pulp as lp

# ============================================
# DATA DEFAULT
# ============================================
NAMA_ALAT = {
    1: "EXC1 Doosan DX300LCA",
    2: "EXC2 Komatsu PC200",
    3: "DT1 HINO FM 280 JD",
    4: "DT2 Hino 130 HD",
    5: "BD1 Komatsu D85E",
    6: "BD2 Komatsu D65P",
    7: "VR1 XCMG XS113E",
    8: "VR2 Sakai SV512",
}

TIPE_ALAT = {
    1: "excavator", 2: "excavator",
    3: "dumptruck", 4: "dumptruck",
    5: "bulldozer", 6: "bulldozer",
    7: "roller",    8: "roller",
}

ALAT = list(range(1, 9))

MB_INTERVALS = [
    (1.00, 1.00),
    (0.95, 1.05),
    (0.90, 1.10),
    (0.85, 1.15),
    (0.80, 1.20),
    (0.75, 1.25),
    (0.70, 1.30),
]

# ============================================
# CORE FUNCTIONS
# ============================================
def hitung_mb_aktual(solution, produkt):
    """
    Mb = Produktivitas Excavator / Produktivitas Dumptruck
    Referensi: Douglas (1964) via Burt & Caccetta (2007)
    """
    prod_exc = (produkt[1] * solution[1] +
                produkt[2] * solution[2])
    prod_dtr = (produkt[3] * solution[3] +
                produkt[4] * solution[4])
    if prod_dtr == 0:
        return None
    return prod_exc / prod_dtr


def solve_ceoe(biaya, produkt, co2_per_jam,
               max_unit, volume_bank, volume_loose,
               volume_compact, waktu_max, T,
               mb_lo, mb_hi, skema):
    """
    Solve ILP untuk satu interval Mb.
    Objective: minimize total biaya operasional harian.
    """
    model = lp.LpProblem(
        f"CEOE_{skema}_Mb{mb_lo}", lp.LpMinimize)

    x = {i: lp.LpVariable(f"x_{i}", lowBound=0, cat="Integer")
         for i in ALAT}

    # Objective — minimize cost
    model += lp.lpSum(biaya[i] * x[i] for i in ALAT)

    # Productivity constraints
    model += (produkt[1]*x[1] + produkt[2]*x[2]
              >= volume_bank / waktu_max)
    model += (produkt[3]*x[3] + produkt[4]*x[4]
              >= volume_loose / waktu_max)
    model += (produkt[5]*x[5] + produkt[6]*x[6]
              >= volume_compact / waktu_max)
    model += (produkt[7]*x[7] + produkt[8]*x[8]
              >= volume_compact / waktu_max)

    # Match Balance — Excavator vs Dump Truck
    exc = produkt[1]*x[1] + produkt[2]*x[2]
    dtr = produkt[3]*x[3] + produkt[4]*x[4]
    model += exc >= mb_lo * dtr
    model += exc <= mb_hi * dtr

    # Bulldozer support constraint
    model += (produkt[5]*x[5] + produkt[6]*x[6]
              >= 0.25 * dtr)

    # Availability constraints
    for i in ALAT:
        model += x[i] <= max_unit[i]

    # Single type — lock alat alternatif = 0
    if skema == "single":
        for i in [2, 4, 6, 8]:
            model += x[i] == 0

    status = model.solve(lp.PULP_CBC_CMD(msg=0))

    if lp.LpStatus[status] != "Optimal":
        return None

    sol = {i: int(x[i].value()) for i in ALAT}
    cost_per_hari = sum(biaya[i] * sol[i] for i in ALAT) * T
    co2_per_hari  = sum(co2_per_jam[i] * sol[i] * T for i in ALAT)

    return {
        "mb_lo": mb_lo,
        "mb_hi": mb_hi,
        "solution": sol,
        "cost_per_hari": cost_per_hari,
        "co2_per_hari": co2_per_hari,
        "mb_aktual": hitung_mb_aktual(sol, produkt),
    }


def run_iterasi(biaya, produkt, co2_per_jam,
                max_unit, volume_bank, volume_loose,
                volume_compact, waktu_max, T, skema):
    """
    Jalankan ILP untuk semua interval Mb secara iteratif.
    """
    results = []
    for mb_lo, mb_hi in MB_INTERVALS:
        r = solve_ceoe(
            biaya, produkt, co2_per_jam, max_unit,
            volume_bank, volume_loose, volume_compact,
            waktu_max, T, mb_lo, mb_hi, skema)
        results.append({
            "mb_lo": mb_lo,
            "mb_hi": mb_hi,
            "result": r
        })
    return results


def pilih_rekomendasi(results, skema):
    """
    Pilih konfigurasi rekomendasi berdasarkan:
    - Mb aktual paling mendekati 1.0 (Douglas 1964)
    - Untuk multitipe: pastikan beneran kombinasi 2+ tipe
    
    Kriteria ini memastikan solusi tidak hanya optimal
    secara matematis, tetapi juga realistis di lapangan.
    """
    feasible = [r["result"] for r in results
                if r["result"] is not None]

    if not feasible:
        return None

    if skema == "single":
        return min(feasible,
                   key=lambda r: abs(r["mb_aktual"] - 1.0))
    else:
        # Filter yang beneran multitipe
        # (minimal 2 tipe excavator berbeda dipakai)
        candidates = [
            r for r in feasible
            if sum(1 for i in [1, 2]
                   if r["solution"][i] > 0) > 1
        ]
        if not candidates:
            candidates = feasible

        return min(candidates,
                   key=lambda r: abs(r["mb_aktual"] - 1.0))