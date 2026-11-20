"""
Ekran 3: Sensor Integration — GoF Adapter Kalıbı ile Heterojen Sensör Entegrasyonu.
"""

from __future__ import annotations

import streamlit as st

from src.models.sensor_models import SensorIntegrationError
from src.patterns.adapter import (
    LegacyStanagRadarSDK,
    StanagRadarAdapter,
    ThermalCameraAdapter,
    VendorThermalDevice,
)
from src.simulation.mission_simulator import MissionSimulator
from ui.components.charts import (
    create_flir_thermal_view_chart,
    create_sensor_polar_and_cartesian_charts,
)
from ui.components.theme import render_pattern_header


def render_sensor_integration_page(sim: MissionSimulator) -> None:
    """Adapter tasarım kalıbı etkileşim ve veri dönüşüm karşılaştırma ekranını çizer."""
    render_pattern_header(
        badge="2. ADAPTER KALIBI — YAPISAL (STRUCTURAL)",
        title="Heterojen Sensör Entegrasyonu ve Birim Normalizasyonu",
        problem_solved=(
            "Görev bilgisayarının (MissionComputer) mevcut kodunu değiştirmeden (Open/Closed Prensibi) "
            "ve tip kontrolü (isinstance) yapmadan, birbirinden tamamen farklı metot imzaları ve "
            "birimler (Miliradyan/Yard/Feet vs. Radyan/Deniz Mili/Kelvin) kullanan harici sensörlerin "
            "ortak TargetSensor arayüzü üzerinden standart TargetData modeline dönüştürülmesini sağlar."
        ),
        participants="TargetSensor (ABC), StanagRadarAdapter, ThermalCameraAdapter, LegacyStanagRadarSDK, VendorThermalDevice, MissionComputer",
    )

    if not sim.last_targets:
        sim.last_targets = sim.mission_computer.collect_all_targets()

    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([2, 2, 1.8, 1.5])
    with col_btn1:
        if st.button("📡 Tekil Sensör Taraması (2 İz Oku)", type="primary", use_container_width=True):
            sim.last_targets = sim.mission_computer.collect_all_targets()
            st.toast(f"{len(sim.last_targets)} sensörden hedef verisi okundu ve normalize edildi.")
    with col_btn2:
        if st.button("🔄 360° Tam Sektör Taraması (6 İz Topla)", use_container_width=True):
            collected = []
            for _ in range(3):
                collected.extend(sim.mission_computer.collect_all_targets())
            sim.last_targets = collected
            st.toast(f"360° Tam Sektör Taraması tamamlandı: {len(sim.last_targets)} normalize hedef izi toplandı!")
    with col_btn3:
        conf_threshold = st.slider(
            "Yüksek Güven Eşiği (`min_confidence`):",
            min_value=0.0,
            max_value=1.0,
            value=0.70,
            step=0.05,
        )
    with col_btn4:
        sweep_angle = st.slider(
            "Radar Tarama Açısı (°):",
            min_value=0.0,
            max_value=355.0,
            value=float((sim.tick_count * 45 + 60) % 360),
            step=15.0,
        )

    targets = sim.last_targets
    filtered_targets = [t for t in targets if t.confidence_score >= conf_threshold]

    # 1. Taktik PPI Radar, 2B Kartezyen Harita ve EO/IR Termal Kamera FLIR Vizörü
    st.subheader(
        f"🎯 Taktik Sensör Füzyon Ekranı (PPI Radar | Kartezyen Harita | EO/IR Termal Vizör — {len(filtered_targets)} Aktif İz)"
    )
    polar_fig, cart_fig = create_sensor_polar_and_cartesian_charts(
        filtered_targets, sweep_angle_deg=sweep_angle
    )

    flir_targets = filtered_targets if filtered_targets else targets
    flir_ctrl_col1, flir_ctrl_col2 = st.columns([3, 1])
    with flir_ctrl_col1:
        selected_target_idx = st.selectbox(
            "🔭 EO/IR Termal Kamera (FLIR) Vizöründe Kilitlenecek Hedefi Seçin:",
            options=list(range(len(flir_targets))),
            format_func=lambda idx: (
                f"{flir_targets[idx].target_id} | {flir_targets[idx].classification} | "
                f"Azimut: {flir_targets[idx].bearing_deg}° | Menzil: {flir_targets[idx].distance_km} km | "
                f"Güven: %{flir_targets[idx].confidence_score*100:.0f} ({flir_targets[idx].source_sensor_name})"
            ),
        )
    with flir_ctrl_col2:
        flir_polarity = st.radio(
            "FLIR Termal Polarite:",
            options=["WHOT", "BHOT"],
            format_func=lambda p: "WHOT (Beyaz Sıcak)" if p == "WHOT" else "BHOT (Siyah Sıcak)",
            horizontal=True,
        )

    g_col1, g_col2, g_col3 = st.columns(3)
    g_col1.plotly_chart(polar_fig, use_container_width=True)
    g_col2.plotly_chart(cart_fig, use_container_width=True)
    if flir_targets:
        flir_fig = create_flir_thermal_view_chart(
            flir_targets[selected_target_idx], polarity=flir_polarity
        )
        g_col3.plotly_chart(flir_fig, use_container_width=True)

    st.divider()

    # 2. Ham ve Normalize Verilerin Yan Yana Karşılaştırması
    st.subheader("🔍 Ham Sensör Çıktısı (Adaptee) vs. Normalize Hedef Verisi (TargetData)")
    for t in targets:
        with st.container():
            c_raw, c_arrow, c_norm = st.columns([5, 2, 5])
            with c_raw:
                st.markdown(f"**1. Ham Sensör Verisi (`{t.sensor_protocol}`)**")
                if isinstance(t.raw_payload, str):
                    st.caption("`LegacyStanagRadarSDK.fetch_polar_blip_buffer() -> str`")
                    st.code(t.raw_payload, language="text")
                else:
                    st.caption("`VendorThermalDevice.capture_heat_signature_json() -> dict`")
                    st.json(t.raw_payload)

            with c_arrow:
                st.markdown("**2. Adapter Dönüşüm Adımları**")
                for note in t.transformation_notes:
                    st.markdown(f"- `{note}`")

            with c_norm:
                st.markdown(f"**3. Ortak Format (`TargetData`: `{t.target_id}`)**")
                st.caption("`TargetSensor.read_target_data() -> TargetData`")
                st.json(
                    {
                        "target_id": t.target_id,
                        "source_sensor_name": t.source_sensor_name,
                        "bearing_deg": f"{t.bearing_deg}°",
                        "distance_km": f"{t.distance_km} km",
                        "altitude_m": f"{t.altitude_m} m",
                        "confidence_score": t.confidence_score,
                        "classification": t.classification,
                        "cartesian_xy_km": [t.cartesian_x_km, t.cartesian_y_km],
                    }
                )
            st.divider()

    # 3. Özel Ham Veri Enjeksiyonu ve Arıza Simülasyonu Laboratuvarı
    with st.expander("🧪 Canlı Ham Sensör Paketi Enjeksiyonu & Donanım Arızası Simülasyon Laboratuvarı", expanded=True):
        lab_col1, lab_col2 = st.columns(2)
        with lab_col1:
            st.markdown("#### 1. STANAG-4607 Radar SDK Paket Enjeksiyonu")
            custom_blip = st.text_input(
                "Özel STANAG ASCII Çerçevesi:",
                value="STANAG4607|TRK:777|AZ_MRAD:1570.80|RNG_YD:10936.1|ALT_FT:3280.8|SNR_DB:23.0|CLS:3",
            )
            fault_code = st.selectbox(
                "Radar Durum Kodu:",
                options=[0x00, 0x04, 0xFF],
                format_func=lambda x: f"0x{x:02X} ({'NOMINAL' if x == 0 else 'DONANIM ARIZASI'})",
            )
            if st.button("➕ STANAG Adaptörüyle Dönüştür & Radar Ekranına Enjekte Et", use_container_width=True):
                test_sdk = LegacyStanagRadarSDK(custom_blip_buffer=custom_blip, status_code=fault_code)
                test_adapter = StanagRadarAdapter(test_sdk)
                try:
                    res = test_adapter.read_target_data()
                    sim.last_targets.append(res)
                    st.success(
                        f"Dönüşüm & Enjeksiyon Başarılı: {res.target_id} -> {res.bearing_deg}°, {res.distance_km} km (PPI Radar ve FLIR listesine eklendi!)"
                    )
                    st.json(res.to_dict())
                except SensorIntegrationError as exc:
                    st.error(f"Adaptör Hatayı Yakaladı (`SensorIntegrationError`): {exc}")

        with lab_col2:
            st.markdown("#### 2. Üçüncü Parti EO/IR Termal Kamera Paket Enjeksiyonu")
            health_state = st.selectbox("Sensör Sağlık Durumu:", options=["NOMINAL", "COOLER_FAULT", "OPTICS_BLOCKED"])
            temp_k = st.slider("Pik Sıcaklık (Kelvin):", min_value=280.0, max_value=400.0, value=363.15)
            range_nm = st.slider("Eğik Menzil (Deniz Mili - NM):", min_value=1.0, max_value=15.0, value=5.0)
            if st.button("➕ Termal Adaptörle Dönüştür & FLIR Vizörüne Enjekte Et", use_container_width=True):
                test_dev = VendorThermalDevice(
                    custom_payload={
                        "device_header": {"vendor": "OptoTherm-X", "fw_ver": "4.2.1", "sensor_health": health_state},
                        "hotspot": {
                            "blob_uid": "888",
                            "angle_rad": 1.0472,
                            "slant_range_nm": range_nm,
                            "elevation_m": 900.0,
                            "peak_temp_kelvin": temp_k,
                            "pixel_cluster_pct": 88.0,
                            "signature_tag": "ENGINE_PLUME",
                        },
                    }
                )
                test_th_adapter = ThermalCameraAdapter(test_dev)
                try:
                    res_th = test_th_adapter.read_target_data()
                    sim.last_targets.append(res_th)
                    st.success(
                        f"Dönüşüm & Enjeksiyon Başarılı: {res_th.target_id} -> {res_th.bearing_deg}°, {res_th.distance_km} km (PPI Radar ve FLIR listesine eklendi!)"
                    )
                    st.json(res_th.to_dict())
                except SensorIntegrationError as exc:
                    st.error(f"Adaptör Hatayı Yakaladı (`SensorIntegrationError`): {exc}")
