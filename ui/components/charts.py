"""
Plotly tabanlı 2B simülasyon grafikleri ve görselleştirme oluşturucuları.

İş mantığı nesnelerini (`UAVPlatform`, `TargetData`, `TelemetryPacketResult`,
`FlightController`, `RoutePlan`) alarak koyu temalı teknik Plotly figürleri üretir.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import plotly.graph_objects as go

from src.models.navigation_models import Point2D, RestrictedZone, RoutePlan
from src.models.sensor_models import TargetData
from src.models.telemetry_models import TelemetryPacketResult
from src.patterns.builder import UAVPlatform
from src.patterns.state import FlightController

_DARK_BG = "#0f172a"
_PAPER_BG = "#111827"
_GRID_COLOR = "#1e293b"
_TEXT_COLOR = "#e2e8f0"


def create_avionics_gauges_chart(hud: Dict[str, Any]) -> go.Figure:
    """
    Canlı Uçuş Göstergeleri (Avionics PFD Cluster):
    Hava Hızı (IAS knots), İrtifa (ALT m/ft), Motor İtkisi (THR %) ve Kalan Yakıt (FUEL %/kg)
    değerlerini gerçek zamanlı 4'lü dairesel havacılık kadranı (`go.Indicator`) olarak çizer.
    """
    fig = go.Figure()

    # 1. Kadran: Hava Hızı (Airspeed — knots)
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=float(hud["airspeed_knots"]),
            number={"suffix": " kts", "font": {"size": 22, "color": "#38bdf8"}},
            title={
                "text": "HAVA HIZI (IAS)<br><span style='font-size:11px;color:#94a3b8'>Seyir Zarbı: 60–145 kts</span>",
                "font": {"size": 13, "color": _TEXT_COLOR},
            },
            domain={"x": [0.00, 0.22], "y": [0.05, 0.82]},
            gauge={
                "axis": {"range": [0, 180], "tickwidth": 1, "tickcolor": "#64748b"},
                "bar": {"color": "#38bdf8", "thickness": 0.32},
                "bgcolor": _DARK_BG,
                "borderwidth": 1,
                "bordercolor": "#334155",
                "steps": [
                    {"range": [0, 60], "color": "rgba(100, 116, 139, 0.25)"},
                    {"range": [60, 145], "color": "rgba(16, 185, 129, 0.22)"},
                    {"range": [145, 165], "color": "rgba(245, 158, 11, 0.28)"},
                    {"range": [165, 180], "color": "rgba(239, 68, 68, 0.32)"},
                ],
                "threshold": {
                    "line": {"color": "#ef4444", "width": 3},
                    "thickness": 0.8,
                    "value": 165,
                },
            },
        )
    )

    # 2. Kadran: İrtifa (Altimeter — metre & feet)
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=float(hud["altitude_m"]),
            number={"suffix": " m", "valueformat": ".0f", "font": {"size": 22, "color": "#22c55e"}},
            title={
                "text": f"İRTİFA (ALT)<br><span style='font-size:11px;color:#94a3b8'>{hud['altitude_ft']:,} ft MSL</span>",
                "font": {"size": 13, "color": _TEXT_COLOR},
            },
            domain={"x": [0.26, 0.48], "y": [0.05, 0.82]},
            gauge={
                "axis": {"range": [0, 8000], "tickwidth": 1, "tickcolor": "#64748b"},
                "bar": {"color": "#22c55e", "thickness": 0.32},
                "bgcolor": _DARK_BG,
                "borderwidth": 1,
                "bordercolor": "#334155",
                "steps": [
                    {"range": [0, 1500], "color": "rgba(56, 189, 248, 0.18)"},
                    {"range": [1500, 6500], "color": "rgba(34, 197, 94, 0.22)"},
                    {"range": [6500, 8000], "color": "rgba(245, 158, 11, 0.28)"},
                ],
                "threshold": {
                    "line": {"color": "#38bdf8", "width": 3},
                    "thickness": 0.8,
                    "value": 6000,
                },
            },
        )
    )

    # 3. Kadran: Motor İtkisi (Throttle — %)
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=float(hud["throttle_pct"]),
            number={"suffix": "%", "valueformat": ".0f", "font": {"size": 22, "color": "#f59e0b"}},
            title={
                "text": f"MOTOR İTKİSİ (THR)<br><span style='font-size:11px;color:#94a3b8'>Faz: {hud['flight_phase']}</span>",
                "font": {"size": 13, "color": _TEXT_COLOR},
            },
            domain={"x": [0.52, 0.74], "y": [0.05, 0.82]},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#64748b"},
                "bar": {"color": "#f59e0b", "thickness": 0.32},
                "bgcolor": _DARK_BG,
                "borderwidth": 1,
                "bordercolor": "#334155",
                "steps": [
                    {"range": [0, 25], "color": "rgba(100, 116, 139, 0.22)"},
                    {"range": [25, 80], "color": "rgba(16, 185, 129, 0.22)"},
                    {"range": [80, 92], "color": "rgba(245, 158, 11, 0.28)"},
                    {"range": [92, 100], "color": "rgba(239, 68, 68, 0.35)"},
                ],
                "threshold": {
                    "line": {"color": "#ef4444", "width": 3},
                    "thickness": 0.8,
                    "value": 95,
                },
            },
        )
    )

    # 4. Kadran: Kalan Yakıt (Fuel — % & kg)
    fuel_val = float(hud["fuel_pct"])
    fuel_bar_color = "#10b981" if fuel_val > 35 else ("#f59e0b" if fuel_val > 15 else "#ef4444")
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=fuel_val,
            number={"suffix": "%", "valueformat": ".0f", "font": {"size": 22, "color": fuel_bar_color}},
            title={
                "text": (
                    f"KALAN YAKIT (FUEL)<br><span style='font-size:11px;color:#94a3b8'>"
                    f"{hud['fuel_remaining_kg']:.0f} / {hud['fuel_initial_kg']:.0f} kg</span>"
                ),
                "font": {"size": 13, "color": _TEXT_COLOR},
            },
            domain={"x": [0.78, 1.00], "y": [0.05, 0.82]},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#64748b"},
                "bar": {"color": fuel_bar_color, "thickness": 0.32},
                "bgcolor": _DARK_BG,
                "borderwidth": 1,
                "bordercolor": "#334155",
                "steps": [
                    {"range": [0, 15], "color": "rgba(239, 68, 68, 0.35)"},
                    {"range": [15, 35], "color": "rgba(245, 158, 11, 0.28)"},
                    {"range": [35, 100], "color": "rgba(16, 185, 129, 0.20)"},
                ],
                "threshold": {
                    "line": {"color": "#ef4444", "width": 3},
                    "thickness": 0.8,
                    "value": 15,
                },
            },
        )
    )

    fig.update_layout(
        height=215,
        margin=dict(l=20, r=20, t=35, b=10),
        paper_bgcolor=_PAPER_BG,
        plot_bgcolor=_DARK_BG,
        font=dict(color=_TEXT_COLOR),
    )
    return fig


def create_weight_breakdown_chart(platform: UAVPlatform) -> go.Figure:
    """
    Builder Kalıbı: İHA platformunun ağırlık bileşenlerini (Boş Gövde, Yakıt,
    Sensörler, Faydalı Yükler, Haberleşme) ve Maksimum Kalkış Ağırlığı (MTOW)
    sınırını gösteren grafik üretir.
    """
    categories = ["Boş Gövde", "Yakıt", "Sensörler", "Faydalı Yükler", "Haberleşme"]
    values = [
        platform.empty_weight_kg,
        platform.fuel_weight_kg,
        platform.sensors_weight_kg,
        platform.payloads_weight_kg,
        platform.comms_weight_kg,
    ]
    colors = ["#3b82f6", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6"]

    fig = go.Figure()
    for cat, val, col in zip(categories, values, colors):
        fig.add_trace(
            go.Bar(
                name=f"{cat} ({val:.0f} kg)",
                y=["Ağırlık Dağılımı"],
                x=[val],
                orientation="h",
                marker_color=col,
                text=[f"{val:.0f} kg" if val > 0 else ""],
                textposition="inside",
            )
        )

    fig.add_vline(
        x=platform.max_takeoff_weight_kg,
        line_width=3,
        line_dash="dash",
        line_color="#f43f5e",
        annotation_text=f"MTOW Sınırı: {platform.max_takeoff_weight_kg:.0f} kg",
        annotation_position="top right",
        annotation_font_color="#fda4af",
    )

    max_x = max(platform.max_takeoff_weight_kg, platform.total_weight_kg) * 1.15
    fig.update_layout(
        barmode="stack",
        title=f"Kalkış Ağırlığı Analizi: {platform.total_weight_kg:.1f} / {platform.max_takeoff_weight_kg:.1f} kg",
        xaxis_title="Ağırlık (kg)",
        xaxis=dict(range=[0, max_x], gridcolor=_GRID_COLOR),
        yaxis=dict(showticklabels=False),
        height=260,
        margin=dict(l=20, r=20, t=45, b=35),
        paper_bgcolor=_PAPER_BG,
        plot_bgcolor=_DARK_BG,
        font=dict(color=_TEXT_COLOR),
        legend=dict(orientation="h", yanchor="bottom", y=-0.45, xanchor="center", x=0.5),
    )
    return fig


def create_uav_blueprint_chart(platform: UAVPlatform) -> go.Figure:
    """
    Öneri D — 2B Teknik İHA Gövde & Kanat İstasyon Şeması (Top-Down CAD Blueprint):
    İHA'nın üstten teknik görünümü üzerinde burun/gövde sensör yuvalarını (`BAY 1..3`),
    SATCOM/Veri Bağı kubbesini ve kanat altı faydalı yük istasyonlarını (`HP 1..4`)
    canlı olarak işaretler.
    """
    fig = go.Figure()
    is_strike = platform.mission_type == "STRIKE"

    # 1. İHA Üstten Gövde ve Kanat Silüeti (CAD Poligonu)
    airframe_x = [
        0.0, 0.55, 0.78, 0.85, 3.2, 3.4, 9.6, 9.8, 0.85, 0.72,
        2.6, 2.5, 0.35, 0.0, -0.35, -2.5, -2.6, -0.72, -0.85,
        -9.8, -9.6, -3.4, -3.2, -0.85, -0.78, -0.55, 0.0,
    ]
    airframe_y = [
        6.2, 5.1, 3.6, 1.8, 1.35, 1.55, 0.35, -0.45, -0.25, -3.6,
        -4.8, -5.5, -4.6, -5.2, -4.6, -5.5, -4.8, -3.6, -0.25,
        -0.45, 0.35, 1.55, 1.35, 1.8, 3.6, 5.1, 6.2,
    ]
    outline_color = "#38bdf8" if is_strike else "#10b981"
    fill_rgba = "rgba(56, 189, 248, 0.14)" if is_strike else "rgba(16, 185, 129, 0.14)"

    fig.add_trace(
        go.Scatter(
            x=airframe_x,
            y=airframe_y,
            fill="toself",
            fillcolor=fill_rgba,
            line=dict(color=outline_color, width=2.2),
            name=f"Gövde Silüeti ({platform.airframe_type})",
            hoverinfo="name",
        )
    )

    # Gövde merkez eksen çizgisi
    fig.add_trace(
        go.Scatter(
            x=[0.0, 0.0],
            y=[-5.6, 6.6],
            mode="lines",
            line=dict(color="#334155", width=1, dash="dash"),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # 2. Haberleşme Kubbesi (SATCOM / Data Link Dome)
    has_comms = platform.comms_module is not None
    comms_label = (
        f"📡 {platform.comms_module.name[:24]} ({platform.comms_module.range_km:.0f} km)"
        if platform.comms_module
        else "❌ HABERLEŞME MODÜLÜ EKSİK"
    )
    fig.add_trace(
        go.Scatter(
            x=[0.0],
            y=[3.8],
            mode="markers+text",
            name="Haberleşme Yuvası (SATCOM/LOS)",
            text=[comms_label],
            textposition="top center",
            textfont=dict(size=10, color="#c084fc" if has_comms else "#ef4444"),
            marker=dict(
                size=14,
                color="#a855f7" if has_comms else "#ef4444",
                symbol="hexagon",
                line=dict(width=1.5, color="#ffffff"),
            ),
        )
    )

    # 3. Sensör Yuvaları (BAY-1 Burun Taret, BAY-2 Gövde Altı Radar, BAY-3 Gövde İçi SIGINT)
    bay_coords = [
        (0.0, 5.4, "BAY-1 (Burun EO/IR)"),
        (0.0, 1.9, "BAY-2 (Gövde Radarı)"),
        (0.0, -1.6, "BAY-3 (Görev Sensörü)"),
    ]
    for idx, (bx, by, bay_title) in enumerate(bay_coords):
        if idx < len(platform.sensors):
            sensor = platform.sensors[idx]
            compatible = (
                not platform.mission_type
                or platform.mission_type in sensor.compatible_missions
            )
            s_color = "#22c55e" if compatible else "#ef4444"
            s_text = f"🟢 {bay_title}:<br>{sensor.name[:22]} ({sensor.weight_kg:.0f}kg)"
        else:
            s_color = "#475569"
            s_text = f"⚪ {bay_title}: BOŞ"

        fig.add_trace(
            go.Scatter(
                x=[bx],
                y=[by],
                mode="markers+text",
                name=bay_title,
                text=[s_text],
                textposition="bottom center" if idx == 2 else "middle right",
                textfont=dict(size=10, color=s_color if s_color != "#475569" else "#94a3b8"),
                marker=dict(
                    size=13,
                    color=s_color,
                    symbol="circle-dot",
                    line=dict(width=1.5, color="#ffffff"),
                ),
                showlegend=(idx == 0),
            )
        )

    # 4. Kanat Altı Faydalı Yük İstasyonları (Hardpoints HP-1..HP-4)
    hp_definitions = [
        (-3.6, 0.55, "HP-1 (Sol İç İstasyon)"),
        (3.6, 0.55, "HP-2 (Sağ İç İstasyon)"),
        (-6.8, 0.10, "HP-3 (Sol Dış İstasyon)"),
        (6.8, 0.10, "HP-4 (Sağ Dış İstasyon)"),
    ]
    active_hps = hp_definitions[: platform.max_hardpoints]

    for idx, (hx, hy, hp_title) in enumerate(active_hps):
        if idx < len(platform.payloads):
            pl = platform.payloads[idx]
            compatible = (
                not platform.mission_type
                or platform.mission_type in pl.compatible_missions
            )
            p_color = "#f59e0b" if compatible else "#ef4444"
            p_text = f"🟧 {hp_title.split()[0]}:<br>{pl.name[:20]}<br>({pl.weight_kg:.0f} kg)"
        else:
            p_color = "#334155"
            p_text = f"⬜ {hp_title.split()[0]}:<br>BOŞ İSTASYON"

        fig.add_trace(
            go.Scatter(
                x=[hx],
                y=[hy],
                mode="markers+text",
                name="Kanat İstasyonu (Hardpoint)",
                text=[p_text],
                textposition="bottom center",
                textfont=dict(size=10, color="#fbbf24" if p_color == "#f59e0b" else "#94a3b8"),
                marker=dict(
                    size=15,
                    color=p_color,
                    symbol="diamond",
                    line=dict(width=1.5, color="#ffffff"),
                ),
                showlegend=(idx == 0),
            )
        )

    fig.update_layout(
        title=(
            f"📐 2B İHA Gövde & Kanat İstasyon Şeması — {platform.model_name} "
            f"(Sensör: {len(platform.sensors)}/{platform.max_sensor_slots} | "
            f"İstasyon: {len(platform.payloads)}/{platform.max_hardpoints})"
        ),
        xaxis=dict(
            title="Kanat Açıklığı Ekseni (Metre)",
            range=[-11.5, 11.5],
            gridcolor=_GRID_COLOR,
            zeroline=False,
        ),
        yaxis=dict(
            title="Gövde Boyu Ekseni (Metre)",
            range=[-6.8, 7.4],
            gridcolor=_GRID_COLOR,
            scaleanchor="x",
            scaleratio=1,
            zeroline=False,
        ),
        height=390,
        margin=dict(l=20, r=20, t=48, b=25),
        paper_bgcolor=_PAPER_BG,
        plot_bgcolor=_DARK_BG,
        font=dict(color=_TEXT_COLOR),
        showlegend=False,
    )
    return fig


def create_uav_capability_radar_chart(platform: UAVPlatform) -> go.Figure:
    """
    Öneri D — 5 Eksenli Platform Yetenek Radar Grafiği (`Scatterpolar`):
    Yapılandırılan İHA'nın Havada Kalış, Harekât Yarıçapı, Keşif/Sensör (ISR),
    Faydalı Yük ve Çeviklik/Ağırlık Marjı puanlarını (0-100) görselleştirir.
    """
    perf = platform.get_performance_metrics()
    scores_dict = perf["radar_scores"]
    categories = list(scores_dict.keys())
    values = list(scores_dict.values())

    # Poligonu kapatmak için ilk elemanı sona ekle
    cat_closed = categories + [categories[0]]
    val_closed = values + [values[0]]

    # Referans profil (RECON vs STRIKE dengeli referans)
    ref_vals = (
        [65.0, 70.0, 75.0, 80.0, 60.0]
        if platform.mission_type == "STRIKE"
        else [85.0, 65.0, 85.0, 45.0, 75.0]
    )
    ref_closed = ref_vals + [ref_vals[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=ref_closed,
            theta=cat_closed,
            name=f"Sınıf Referans Profili ({platform.mission_type})",
            line=dict(color="#64748b", width=2, dash="dot"),
            fill="toself",
            fillcolor="rgba(100, 116, 139, 0.12)",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=val_closed,
            theta=cat_closed,
            name=platform.model_name or "Aktif Taslak",
            line=dict(color="#06b6d4", width=3),
            fill="toself",
            fillcolor="rgba(6, 182, 212, 0.28)",
            marker=dict(size=8, color="#38bdf8"),
        )
    )

    fig.update_layout(
        title="🕸️ 5 Eksenli Mühendislik ve Görev Yetenek Analizi (0–100 Puan)",
        polar=dict(
            bgcolor=_DARK_BG,
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor=_GRID_COLOR,
                tickfont=dict(size=10, color="#94a3b8"),
            ),
            angularaxis=dict(
                gridcolor=_GRID_COLOR,
                linecolor="#334155",
                tickfont=dict(size=11, color=_TEXT_COLOR),
            ),
        ),
        height=390,
        margin=dict(l=40, r=40, t=50, b=30),
        paper_bgcolor=_PAPER_BG,
        font=dict(color=_TEXT_COLOR),
        legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5),
    )
    return fig


def create_sensor_polar_and_cartesian_charts(
    targets: Sequence[TargetData],
    sweep_angle_deg: Optional[float] = None,
) -> Tuple[go.Figure, go.Figure]:
    """
    Adapter Kalıbı + Öneri E (Taktik PPI Radar Tarama Ekranı):
    Normalize edilmiş sensör hedeflerini hem 2B Kutupsal Radar PPI ekranında
    (Azimut ° / Menzil km, opsiyonel radar tarama hüzmesiyle) hem de 2B Kartezyen
    taktik düzlemde (Doğu X / Kuzey Y km, mesafe halkaları ve yön vektörleriyle) çizer.
    """
    polar_fig = go.Figure()
    cart_fig = go.Figure()

    # Opsiyonel PPI Radar Tarama Hüzmesi (Phosphor Green Sweep Sector)
    if sweep_angle_deg is not None:
        beam_angles = [
            (sweep_angle_deg - 28.0 + i * 2.8) % 360.0 for i in range(11)
        ]
        beam_r = [0.0] + [27.0 for _ in beam_angles] + [0.0]
        beam_theta = [sweep_angle_deg] + beam_angles + [sweep_angle_deg]
        polar_fig.add_trace(
            go.Scatterpolar(
                r=beam_r,
                theta=beam_theta,
                fill="toself",
                fillcolor="rgba(34, 197, 94, 0.16)",
                line=dict(color="rgba(34, 197, 94, 0.75)", width=1.5),
                name=f"📡 PPI Radar Hüzmesi ({sweep_angle_deg:.0f}°)",
                hoverinfo="name",
            )
        )

        # Kartezyen ekran üzerinde 10 km ve 20 km taktik mesafe halkaları
        ring_thetas = [math.radians(d) for d in range(0, 365, 6)]
        for ring_km in (10.0, 20.0):
            cart_fig.add_trace(
                go.Scatter(
                    x=[ring_km * math.cos(t) for t in ring_thetas],
                    y=[ring_km * math.sin(t) for t in ring_thetas],
                    mode="lines",
                    line=dict(color="rgba(34, 197, 94, 0.25)", width=1, dash="dot"),
                    name=f"Menzil Halkası ({ring_km:.0f} km)",
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    # İHA merkez noktası
    cart_fig.add_trace(
        go.Scatter(
            x=[0.0],
            y=[0.0],
            mode="markers+text",
            name="İHA Merkez Konumu",
            text=["🛸 İHA (0,0)"],
            textposition="bottom center",
            marker=dict(size=14, color="#38bdf8", symbol="triangle-up"),
        )
    )

    color_map = {
        "STANAG_4607_POLAR_LEGACY": "#22c55e",
        "VENDOR_EOIR_JSON_V2": "#f97316",
    }
    symbol_map = {
        "RADAR_EMITTER": "diamond-cross",
        "SURFACE_VEHICLE": "square",
        "AIR_TRACK": "triangle-up",
        "THERMAL_ANOMALY": "star",
    }

    for t in targets:
        col = (
            "#ef4444"
            if t.classification == "RADAR_EMITTER"
            else color_map.get(t.sensor_protocol, "#06b6d4")
        )
        sym = symbol_map.get(t.classification, "diamond")
        label = f"{t.target_id} ({t.classification}, Güven={t.confidence_score:.2f})"

        polar_fig.add_trace(
            go.Scatterpolar(
                r=[t.distance_km],
                theta=[t.bearing_deg],
                mode="markers+text",
                name=label,
                text=[f"{t.target_id}<br>{t.bearing_deg:.0f}°"],
                textposition="top center",
                marker=dict(
                    size=13,
                    color=col,
                    symbol=sym,
                    line=dict(width=1.5, color="#ffffff"),
                ),
            )
        )

        if sweep_angle_deg is not None:
            # İHA merkezinden hedefe taktik kerteriz/vektör çizgisi
            cart_fig.add_trace(
                go.Scatter(
                    x=[0.0, t.cartesian_x_km],
                    y=[0.0, t.cartesian_y_km],
                    mode="lines",
                    line=dict(color=col, width=1.2, dash="dot"),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

        cart_fig.add_trace(
            go.Scatter(
                x=[t.cartesian_x_km],
                y=[t.cartesian_y_km],
                mode="markers+text",
                name=label,
                text=[f"{t.target_id}<br>({t.altitude_m:.0f}m | %{t.confidence_score*100:.0f})"],
                textposition="top center",
                marker=dict(
                    size=13,
                    color=col,
                    symbol=sym,
                    line=dict(width=1.5, color="#ffffff"),
                ),
            )
        )

    polar_fig.update_layout(
        title="📡 Taktik PPI Kutupsal Radar Ekranı (Azimut ° / Menzil km)",
        polar=dict(
            bgcolor="#071318",
            angularaxis=dict(
                direction="clockwise",
                rotation=90,
                gridcolor="#134e4a",
                linecolor="#0d9488",
            ),
            radialaxis=dict(
                range=[0, 28],
                gridcolor="#134e4a",
                ticksuffix=" km",
            ),
        ),
        height=400,
        margin=dict(l=30, r=30, t=50, b=30),
        paper_bgcolor=_PAPER_BG,
        font=dict(color=_TEXT_COLOR),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    )

    cart_fig.update_layout(
        title="🎯 2B Kartezyen Normalize Hedef Haritası (Doğu X / Kuzey Y)",
        xaxis=dict(title="Doğu - Batı X (km)", range=[-28, 28], gridcolor=_GRID_COLOR, zerolinecolor="#475569"),
        yaxis=dict(
            title="Kuzey - Güney Y (km)",
            range=[-28, 28],
            gridcolor=_GRID_COLOR,
            zerolinecolor="#475569",
            scaleanchor="x",
            scaleratio=1,
        ),
        height=400,
        margin=dict(l=30, r=30, t=50, b=30),
        paper_bgcolor=_PAPER_BG,
        plot_bgcolor=_DARK_BG,
        font=dict(color=_TEXT_COLOR),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    )

    return polar_fig, cart_fig


def create_flir_thermal_view_chart(
    target: TargetData,
    polarity: str = "WHOT",
) -> go.Figure:
    """
    Öneri E — Sentetik EO/IR Termal Kamera Vizörü (FLIR Targeting Pod HUD):
    Seçilen `TargetData` hedefi için 2B kızılötesi ısı imzası matrisi (`Heatmap`),
    lazer nişangâh artı kılı (crosshair reticle), kilitlenme kutusu (tracking box)
    ve ekran üstü telemetri (OSD) verilerini çizer.
    """
    grid_coords = [round(-15.0 + i * 1.0, 1) for i in range(31)]

    # Ham veriden Kelvin sıcaklığı varsa oku, yoksa güven skorundan sentetik pik sıcaklık üret
    peak_temp_c = 78.0
    if isinstance(target.raw_payload, dict) and "hotspot" in target.raw_payload:
        raw_k = float(target.raw_payload["hotspot"].get("peak_temp_kelvin", 351.15))
        peak_temp_c = round(raw_k - 273.15, 1)
    else:
        peak_temp_c = round(35.0 + target.confidence_score * 55.0, 1)

    ambient_temp_c = 18.0
    sigma = 2.6 if target.classification != "RADAR_EMITTER" else 3.2

    z_matrix: List[List[float]] = []
    for y_val in grid_coords:
        row: List[float] = []
        for x_val in grid_coords:
            dist_sq = (x_val ** 2) + (y_val ** 2)
            # Merkez ısı çekirdeği + ikincil egzoz/motor uzantısı + hafif arka plan dokusu
            core_heat = (peak_temp_c - ambient_temp_c) * math.exp(-dist_sq / (2.0 * (sigma ** 2)))
            plume_heat = (
                (peak_temp_c - ambient_temp_c)
                * 0.35
                * math.exp(-(((x_val - 1.8) ** 2) + ((y_val + 1.2) ** 2)) / 6.5)
            )
            bg_texture = 1.8 * math.sin(x_val * 0.65) * math.cos(y_val * 0.65)
            row.append(round(ambient_temp_c + core_heat + plume_heat + bg_texture, 2))
        z_matrix.append(row)

    colorscale = "Hot" if polarity == "WHOT" else "Greys"
    reticle_color = "#22c55e" if target.confidence_score >= 0.75 else "#f59e0b"

    fig = go.Figure()
    fig.add_trace(
        go.Heatmap(
            x=grid_coords,
            y=grid_coords,
            z=z_matrix,
            colorscale=colorscale,
            colorbar=dict(title="°C", thickness=14),
            hovertemplate="Azimut Sapma: %{x} mrad<br>Elevasyon Sapma: %{y} mrad<br>Sıcaklık: %{z:.1f} °C<extra></extra>",
        )
    )

    # FLIR Nişangâh Artı Kılı (Crosshair) ve Kilitlenme Çerçevesi (Lock Box)
    reticle_segments = [
        ([-12.0, -2.5], [0.0, 0.0]),
        ([2.5, 12.0], [0.0, 0.0]),
        ([0.0, 0.0], [-12.0, -2.5]),
        ([0.0, 0.0], [2.5, 12.0]),
        # Köşe kilit braketleri
        ([-4.2, -4.2, -2.6], [2.6, 4.2, 4.2]),
        ([2.6, 4.2, 4.2], [4.2, 4.2, 2.6]),
        ([-4.2, -4.2, -2.6], [-2.6, -4.2, -4.2]),
        ([2.6, 4.2, 4.2], [-4.2, -4.2, -2.6]),
    ]
    for rx, ry in reticle_segments:
        fig.add_trace(
            go.Scatter(
                x=rx,
                y=ry,
                mode="lines",
                line=dict(color=reticle_color, width=2.2),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # FLIR HUD Ekran Üstü Telemetri (OSD Annotations)
    osd_annotations = [
        dict(
            x=-14.2,
            y=13.8,
            text=f"<b>FLIR {polarity} | 4.0X | {target.sensor_protocol[:16]}</b>",
            showarrow=False,
            xanchor="left",
            font=dict(color=reticle_color, size=11, family="Consolas, monospace"),
            bgcolor="rgba(9, 13, 22, 0.72)",
        ),
        dict(
            x=14.2,
            y=13.8,
            text=f"<b>LOCK: {target.target_id} [{target.classification}]</b>",
            showarrow=False,
            xanchor="right",
            font=dict(color=reticle_color, size=11, family="Consolas, monospace"),
            bgcolor="rgba(9, 13, 22, 0.72)",
        ),
        dict(
            x=-14.2,
            y=-13.8,
            text=f"<b>LRF: {target.distance_km:.2f} KM | ALT: {target.altitude_m:.0f} M | T-MAX: {peak_temp_c:.1f}°C</b>",
            showarrow=False,
            xanchor="left",
            font=dict(color=reticle_color, size=11, family="Consolas, monospace"),
            bgcolor="rgba(9, 13, 22, 0.72)",
        ),
        dict(
            x=14.2,
            y=-13.8,
            text=f"<b>AZ: {target.bearing_deg:05.1f}° | CONF: %{target.confidence_score*100:.0f}</b>",
            showarrow=False,
            xanchor="right",
            font=dict(color=reticle_color, size=11, family="Consolas, monospace"),
            bgcolor="rgba(9, 13, 22, 0.72)",
        ),
    ]

    fig.update_layout(
        title=f"🔭 EO/IR Termal Kamera Nişangâh Vizörü (FLIR HUD — {target.target_id})",
        xaxis=dict(
            title="Gimbal Azimut Sapması (mrad)",
            range=[-15, 15],
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            title="Gimbal Elevasyon Sapması (mrad)",
            range=[-15, 15],
            showgrid=False,
            zeroline=False,
            scaleanchor="x",
            scaleratio=1,
        ),
        annotations=osd_annotations,
        height=400,
        margin=dict(l=25, r=25, t=50, b=30),
        paper_bgcolor=_PAPER_BG,
        plot_bgcolor=_DARK_BG,
        font=dict(color=_TEXT_COLOR),
    )
    return fig


def create_telemetry_stage_size_chart(packet: TelemetryPacketResult) -> go.Figure:
    """
    Decorator Kalıbı: Telemetri mesajının her bir sarmalayıcı katmandan geçerken
    sahip olduğu bayt boyutunu adım adım karşılaştırır.
    """
    labels = ["Ham Mesaj"] + [
        f"Adım {s.step_index}: {s.layer_name}" for s in packet.stages
    ]
    sizes = [packet.original_size_bytes] + [s.output_size_bytes for s in packet.stages]
    colors = ["#64748b"] + ["#06b6d4", "#10b981", "#8b5cf6", "#f59e0b"][: len(packet.stages)]

    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=sizes,
                marker_color=colors,
                text=[f"{sz} Bayt" for sz in sizes],
                textposition="outside",
            )
        ]
    )
    max_y = max(sizes) * 1.25 if sizes else 100
    fig.update_layout(
        title="Decorator Zinciri Boyunca Paket Boyutu Değişimi (Bayt)",
        xaxis_title="İşleme Aşaması (İçten Dışa)",
        yaxis_title="Boyut (Bayt)",
        yaxis=dict(range=[0, max_y], gridcolor=_GRID_COLOR),
        xaxis=dict(gridcolor=_GRID_COLOR),
        height=320,
        margin=dict(l=30, r=30, t=50, b=30),
        paper_bgcolor=_PAPER_BG,
        plot_bgcolor=_DARK_BG,
        font=dict(color=_TEXT_COLOR),
    )
    return fig


def create_rf_spectrum_chart(
    frequency_band: str,
    active_layers: Sequence[str],
    jamming_active: bool = True,
    jamming_intensity_db: float = 20.0,
) -> go.Figure:
    """
    Öneri F — Elektronik Harp (EW) RF Frekans Spektrum Analizörü:
    Seçilen veri bağı frekans bandında taşıyıcı telemetri sinyal gücünü (`dBm`),
    termal gürültü tabanını, düşman elektronik karıştırma (jamming) darbelerini ve
    `AntiJammingDecorator` aktifken frekans atlamalı (`FHSS`) yedek taşıyıcılar ile
    FEC kazancının bağlantıyı nasıl ayakta tuttuğunu görselleştirir.
    """
    band_cfg = {
        "SATCOM-Ku": (14250.0, 50.0, "MHz"),
        "UHF-433MHz": (433.5, 6.0, "MHz"),
        "L-Band-Tactical": (1350.0, 40.0, "MHz"),
        "S-Band-LOS": (2250.0, 40.0, "MHz"),
    }
    center_f, half_span, unit = band_cfg.get(frequency_band, (14250.0, 50.0, "MHz"))

    has_antijam = "AntiJammingDecorator" in active_layers
    has_aes = "AesEncryptionDecorator" in active_layers

    n_pts = 160
    freqs = [
        round(center_f - half_span + (2.0 * half_span * i / (n_pts - 1)), 2)
        for i in range(n_pts)
    ]

    noise_floor_dbm = -96.0
    carrier_peak_dbm = -48.0
    sigma_main = half_span * 0.085

    signal_dbm: List[float] = []
    jammer_dbm: List[float] = []

    hop1_f = center_f - half_span * 0.42
    hop2_f = center_f + half_span * 0.46
    sigma_hop = half_span * 0.065

    for idx, f in enumerate(freqs):
        # Sentetik gürültü tabanı dalgalanması
        ripple = 1.6 * math.sin(idx * 0.7) + 1.1 * math.cos(idx * 1.9)
        base_n = noise_floor_dbm + ripple

        # Ana taşıyıcı sinyal lobu
        main_lobe = (carrier_peak_dbm - noise_floor_dbm) * math.exp(
            -((f - center_f) ** 2) / (2.0 * (sigma_main ** 2))
        )

        # AntiJammingDecorator aktifse FHSS frekans atlama yedek kanalları oluştur
        fhss_lobe = 0.0
        if has_antijam:
            lobe_a = (carrier_peak_dbm - 4.0 - noise_floor_dbm) * math.exp(
                -((f - hop1_f) ** 2) / (2.0 * (sigma_hop ** 2))
            )
            lobe_b = (carrier_peak_dbm - 3.0 - noise_floor_dbm) * math.exp(
                -((f - hop2_f) ** 2) / (2.0 * (sigma_hop ** 2))
            )
            fhss_lobe = max(lobe_a, lobe_b)

        sig_val = round(base_n + max(main_lobe, fhss_lobe), 2)
        signal_dbm.append(sig_val)

        # Düşman Elektronik Karıştırma (Jamming) Darbesi
        if jamming_active:
            jam_peak = -66.0 + jamming_intensity_db  # ör. -46 dBm (taşıyıcıyı bastıran darbe)
            jam_sigma = half_span * 0.13
            jam_lobe = max(
                0.0,
                (jam_peak - noise_floor_dbm)
                * math.exp(-((f - (center_f + half_span * 0.04)) ** 2) / (2.0 * (jam_sigma ** 2))),
            )
            jammer_dbm.append(round(base_n + jam_lobe, 2))
        else:
            jammer_dbm.append(round(base_n, 2))

    # Demodülasyon eşiği (AntiJamming FEC aktifse alıcı eşiği -72 dBm'e kadar esner)
    demod_threshold = -72.0 if has_antijam else -60.0
    link_status = (
        "🟢 BAĞLANTI GÜVENDE (FHSS + FEC AKTİF)"
        if (has_antijam or not jamming_active)
        else "🔴 KARIŞTIRMA ALTINDA (PAKET KAYBI RİSKİ)"
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=freqs,
            y=signal_dbm,
            mode="lines",
            fill="tozeroy",
            fillcolor="rgba(6, 182, 212, 0.22)",
            line=dict(color="#06b6d4", width=2.5),
            name=(
                f"📡 Telemetri Sinyali ({'FHSS + AES' if (has_antijam and has_aes) else ('FHSS Korumalı' if has_antijam else 'Tek Taşıyıcı')})"
            ),
        )
    )

    if jamming_active:
        fig.add_trace(
            go.Scatter(
                x=freqs,
                y=jammer_dbm,
                mode="lines",
                fill="tozeroy",
                fillcolor="rgba(239, 68, 68, 0.26)",
                line=dict(color="#ef4444", width=2.2, dash="dash"),
                name=f"⚡ EW Elektronik Karıştırma Darbesi (+{jamming_intensity_db:.0f} dB)",
            )
        )

    fig.add_hline(
        y=demod_threshold,
        line_width=2,
        line_dash="dot",
        line_color="#22c55e" if has_antijam else "#f59e0b",
        annotation_text=(
            f"Alıcı Demodülasyon Eşiği: {demod_threshold:.0f} dBm "
            f"({'FEC Kazancı +12 dB' if has_antijam else 'Standart'})"
        ),
        annotation_position="top right",
        annotation_font_color="#86efac" if has_antijam else "#fde047",
    )

    fig.update_layout(
        title=f"📶 RF Spektrum Analizörü ({frequency_band}) — {link_status}",
        xaxis=dict(title=f"Frekans ({unit})", gridcolor=_GRID_COLOR),
        yaxis=dict(title="Sinyal Gücü (dBm)", range=[-105, -28], gridcolor=_GRID_COLOR),
        height=340,
        margin=dict(l=30, r=30, t=50, b=30),
        paper_bgcolor=_PAPER_BG,
        plot_bgcolor=_DARK_BG,
        font=dict(color=_TEXT_COLOR),
        legend=dict(orientation="h", yanchor="bottom", y=-0.26, xanchor="center", x=0.5),
    )
    return fig


def create_flight_dynamics_chart(controller: FlightController) -> go.Figure:
    """
    State Kalıbı: Uçuş kontrolcüsünün durum geçiş geçmişindeki irtifa (m),
    hız (knot) ve motor itkisi (%) değişimini görselleştirir.
    """
    history = controller.get_transition_history()
    accepted_steps = [h for h in history if h.accepted]

    if not accepted_steps:
        steps_x = ["Başlangıç (PREFLIGHT_IDLE)"]
        altitudes = [controller.altitude_m]
        speeds = [controller.speed_knots]
        throttles = [controller.throttle_pct]
    else:
        steps_x = ["0: IDLE"] + [
            f"{idx + 1}: {item.current_phase}" for idx, item in enumerate(accepted_steps)
        ]
        altitudes = [0.0] + [item.altitude_m for item in accepted_steps]
        speeds = [0.0] + [item.speed_knots for item in accepted_steps]
        throttles = [12.0] + [item.throttle_pct for item in accepted_steps]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=steps_x,
            y=altitudes,
            mode="lines+markers",
            name="İrtifa (m)",
            line=dict(color="#38bdf8", width=3),
            marker=dict(size=9),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=steps_x,
            y=speeds,
            mode="lines+markers",
            name="Hız (knot)",
            yaxis="y2",
            line=dict(color="#22c55e", width=2.5, dash="dot"),
            marker=dict(size=8),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=steps_x,
            y=throttles,
            mode="lines+markers",
            name="Motor İtkisi (%)",
            yaxis="y2",
            line=dict(color="#f59e0b", width=2.5),
            marker=dict(size=8),
        )
    )

    fig.update_layout(
        title="Uçuş Fazı Geçişlerine Göre İrtifa, Hız ve Motor Tepkisi",
        xaxis=dict(title="Durum Geçiş Adımı", gridcolor=_GRID_COLOR),
        yaxis=dict(title="İrtifa (m)", range=[-200, 7000], gridcolor=_GRID_COLOR),
        yaxis2=dict(
            title="Hız (kts) / Motor (%)",
            overlaying="y",
            side="right",
            range=[0, 200],
            showgrid=False,
        ),
        height=340,
        margin=dict(l=30, r=30, t=50, b=30),
        paper_bgcolor=_PAPER_BG,
        plot_bgcolor=_DARK_BG,
        font=dict(color=_TEXT_COLOR),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
    )
    return fig


def create_route_map_2d_chart(
    route_plans: Sequence[RoutePlan],
    restricted_zones: Sequence[RestrictedZone],
    active_strategy_name: Optional[str] = None,
    uav_position: Optional[Point2D] = None,
    uav_heading_deg: Optional[float] = None,
    flight_trail: Optional[Sequence[Point2D]] = None,
    sensor_fov_range_km: float = 18.0,
    sensor_fov_half_angle_deg: float = 28.0,
    detected_targets: Optional[Sequence[TargetData]] = None,
) -> go.Figure:
    """
    Strategy Kalıbı + Canlı İHA Takibi:
    2B sentetik harita (100x100 km) üzerinde dairesel kısıtlı bölgeleri, seçilen
    rotaları, İHA'nın kat ettiği uçuş izini (`flight_trail`), ileri yönlü sensör
    tarama konisini (`FOV cone`), anlık İHA konumunu/yönünü ve algılanan hedefleri çizer.
    """
    fig = go.Figure()

    # 0. Taktik Sektör Kılavuz Çizgileri (Quadrant Grid)
    fig.add_vline(x=50.0, line_width=1, line_dash="dot", line_color="#334155")
    fig.add_hline(y=50.0, line_width=1, line_dash="dot", line_color="#334155")

    # 1. Kısıtlı Bölgeleri (RestrictedZone) dış erken-ihbar halkası + iç yasak bölge olarak çiz
    for zone in restricted_zones:
        theta_vals = [math.radians(deg) for deg in range(0, 365, 5)]
        outer_r = round(zone.radius_km * 1.22, 1)
        ox = [zone.center.x_km + outer_r * math.cos(t) for t in theta_vals]
        oy = [zone.center.y_km + outer_r * math.sin(t) for t in theta_vals]
        fig.add_trace(
            go.Scatter(
                x=ox,
                y=oy,
                mode="lines",
                line=dict(color="rgba(245, 158, 11, 0.55)", width=1.2, dash="dot"),
                name=f"Radar İhbar Halkası: {zone.zone_id} ({outer_r} km)",
                showlegend=False,
                hoverinfo="name",
            )
        )

        zx = [zone.center.x_km + zone.radius_km * math.cos(t) for t in theta_vals]
        zy = [zone.center.y_km + zone.radius_km * math.sin(t) for t in theta_vals]

        fig.add_trace(
            go.Scatter(
                x=zx,
                y=zy,
                fill="toself",
                fillcolor="rgba(239, 68, 68, 0.22)",
                line=dict(color="#ef4444", width=2, dash="dash"),
                name=f"Kısıtlı Bölge: {zone.zone_id} (R={zone.radius_km} km)",
                hoverinfo="name",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[zone.center.x_km],
                y=[zone.center.y_km],
                mode="markers+text",
                text=[f"⚠️ {zone.zone_id}"],
                textposition="middle center",
                marker=dict(size=8, color="#ef4444", symbol="x"),
                showlegend=False,
            )
        )

    style_map = {
        "SHORTEST_PATH": {"color": "#f43f5e", "dash": "dot"},
        "RADAR_EVASION": {"color": "#10b981", "dash": "solid"},
        "LOITERING_SEARCH": {"color": "#38bdf8", "dash": "dashdot"},
    }

    # 2. Rota Planlarını Çiz
    for plan in route_plans:
        st_cfg = style_map.get(plan.strategy_name, {"color": "#a855f7", "dash": "solid"})
        is_highlighted = (
            active_strategy_name is None or plan.strategy_name == active_strategy_name
        )
        line_width = 3.5 if is_highlighted else 2.0
        opacity = 0.85 if is_highlighted else 0.45

        xs = [wp.x_km for wp in plan.waypoints]
        ys = [wp.y_km for wp in plan.waypoints]
        labels = [wp.label for wp in plan.waypoints]

        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines+markers+text" if is_highlighted else "lines+markers",
                name=f"{plan.strategy_title} ({plan.total_distance_km} km)",
                text=labels if is_highlighted else None,
                textposition="top center",
                opacity=opacity,
                line=dict(color=st_cfg["color"], width=line_width, dash=st_cfg["dash"]),
                marker=dict(size=8 if is_highlighted else 6, color=st_cfg["color"]),
            )
        )

    # 3. Başlangıç ve Hedef Noktalarını Vurgula
    if route_plans and route_plans[0].waypoints:
        start_pt = route_plans[0].waypoints[0]
        end_pt = route_plans[0].waypoints[-1]
        fig.add_trace(
            go.Scatter(
                x=[start_pt.x_km],
                y=[start_pt.y_km],
                mode="markers",
                name="Kalkış Üssü (Start)",
                marker=dict(size=15, color="#22c55e", symbol="star"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[end_pt.x_km],
                y=[end_pt.y_km],
                mode="markers",
                name="Görev Hedefi (Target)",
                marker=dict(size=15, color="#eab308", symbol="diamond-tall"),
            )
        )

    # 4. Kat Edilen Uçuş İzi (Flight Trail / Breadcrumb)
    if flight_trail and len(flight_trail) >= 2:
        trail_x = [pt.x_km for pt in flight_trail]
        trail_y = [pt.y_km for pt in flight_trail]
        fig.add_trace(
            go.Scatter(
                x=trail_x,
                y=trail_y,
                mode="lines+markers",
                name="✈️ Kat Edilen Uçuş İzi (Flight Trail)",
                line=dict(color="#f59e0b", width=4.0),
                marker=dict(size=6, color="#fbbf24", symbol="circle"),
            )
        )

    # 5. Canlı İHA Konumu, Yön Vektörü ve İleri Sensör Tarama Konisi (FOV Cone)
    if uav_position is not None:
        hdg = uav_heading_deg if uav_heading_deg is not None else 45.0

        # Sensör Tarama Konisi (FOV Sector)
        cone_angles = [
            hdg - sensor_fov_half_angle_deg + (i * (2.0 * sensor_fov_half_angle_deg) / 20.0)
            for i in range(21)
        ]
        cone_x = [uav_position.x_km] + [
            uav_position.x_km + sensor_fov_range_km * math.sin(math.radians(a))
            for a in cone_angles
        ] + [uav_position.x_km]
        cone_y = [uav_position.y_km] + [
            uav_position.y_km + sensor_fov_range_km * math.cos(math.radians(a))
            for a in cone_angles
        ] + [uav_position.y_km]

        fig.add_trace(
            go.Scatter(
                x=cone_x,
                y=cone_y,
                fill="toself",
                fillcolor="rgba(56, 189, 248, 0.17)",
                line=dict(color="rgba(56, 189, 248, 0.65)", width=1.5, dash="dot"),
                name=f"📡 Sensör Tarama Konisi (FOV {sensor_fov_range_km:.0f} km)",
                hoverinfo="name",
            )
        )

        # Algılanan Sensör Hedeflerini İHA Konumuna Göre Harita Üzerinde Göster
        if detected_targets:
            tgt_x = [
                min(102.0, max(2.0, round(uav_position.x_km + t.cartesian_x_km * 0.55, 2)))
                for t in detected_targets
            ]
            tgt_y = [
                min(102.0, max(2.0, round(uav_position.y_km + t.cartesian_y_km * 0.55, 2)))
                for t in detected_targets
            ]
            tgt_labels = [f"🎯 {t.target_id}" for t in detected_targets]
            fig.add_trace(
                go.Scatter(
                    x=tgt_x,
                    y=tgt_y,
                    mode="markers+text",
                    name="🎯 Algılanan Sensör İzleri",
                    text=tgt_labels,
                    textposition="bottom center",
                    marker=dict(
                        size=11,
                        color="#f97316",
                        symbol="cross-thin",
                        line=dict(width=2.5, color="#fb923c"),
                    ),
                )
            )

        # Canlı İHA Sembolü (Pusula açısına göre döndürülmüş üçgen)
        fig.add_trace(
            go.Scatter(
                x=[uav_position.x_km],
                y=[uav_position.y_km],
                mode="markers+text",
                name=f"🛸 Aktif İHA ({uav_position.x_km:.1f}, {uav_position.y_km:.1f})",
                text=[f"🛸 İHA ({hdg:.0f}°)"],
                textposition="bottom right",
                textfont=dict(color="#38bdf8", size=12),
                marker=dict(
                    size=17,
                    color="#38bdf8",
                    symbol="triangle-up",
                    angle=hdg,
                    line=dict(width=2, color="#ffffff"),
                ),
            )
        )

    fig.update_layout(
        title="2B Sentetik Görev Haritası, Canlı İHA Konumu ve Sensör FOV Simülasyonu (100x100 km)",
        xaxis=dict(title="Doğu X Koordinatı (km)", range=[0, 105], gridcolor=_GRID_COLOR),
        yaxis=dict(
            title="Kuzey Y Koordinatı (km)",
            range=[0, 105],
            gridcolor=_GRID_COLOR,
            scaleanchor="x",
            scaleratio=1,
        ),
        height=540,
        margin=dict(l=30, r=30, t=50, b=30),
        paper_bgcolor=_PAPER_BG,
        plot_bgcolor=_DARK_BG,
        font=dict(color=_TEXT_COLOR),
        legend=dict(orientation="h", yanchor="bottom", y=-0.24, xanchor="center", x=0.5),
    )
    return fig


def _synthetic_terrain_elevation_m(distance_km: float, total_dist_km: float) -> float:
    """Rota mesafesi boyunca gerçekçi sentetik arazi yükselti profili (metre MSL) üretir."""
    if total_dist_km <= 0.0:
        return 180.0
    ratio = distance_km / total_dist_km
    hill_1 = 420.0 * math.sin(ratio * math.pi)
    ridge_2 = 240.0 * (math.sin(ratio * 3.2 * math.pi) ** 2)
    detail = 75.0 * math.cos(ratio * 7.0 * math.pi)
    return round(max(120.0, 210.0 + hill_1 + ridge_2 + detail), 1)


def _compute_waypoint_profile(
    plan: RoutePlan,
) -> Tuple[List[float], List[float], List[str]]:
    """
    Bir `RoutePlan` içindeki waypoint'ler için:
    - Kümülatif mesafe listesini (`km`)
    - Her waypoint'teki planlanan irtifayı (`m`)
    - Waypoint etiketlerini döndürür.
    """
    wps = plan.waypoints
    if not wps:
        return [0.0], [0.0], ["Başlangıç"]

    cum_dists: List[float] = [0.0]
    for i in range(1, len(wps)):
        cum_dists.append(round(cum_dists[-1] + wps[i - 1].distance_to(wps[i]), 2))

    rec_alt = plan.recommended_altitude_m
    altitudes: List[float] = []
    labels: List[str] = []
    n_wps = len(wps)

    for idx, wp in enumerate(wps):
        labels.append(wp.label or f"WP-{idx + 1}")
        if idx == 0:
            altitudes.append(220.0)  # Kalkış pisti / Başlangıç irtifası
        elif idx == n_wps - 1:
            altitudes.append(round(max(1100.0, rec_alt * 0.80), 0))  # Görev/Hedef yaklaşma irtifası
        else:
            altitudes.append(rec_alt)

    # Eğer sadece 2 nokta varsa (ör. ShortestPathStrategy), tırmanış ve alçalış omuz noktaları ekle
    if len(cum_dists) == 2 and cum_dists[-1] > 10.0:
        total_d = cum_dists[-1]
        cum_dists = [
            0.0,
            round(total_d * 0.14, 2),
            round(total_d * 0.85, 2),
            total_d,
        ]
        altitudes = [
            220.0,
            rec_alt,
            rec_alt,
            round(max(1100.0, rec_alt * 0.80), 0),
        ]
        labels = [
            wps[0].label or "Kalkış (Start)",
            "TOC (Tırmanış Sonu)",
            "TOD (Alçalış Başı)",
            wps[-1].label or "Hedef (Target)",
        ]

    return cum_dists, altitudes, labels


def create_altitude_profile_chart(
    route_plan: RoutePlan,
    distance_traveled_km: float = 0.0,
    current_altitude_m: float = 0.0,
    current_phase_name: str = "PREFLIGHT_IDLE",
) -> go.Figure:
    """
    Öneri C — Dikey Durum Göstergesi (Vertical Situation Display / Altitude Profile):
    Rota mesafesi boyunca sentetik arazi yükselti kesitini, minimum güvenli irtifa (MSA)
    sınırını, seçilen stratejinin önerdiği dikey uçuş zarfını ve İHA'nın anlık irtifa/mesafe
    konumunu çizer.
    """
    fig = go.Figure()
    total_dist = max(10.0, route_plan.total_distance_km)

    # 1. Sentetik Arazi Kesiti ve Minimum Güvenli İrtifa (MSA)
    sample_count = 60
    dist_samples = [round((i / sample_count) * total_dist, 2) for i in range(sample_count + 1)]
    terrain_m = [_synthetic_terrain_elevation_m(d, total_dist) for d in dist_samples]
    msa_m = [round(t + 380.0, 1) for t in terrain_m]

    fig.add_trace(
        go.Scatter(
            x=dist_samples,
            y=terrain_m,
            fill="tozeroy",
            fillcolor="rgba(71, 85, 105, 0.42)",
            line=dict(color="#64748b", width=2),
            name="⛰️ Arazi Yükselti Kesiti (MSL)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dist_samples,
            y=msa_m,
            mode="lines",
            line=dict(color="#ef4444", width=1.5, dash="dot"),
            name="⚠️ Min. Güvenli İrtifa (MSA +380m)",
        )
    )

    # 2. Planlanan Strateji Dikey Uçuş Profili
    wp_dists, wp_alts, wp_labels = _compute_waypoint_profile(route_plan)
    fig.add_trace(
        go.Scatter(
            x=wp_dists,
            y=wp_alts,
            mode="lines+markers+text",
            name=f"📐 Planlanan Dikey Profil ({route_plan.recommended_altitude_m:.0f} m)",
            text=[f"{lbl}<br>({alt:.0f}m)" for lbl, alt in zip(wp_labels, wp_alts)],
            textposition="top center",
            line=dict(color="#10b981", width=3, dash="solid"),
            marker=dict(size=9, color="#10b981", symbol="diamond"),
        )
    )

    # 3. Canlı İHA Dikey Konumu ve Yerden Yükseklik (AGL) İzdüşümü
    clamped_d = min(total_dist, max(0.0, distance_traveled_km))
    ground_below = _synthetic_terrain_elevation_m(clamped_d, total_dist)
    effective_alt = (
        max(ground_below, current_altitude_m)
        if current_phase_name != "PREFLIGHT_IDLE"
        else ground_below
    )
    agl_m = max(0.0, round(effective_alt - ground_below, 0))

    fig.add_trace(
        go.Scatter(
            x=[clamped_d, clamped_d],
            y=[ground_below, effective_alt],
            mode="lines",
            line=dict(color="#38bdf8", width=2, dash="dash"),
            name=f"📏 Yerden Yükseklik (AGL: {agl_m:.0f} m)",
            showlegend=True,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[clamped_d],
            y=[effective_alt],
            mode="markers+text",
            name=f"🛸 Aktif İHA İrtifası ({effective_alt:.0f} m MSL)",
            text=[f"🛸 İHA: {effective_alt:.0f} m MSL<br>(AGL: {agl_m:.0f} m)"],
            textposition="bottom right",
            textfont=dict(color="#38bdf8", size=12),
            marker=dict(
                size=15,
                color="#38bdf8",
                symbol="triangle-right",
                line=dict(width=2, color="#ffffff"),
            ),
        )
    )

    max_y = max(7200.0, route_plan.recommended_altitude_m * 1.22, effective_alt * 1.2)
    fig.update_layout(
        title=(
            f"⛰️ Dikey Uçuş ve Arazi Kesiti (Vertical Situation Display — {route_plan.strategy_title})"
        ),
        xaxis=dict(
            title="Rota Boyunca Kümülatif Mesafe (km)",
            range=[-2, total_dist * 1.05],
            gridcolor=_GRID_COLOR,
        ),
        yaxis=dict(
            title="İrtifa (Metre MSL)",
            range=[0, max_y],
            gridcolor=_GRID_COLOR,
        ),
        height=330,
        margin=dict(l=30, r=30, t=50, b=30),
        paper_bgcolor=_PAPER_BG,
        plot_bgcolor=_DARK_BG,
        font=dict(color=_TEXT_COLOR),
        legend=dict(orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5),
    )
    return fig


def create_route_map_3d_chart(
    route_plans: Sequence[RoutePlan],
    restricted_zones: Sequence[RestrictedZone],
    active_strategy_name: Optional[str] = None,
    uav_position: Optional[Point2D] = None,
    current_altitude_m: float = 0.0,
    flight_trail: Optional[Sequence[Point2D]] = None,
) -> go.Figure:
    """
    Öneri C — 3B Hava Sahası, 3B Uçuş Yörüngeleri ve 3B Kısıtlı Bölge Radar Kubbeleri (`Scatter3d` / `Surface`):
    100x100 km görev alanını 0–7000 m irtifa zarfıyla 3 boyutlu olarak görselleştirir.
    """
    fig = go.Figure()

    # 1. Kısıtlı Bölgeleri 3B Radar Tehdit Kubbesi / Silindiri olarak çiz
    dome_ceiling_m = 5200.0
    for zone in restricted_zones:
        theta_vals = [math.radians(deg) for deg in range(0, 365, 12)]
        for ring_alt, ring_alpha, show_leg in [
            (0.0, 0.9, True),
            (2600.0, 0.65, False),
            (dome_ceiling_m, 0.85, False),
        ]:
            rx = [zone.center.x_km + zone.radius_km * math.cos(t) for t in theta_vals]
            ry = [zone.center.y_km + zone.radius_km * math.sin(t) for t in theta_vals]
            rz = [ring_alt for _ in theta_vals]
            fig.add_trace(
                go.Scatter3d(
                    x=rx,
                    y=ry,
                    z=rz,
                    mode="lines",
                    name=f"⚠️ 3B Radar Kubbesi: {zone.zone_id} (Tavan: {dome_ceiling_m:.0f}m)",
                    showlegend=show_leg,
                    line=dict(
                        color=f"rgba(239, 68, 68, {ring_alpha})",
                        width=4 if ring_alt == 0.0 else 2.5,
                    ),
                )
            )

        # Dikey radar kubbe dikmeleri (3B hacim algısı için)
        pillar_x: List[Optional[float]] = []
        pillar_y: List[Optional[float]] = []
        pillar_z: List[Optional[float]] = []
        for deg in range(0, 360, 45):
            rad = math.radians(deg)
            px = zone.center.x_km + zone.radius_km * math.cos(rad)
            py = zone.center.y_km + zone.radius_km * math.sin(rad)
            pillar_x.extend([px, px, None])
            pillar_y.extend([py, py, None])
            pillar_z.extend([0.0, dome_ceiling_m, None])

        fig.add_trace(
            go.Scatter3d(
                x=pillar_x,
                y=pillar_y,
                z=pillar_z,
                mode="lines",
                line=dict(color="rgba(239, 68, 68, 0.40)", width=2),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    style_map = {
        "SHORTEST_PATH": {"color": "#f43f5e", "dash": "dot"},
        "RADAR_EVASION": {"color": "#10b981", "dash": "solid"},
        "LOITERING_SEARCH": {"color": "#38bdf8", "dash": "dashdot"},
    }

    # 2. 3B Rota Yörüngelerini Çiz
    for plan in route_plans:
        st_cfg = style_map.get(plan.strategy_name, {"color": "#a855f7", "dash": "solid"})
        is_highlighted = (
            active_strategy_name is None or plan.strategy_name == active_strategy_name
        )
        wps = plan.waypoints
        if not wps:
            continue

        xs = [wp.x_km for wp in wps]
        ys = [wp.y_km for wp in wps]
        rec_alt = plan.recommended_altitude_m
        zs = [
            220.0
            if i == 0
            else (round(max(1100.0, rec_alt * 0.80), 0) if i == len(wps) - 1 else rec_alt)
            for i in range(len(wps))
        ]
        # Eğer sadece 2 nokta varsa (ShortestPathStrategy), orta noktada seyir irtifasını göster
        if len(wps) == 2:
            mid_x = round((wps[0].x_km + wps[1].x_km) / 2.0, 2)
            mid_y = round((wps[0].y_km + wps[1].y_km) / 2.0, 2)
            xs = [wps[0].x_km, mid_x, wps[1].x_km]
            ys = [wps[0].y_km, mid_y, wps[1].y_km]
            zs = [220.0, rec_alt, round(max(1100.0, rec_alt * 0.80), 0)]

        fig.add_trace(
            go.Scatter3d(
                x=xs,
                y=ys,
                z=zs,
                mode="lines+markers",
                name=f"3B {plan.strategy_title} ({rec_alt:.0f} m)",
                opacity=1.0 if is_highlighted else 0.50,
                line=dict(color=st_cfg["color"], width=7 if is_highlighted else 4),
                marker=dict(size=5 if is_highlighted else 3, color=st_cfg["color"]),
            )
        )

        # Aktif rotanın yer izdüşümü dikmeleri (curtain lines)
        if is_highlighted:
            drop_x: List[Optional[float]] = []
            drop_y: List[Optional[float]] = []
            drop_z: List[Optional[float]] = []
            for vx, vy, vz in zip(xs, ys, zs):
                drop_x.extend([vx, vx, None])
                drop_y.extend([vy, vy, None])
                drop_z.extend([0.0, vz, None])
            fig.add_trace(
                go.Scatter3d(
                    x=drop_x,
                    y=drop_y,
                    z=drop_z,
                    mode="lines",
                    line=dict(color="rgba(148, 163, 184, 0.35)", width=1.5),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    # 3. 3B Canlı Uçuş İzi ve Anlık İHA Konumu
    uav_z = max(250.0, current_altitude_m)
    if flight_trail and len(flight_trail) >= 2:
        tx = [pt.x_km for pt in flight_trail]
        ty = [pt.y_km for pt in flight_trail]
        tz = [
            220.0 if idx == 0 else uav_z
            for idx in range(len(flight_trail))
        ]
        fig.add_trace(
            go.Scatter3d(
                x=tx,
                y=ty,
                z=tz,
                mode="lines+markers",
                name="✈️ 3B Kat Edilen Uçuş İzi",
                line=dict(color="#f59e0b", width=6),
                marker=dict(size=4, color="#fbbf24"),
            )
        )

    if uav_position is not None:
        fig.add_trace(
            go.Scatter3d(
                x=[uav_position.x_km],
                y=[uav_position.y_km],
                z=[uav_z],
                mode="markers+text",
                name=f"🛸 3B Aktif İHA ({uav_z:.0f} m)",
                text=[f"🛸 İHA ({uav_position.x_km:.0f}, {uav_position.y_km:.0f} km | {uav_z:.0f}m)"],
                textposition="top center",
                marker=dict(
                    size=9,
                    color="#38bdf8",
                    symbol="diamond",
                    line=dict(width=2, color="#ffffff"),
                ),
            )
        )

    fig.update_layout(
        title="🌐 3B Hava Sahası, Uçuş Yörüngeleri ve Kısıtlı Bölge Radar Kubbeleri",
        scene=dict(
            xaxis=dict(
                title="Doğu X (km)",
                range=[0, 105],
                backgroundcolor=_DARK_BG,
                gridcolor=_GRID_COLOR,
            ),
            yaxis=dict(
                title="Kuzey Y (km)",
                range=[0, 105],
                backgroundcolor=_DARK_BG,
                gridcolor=_GRID_COLOR,
            ),
            zaxis=dict(
                title="İrtifa Z (m MSL)",
                range=[0, 7000],
                backgroundcolor=_DARK_BG,
                gridcolor=_GRID_COLOR,
            ),
            camera=dict(eye=dict(x=1.45, y=-1.45, z=0.95)),
            aspectmode="manual",
            aspectratio=dict(x=1.2, y=1.2, z=0.65),
        ),
        height=560,
        margin=dict(l=10, r=10, t=50, b=20),
        paper_bgcolor=_PAPER_BG,
        font=dict(color=_TEXT_COLOR),
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5),
    )
    return fig
