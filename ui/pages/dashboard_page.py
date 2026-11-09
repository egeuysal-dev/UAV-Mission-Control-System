"""
Ekran 1: Dashboard — Genel Simülasyon Durumu, Aktif Uçuş Fazı, Telemetri ve Olay Kayıtları.
"""

from __future__ import annotations

import streamlit as st

from src.simulation.mission_simulator import MissionSimulator
from src.utils.logger import system_logger
from ui.components.charts import (
    create_route_map_2d_chart,
    create_weight_breakdown_chart,
)
from ui.components.theme import render_pattern_header


def render_dashboard_page(sim: MissionSimulator) -> None:
    """Genel görev kontrol panelini (Dashboard) çizer."""
    render_pattern_header(
        badge="MİMARİ ORKESTRASYON | 5 GOF TASARIM KALIBI",
        title="Yer Kontrol İstasyonu (YKİ) — Ana Simülasyon Paneli",
        problem_solved=(
            "Builder ile yapılandırılan İHA platformunu, State ile yönetilen uçuş fazını, "
            "Adapter ile normalize edilen sensör verilerini, Strategy ile hesaplanan 2B rotayı "
            "ve Decorator ile şifrelenen/korunan telemetri kanalını tek bir simülasyon döngüsünde birleştirir."
        ),
        participants="UAVPlatform, MissionComputer, TelemetryChannelDecorator, FlightController, NavigationSystem",
    )

    # Üst Metrik Kartları (KPIs)
    fc = sim.flight_controller
    uav = sim.active_platform
    route = sim.last_route_plan
    packet = sim.last_telemetry_packet

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric(
        "1. Aktif İHA (Builder)",
        uav.model_name,
        f"{uav.total_weight_kg:.0f}/{uav.max_takeoff_weight_kg:.0f} kg",
    )
    col2.metric(
        "2. Uçuş Fazı (State)",
        fc.current_phase_name,
        f"İrtifa: {fc.altitude_m:.0f} m | {fc.speed_knots:.0f} kts",
    )
    col3.metric(
        "3. Sensörler (Adapter)",
        f"{len(sim.mission_computer.get_registered_sensors())} Aktif",
        f"Son Hedef: {len(sim.last_targets)} iz",
    )
    col4.metric(
        "4. Telemetri (Decorator)",
        f"{len(sim.decorator_layers)} Katman",
        f"{packet.final_size_bytes if packet else 0} Bayt",
    )
    col5.metric(
        "5. Rota (Strategy)",
        route.strategy_name if route else "YOK",
        f"{route.total_distance_km if route else 0:.1f} km",
    )

    st.divider()

    # Simülasyon Döngüsü (Tick) Kontrolü
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 1])
    with ctrl_col1:
        auto_evade = st.checkbox(
            "Radar emisyonu algılandığında otomatik RadarEvasionStrategy'ye geç",
            value=True,
        )
    with ctrl_col2:
        if st.button("🚀 Tek Adım Simülasyon Döngüsü Çalıştır (Run Tick)", type="primary", use_container_width=True):
            tick_info = sim.run_simulation_tick(auto_evade_radar_threat=auto_evade)
            st.toast(
                f"Simülasyon Döngüsü #{tick_info['tick']} tamamlandı! "
                f"({tick_info['targets_collected']} hedef okundu, {tick_info['telemetry_bytes']}B iletildi)"
            )
    with ctrl_col3:
        if st.button("🧹 Logları Temizle", use_container_width=True):
            system_logger.clear()
            st.rerun()

    # Orta Bölüm: 2B Harita ve Ağırlık/Telemetri Özeti
    left_col, right_col = st.columns([3, 2])
    with left_col:
        st.subheader("🗺️ Aktif Görev Haritası (2B Simülasyon)")
        if route is not None:
            map_fig = create_route_map_2d_chart(
                route_plans=[route],
                restricted_zones=sim.restricted_zones,
                active_strategy_name=route.strategy_name,
            )
            st.plotly_chart(map_fig, use_container_width=True)

    with right_col:
        st.subheader("⚖️ Platform Ağırlık Dağılımı")
        weight_fig = create_weight_breakdown_chart(uav)
        st.plotly_chart(weight_fig, use_container_width=True)

        st.subheader("📡 Son Telemetri Sarmalama Zinciri")
        if packet is not None:
            st.code(packet.wrapping_expression, language="python")
            st.caption(f"Son İletilen Çerçeve ({packet.final_size_bytes} Bayt):")
            st.code(
                packet.final_payload[:160] + ("..." if len(packet.final_payload) > 160 else ""),
                language="text",
            )

    st.divider()

    # Alt Bölüm: Sistem Olay Günlüğü
    st.subheader("📋 Merkezi Sistem Olay Günlüğü (MissionEventLogger)")
    events = system_logger.get_events()
    if not events:
        st.info("Henüz kayıtlı sistem olayı bulunmuyor.")
    else:
        log_rows = [
            {
                "Saat (UTC)": ev.timestamp,
                "Seviye": ev.level,
                "Modül / Kalıp": ev.module,
                "Olay Açıklaması": ev.message,
            }
            for ev in reversed(events[-25:])
        ]
        st.dataframe(log_rows, use_container_width=True, hide_index=True)
