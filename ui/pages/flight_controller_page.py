"""
Ekran 5: Flight Controller — GoF State Kalıbı ile Uçuş Fazları ve Durum Geçişleri.
"""

from __future__ import annotations

import streamlit as st

from src.models.flight_state_models import FlightCommands
from src.patterns.state import PreflightIdleState
from src.simulation.mission_simulator import MissionSimulator
from ui.components.charts import create_flight_dynamics_chart
from ui.components.theme import render_pattern_header


def render_flight_controller_page(sim: MissionSimulator) -> None:
    """State tasarım kalıbı uçuş fazı kontrol ekranını çizer."""
    render_pattern_header(
        badge="4. STATE KALIBI — DAVRANIŞSAL (BEHAVIORAL)",
        title="Uçuş Fazları, Komut Yetkilendirmesi ve Acil Durum (Failsafe) Yönetimi",
        problem_solved=(
            "İHA'nın bulunduğu uçuş fazına (Yerde Bekleme, Kalkış, Seyir, Temsili Görev, Acil Eve Dönüş) "
            "göre değişen irtifa kontrolünü, motor tepkisini ve geçerli komut kurallarını FlightController "
            "içindeki devasa if-elif-else bloklarından kurtarır. Her uçuş fazı kendi sınıfında kapsüllenir."
        ),
        participants="FlightController, FlightPhaseState (ABC), PreflightIdleState, TakeOffState, CruiseState, CombatState, EmergencyReturnState",
    )

    fc = sim.flight_controller
    summary = fc.get_status_summary()

    # Üst Durum Metrikleri
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Aktif Faz (State)", summary["current_phase"], summary["state_class"])
    m2.metric("Simüle İrtifa", f"{summary['altitude_m']:.0f} m")
    m3.metric("Hava Hızı", f"{summary['speed_knots']:.0f} knots")
    m4.metric("Motor İtkisi (Throttle)", f"%{summary['throttle_pct']:.0f}")
    m5.metric("Temsili Görev Adımı", str(summary["completed_sim_tasks"]))

    st.info(f"**Aktif Motor & Otopilot Tepki Rejimi:** {summary['engine_response']}")
    if summary["emergency_reason"]:
        st.error(f"🚨 **AKTİF ACİL DURUM (FAILSAFE):** {summary['emergency_reason']}")

    col_cmd, col_rules = st.columns([3, 2])

    with col_cmd:
        st.subheader("🎮 Uçuş Kontrol Komut Paneli (`execute_command`)")
        st.caption(
            "Yeşil işaretli (✅) komutlar mevcut fazda geçerlidir; kırmızı işaretli (🚫) "
            "komutlara tıklandığında aktif `FlightPhaseState` sınıfının geçersiz komutu nasıl reddettiğini test edebilirsiniz."
        )

        allowed_set = set(summary["allowed_commands"])
        cmd_descriptions = {
            FlightCommands.START_ENGINE_CHECKS: "Motor & Aviyonik Testi (START_ENGINE_CHECKS)",
            FlightCommands.TAKE_OFF: "Kalkışa Geç (TAKE_OFF)",
            FlightCommands.CLIMB_TO_CRUISE: "Seyir İrtifasına Tırman (CLIMB_TO_CRUISE)",
            FlightCommands.MAINTAIN_VECTOR: "Seyir Vektörünü Koru (MAINTAIN_VECTOR)",
            FlightCommands.ENTER_MISSION_ZONE: "Görev Bölgesine Gir (ENTER_MISSION_ZONE)",
            FlightCommands.EXECUTE_SIM_TASK: "Temsili Görev Adımı Yürüt (EXECUTE_SIM_TASK)",
            FlightCommands.EXIT_MISSION_ZONE: "Görev Bölgesinden Çık (EXIT_MISSION_ZONE)",
            FlightCommands.LAND_AND_PARKING: "İniş ve Park (LAND_AND_PARKING)",
        }

        btn_cols = st.columns(2)
        for idx, (cmd_key, cmd_label) in enumerate(cmd_descriptions.items()):
            is_allowed = cmd_key in allowed_set
            icon = "✅" if is_allowed else "🚫"
            target_col = btn_cols[idx % 2]
            if target_col.button(
                f"{icon} {cmd_label}",
                key=f"cmd_btn_{cmd_key}",
                use_container_width=True,
                type="primary" if is_allowed else "secondary",
            ):
                res = fc.execute_command(cmd_key)
                if res.accepted:
                    st.success(f"✔️ **Kabul Edildi (`{res.previous_phase}` ➡️ `{res.current_phase}`):** {res.message}")
                else:
                    st.error(f"❌ **Reddedildi (`{res.current_phase}`):** {res.message}")

        st.divider()
        st.markdown("#### 🚨 Acil Durum (Failsafe) Senaryo Tetikleyicisi (`trigger_emergency`)")
        emg_col1, emg_col2, emg_col3 = st.columns([2, 1, 1])
        emg_reason = emg_col1.selectbox(
            "Simüle Edilecek Acil Durum Senaryosu:",
            options=[
                "Veri Bağı (Data Link) Sinyal Kesintisi",
                "Kritik Yakıt Seviyesi Uyarısı",
                "İkincil Alternatör / Sensör Güç Kaybı",
            ],
        )
        if emg_col2.button("🚨 Acil Eve Dönüş Tetikle", use_container_width=True):
            res_emg = fc.trigger_emergency(emg_reason)
            st.warning(res_emg.message)
            st.rerun()

        if emg_col3.button("🔄 Durumu Sıfırla (Idle)", use_container_width=True):
            fc.clear_emergency_reason()
            fc.transition_to(PreflightIdleState())
            st.rerun()

    with col_rules:
        st.subheader("📌 Aktif Faz Kuralları")
        st.markdown(f"**Aktif Durum Sınıfı:** `{summary['state_class']}`")
        st.markdown("**İzin Verilen Komutlar (`allowed_commands`):**")
        for ac in summary["allowed_commands"]:
            st.markdown(f"- 🟢 `{ac}`")

        rejected_cmds = [
            c for c in FlightCommands.ALL_COMMANDS if c not in summary["allowed_commands"]
        ]
        st.markdown("**Bu Fazda Reddedilecek Komutlar:**")
        for rc in rejected_cmds:
            st.markdown(f"- 🔴 `{rc}`")

    st.divider()

    # Grafik ve Geçiş Geçmişi Tablosu
    st.subheader("📈 Uçuş Dinamikleri ve Durum Geçiş Geçmişi")
    dyn_fig = create_flight_dynamics_chart(fc)
    st.plotly_chart(dyn_fig, use_container_width=True)

    history = fc.get_transition_history()
    if history:
        st.dataframe(
            [
                {
                    "Adım": idx + 1,
                    "Komut": h.command,
                    "Durum": "KABUL EDİLDİ" if h.accepted else "REDDEDİLDİ",
                    "Önceki Faz": h.previous_phase,
                    "Yeni Faz": h.current_phase,
                    "İrtifa (m)": h.altitude_m,
                    "Hız (kts)": h.speed_knots,
                    "Motor (%)": h.throttle_pct,
                    "Açıklama": h.message,
                }
                for idx, h in enumerate(reversed(history))
            ],
            use_container_width=True,
            hide_index=True,
        )
