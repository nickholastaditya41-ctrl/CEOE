import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from engine import (
    NAMA_ALAT, TIPE_ALAT, ALAT,
    run_iterasi, pilih_rekomendasi
)
from sensitivity import (
    sensitivity_mb, sensitivity_durasi,
    generate_insight_mb, generate_insight_durasi,
)

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title="CEOE - Construction Equipment Optimization Engine",
    layout="wide"
)

# ============================================
# CUSTOM CSS
# ============================================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg,
        #0D1B2A 0%, #1B2E45 50%, #0D1B2A 100%);
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,
        #0A1628 0%, #162840 100%);
    border-right: 1px solid rgba(255,255,255,0.1);
}
[data-testid="stButton"] > button {
    background: linear-gradient(90deg, #1B3A6B, #2E5FA3);
    color: white;
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 8px;
    font-weight: 600;
    letter-spacing: 0.5px;
    transition: all 0.3s ease;
}
[data-testid="stButton"] > button:hover {
    background: linear-gradient(90deg, #2E5FA3, #1B3A6B);
    border: 1px solid rgba(255,255,255,0.4);
    transform: translateY(-1px);
}
[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
    background: linear-gradient(90deg, #1B3A6B, #2E5FA3) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
}
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px;
    padding: 1rem;
}
[data-testid="stMetricValue"] { color: #FFFFFF; font-weight: 700; }
[data-testid="stMetricDelta"] { color: #4CAF9A; }
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
}
h1 {
    background: linear-gradient(90deg, #FFFFFF, #A8C4E0);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
}
h2, h3 {
    color: #A8C4E0;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    padding-bottom: 0.3rem;
}
[data-testid="stCaptionContainer"] { color: rgba(255,255,255,0.5); }
[data-testid="stNumberInput"] input {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.15);
    color: white; border-radius: 6px;
}
[data-testid="stMultiSelect"] > div {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.15);
}
hr { border-color: rgba(255,255,255,0.1); }
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
}
[data-testid="stAlert"] {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.15);
}
.ceoe-footer {
    text-align: center; padding: 1.5rem;
    color: rgba(255,255,255,0.3); font-size: 12px;
    border-top: 1px solid rgba(255,255,255,0.1);
    margin-top: 2rem; letter-spacing: 0.3px;
}
</style>
""", unsafe_allow_html=True)

# ============================================
# PLOTLY THEME
# ============================================
PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(255,255,255,0.03)",
    font=dict(color="#A8C4E0", family="sans-serif"),
    title_font=dict(color="#FFFFFF", size=14),
    margin=dict(t=50, b=40, l=60, r=20),
)

AXIS_STYLE = dict(
    gridcolor="rgba(255,255,255,0.05)",
    linecolor="rgba(255,255,255,0.1)"
)

LEGEND_BOTTOM = dict(
    bgcolor="rgba(255,255,255,0.05)",
    bordercolor="rgba(255,255,255,0.1)",
    borderwidth=1,
    orientation="h",
    y=-0.25
)

LEGEND_DONUT = dict(
    bgcolor="rgba(255,255,255,0.05)",
    bordercolor="rgba(255,255,255,0.1)",
    borderwidth=1,
    orientation="h",
    y=-0.15
)

# ============================================
# HEADER
# ============================================
st.title("CONSTRUCTION EQUIPMENT OPTIMIZATION ENGINE")
st.caption(
    "Optimasi konfigurasi alat berat menggunakan "
    "Integer Linear Programming (ILP) — "
    "Nickholast Aditya Pratama, UGM 2025"
)

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    st.header("PARAMETER PROYEK")

    st.subheader("Volume Pekerjaan")
    volume_compact = st.number_input(
        "Volume Padat / Compact (m³)",
        value=128411.63, step=100.0, format="%.2f",
        key="sb_volume_compact")
    volume_bank = st.number_input(
        "Volume Asli / Bank (m³)",
        value=119422.82, step=100.0, format="%.2f",
        help="Volume Compact x 0.93",
        key="sb_volume_bank")
    volume_loose = st.number_input(
        "Volume Gembur / Loose (m³)",
        value=204174.50, step=100.0, format="%.2f",
        help="Volume Compact x 1.59",
        key="sb_volume_loose")

    st.subheader("Waktu dan Durasi")
    T = st.number_input(
        "Jam Kerja per Hari",
        value=8, min_value=1, max_value=24, step=1,
        key="sb_T")
    total_days = st.number_input(
        "Durasi Proyek (hari)",
        value=74, min_value=1, step=1,
        key="sb_total_days")

    waktu_max = int(T * total_days)
    st.info(
        f"Total waktu proyek: **{waktu_max} jam**  \n"
        f"{total_days} hari x {T} jam/hari"
    )

    st.subheader("Skema Optimasi")
    skema_pilihan = st.multiselect(
        "Pilih skema:",
        ["single", "multitipe"],
        default=["single", "multitipe"],
        key="sb_skema",
        format_func=lambda x: (
            "Tipe Tunggal" if x == "single" else "Multitipe"
        )
    )

# ============================================
# DATA ALAT BERAT
# ============================================
st.header("DATA ALAT BERAT")
st.caption("Edit data sesuai alat yang tersedia di proyek.")

default_data = {
    "ID": list(ALAT),
    "Nama Alat": [NAMA_ALAT[i] for i in ALAT],
    "Tipe": [TIPE_ALAT[i] for i in ALAT],
    "Biaya (Rp/jam)": [
        678569.75, 501209.75, 584812.00, 289156.00,
        399993.75, 370713.75, 438833.75, 435025.75,
    ],
    "Produktivitas (m3/jam)": [
        105.983, 84.748, 5.867, 2.070,
        134.637, 62.033, 124.600, 120.000,
    ],
    "CO2 (kg/jam)": [
        47.55, 38.32, 76.08, 52.76,
        57.06, 35.55, 38.04, 33.60,
    ],
    "Max Unit": [4, 4, 60, 19, 4, 6, 4, 3],
}

df_input = pd.DataFrame(default_data)
df_edited = st.data_editor(
    df_input, hide_index=True, use_container_width=True,
    column_config={
        "ID": st.column_config.NumberColumn(disabled=True),
        "Tipe": st.column_config.SelectboxColumn(
            options=["excavator", "dumptruck", "bulldozer", "roller"],
            disabled=True),
        "Biaya (Rp/jam)": st.column_config.NumberColumn(format="%.2f"),
        "Produktivitas (m3/jam)": st.column_config.NumberColumn(format="%.3f"),
        "CO2 (kg/jam)": st.column_config.NumberColumn(format="%.2f"),
    }
)

# ============================================
# KONDISI EKSISTING
# ============================================
st.header("KONDISI EKSISTING")
col1, col2 = st.columns(2)
with col1:
    existing_cost = st.number_input(
        "Biaya Operasional per Hari (Rp)",
        value=329_266_472, step=1_000_000,
        key="main_existing_cost")
with col2:
    existing_co2 = st.number_input(
        "Emisi Karbon per Hari (kgCO2)",
        value=41083.20, step=100.0, format="%.2f",
        key="main_existing_co2")

# ============================================
# TOMBOL OPTIMASI
# ============================================
st.markdown("<br>", unsafe_allow_html=True)
run = st.button(
    "Jalankan Optimasi",
    type="primary",
    use_container_width=True)

# ============================================
# HASIL OPTIMASI
# ============================================
if run:
    if not skema_pilihan:
        st.warning("Pilih minimal satu skema optimasi.")
        st.stop()

    biaya       = dict(zip(ALAT, df_edited["Biaya (Rp/jam)"].tolist()))
    produkt     = dict(zip(ALAT, df_edited["Produktivitas (m3/jam)"].tolist()))
    co2_per_jam = dict(zip(ALAT, df_edited["CO2 (kg/jam)"].tolist()))
    max_unit    = dict(zip(ALAT, df_edited["Max Unit"].tolist()))

    # Simpan semua ke session_state agar bisa diakses setelah rerun
    st.session_state["biaya"]       = biaya
    st.session_state["produkt"]     = produkt
    st.session_state["co2_per_jam"] = co2_per_jam
    st.session_state["max_unit"]    = max_unit
    st.session_state["run_params"]  = {
        "volume_bank":    volume_bank,
        "volume_loose":   volume_loose,
        "volume_compact": volume_compact,
        "waktu_max":      waktu_max,
        "T":              T,
        "total_days":     total_days,
        "existing_cost":  existing_cost,
        "existing_co2":   existing_co2,
        "skema_pilihan":  skema_pilihan,
    }
    # Reset hasil sensitivity saat optimasi diulang
    st.session_state.pop("sa_mb", None)
    st.session_state.pop("sa_dur", None)

    st.header("HASIL OPTIMASI")

    all_rekomendasi = {}
    all_iterasi     = {}

    for skema in skema_pilihan:
        label = "Tipe Tunggal" if skema == "single" else "Multitipe"
        st.subheader(f"Skema {label}")

        with st.spinner(f"Menjalankan iterasi Match Balance — Skema {label}..."):
            iterasi_results = run_iterasi(
                biaya, produkt, co2_per_jam, max_unit,
                volume_bank, volume_loose, volume_compact,
                waktu_max, T, skema)
            rekomendasi = pilih_rekomendasi(iterasi_results, skema)

        if rekomendasi is None:
            st.error(f"Tidak ditemukan solusi feasible untuk skema {label}.")
            continue

        all_rekomendasi[skema] = rekomendasi
        all_iterasi[skema]     = iterasi_results

        cost_saving_pct = (existing_cost - rekomendasi["cost_per_hari"]) / existing_cost * 100
        co2_saving_pct  = (existing_co2  - rekomendasi["co2_per_hari"])  / existing_co2  * 100
        cost_saving_rp  = existing_cost - rekomendasi["cost_per_hari"]
        co2_saving_kg   = existing_co2  - rekomendasi["co2_per_hari"]
        total_cost      = rekomendasi["cost_per_hari"] * total_days

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Biaya per Hari",
                    f"Rp {rekomendasi['cost_per_hari']:,.0f}",
                    f"-{cost_saving_pct:.2f}%")
        col2.metric("Penghematan per Hari",
                    f"Rp {cost_saving_rp:,.0f}")
        col3.metric("Emisi CO2 per Hari",
                    f"{rekomendasi['co2_per_hari']:,.0f} kg",
                    f"-{co2_saving_pct:.2f}%")
        col4.metric("Reduksi Emisi per Hari",
                    f"{co2_saving_kg:,.2f} kg")
        col5.metric("Match Balance Aktual",
                    f"{rekomendasi['mb_aktual']:.4f}")

        st.info(
            f"Total biaya proyek ({total_days} hari): "
            f"**Rp {total_cost:,.0f}**"
        )

        st.markdown("**Konfigurasi Alat Optimal**")
        config_data = []
        for i in ALAT:
            unit = rekomendasi["solution"][i]
            if unit > 0:
                config_data.append({
                    "Alat": NAMA_ALAT[i],
                    "Tipe": TIPE_ALAT[i].capitalize(),
                    "Jumlah Unit": unit,
                    "Biaya per Hari (Rp)": f"{biaya[i]*unit*T:,.0f}",
                    "Emisi CO2 per Hari (kg)": f"{co2_per_jam[i]*unit*T:,.2f}",
                })
        st.dataframe(pd.DataFrame(config_data),
                     hide_index=True, use_container_width=True)

        with st.expander("Lihat Semua Iterasi Match Balance"):
            iter_data = []
            for r in iterasi_results:
                if r["result"]:
                    res = r["result"]
                    is_rek = (res["mb_lo"] == rekomendasi["mb_lo"] and
                              res["mb_hi"] == rekomendasi["mb_hi"])
                    iter_data.append({
                        "Interval Mb": f"{r['mb_lo']:.2f} - {r['mb_hi']:.2f}",
                        "Mb Aktual": f"{res['mb_aktual']:.4f}",
                        "Biaya per Hari (Rp)": f"{res['cost_per_hari']:,.0f}",
                        "Penghematan (%)": f"{(existing_cost-res['cost_per_hari'])/existing_cost*100:.2f}%",
                        "Emisi CO2 (kg)": f"{res['co2_per_hari']:,.0f}",
                        "Reduksi CO2 (%)": f"{(existing_co2-res['co2_per_hari'])/existing_co2*100:.2f}%",
                        "Status": "Rekomendasi" if is_rek else "Feasible",
                    })
                else:
                    iter_data.append({
                        "Interval Mb": f"{r['mb_lo']:.2f} - {r['mb_hi']:.2f}",
                        "Mb Aktual": "-", "Biaya per Hari (Rp)": "Infeasible",
                        "Penghematan (%)": "-", "Emisi CO2 (kg)": "-",
                        "Reduksi CO2 (%)": "-", "Status": "Infeasible",
                    })
            st.dataframe(pd.DataFrame(iter_data),
                         hide_index=True, use_container_width=True)

        st.divider()

    # Simpan hasil ke session_state
    st.session_state["all_rekomendasi"] = all_rekomendasi
    st.session_state["all_iterasi"]     = all_iterasi

    # ============================================
    # PERBANDINGAN DUA SKEMA
    # ============================================
    if len(all_rekomendasi) == 2:
        st.header("PERBANDINGAN SKEMA OPTIMASI")
        r_s = all_rekomendasi["single"]
        r_m = all_rekomendasi["multitipe"]

        comp_data = {
            "Aspek": [
                "Biaya per Hari (Rp)",
                "Penghematan Biaya (%)",
                "Emisi CO2 per Hari (kg)",
                "Reduksi Emisi CO2 (%)",
                "Total Biaya Proyek (Rp)",
                "Match Balance Aktual",
                "Fleksibilitas Pengadaan Alat",
                "Risiko Implementasi",
            ],
            "Kondisi Eksisting": [
                f"{existing_cost:,.0f}", "-",
                f"{existing_co2:,.2f}", "-",
                f"{existing_cost * total_days:,.0f}",
                "1.2043", "-", "-",
            ],
            "Skema Tipe Tunggal": [
                f"{r_s['cost_per_hari']:,.0f}",
                f"{(existing_cost-r_s['cost_per_hari'])/existing_cost*100:.2f}%",
                f"{r_s['co2_per_hari']:,.2f}",
                f"{(existing_co2-r_s['co2_per_hari'])/existing_co2*100:.2f}%",
                f"{r_s['cost_per_hari']*total_days:,.0f}",
                f"{r_s['mb_aktual']:.4f}",
                "Rendah", "Rendah",
            ],
            "Skema Multitipe": [
                f"{r_m['cost_per_hari']:,.0f}",
                f"{(existing_cost-r_m['cost_per_hari'])/existing_cost*100:.2f}%",
                f"{r_m['co2_per_hari']:,.2f}",
                f"{(existing_co2-r_m['co2_per_hari'])/existing_co2*100:.2f}%",
                f"{r_m['cost_per_hari']*total_days:,.0f}",
                f"{r_m['mb_aktual']:.4f}",
                "Tinggi", "Sedang",
            ],
        }
        st.dataframe(pd.DataFrame(comp_data),
                     hide_index=True, use_container_width=True)
        st.success(
            "Skema Multitipe direkomendasikan sebagai solusi paling optimal "
            "dari aspek biaya operasional maupun emisi karbon, dengan Match "
            "Balance yang mendekati 1.0 dan adaptif terhadap kondisi lapangan."
        )

    # ============================================
    # ANALYTICS & BUSINESS INTELLIGENCE
    # ============================================
    if all_rekomendasi:
        st.header("ANALYTICS DAN BUSINESS INTELLIGENCE")

        # ── Breakdown Biaya dan Emisi per Tipe Alat ──
        st.subheader("Breakdown Biaya dan Emisi per Tipe Alat")
        st.caption(
            "Komposisi kontribusi setiap tipe alat terhadap "
            "total biaya operasional dan emisi karbon harian."
        )

        skema_feasible = [s for s in skema_pilihan if s in all_rekomendasi]
        tab_labels = [
            "Tipe Tunggal" if s == "single" else "Multitipe"
            for s in skema_feasible
        ]
        tabs = st.tabs(tab_labels)

        for idx, skema in enumerate(skema_feasible):
            rek = all_rekomendasi[skema]
            sol = rek["solution"]

            with tabs[idx]:
                tipe_labels = ["Excavator", "Dump Truck", "Bulldozer", "Roller"]
                tipe_ids    = [[1, 2], [3, 4], [5, 6], [7, 8]]
                tipe_colors = ["#2E5FA3", "#4CAF9A", "#F5A623", "#E05C5C"]

                biaya_per_tipe = []
                co2_per_tipe   = []
                for ids in tipe_ids:
                    b = sum(biaya[i] * sol[i] * T for i in ids)
                    c = sum(co2_per_jam[i] * sol[i] * T for i in ids)
                    biaya_per_tipe.append(b)
                    co2_per_tipe.append(c)

                col_a, col_b = st.columns(2)

                with col_a:
                    fig_biaya = go.Figure(go.Pie(
                        labels=tipe_labels,
                        values=biaya_per_tipe,
                        hole=0.55,
                        marker=dict(
                            colors=tipe_colors,
                            line=dict(color="#0D1B2A", width=2)
                        ),
                        textinfo="label+percent",
                        textfont=dict(color="#FFFFFF", size=12),
                        hovertemplate=(
                            "<b>%{label}</b><br>"
                            "Biaya: Rp %{value:,.0f}<br>"
                            "Proporsi: %{percent}<extra></extra>"
                        )
                    ))
                    fig_biaya.update_layout(
                        **PLOT_LAYOUT,
                        title="Proporsi Biaya per Tipe Alat",
                        annotations=[dict(
                            text=f"Rp<br>{rek['cost_per_hari']/1e6:.1f}M",
                            x=0.5, y=0.5, showarrow=False,
                            font=dict(size=14, color="#FFFFFF")
                        )],
                        legend=LEGEND_DONUT
                    )
                    st.plotly_chart(fig_biaya, use_container_width=True)

                with col_b:
                    fig_co2 = go.Figure(go.Pie(
                        labels=tipe_labels,
                        values=co2_per_tipe,
                        hole=0.55,
                        marker=dict(
                            colors=tipe_colors,
                            line=dict(color="#0D1B2A", width=2)
                        ),
                        textinfo="label+percent",
                        textfont=dict(color="#FFFFFF", size=12),
                        hovertemplate=(
                            "<b>%{label}</b><br>"
                            "CO2: %{value:,.1f} kg<br>"
                            "Proporsi: %{percent}<extra></extra>"
                        )
                    ))
                    fig_co2.update_layout(
                        **PLOT_LAYOUT,
                        title="Proporsi Emisi CO2 per Tipe Alat",
                        annotations=[dict(
                            text=f"{rek['co2_per_hari']:,.0f}<br>kgCO2",
                            x=0.5, y=0.5, showarrow=False,
                            font=dict(size=14, color="#FFFFFF")
                        )],
                        showlegend=True,
                        legend=LEGEND_DONUT
                    )
                    st.plotly_chart(fig_co2, use_container_width=True)

                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(
                    name="Sebelum Optimasi",
                    x=tipe_labels,
                    y=[
                        sum(biaya[i] * ([4, 0, 60, 0, 4, 0, 4, 0][i - 1]) * T
                            for i in ids)
                        for ids in tipe_ids
                    ],
                    marker_color="rgba(168,196,224,0.4)",
                    marker_line=dict(color="#A8C4E0", width=1),
                ))
                fig_bar.add_trace(go.Bar(
                    name="Setelah Optimasi",
                    x=tipe_labels,
                    y=biaya_per_tipe,
                    marker_color=tipe_colors,
                    marker_line=dict(color="#FFFFFF", width=0.5),
                ))
                fig_bar.update_layout(
                    **PLOT_LAYOUT,
                    title="Perbandingan Biaya per Tipe Alat — Sebelum vs Sesudah Optimasi",
                    xaxis_title="Tipe Alat",
                    yaxis_title="Biaya per Hari (Rp)",
                    barmode="group",
                    legend=LEGEND_BOTTOM
                )
                fig_bar.update_xaxes(**AXIS_STYLE)
                fig_bar.update_yaxes(tickformat=",.0f", **AXIS_STYLE)
                st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()

        # ── Perbandingan Interval Match Balance (dari run utama) ──
        st.subheader("Perbandingan Interval Match Balance")
        st.caption(
            "Tren biaya optimasi dan Mb aktual terhadap perubahan "
            "interval toleransi Match Balance. Menunjukkan trade-off "
            "antara keseimbangan operasional dan efisiensi biaya."
        )

        fig_mb = go.Figure()
        mb_colors = {"single": "#4CAF9A", "multitipe": "#2E5FA3"}
        x_labels  = []

        for skema in skema_pilihan:
            if skema not in all_iterasi:
                continue

            label = "Tipe Tunggal" if skema == "single" else "Multitipe"
            rek   = all_rekomendasi[skema]

            data_points = []
            for r in all_iterasi[skema]:
                if r["result"]:
                    res    = r["result"]
                    lo, hi = r["mb_lo"], r["mb_hi"]
                    data_points.append({
                        "label":  f"{lo:.2f}-{hi:.2f}",
                        "biaya":  res["cost_per_hari"],
                        "spread": hi - lo,
                    })

            if not data_points:
                continue

            data_points = sorted(data_points, key=lambda x: x["spread"])
            x_labels    = [d["label"] for d in data_points]
            y_biaya     = [d["biaya"] for d in data_points]

            fig_mb.add_trace(go.Scatter(
                x=x_labels, y=y_biaya,
                mode="lines+markers",
                name=f"Biaya — {label}",
                line=dict(color=mb_colors[skema], width=2.5),
                marker=dict(size=8, symbol="circle"),
                hovertemplate=(
                    f"<b>{label}</b><br>"
                    "Interval Mb: %{x}<br>"
                    "Biaya/hari: Rp %{y:,.0f}<extra></extra>"
                ),
                yaxis="y1"
            ))

            rek_label = f"{rek['mb_lo']:.2f}-{rek['mb_hi']:.2f}"
            if rek_label in x_labels:
                idx_rek = x_labels.index(rek_label)
                fig_mb.add_trace(go.Scatter(
                    x=[rek_label],
                    y=[y_biaya[idx_rek]],
                    mode="markers",
                    name=f"Rekomendasi — {label}",
                    marker=dict(
                        size=14, color=mb_colors[skema],
                        symbol="star",
                        line=dict(color="#FFFFFF", width=1.5)
                    ),
                    hovertemplate=(
                        f"<b>Rekomendasi {label}</b><br>"
                        "Interval Mb: %{x}<br>"
                        "Biaya/hari: Rp %{y:,.0f}<extra></extra>"
                    ),
                    yaxis="y1"
                ))

        if all_iterasi:
            first_skema = list(all_iterasi.keys())[0]
            x_ref = [
                f"{r['mb_lo']:.2f}-{r['mb_hi']:.2f}"
                for r in all_iterasi[first_skema]
                if r["result"]
            ]
            fig_mb.add_trace(go.Scatter(
                x=x_ref,
                y=[1.0] * len(x_ref),
                mode="lines",
                name="Mb Ideal (1.0)",
                line=dict(color="rgba(255,200,100,0.6)", width=1.5, dash="dash"),
                yaxis="y2"
            ))

        fig_mb.update_layout(
            **PLOT_LAYOUT,
            title="Tren Biaya Optimasi terhadap Interval Match Balance",
            xaxis_title="Interval Toleransi Match Balance",
            yaxis2=dict(
                title=dict(text="Match Balance Aktual", font=dict(color="#F5A623")),
                overlaying="y",
                side="right",
                range=[0.5, 1.5],
                gridcolor="rgba(255,255,255,0)",
                tickfont=dict(color="#F5A623")
            ),
            legend=LEGEND_BOTTOM
        )
        fig_mb.update_xaxes(
            categoryorder="array",
            categoryarray=x_labels,
            **AXIS_STYLE
        )
        fig_mb.update_yaxes(
            title_text="Biaya per Hari (Rp)",
            tickformat=",.0f",
            **AXIS_STYLE
        )
        st.plotly_chart(fig_mb, use_container_width=True)
        st.caption(
            "Bintang (*) menandai interval yang dipilih sebagai rekomendasi "
            "— Mb aktual paling mendekati 1.0 dengan biaya yang efisien."
        )

        st.divider()

# ============================================
# SENSITIVITY ANALYSIS
# PENTING: Di luar blok `if run:` supaya button bisa diklik
#          kapan saja setelah optimasi selesai.
# ============================================
if "all_rekomendasi" in st.session_state and st.session_state["all_rekomendasi"]:

    # Ambil semua data yang dibutuhkan dari session_state
    all_rekomendasi = st.session_state["all_rekomendasi"]
    all_iterasi     = st.session_state["all_iterasi"]
    params          = st.session_state["run_params"]

    biaya       = st.session_state["biaya"]
    produkt     = st.session_state["produkt"]
    co2_per_jam = st.session_state["co2_per_jam"]
    max_unit    = st.session_state["max_unit"]

    volume_bank_sa    = params["volume_bank"]
    volume_loose_sa   = params["volume_loose"]
    volume_compact_sa = params["volume_compact"]
    waktu_max_sa      = params["waktu_max"]
    T_sa              = params["T"]
    total_days_sa     = params["total_days"]
    existing_cost_sa  = params["existing_cost"]
    existing_co2_sa   = params["existing_co2"]
    skema_pilihan_sa  = params["skema_pilihan"]

    st.header("SENSITIVITY ANALYSIS")
    st.caption(
        "Re-run solver untuk setiap titik variasi. "
        "Jalankan secara terpisah agar tidak membebani komputasi utama."
    )

    tab_sa_mb, tab_sa_dur = st.tabs(["Match Balance", "Durasi Proyek"])

    # ── TAB 1: SENSITIVITY MATCH BALANCE ──
    with tab_sa_mb:
        st.subheader("Sensitivity: Match Balance Interval")
        st.caption(
            "Solver dijalankan ulang untuk setiap spread interval MB. "
            "Memperlihatkan bagaimana konfigurasi alat dan biaya berubah "
            "saat toleransi keseimbangan operasional diperlonggar atau diperketat."
        )

        col_run_mb, col_info_mb = st.columns([1, 3])
        with col_run_mb:
            btn_mb = st.button(
                "Jalankan Sensitivity MB",
                type="primary",
                use_container_width=True,
                key="btn_sa_mb"
            )
        with col_info_mb:
            st.info(
                f"Akan menjalankan 7 titik variasi × "
                f"{len(skema_pilihan_sa)} skema = "
                f"{7 * len(skema_pilihan_sa)} solve calls. "
                f"Estimasi: ~10–20 detik."
            )

        if btn_mb:
            sa_mb_results = {}
            for skema in skema_pilihan_sa:
                if skema not in all_rekomendasi:
                    continue
                label = "Tipe Tunggal" if skema == "single" else "Multitipe"
                with st.spinner(f"Running sensitivity MB — {label}..."):
                    sa_mb_results[skema] = sensitivity_mb(
                        biaya, produkt, co2_per_jam, max_unit,
                        volume_bank_sa, volume_loose_sa, volume_compact_sa,
                        waktu_max_sa, T_sa, skema
                    )
            st.session_state["sa_mb"] = sa_mb_results
            st.session_state["sa_mb_params"] = {
                "existing_cost": existing_cost_sa
            }

        if "sa_mb" in st.session_state:
            sa_mb_data   = st.session_state["sa_mb"]
            _ex_cost_mb  = st.session_state["sa_mb_params"]["existing_cost"]
            skema_colors = {"single": "#4CAF9A", "multitipe": "#2E5FA3"}

            for skema, rows in sa_mb_data.items():
                label    = "Tipe Tunggal" if skema == "single" else "Multitipe"
                feasible = [r for r in rows if r["feasible"]]
                if not feasible:
                    st.warning(f"Skema {label}: tidak ada solusi feasible.")
                    continue

                st.markdown(f"**Skema {label}**")

                # Chart 1: Tren biaya vs interval MB
                fig_cost = go.Figure()
                fig_cost.add_trace(go.Scatter(
                    x=[r["label"] for r in feasible],
                    y=[r["cost_per_hari"] for r in feasible],
                    mode="lines+markers",
                    name=f"Biaya/hari — {label}",
                    line=dict(color=skema_colors[skema], width=2.5),
                    marker=dict(size=8),
                    hovertemplate=(
                        "Interval: %{x}<br>"
                        "Biaya: Rp %{y:,.0f}<extra></extra>"
                    )
                ))
                best_cost_pt = min(feasible, key=lambda r: r["cost_per_hari"])
                fig_cost.add_trace(go.Scatter(
                    x=[best_cost_pt["label"]],
                    y=[best_cost_pt["cost_per_hari"]],
                    mode="markers",
                    name="Biaya optimal",
                    marker=dict(
                        size=14, color=skema_colors[skema],
                        symbol="star",
                        line=dict(color="#FFFFFF", width=1.5)
                    ),
                    hovertemplate=(
                        "<b>Biaya optimal</b><br>"
                        "Interval: %{x}<br>"
                        "Biaya: Rp %{y:,.0f}<extra></extra>"
                    )
                ))
                fig_cost.add_hline(
                    y=_ex_cost_mb,
                    line=dict(color="rgba(255,200,100,0.6)", width=1.5, dash="dash"),
                    annotation_text="Biaya eksisting",
                    annotation_position="top right",
                    annotation_font=dict(color="#F5A623", size=11)
                )
                fig_cost.update_layout(
                    **PLOT_LAYOUT,
                    title="Tren Biaya per Hari vs Interval MB",
                    xaxis_title="Interval Match Balance",
                    yaxis_title="Biaya per Hari (Rp)",
                    legend=LEGEND_BOTTOM
                )
                fig_cost.update_xaxes(**AXIS_STYLE)
                fig_cost.update_yaxes(tickformat=",.0f", **AXIS_STYLE)
                st.plotly_chart(fig_cost, use_container_width=True)

                # Chart 2: Mb aktual vs Mb ideal
                fig_mb_sa = go.Figure()
                fig_mb_sa.add_trace(go.Scatter(
                    x=[r["label"] for r in feasible],
                    y=[r["mb_aktual"] for r in feasible],
                    mode="lines+markers",
                    name="Mb aktual",
                    line=dict(color=skema_colors[skema], width=2.5),
                    marker=dict(size=8),
                    hovertemplate=(
                        "Interval: %{x}<br>"
                        "Mb aktual: %{y:.4f}<extra></extra>"
                    )
                ))
                fig_mb_sa.add_hline(
                    y=1.0,
                    line=dict(color="rgba(255,200,100,0.7)", width=1.5, dash="dash"),
                    annotation_text="Mb ideal (1.0)",
                    annotation_position="top right",
                    annotation_font=dict(color="#F5A623", size=11)
                )
                best_mb_pt = min(feasible, key=lambda r: abs(r["mb_aktual"] - 1.0))
                fig_mb_sa.add_trace(go.Scatter(
                    x=[best_mb_pt["label"]],
                    y=[best_mb_pt["mb_aktual"]],
                    mode="markers",
                    name="Mb paling seimbang",
                    marker=dict(
                        size=14, color="#F5A623",
                        symbol="star",
                        line=dict(color="#FFFFFF", width=1.5)
                    ),
                    hovertemplate=(
                        "<b>Paling seimbang</b><br>"
                        "Interval: %{x}<br>"
                        "Mb: %{y:.4f}<extra></extra>"
                    )
                ))
                fig_mb_sa.update_layout(
                    **PLOT_LAYOUT,
                    title="Mb Aktual vs Mb Ideal (1.0) per Interval",
                    xaxis_title="Interval Match Balance",
                    yaxis_title="Match Balance Aktual",
                    legend=LEGEND_BOTTOM
                )
                fig_mb_sa.update_xaxes(**AXIS_STYLE)
                fig_mb_sa.update_yaxes(**AXIS_STYLE)
                st.plotly_chart(fig_mb_sa, use_container_width=True)

                # Chart 3: Perubahan konfigurasi unit per interval
                tipe_labels_sa = ["Excavator", "Dump Truck", "Bulldozer", "Roller"]
                tipe_keys_sa   = ["unit_exc", "unit_dt", "unit_bd", "unit_vr"]
                tipe_colors_sa = ["#2E5FA3", "#4CAF9A", "#F5A623", "#E05C5C"]

                fig_unit_mb = go.Figure()
                for tipe, key, color in zip(tipe_labels_sa, tipe_keys_sa, tipe_colors_sa):
                    fig_unit_mb.add_trace(go.Bar(
                        name=tipe,
                        x=[r["label"] for r in feasible],
                        y=[r[key] for r in feasible],
                        marker_color=color,
                        hovertemplate=(
                            f"<b>{tipe}</b><br>"
                            "Interval: %{x}<br>"
                            "Unit: %{y}<extra></extra>"
                        )
                    ))
                fig_unit_mb.update_layout(
                    **PLOT_LAYOUT,
                    title="Perubahan Konfigurasi Unit per Interval MB",
                    xaxis_title="Interval Match Balance",
                    yaxis_title="Jumlah Unit",
                    barmode="stack",
                    legend=LEGEND_BOTTOM
                )
                fig_unit_mb.update_xaxes(**AXIS_STYLE)
                fig_unit_mb.update_yaxes(**AXIS_STYLE)
                st.plotly_chart(fig_unit_mb, use_container_width=True)

                # Tabel ringkasan
                with st.expander("Tabel Ringkasan Sensitivity MB"):
                    tbl_mb = []
                    for r in rows:
                        if r["feasible"]:
                            saving       = (_ex_cost_mb - r["cost_per_hari"]) / _ex_cost_mb * 100
                            is_best_cost = r["label"] == best_cost_pt["label"]
                            is_best_mb   = r["label"] == best_mb_pt["label"]
                            status = []
                            if is_best_cost: status.append("Biaya optimal")
                            if is_best_mb:   status.append("MB paling seimbang")
                            score_str = f"{r['score']:.4f}" if r.get("score") is not None else "—"
                            tbl_mb.append({
                                "Interval MB":      r["label"],
                                "Mb Aktual":        f"{r['mb_aktual']:.4f}",
                                "Biaya/Hari (Rp)":  f"{r['cost_per_hari']:,.0f}",
                                "Penghematan (%)":  f"{saving:.2f}%",
                                "Total Unit":       r["unit_total"],
                                "EXC/DT/BD/VR":     f"{r['unit_exc']}/{r['unit_dt']}/{r['unit_bd']}/{r['unit_vr']}",
                                "Sweet Spot Score": score_str,
                                "Keterangan":       " + ".join(status) if status else "—",
                            })
                        else:
                            tbl_mb.append({
                                "Interval MB":      r["label"],
                                "Mb Aktual":        "—",
                                "Biaya/Hari (Rp)":  "Infeasible",
                                "Penghematan (%)":  "—",
                                "Total Unit":       "—",
                                "EXC/DT/BD/VR":     "—",
                                "Sweet Spot Score": "—",
                                "Keterangan":       "Infeasible",
                            })
                    st.dataframe(pd.DataFrame(tbl_mb),
                                 hide_index=True, use_container_width=True)

                # Business Intelligence Insights
                st.markdown("**Business Intelligence Insights**")
                for ins in generate_insight_mb(rows, _ex_cost_mb, label):
                    if ins["severity"] == "success":
                        st.success(ins["text"])
                    elif ins["severity"] == "warning":
                        st.warning(ins["text"])
                    else:
                        st.info(ins["text"])

                st.divider()

    # ── TAB 2: SENSITIVITY DURASI ──
    with tab_sa_dur:
        st.subheader("Sensitivity: Durasi Proyek")
        st.caption(
            "Solver dijalankan ulang untuk setiap variasi durasi (±30 hari, step 5 hari). "
            "Berbeda dari chart lama yang hanya mengalikan biaya — "
            "di sini constraint produktivitas minimum ikut berubah, "
            "sehingga konfigurasi unit optimal bisa berbeda di setiap titik."
        )

        col_run_dur, col_info_dur = st.columns([1, 3])
        with col_run_dur:
            btn_dur = st.button(
                "Jalankan Sensitivity Durasi",
                type="primary",
                use_container_width=True,
                key="btn_sa_dur"
            )
        with col_info_dur:
            n_titik = len(list(range(max(1, total_days_sa - 30), total_days_sa + 31, 5)))
            st.info(
                f"Akan menjalankan ~{n_titik} titik durasi × "
                f"{len(skema_pilihan_sa)} skema × 7 interval MB = "
                f"~{n_titik * len(skema_pilihan_sa) * 7} solve calls. "
                f"Estimasi: ~20–40 detik."
            )

        if btn_dur:
            sa_dur_results = {}
            for skema in skema_pilihan_sa:
                if skema not in all_rekomendasi:
                    continue
                label = "Tipe Tunggal" if skema == "single" else "Multitipe"
                with st.spinner(f"Running sensitivity durasi — {label}..."):
                    sa_dur_results[skema] = sensitivity_durasi(
                        biaya, produkt, co2_per_jam, max_unit,
                        volume_bank_sa, volume_loose_sa, volume_compact_sa,
                        T_sa, skema, total_days_sa
                    )
            st.session_state["sa_dur"] = sa_dur_results
            st.session_state["sa_dur_params"] = {
                "existing_cost": existing_cost_sa,
                "total_days":    total_days_sa,
            }

        if "sa_dur" in st.session_state:
            sa_dur_data  = st.session_state["sa_dur"]
            _ex_cost_dur = st.session_state["sa_dur_params"]["existing_cost"]
            _total_days  = st.session_state["sa_dur_params"]["total_days"]
            skema_colors = {"single": "#4CAF9A", "multitipe": "#2E5FA3"}

            # Chart 1: Total cost vs durasi — semua skema
            fig_total = go.Figure()
            all_hari = sorted(set(
                r["hari"]
                for rows in sa_dur_data.values()
                for r in rows if r["feasible"]
            ))
            fig_total.add_trace(go.Scatter(
                x=all_hari,
                y=[_ex_cost_dur * h for h in all_hari],
                mode="lines",
                name="Kondisi Eksisting",
                line=dict(color="rgba(168,196,224,0.5)", width=2, dash="dot"),
                hovertemplate=(
                    "Durasi: %{x} hari<br>"
                    "Total biaya eksisting: Rp %{y:,.0f}<extra></extra>"
                )
            ))
            for skema, rows in sa_dur_data.items():
                label    = "Tipe Tunggal" if skema == "single" else "Multitipe"
                feasible = [r for r in rows if r["feasible"]]
                if not feasible:
                    continue
                fig_total.add_trace(go.Scatter(
                    x=[r["hari"] for r in feasible],
                    y=[r["total_cost"] for r in feasible],
                    mode="lines+markers",
                    name=f"Optimasi — {label}",
                    line=dict(color=skema_colors[skema], width=2.5),
                    marker=dict(size=7),
                    hovertemplate=(
                        f"<b>{label}</b><br>"
                        "Durasi: %{x} hari<br>"
                        "Total cost: Rp %{y:,.0f}<extra></extra>"
                    )
                ))
                aktual_pt = next((r for r in feasible if r["is_aktual"]), None)
                if aktual_pt:
                    fig_total.add_trace(go.Scatter(
                        x=[aktual_pt["hari"]],
                        y=[aktual_pt["total_cost"]],
                        mode="markers",
                        name=f"Durasi aktual — {label}",
                        marker=dict(
                            size=14, color=skema_colors[skema],
                            symbol="star",
                            line=dict(color="#FFFFFF", width=1.5)
                        ),
                        showlegend=False,
                        hovertemplate=(
                            f"<b>Durasi aktual ({_total_days} hari)</b><br>"
                            "Total cost: Rp %{y:,.0f}<extra></extra>"
                        )
                    ))
            fig_total.add_vline(
                x=_total_days,
                line=dict(color="rgba(255,200,100,0.7)", width=1.5, dash="dash"),
                annotation_text=f"Durasi aktual ({_total_days} hari)",
                annotation_position="top right",
                annotation_font=dict(color="#F5A623", size=11)
            )
            fig_total.update_layout(
                **PLOT_LAYOUT,
                title="Total Biaya Proyek vs Variasi Durasi",
                xaxis_title="Durasi Proyek (hari)",
                yaxis_title="Total Biaya Proyek (Rp)",
                legend=LEGEND_BOTTOM
            )
            fig_total.update_xaxes(**AXIS_STYLE)
            fig_total.update_yaxes(tickformat=",.0f", **AXIS_STYLE)
            st.plotly_chart(fig_total, use_container_width=True)

            # Chart 2 + Tabel + Insight: per skema
            for skema, rows in sa_dur_data.items():
                label    = "Tipe Tunggal" if skema == "single" else "Multitipe"
                feasible = [r for r in rows if r["feasible"]]
                if not feasible:
                    continue

                tipe_labels_dur = ["Excavator", "Dump Truck", "Bulldozer", "Roller"]
                tipe_keys_dur   = ["unit_exc", "unit_dt", "unit_bd", "unit_vr"]
                tipe_colors_dur = ["#2E5FA3", "#4CAF9A", "#F5A623", "#E05C5C"]

                fig_unit_dur = go.Figure()
                for tipe, key, color in zip(tipe_labels_dur, tipe_keys_dur, tipe_colors_dur):
                    fig_unit_dur.add_trace(go.Bar(
                        name=tipe,
                        x=[r["hari"] for r in feasible],
                        y=[r[key] for r in feasible],
                        marker_color=color,
                        hovertemplate=(
                            f"<b>{tipe}</b><br>"
                            "Durasi: %{x} hari<br>"
                            "Unit: %{y}<extra></extra>"
                        )
                    ))
                fig_unit_dur.add_vline(
                    x=_total_days,
                    line=dict(color="rgba(255,200,100,0.7)", width=1.5, dash="dash"),
                    annotation_text="Durasi aktual",
                    annotation_font=dict(color="#F5A623", size=10)
                )
                fig_unit_dur.update_layout(
                    **PLOT_LAYOUT,
                    title=f"Komposisi Unit Optimal vs Durasi — Skema {label}",
                    xaxis_title="Durasi Proyek (hari)",
                    yaxis_title="Jumlah Unit",
                    barmode="stack",
                    legend=LEGEND_BOTTOM
                )
                fig_unit_dur.update_xaxes(**AXIS_STYLE)
                fig_unit_dur.update_yaxes(**AXIS_STYLE)
                st.plotly_chart(fig_unit_dur, use_container_width=True)

                with st.expander(f"Tabel Ringkasan Sensitivity Durasi — {label}"):
                    tbl_dur = []
                    for r in rows:
                        if r["feasible"]:
                            saving_hari = (_ex_cost_dur - r["cost_per_hari"]) / _ex_cost_dur * 100
                            total_hemat = (_ex_cost_dur - r["cost_per_hari"]) * r["hari"]
                            tbl_dur.append({
                                "Durasi (hari)":  r["hari"],
                                "Keterangan":     (
                                    "Durasi aktual" if r["is_aktual"] else
                                    f"Dipercepat {_total_days - r['hari']} hari"
                                    if r["hari"] < _total_days else
                                    f"Molor {r['hari'] - _total_days} hari"
                                ),
                                "Cost/Hari (Rp)":   f"{r['cost_per_hari']:,.0f}",
                                "Total Cost (Rp)":  f"{r['total_cost']:,.0f}",
                                "Hemat/Hari (%)":   f"{saving_hari:.2f}%",
                                "Total Hemat (Rp)": f"{total_hemat:,.0f}",
                                "Unit Total":       r["unit_total"],
                                "EXC/DT/BD/VR":     f"{r['unit_exc']}/{r['unit_dt']}/{r['unit_bd']}/{r['unit_vr']}",
                                "Mb Aktual":        f"{r['mb_aktual']:.4f}",
                            })
                        else:
                            tbl_dur.append({
                                "Durasi (hari)":  r["hari"],
                                "Keterangan":     "Infeasible",
                                "Cost/Hari (Rp)":   "—",
                                "Total Cost (Rp)":  "—",
                                "Hemat/Hari (%)":   "—",
                                "Total Hemat (Rp)": "—",
                                "Unit Total":       "—",
                                "EXC/DT/BD/VR":     "—",
                                "Mb Aktual":        "—",
                            })
                    st.dataframe(pd.DataFrame(tbl_dur),
                                 hide_index=True, use_container_width=True)

                st.markdown("**Business Intelligence Insights**")
                for ins in generate_insight_durasi(rows, _ex_cost_dur, _total_days, label):
                    if ins["severity"] == "success":
                        st.success(ins["text"])
                    elif ins["severity"] == "warning":
                        st.warning(ins["text"])
                    else:
                        st.info(ins["text"])

                st.divider()

# ============================================
# FOOTER
# ============================================
st.markdown("""
<div class="ceoe-footer">
    CONSTRUCTION EQUIPMENT OPTIMIZATION ENGINE (CEOE)<br>
    Nickholast Aditya Pratama &nbsp;|&nbsp;
    Civil Engineering Technology, Universitas Gadjah Mada 2025<br>
    Integer Linear Programming (ILP) + Match Balance Iteration Method
</div>
""", unsafe_allow_html=True)