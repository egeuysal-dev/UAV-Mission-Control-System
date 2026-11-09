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
from ui.components.charts import create_sensor_polar_and_cartesian_charts
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

    col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 1])
    with col_btn1:
        if st.button("📡 MissionComputer.collect_all_targets() Çalıştır", type="primary", use_container_width=True):
            sim.last_targets = sim.mission_computer.collect_all_targets()
            st.toast(f"{len(sim.last_targets)} sensörden hedef verisi okundu ve normalize edildi.")
    with col_btn2:
        conf_threshold = st.slider(
            "Yüksek Güven Eşiği (filter_high_confidence_targets):",
            min_value=0.0,
            max_value=1.0,
            value=0.75,
            step=0.05,
        )
    with col_btn3:
        if not sim.last_targets:
            sim.last_targets = sim.mission_computer.collect_all_targets()

    targets = sim.last_targets
    filtered_targets = [t for t in targets if t.confidence_score >= conf_threshold]

    # Ham ve Normalize Verilerin Yan Yana Karşılaştırması
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

    # 2B Kutupsal ve Kartezyen Görselleştirme
    st.subheader(f"🎯 Normalize Hedeflerin 2B Görselleştirmesi (Eşik >= {conf_threshold:.2f}: {len(filtered_targets)} Hedef)")
    polar_fig, cart_fig = create_sensor_polar_and_cartesian_charts(filtered_targets)
    g_col1, g_col2 = st.columns(2)
    g_col1.plotly_chart(polar_fig, use_container_width=True)
    g_col2.plotly_chart(cart_fig, use_container_width=True)

    # Özel Ham Veri ve Arıza Simülasyonu Laboratuvarı
    with st.expander("🧪 Özel Ham Sensör Verisi & Donanım Arızası Simülasyon Laboratuvarı", expanded=False):
        lab_col1, lab_col2 = st.columns(2)
        with lab_col1:
            st.markdown("#### STANAG Radar SDK Testi")
            custom_blip = st.text_input(
                "Özel STANAG ASCII Çerçevesi:",
                value="STANAG4607|TRK:777|AZ_MRAD:1570.80|RNG_YD:10936.1|ALT_FT:3280.8|SNR_DB:23.0|CLS:3",
            )
            fault_code = st.selectbox("Radar Durum Kodu:", options=[0x00, 0x04, 0xFF], format_func=lambda x: f"0x{x:02X} ({'NOMINAL' if x == 0 else 'DONANIM ARIZASI'})")
            if st.button("STANAG Adaptörünü Test Et"):
                test_sdk = LegacyStanagRadarSDK(custom_blip_buffer=custom_blip, status_code=fault_code)
                test_adapter = StanagRadarAdapter(test_sdk)
                try:
                    res = test_adapter.read_target_data()
                    st.success(f"Dönüşüm Başarılı: {res.target_id} -> {res.bearing_deg}°, {res.distance_km} km")
                    st.json(res.to_dict())
                except SensorIntegrationError as exc:
                    st.error(f"Adaptör Hatayı Yakaladı (`SensorIntegrationError`): {exc}")

        with lab_col2:
            st.markdown("#### Üçüncü Parti Termal Kamera Testi")
            health_state = st.selectbox("Sensör Sağlık Durumu:", options=["NOMINAL", "COOLER_FAULT", "OPTICS_BLOCKED"])
            temp_k = st.slider("Pik Sıcaklık (Kelvin):", min_value=280.0, max_value=400.0, value=363.15)
            range_nm = st.slider("Eğik Menzil (Deniz Mili - NM):", min_value=1.0, max_value=15.0, value=5.0)
            if st.button("Termal Kamera Adaptörünü Test Et"):
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
                    st.success(f"Dönüşüm Başarılı: {res_th.target_id} -> {res_th.bearing_deg}°, {res_th.distance_km} km")
                    st.json(res_th.to_dict())
                except SensorIntegrationError as exc:
                    st.error(f"Adaptör Hatayı Yakaladı (`SensorIntegrationError`): {exc}")
