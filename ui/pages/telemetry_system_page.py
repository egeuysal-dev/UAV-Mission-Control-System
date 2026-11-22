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
from ui.components.charts import (
    create_rf_spectrum_chart,
    create_telemetry_stage_size_chart,
)
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

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Ham Mesaj Boyutu", f"{packet.original_size_bytes} Bayt")
        m2.metric("Nihai Paket Boyutu", f"{packet.final_size_bytes} Bayt")
        overhead_pct = round(
            ((packet.final_size_bytes - packet.original_size_bytes) / max(1, packet.original_size_bytes)) * 100.0,
            1,
        )
        m3.metric("Paket Değişimi", f"{overhead_pct:+.1f}%", f"{len(packet.stages)} Aşama")
        est_latency_ms = round(
            1.8
            + (1.4 if "CompressionDecorator" in sim.decorator_layers else 0.0)
            + (2.6 if "AesEncryptionDecorator" in sim.decorator_layers else 0.0)
            + (3.1 if "AntiJammingDecorator" in sim.decorator_layers else 0.0),
            1,
        )
        m4.metric("Tahmini Gecikme", f"{est_latency_ms} ms")

        fig_size = create_telemetry_stage_size_chart(packet)
        st.plotly_chart(fig_size, use_container_width=True)

    st.divider()

    # Öneri F: Elektronik Harp (EW) RF Spektrum Analizörü ve Siber Saldırı Laboratuvarı
    st.subheader("📶 Elektronik Harp (EW) RF Spektrum Analizörü ve Siber Saldırı (MITM / Bit-Flip) Laboratuvarı")
    ew_col1, ew_col2 = st.columns([3, 2])

    with ew_col1:
        jam_intensity = st.slider(
            "Düşman Elektronik Karıştırma (Jamming) Şiddeti (+dB):",
            min_value=5.0,
            max_value=32.0,
            value=20.0,
            step=1.0,
            disabled=not sim.simulate_interference,
        )
        rf_fig = create_rf_spectrum_chart(
            frequency_band=sim.frequency_band,
            active_layers=sim.decorator_layers,
            jamming_active=sim.simulate_interference,
            jamming_intensity_db=jam_intensity,
        )
        st.plotly_chart(rf_fig, use_container_width=True)

    with ew_col2:
        st.markdown("#### ⚔️ Canlı Siber Saldırı & Paket Bozulma Testleri")
        st.caption(
            "İletilen gerçek telemetri çerçevesi (`packet.final_payload`) üzerinde saldırı/parazit "
            "simüle ederek aktif Decorator katmanlarının (`AES-256-GCM` ve `CRC32/FEC`) tepkisini test edin."
        )

        # Test 1: RF Kanal Paraziti (Bit-Flip Bozulma)
        if st.button("⚡ 1. RF Paraziti Enjekte Et (Gövde Bit-Flip Bozulması)", use_container_width=True, type="primary"):
            frame = packet.final_payload
            # Çerçevenin son 3 karakterini boz (RF gürültüsü simülasyonu)
            corrupted_frame = frame[:-3] + ("X" if frame[-3] != "X" else "Z") + frame[-2:]
            st.code(f"Bozulmuş Çerçeve Sonu: ...{corrupted_frame[-48:]}", language="text")
            try:
                repaired = channel.receive(corrupted_frame)
                if "AntiJammingDecorator" in sim.decorator_layers:
                    st.success(
                        "✅ **AntiJammingDecorator (CRC32/FEC) PAKETİ KURTARDI!** "
                        "CRC32 uyuşmazlığı tespit edildi ve yedek FEC bloğundan orijinal telemetri hatasız onarıldı."
                    )
                    st.code(repaired, language="json")
                else:
                    st.warning(
                        "⚠️ **KORUMASIZ KANAL UYARISI:** `AntiJammingDecorator` ve `AesEncryptionDecorator` "
                        "kapalı olduğu için bozuk veri sessizce alıcıya ulaştı (veri bütünlüğü bozuldu)!"
                    )
                    st.code(repaired, language="text")
            except TelemetryProcessingError as exc:
                st.error(
                    f"❌ **Alıcı Paketi Reddetti (`TelemetryProcessingError`):** {exc} "
                    f"(Not: RF bit hatalarını otomatik onarmak için `AntiJammingDecorator` katmanını en dışa ekleyin.)"
                )

        # Test 2: MITM (Ortadaki Adam) Yetkisiz Paket Değiştirme Saldırısı
        if st.button("🕵️ 2. MITM Saldırısı (Şifreli/Açık Pakete Yetkisiz Müdahale)", use_container_width=True):
            frame = packet.final_payload
            if "AES256GCM:" in frame:
                # AES-256-GCM şifreli metninin ortasından karakter değiştir (FEC'yi de aşan bütünlük saldırısı)
                tampered_frame = frame.replace("AES256GCM:", "AES256GCM:")
                aes_idx = tampered_frame.find("AES256GCM:") + 18
                if aes_idx < len(tampered_frame) - 2:
                    flipped_ch = "A" if tampered_frame[aes_idx] != "A" else "B"
                    tampered_frame = (
                        tampered_frame[:aes_idx] + flipped_ch + tampered_frame[aes_idx + 1 :]
                    )
                # Eğer AntiJamming dışarıdaysa ve saldırgan FEC bloğunu da bozduysa AES-GCM yakalar
                if tampered_frame.startswith("AJ_FEC|"):
                    # Saldırganın hem gövdeyi hem de FEC bloğunu değiştirdiği gelişmiş MITM simülasyonu
                    parts = tampered_frame.split("|", 4)
                    if len(parts) == 5:
                        fec_body = parts[2]
                        parts[2] = fec_body[:-2] + ("Q" if fec_body[-2] != "Q" else "W") + fec_body[-1]
                        tampered_frame = "|".join(parts)
            else:
                # Şifreleme yoksa saldırgan telemetri irtifasını/notunu açıkça değiştirir!
                tampered_frame = frame.replace("NOMINAL", "SPOOFED_BY_MITM")
                if tampered_frame == frame:
                    tampered_frame = frame[:-2] + "99"

            try:
                received_after_mitm = channel.receive(tampered_frame)
                st.error(
                    "🚨 **GÜVENLİK AÇIĞI TESPİT EDİLDİ (MITM BAŞARILI OLDU)!** "
                    "`AesEncryptionDecorator` aktif olmadığı için saldırgan telemetri mesajını fark edilmeden değiştirdi:"
                )
                st.code(received_after_mitm, language="text")
            except TelemetryProcessingError as exc:
                st.success(
                    f"🛡️ **SİBER SALDIRI ENGELLENDİ!** Aktif güvenlik dekoratörleri yetkisiz paket "
                    f"değişikliğini (AES-256-GCM 128-bit Auth Tag / CRC32) anında yakalayıp reddetti:\n\n`{exc}`"
                )

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
