"""
Ekran 1: Dashboard — Genel Simülasyon Durumu, Aktif Uçuş Fazı, Telemetri ve Olay Kayıtları.
"""

from __future__ import annotations

import streamlit as st

from src.simulation.mission_simulator import MissionSimulator
from src.utils.logger import system_logger
from ui.components.charts import (
    create_avionics_gauges_chart,
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

    # Canlı Aviyonik Uçuş Göstergeleri (4'lü PFD Kadran Paneli)
    st.markdown("#### 🎛️ Canlı Aviyonik Uçuş Göstergeleri (Primary Flight Display — PFD)")
    gauges_fig = create_avionics_gauges_chart(sim.get_hud_telemetry())
    st.plotly_chart(gauges_fig, use_container_width=True)

    st.divider()

    # Simülasyon Döngüsü (Tick) ve Canlı Görev Oynatıcı (Mission Playback)
    st.markdown("#### 🎮 Canlı Görev Simülasyonu ve Zaman Adımlı İHA Uçuş Kontrolü")

    chk_col1, chk_col2 = st.columns(2)
    with chk_col1:
        auto_lifecycle = st.checkbox(
            "🤖 Otopilot Uçuş Fazı Yönetimi (IDLE ➡️ TAKE_OFF ➡️ CRUISE ➡️ COMBAT otomatik geçiş)",
            value=True,
        )
    with chk_col2:
        auto_evade = st.checkbox(
            "📡 Radar emisyonu algılandığında otomatik RadarEvasionStrategy'ye geç",
            value=True,
        )

    total_dist = route.total_distance_km if route else 100.0
    progress_ratio = min(1.0, max(0.0, sim.route_progress_pct / 100.0))
    st.progress(
        progress_ratio,
        text=(
            f"✈️ Rota İlerlemesi: %{sim.route_progress_pct:.1f} "
            f"({sim.route_distance_traveled_km:.1f} / {total_dist:.1f} km) | "
            f"Anlık İHA Koordinatı: ({sim.uav_position.x_km:.1f}, {sim.uav_position.y_km:.1f}) km | "
            f"Pusula: {sim.heading_deg:.1f}° ({sim._cardinal_direction(sim.heading_deg)}) | "
            f"İz Noktası: {len(sim.flight_trail)}"
        ),
    )

    btn_c1, btn_c2, btn_c3, btn_c4, btn_c5 = st.columns([2, 2, 2, 1.5, 1.2])
    with btn_c1:
        if st.button(
            "🚀 +1 Adım İlerlet (Run Tick)",
            type="primary",
            use_container_width=True,
        ):
            tick_info = sim.run_simulation_tick(
                auto_evade_radar_threat=auto_evade,
                auto_lifecycle=auto_lifecycle,
            )
            emg_note = " | 🚨 KRİTİK YAKIT FAILSAFE TETİKLENDİ!" if tick_info["emergency_triggered"] else ""
            st.session_state["last_tick_toast"] = (
                f"Adım #{tick_info['tick']}: İHA ({tick_info['uav_x_km']:.1f}, {tick_info['uav_y_km']:.1f}) km "
                f"konumuna ilerledi (%{tick_info['route_progress_pct']:.1f}) | "
                f"Faz: {tick_info['flight_phase']} | Yakıt: {tick_info['fuel_remaining_kg']:.1f} kg{emg_note}"
            )
            st.rerun()

    with btn_c2:
        if st.button(
            "⏩ 5 Adım Hızlı Uçuş (5x Oynat)",
            use_container_width=True,
        ):
            last_info = None
            for _ in range(5):
                last_info = sim.run_simulation_tick(
                    auto_evade_radar_threat=auto_evade,
                    auto_lifecycle=auto_lifecycle,
                )
            if last_info:
                st.session_state["last_tick_toast"] = (
                    f"5 Adımlı Hızlı Uçuş tamamlandı (Adım #{last_info['tick']}): "
                    f"İHA ({last_info['uav_x_km']:.1f}, {last_info['uav_y_km']:.1f}) km konumunda "
                    f"(%{last_info['route_progress_pct']:.1f}) | Faz: {last_info['flight_phase']}"
                )
            st.rerun()

    with btn_c3:
        if st.button(
            "⛽ Kritik Yakıt (%14) & Failsafe Testi",
            use_container_width=True,
        ):
            sim.current_fuel_kg = round(sim.active_platform.fuel_weight_kg * 0.14, 1)
            tick_info = sim.run_simulation_tick(
                auto_evade_radar_threat=auto_evade,
                auto_lifecycle=auto_lifecycle,
            )
            st.session_state["last_tick_toast"] = (
                f"🚨 Kritik Yakıt Testi: Kalan yakıt {tick_info['fuel_remaining_kg']:.1f} kg (<=%15) "
                f"olduğu için State Kalıbı otomatik olarak EMERGENCY_RETURN fazına geçti ve İHA Ana Üsse yöneldi!"
            )
            st.rerun()

    with btn_c4:
        if st.button("🔄 Konumu Üsse Sıfırla", use_container_width=True):
            sim.reset_flight_position()
            st.session_state["last_tick_toast"] = "İHA konumu, uçuş izi ve yakıt seviyesi Ana Üsse (Start) sıfırlandı."
            st.rerun()

    with btn_c5:
        if st.button("🧹 Logları Sil", use_container_width=True):
            system_logger.clear()
            st.rerun()

    if "last_tick_toast" in st.session_state:
        msg_txt = st.session_state.pop("last_tick_toast")
        if "🚨" in msg_txt:
            st.error(msg_txt)
        else:
            st.success(msg_txt)

    # Orta Bölüm: 2B Harita ve Ağırlık/Telemetri Özeti
    left_col, right_col = st.columns([3, 2])
    with left_col:
        st.subheader("🗺️ Canlı Görev Haritası, İHA Uçuş İzi ve Sensör FOV Konisi")
        if route is not None:
            map_fig = create_route_map_2d_chart(
                route_plans=[route],
                restricted_zones=sim.restricted_zones,
                active_strategy_name=route.strategy_name,
                uav_position=sim.uav_position,
                uav_heading_deg=sim.heading_deg,
                flight_trail=sim.flight_trail,
                sensor_fov_range_km=sim.sensor_fov_range_km,
                sensor_fov_half_angle_deg=sim.sensor_fov_half_angle_deg,
                detected_targets=sim.last_targets,
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
