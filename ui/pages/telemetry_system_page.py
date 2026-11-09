"""
Ekran 4: Telemetry System — GoF Decorator Kalıbı ile Dinamik Telemetri Katmanları.
"""

from __future__ import annotations

import streamlit as st

from src.models.telemetry_models import TelemetryMessage, TelemetryProcessingError
from src.patterns.decorator import (
    DECORATOR_REGISTRY,
    build_telemetry_chain,
    remove_decorator_layer,
)
from src.simulation.mission_simulator import MissionSimulator
from ui.components.charts import create_telemetry_stage_size_chart
from ui.components.theme import render_pattern_header


def render_telemetry_system_page(sim: MissionSimulator) -> None:
    """Decorator tasarım kalıbı etkileşim ve katman yönetimi ekranını çizer."""
    render_pattern_header(
        badge="3. DECORATOR KALIBI — YAPISAL (STRUCTURAL)",
        title="Dinamik Telemetri İşleme Katmanları ve Nesne Sarmalama Zinciri",
        problem_solved=(
            "Telemetri kanalına şifreleme (AES-256-GCM), sıkıştırma (ZLIB) ve parazit/hata koruma "
            "(CRC32 + Temsili FEC) özelliklerini kalıtımla eklemek 2³ = 8 farklı alt sınıf (sınıf patlaması) "
            "oluşturur ve katman sırasını değiştirmeye izin vermez. GoF nesne tabanlı Decorator kalıbı ile "
            "bu katmanlar BaseRadioChannel üzerine çalışma zamanında istenilen sıra ve kombinasyonla eklenip çıkarılabilir."
        ),
        participants="TelemetryChannel (ABC), BaseRadioChannel, TelemetryChannelDecorator, AesEncryptionDecorator, CompressionDecorator, AntiJammingDecorator",
    )

    col_cfg, col_chain = st.columns([1, 1])

    with col_cfg:
        st.subheader("1. Katman Kombinasyonu ve Sıralama Yönetimi")
        available_layers = list(DECORATOR_REGISTRY.keys())

        selected_layers = st.multiselect(
            "Uygulanacak Decorator Katmanlarını Seçin (Seçim sırası içten dışa sarmalama sırasını belirler):",
            options=available_layers,
            default=sim.decorator_layers,
        )

        # Hızlı sıra değiştirme kısayolları
        b_col1, b_col2, b_col3 = st.columns(3)
        if b_col1.button("🔄 Sıkıştırma -> AES -> AntiJam", use_container_width=True):
            selected_layers = ["CompressionDecorator", "AesEncryptionDecorator", "AntiJammingDecorator"]
            sim.decorator_layers = selected_layers
            st.rerun()
        if b_col2.button("🔄 AES -> Sıkıştırma -> AntiJam", use_container_width=True):
            selected_layers = ["AesEncryptionDecorator", "CompressionDecorator", "AntiJammingDecorator"]
            sim.decorator_layers = selected_layers
            st.rerun()
        if b_col3.button("📻 Yalnızca BaseRadioChannel", use_container_width=True):
            selected_layers = []
            sim.decorator_layers = selected_layers
            st.rerun()

        freq_band = st.selectbox(
            "Temel Radyo Kanalı Frekans Bandı (BaseRadioChannel):",
            options=["SATCOM-Ku", "UHF-433MHz", "L-Band-Tactical", "S-Band-LOS"],
            index=0,
        )
        sim_interference = st.checkbox(
            "AntiJammingDecorator: Kanal paraziti (bit hatası) ve FEC kurtarma simülasyonunu etkinleştir",
            value=sim.simulate_interference,
        )
        status_note = st.text_input(
            "Sanal Telemetri Durum Notu:",
            value="NOMINAL_FLIGHT_TELEMETRY_PACKET_STREAM_ACTIVE",
        )

        sim.decorator_layers = list(selected_layers)
        sim.frequency_band = freq_band
        sim.simulate_interference = sim_interference

    # Kanalı inşa et ve mesajı gönder
    channel = build_telemetry_chain(
        layer_names=sim.decorator_layers,
        frequency_band=sim.frequency_band,
        simulate_interference=sim.simulate_interference,
    )
    sample_msg = TelemetryMessage(
        uav_id=sim.active_platform.model_name,
        flight_phase=sim.flight_controller.current_phase_name,
        altitude_m=sim.flight_controller.altitude_m,
        speed_knots=sim.flight_controller.speed_knots,
        heading_deg=45.0,
        fuel_remaining_kg=sim.active_platform.fuel_weight_kg,
        status_note=status_note,
    )
    packet = channel.transmit(sample_msg.to_payload_string())
    sim.last_telemetry_packet = packet

    with col_chain:
        st.subheader("2. Oluşturulan Nesne Sarmalama Zinciri (Object Wrapping)")
        st.markdown("**GoF Nesne Kompozisyon İfadesi:**")
        st.code(packet.wrapping_expression, language="python")

        st.markdown("**İçten Dışa İşleme Boru Hattı (Pipeline):**")
        chain_badges = " ➡️ ".join([f"`{layer}`" for layer in packet.wrapping_chain])
        st.markdown(chain_badges)

        m1, m2, m3 = st.columns(3)
        m1.metric("Ham Mesaj Boyutu", f"{packet.original_size_bytes} Bayt")
        m2.metric("Nihai Paket Boyutu", f"{packet.final_size_bytes} Bayt")
        m3.metric("Toplam Katman Sayısı", f"{len(packet.stages)} Aşama")

        fig_size = create_telemetry_stage_size_chart(packet)
        st.plotly_chart(fig_size, use_container_width=True)

    st.divider()

    # Her Aşamadaki Veri Dönüşümü
    st.subheader("🔬 Aşama Aşama Veri Dönüşüm İncelemesi (Stage-by-Stage Transformation)")
    for stage in packet.stages:
        with st.expander(
            f"Adım #{stage.step_index}: {stage.layer_name} — {stage.operation_summary} "
            f"({stage.input_size_bytes}B ➡️ {stage.output_size_bytes}B)",
            expanded=(stage.step_index == len(packet.stages) - 1),
        ):
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                st.caption(f"Girdi Verisi ({stage.input_size_bytes} Bayt):")
                st.code(stage.input_data, language="text")
            with s_col2:
                st.caption(f"Çıktı Verisi ({stage.output_size_bytes} Bayt):")
                st.code(stage.output_data, language="text")
            if stage.metadata:
                st.caption("Katman Meta Verisi:")
                st.json(stage.metadata)

    st.divider()

    # Dıştan İçe Geri Çözme (Receive) ve Katman Çıkarma Testi
    rec_col1, rec_col2 = st.columns(2)
    with rec_col1:
        st.subheader("🔓 Alıcı Tarafı Çözme Doğrulaması (`channel.receive()`)")
        try:
            recovered_str = channel.receive(packet.final_payload)
            st.success("✅ Dış katmandan iç katmana doğru tüm dekoratörler başarıyla çözüldü ve orijinal mesaj doğrulandı!")
            st.code(recovered_str, language="json")
        except TelemetryProcessingError as exc:
            st.error(f"Çözme hatası: {exc}")

    with rec_col2:
        st.subheader("✂️ Çalışma Zamanında Katman Çıkarma (`remove_decorator_layer`)")
        if sim.decorator_layers:
            layer_to_drop = st.selectbox(
                "Zincirden çıkarılacak katmanı seçin:",
                options=sim.decorator_layers,
            )
            if st.button(f"'{layer_to_drop}' Katmanını Zincirden Çıkar"):
                stripped_channel = remove_decorator_layer(channel, layer_to_drop)
                st.info(f"Yeni Sarmalama Zinciri: `{stripped_channel.format_wrapping_chain()}`")
                sim.decorator_layers = [
                    l for l in sim.decorator_layers if l != layer_to_drop
                ]
                st.rerun()
        else:
            st.info("Şu anda yalnızca `BaseRadioChannel` aktif; çıkarılacak dekoratör katmanı yok.")
