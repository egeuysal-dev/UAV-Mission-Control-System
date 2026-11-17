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
