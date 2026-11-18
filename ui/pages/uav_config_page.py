"""
Ekran 2: UAV Configuration — GoF Builder Kalıbı ile Platform Oluşturma ve Doğrulama.
"""

from __future__ import annotations

import streamlit as st

from src.models.uav_models import (
    COMMS_CATALOG,
    PAYLOAD_CATALOG,
    SENSOR_CATALOG,
    UAVConfigurationError,
)
from src.patterns.builder import (
    MissionPrepDirector,
    ReconUAVBuilder,
    StrikeUAVBuilder,
)
from src.simulation.mission_simulator import MissionSimulator
from ui.components.charts import (
    create_uav_blueprint_chart,
    create_uav_capability_radar_chart,
    create_weight_breakdown_chart,
)
from ui.components.theme import render_pattern_header


def render_uav_config_page(sim: MissionSimulator) -> None:
    """Builder tasarım kalıbı etkileşim ekranını çizer."""
    render_pattern_header(
        badge="1. BUILDER KALIBI — YARATIMSAL (CREATIONAL)",
        title="İHA Görev Yapılandırması ve Mühendislik Doğrulaması",
        problem_solved=(
            "Çok sayıda opsiyonel bileşene (sensör, faydalı yük, yakıt, haberleşme) ve çapraz kısıtlara "
            "(Maksimum Kalkış Ağırlığı / MTOW ve görev profili uyumluluğu) sahip UAVPlatform nesnesinin "
            "hataya açık çok parametreli kurucular (telescoping constructor) yerine adım adım ve doğrulanarak inşa edilmesini sağlar."
        ),
        participants="UAVConfigurationBuilder (ABC), StrikeUAVBuilder, ReconUAVBuilder, MissionPrepDirector, UAVPlatform",
    )

    tab_custom, tab_director, tab_catalog = st.tabs(
        [
            "🛠️ Özel İHA İnşası (Step-by-Step Builder)",
            "🎖️ Hazır Görev Reçeteleri (MissionPrepDirector)",
            "📚 Bileşen Kataloğu ve Uyumluluk Kuralları",
        ]
    )

    with tab_custom:
        col_form, col_preview = st.columns([1, 1])

        with col_form:
            st.subheader("1. Builder ve Bileşen Seçimi")
            mission_choice = st.radio(
                "ConcreteBuilder Seçin:",
                options=["RECON (ReconUAVBuilder — MTOW: 1750 kg, 2 İstasyon)", "STRIKE (StrikeUAVBuilder — MTOW: 5500 kg, 4 İstasyon)"],
                horizontal=False,
            )
            is_strike = mission_choice.startswith("STRIKE")
            builder = StrikeUAVBuilder() if is_strike else ReconUAVBuilder()

            default_name = "AKINCI-S Özel Yapılandırma" if is_strike else "ANKA-R Özel Yapılandırma"
            model_name = st.text_input("İHA Model Adı:", value=default_name)

            max_fuel_slider = 1600.0 if is_strike else 700.0
            default_fuel = 1000.0 if is_strike else 380.0
            fuel_kg = st.slider(
                "Yakıt Miktarı (kg):",
                min_value=0.0,
                max_value=max_fuel_slider,
                value=default_fuel,
                step=10.0,
            )

            selected_sensors = st.multiselect(
                "Sensörler (En az 1, En fazla 3; uyumluluk kontrol edilir):",
                options=list(SENSOR_CATALOG.keys()),
                default=["EO/IR Termal Kamera Podu"],
            )

            selected_payloads = st.multiselect(
                "Faydalı Yükler / Görev Podları (İstasyon ve profil uyumluluğu kontrol edilir):",
                options=list(PAYLOAD_CATALOG.keys()),
                default=(
                    ["Lazer İşaretleme ve Eğitim Podu"]
                    if is_strike
                    else ["Geniş Alan Haritalama Podu"]
                ),
            )

            comms_options = ["(Seçilmedi — Hatayı Test Et)"] + list(COMMS_CATALOG.keys())
            selected_comms = st.selectbox(
                "Haberleşme Modülü (Comms Module):",
                options=comms_options,
                index=1,
            )

            # Taslak nesneyi adım adım oluştur
            builder.reset()
            builder.set_airframe(model_name)
            builder.set_fuel_capacity(fuel_kg)
            for s_name in selected_sensors:
                builder.add_sensor(s_name)
            for p_name in selected_payloads:
                builder.add_payload(p_name)
            if selected_comms != "(Seçilmedi — Hatayı Test Et)":
                builder.set_comms_module(selected_comms)

            draft = builder.get_draft_platform()

            if st.button("🔨 builder.build() Çağır ve Aktif İHA Olarak Ata", type="primary", use_container_width=True):
                try:
                    built_uav = builder.build()
                    sim.active_platform = built_uav
                    sim.current_fuel_kg = built_uav.fuel_weight_kg
                    sim.transmit_current_telemetry("UAV_RECONFIGURED")
                    st.success(
                        f"✅ `{built_uav.model_name}` başarıyla doğrulandı, inşa edildi ve aktif simülasyona atandı!"
                    )
                except UAVConfigurationError as exc:
                    st.error("❌ `UAVConfigurationBuilder.build()` Geçersiz Yapılandırmayı Reddetti!")
                    for err_item in exc.errors:
                        st.warning(f"• {err_item}")

        with col_preview:
            st.subheader("2. Canlı Taslak Analizi ve Doğrulama")
            is_valid, validation_errors = draft.validate()
            perf = draft.get_performance_metrics()

            m1, m2, m3 = st.columns(3)
            m1.metric(
                "Toplam Ağırlık",
                f"{draft.total_weight_kg:.1f} kg",
                f"MTOW: {draft.max_takeoff_weight_kg:.0f} kg (%{perf['mtow_usage_pct']:.0f})",
            )
            m2.metric(
                "Kalan Ağırlık Marjı",
                f"{draft.remaining_weight_capacity_kg:.1f} kg",
                delta_color="normal" if draft.remaining_weight_capacity_kg >= 0 else "inverse",
            )
            m3.metric(
                "Tahmini Havada Kalış",
                f"{draft.estimated_endurance_hours:.1f} Saat",
                f"Tüketim: {perf['burn_rate_kg_hr']:.1f} kg/sa",
            )

            p1, p2, p3 = st.columns(3)
            p1.metric(
                "Harekât Yarıçapı",
                f"{perf['combat_radius_km']:.0f} km",
                f"Menzil: {perf['max_ferry_range_km']:.0f} km",
            )
            p2.metric(
                "Optimal Seyir Hızı",
                f"{perf['cruise_speed_kts']:.0f} knots",
                f"Tavan: {perf['service_ceiling_m']:.0f} m",
            )
            p3.metric(
                "Kalkış Koşusu / Güç",
                f"{perf['takeoff_roll_m']:.0f} m",
                f"Sensör Gücü: {perf['sensor_power_watts']:.0f} W",
            )

            fig = create_weight_breakdown_chart(draft)
            st.plotly_chart(fig, use_container_width=True)

            if is_valid:
                st.success("✅ Tüm mühendislik, ağırlık (MTOW) ve görev profili uyumluluk kuralları sağlanıyor.")
            else:
                st.error(f"⚠️ Taslakta {len(validation_errors)} doğrulama ihlali tespit edildi:")
                for err in validation_errors:
                    st.markdown(f"- ❌ **{err}**")

            with st.expander("📄 UAVPlatform.to_summary_dict() Çıktısını İncele", expanded=False):
                st.json(draft.to_summary_dict())

        st.divider()
        st.subheader("3. 📐 Teknik İHA Gövde & İstasyon Şeması (CAD Blueprint) ve 5 Eksenli Yetenek Analizi")
        bp_col, rad_col = st.columns([3, 2])
        with bp_col:
            bp_fig = create_uav_blueprint_chart(draft)
            st.plotly_chart(bp_fig, use_container_width=True, key="draft_blueprint_chart")
        with rad_col:
            rad_fig = create_uav_capability_radar_chart(draft)
            st.plotly_chart(rad_fig, use_container_width=True, key="draft_radar_chart")

    with tab_director:
        st.subheader("🎖️ MissionPrepDirector — Standart Görev Reçeteleri")
        st.write(
            "`MissionPrepDirector` sınıfı, `UAVConfigurationBuilder` arayüzünü kullanarak "
            "önceden doğrulanmış standart İHA konfigürasyonlarını tek komutla üretir."
        )
        d_col1, d_col2, d_col3, d_col4 = st.columns(4)
        if d_col1.button("🛰️ Standart Keşif (ANKA-R)", use_container_width=True):
            sim.set_preset_platform("STD_RECON")
            st.rerun()
        if d_col2.button("🌐 Uzun Menzil Keşif (AKSUNGUR-R)", use_container_width=True):
            sim.set_preset_platform("LONG_RECON")
            st.rerun()
        if d_col3.button("⚡ Standart Taktik (AKINCI-S)", use_container_width=True):
            sim.set_preset_platform("STD_STRIKE")
            st.rerun()
        if d_col4.button("🛡️ Ağır Görev (AKINCI-B)", use_container_width=True):
            sim.set_preset_platform("HEAVY_STRIKE")
            st.rerun()

        dir_bp_col, dir_rad_col = st.columns([3, 2])
        with dir_bp_col:
            st.plotly_chart(
                create_uav_blueprint_chart(sim.active_platform),
                use_container_width=True,
                key="director_blueprint_chart",
            )
        with dir_rad_col:
            st.plotly_chart(
                create_uav_capability_radar_chart(sim.active_platform),
                use_container_width=True,
                key="director_radar_chart",
            )

        with st.expander("#### 📄 Aktif Simülasyon İHA Özeti (JSON)", expanded=False):
            st.json(sim.active_platform.to_summary_dict())

    with tab_catalog:
        st.subheader("Sensör Kataloğu")
        st.dataframe(
            [
                {
                    "Sensör Adı": s.name,
                    "Tip": s.sensor_type,
                    "Ağırlık (kg)": s.weight_kg,
                    "Güç (W)": s.power_watts,
                    "Uyumlu Görevler": ", ".join(s.compatible_missions),
                    "Açıklama": s.description,
                }
                for s in SENSOR_CATALOG.values()
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.subheader("Faydalı Yük Kataloğu (Temsili Simülasyon Yükleri)")
        st.dataframe(
            [
                {
                    "Yük Adı": p.name,
                    "Kategori": p.category,
                    "Ağırlık (kg)": p.weight_kg,
                    "İstasyon Tipi": p.hardpoint_type,
                    "Uyumlu Görevler": ", ".join(p.compatible_missions),
                    "Açıklama": p.description,
                }
                for p in PAYLOAD_CATALOG.values()
            ],
            use_container_width=True,
            hide_index=True,
        )
