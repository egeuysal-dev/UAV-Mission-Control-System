"""
Plotly tabanlı 2B simülasyon grafikleri ve görselleştirme oluşturucuları.

İş mantığı nesnelerini (`UAVPlatform`, `TargetData`, `TelemetryPacketResult`,
`FlightController`, `RoutePlan`) alarak koyu temalı teknik Plotly figürleri üretir.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Sequence, Tuple

import plotly.graph_objects as go

from src.models.navigation_models import RestrictedZone, RoutePlan
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


def create_sensor_polar_and_cartesian_charts(
    targets: Sequence[TargetData],
) -> Tuple[go.Figure, go.Figure]:
    """
    Adapter Kalıbı: Normalize edilmiş sensör hedeflerini hem 2B Kutupsal Radar
    ekranında (Azimut ° / Menzil km) hem de 2B Kartezyen düzlemde (Doğu X / Kuzey Y km) çizer.
    """
    polar_fig = go.Figure()
    cart_fig = go.Figure()

    # İHA merkez noktası
    cart_fig.add_trace(
        go.Scatter(
            x=[0.0],
            y=[0.0],
            mode="markers+text",
            name="İHA Merkez Konumu",
            text=["İHA (0,0)"],
            textposition="bottom center",
            marker=dict(size=14, color="#38bdf8", symbol="triangle-up"),
        )
    )

    color_map = {
        "STANAG_4607_POLAR_LEGACY": "#22c55e",
        "VENDOR_EOIR_JSON_V2": "#f97316",
    }

    for t in targets:
        col = color_map.get(t.sensor_protocol, "#06b6d4")
        label = f"{t.target_id} ({t.classification}, Güven={t.confidence_score:.2f})"

        polar_fig.add_trace(
            go.Scatterpolar(
                r=[t.distance_km],
                theta=[t.bearing_deg],
                mode="markers+text",
                name=label,
                text=[t.target_id],
                textposition="top center",
                marker=dict(size=13, color=col, line=dict(width=1.5, color="#ffffff")),
            )
        )

        cart_fig.add_trace(
            go.Scatter(
                x=[t.cartesian_x_km],
                y=[t.cartesian_y_km],
                mode="markers+text",
                name=label,
                text=[f"{t.target_id}<br>({t.altitude_m:.0f}m)"],
                textposition="top center",
                marker=dict(size=13, color=col, symbol="diamond"),
            )
        )

    polar_fig.update_layout(
        title="2B Kutupsal Sensör Ekranı (Derece / km)",
        polar=dict(
            bgcolor=_DARK_BG,
            angularaxis=dict(
                direction="clockwise",
                rotation=90,
                gridcolor=_GRID_COLOR,
                linecolor="#334155",
            ),
            radialaxis=dict(
                range=[0, 28],
                gridcolor=_GRID_COLOR,
                ticksuffix=" km",
            ),
        ),
        height=380,
        margin=dict(l=30, r=30, t=50, b=30),
        paper_bgcolor=_PAPER_BG,
        font=dict(color=_TEXT_COLOR),
        showlegend=True,
    )

    cart_fig.update_layout(
        title="2B Kartezyen Normalize Hedef Haritası (Doğu X / Kuzey Y)",
        xaxis=dict(title="Doğu - Batı X (km)", range=[-28, 28], gridcolor=_GRID_COLOR, zerolinecolor="#475569"),
        yaxis=dict(title="Kuzey - Güney Y (km)", range=[-28, 28], gridcolor=_GRID_COLOR, zerolinecolor="#475569"),
        height=380,
        margin=dict(l=30, r=30, t=50, b=30),
        paper_bgcolor=_PAPER_BG,
        plot_bgcolor=_DARK_BG,
        font=dict(color=_TEXT_COLOR),
        showlegend=True,
    )

    return polar_fig, cart_fig


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
) -> go.Figure:
    """
    Strategy Kalıbı: 2B sentetik harita (100x100 km) üzerinde dairesel kısıtlı
    bölgeleri ve seçilen/karşılaştırılan stratejilerin ürettiği 2B rotaları çizer.
    """
    fig = go.Figure()

    # 1. Kısıtlı Bölgeleri (RestrictedZone) daire olarak çiz
    for zone in restricted_zones:
        theta_vals = [math.radians(deg) for deg in range(0, 365, 5)]
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
        line_width = 4.0 if is_highlighted else 2.0
        opacity = 1.0 if is_highlighted else 0.55

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
                marker=dict(size=9 if is_highlighted else 6, color=st_cfg["color"]),
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

    fig.update_layout(
        title="2B Sentetik Görev Haritası ve Rota Karşılaştırması (100x100 km)",
        xaxis=dict(title="Doğu X Koordinatı (km)", range=[0, 105], gridcolor=_GRID_COLOR),
        yaxis=dict(
            title="Kuzey Y Koordinatı (km)",
            range=[0, 105],
            gridcolor=_GRID_COLOR,
            scaleanchor="x",
            scaleratio=1,
        ),
        height=520,
        margin=dict(l=30, r=30, t=50, b=30),
        paper_bgcolor=_PAPER_BG,
        plot_bgcolor=_DARK_BG,
        font=dict(color=_TEXT_COLOR),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
    )
    return fig
