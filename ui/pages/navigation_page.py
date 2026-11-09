"""
Ekran 6: Navigation — GoF Strategy Kalıbı ile Değişken Güdüm ve 2B Rota Planlama.
"""

from __future__ import annotations

import streamlit as st

from src.models.navigation_models import Point2D, RestrictedZone
from src.patterns.strategy import (
    LoiteringSearchStrategy,
    RadarEvasionStrategy,
    ShortestPathStrategy,
)
from src.simulation.mission_simulator import MissionSimulator
from ui.components.charts import create_route_map_2d_chart
from ui.components.theme import render_pattern_header


def render_navigation_page(sim: MissionSimulator) -> None:
    """Strategy tasarım kalıbı rota planlama ve 2B harita karşılaştırma ekranını çizer."""
    render_pattern_header(
        badge="5. STRATEGY KALIBI — DAVRANIŞSAL (BEHAVIORAL)",
        title="Dinamik Rota Planlama Algoritmaları ve 2B Sentetik Harita Simülasyonu",
        problem_solved=(
            "Rota hesaplama algoritmalarını NavigationSystem sınıfından soyutlar. Görev esnasında "
            "kısıtlı bölge durumu veya görev tipi değiştiğinde, NavigationSystem kendi kodunu "
            "değiştirmeden çalışma zamanında ShortestPathStrategy, RadarEvasionStrategy ve "
            "LoiteringSearchStrategy arasında dinamik geçiş yapabilir."
        ),
        participants="NavigationSystem, RoutePlanningStrategy (ABC), ShortestPathStrategy, RadarEvasionStrategy, LoiteringSearchStrategy",
    )

    col_ctrl, col_map = st.columns([1, 2])

    with col_ctrl:
        st.subheader("🧭 Strateji ve Koordinat Ayarları")
        strategy_options = {
            "SHORTEST_PATH": "1. ShortestPathStrategy (En Kısa Doğrudan Rota)",
            "RADAR_EVASION": "2. RadarEvasionStrategy (Kısıtlı Bölgeden Kaçınma)",
            "LOITERING_SEARCH": "3. LoiteringSearchStrategy (Serpantin Bölge Tarama)",
        }
        current_key = sim.navigation_system.strategy.strategy_name
        selected_key = st.radio(
            "Aktif Strateji (`NavigationSystem.set_strategy`):",
            options=list(strategy_options.keys()),
            format_func=lambda k: strategy_options[k],
            index=list(strategy_options.keys()).index(current_key)
            if current_key in strategy_options
            else 1,
        )

        show_all = st.checkbox(
            "Üç stratejinin tamamını 2B harita üzerinde aynı anda karşılaştır",
            value=True,
        )

        st.markdown("#### 📍 Başlangıç ve Hedef Koordinatları (km)")
        s_col1, s_col2 = st.columns(2)
        start_x = s_col1.slider("Kalkış X (km):", 2.0, 40.0, float(sim.start_point.x_km), 1.0)
        start_y = s_col2.slider("Kalkış Y (km):", 2.0, 40.0, float(sim.start_point.y_km), 1.0)

        d_col1, d_col2 = st.columns(2)
        dest_x = d_col1.slider("Hedef X (km):", 55.0, 95.0, float(sim.destination_point.x_km), 1.0)
        dest_y = d_col2.slider("Hedef Y (km):", 55.0, 95.0, float(sim.destination_point.y_km), 1.0)

        st.markdown("#### ⚠️ Sentetik Kısıtlı Bölge Yarıçapları")
        r1 = st.slider("RZ-ALPHA Yarıçapı (Merkez 42, 40):", 5.0, 22.0, float(sim.restricted_zones[0].radius_km), 1.0)
        r2 = st.slider("RZ-BRAVO Yarıçapı (Merkez 66, 62):", 5.0, 20.0, float(sim.restricted_zones[1].radius_km), 1.0)

        sim.start_point = Point2D(start_x, start_y, "Kalkış (Start)")
        sim.destination_point = Point2D(dest_x, dest_y, "Hedef (Target)")
        sim.restricted_zones = [
            RestrictedZone("RZ-ALPHA", "Kısıtlı Bölge Alfa", Point2D(42.0, 40.0, "RZ-ALPHA"), r1),
            RestrictedZone("RZ-BRAVO", "Kısıtlı Bölge Bravo", Point2D(66.0, 62.0, "RZ-BRAVO"), r2),
        ]

        if selected_key == "SHORTEST_PATH":
            sim.navigation_system.set_strategy(ShortestPathStrategy())
        elif selected_key == "RADAR_EVASION":
            sim.navigation_system.set_strategy(RadarEvasionStrategy())
        else:
            sim.navigation_system.set_strategy(LoiteringSearchStrategy())

        active_plan = sim.navigation_system.calculate_route(
            sim.start_point, sim.destination_point, sim.restricted_zones
        )
        sim.last_route_plan = active_plan
        all_plans = sim.navigation_system.compare_all_strategies(
            sim.start_point, sim.destination_point, sim.restricted_zones
        )

    with col_map:
        st.subheader("🗺️ 2B Sentetik Harita ve Rota Görselleştirmesi")
        plans_to_draw = all_plans if show_all else [active_plan]
        map_fig = create_route_map_2d_chart(
            route_plans=plans_to_draw,
            restricted_zones=sim.restricted_zones,
            active_strategy_name=active_plan.strategy_name,
        )
        st.plotly_chart(map_fig, use_container_width=True)

        # Aktif Strateji Özet Durumu
        if active_plan.is_safe:
            st.success(
                f"✅ **Aktif Strateji (`{active_plan.strategy_title}`):** Kısıtlı bölge ihlali yok! "
                f"Mesafe: `{active_plan.total_distance_km} km` | Süre: `{active_plan.estimated_duration_min} dk` | "
                f"Yakıt: `{active_plan.estimated_fuel_kg} kg` | İrtifa: `{active_plan.recommended_altitude_m:.0f} m`"
            )
        else:
            st.error(
                f"⚠️ **Aktif Strateji (`{active_plan.strategy_title}`):** "
                f"`{list(active_plan.violated_zones)}` kısıtlı bölgeleri ihlal ediliyor! "
                f"Güvenli rota için `RadarEvasionStrategy` veya `LoiteringSearchStrategy` seçin."
            )

    st.divider()

    # 3 Stratejinin Karşılaştırma Tablosu
    st.subheader("📊 Üç Navigasyon Stratejisinin Karşılaştırmalı Analizi")
    st.dataframe(
        [
            {
                "Strateji": p.strategy_title,
                "Durum": "⭐ AKTİF" if p.strategy_name == active_plan.strategy_name else "Alternatif",
                "Toplam Mesafe (km)": p.total_distance_km,
                "Tahmini Süre (dk)": p.estimated_duration_min,
                "Tahmini Yakıt (kg)": p.estimated_fuel_kg,
                "Önerilen İrtifa (m)": p.recommended_altitude_m,
                "Waypoint Sayısı": p.waypoint_count,
                "İhlal Edilen Bölgeler": ", ".join(p.violated_zones) if p.violated_zones else "Yok (Güvenli ✅)",
                "Güvenlik Skoru": p.safety_score,
                "Açıklama": p.notes,
            }
            for p in all_plans
        ],
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("📍 Aktif Rotanın Waypoint (Dönüş Noktası) Koordinat Listesi", expanded=False):
        st.dataframe(
            [
                {
                    "Sıra": idx + 1,
                    "Etiket": wp.label,
                    "X (Doğu km)": wp.x_km,
                    "Y (Kuzey km)": wp.y_km,
                }
                for idx, wp in enumerate(active_plan.waypoints)
            ],
            use_container_width=True,
            hide_index=True,
        )
