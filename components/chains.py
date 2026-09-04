import streamlit as st
import io

from components.detail import render_detail
from db import (
    accept_chain,
    decline_chain,
    get_conn,
    get_item_from_item_id,
    get_user_by_username,
    leave_chain,
)

from services.utils import renderizar_imagen
from PIL import Image, ImageOps
import requests

IMG_FULL = "star_full.png"  # Estrella groga
IMG_HALF = "star_half.png"  # Mitja estrella
IMG_EMPTY = "star_empty.png"  # Estrella grisa
star_size = 50


def get_star_image(position, score):
    diff = float(score) - (position - 1)
    if diff >= 0.75:
        return IMG_FULL
    elif diff >= 0.25:
        return IMG_HALF
    else:
        return IMG_EMPTY


def exit_detail():
    st.session_state.detail_chain = None
    st.session_state.show_chains = True


def exit_chains():
    st.session_state.show_chains = False


def prev_step(state_key, current_step, total_steps):
    st.session_state[state_key] = (current_step - 1) % total_steps


def next_step(state_key, current_step, total_steps):
    st.session_state[state_key] = (current_step + 1) % total_steps


@st.dialog("Avís", width="medium", dismissible=False, icon=":material/info:")
def confirm(action, item_id, chain_id):
    st.subheader(
        f"Estàs segur que vols {action} la cadena d'intercanvi (#{chain_id})?"
    )

    if action == "acceptar":
        st.write(
            "Tingues en compte que el teu article només pot estar actiu en **una cadena alhora**. "
            "En acceptar aquesta proposta, et desvincularàs automàticament de qualsevol altra cadena on estiguessis participant amb aquest objecte."
        )
        st.warning(
            "**Punt de no retorn:** Si la resta d'usuaris d'aquesta cadena també l'accepten, "
            "el tracte es tancarà i ja no podràs canviar d'opinió.",
            icon=":material/warning:",
        )
        confirm_label = "Acceptar cadena"

        def action_callback():
            accept_chain(chain_id, item_id)

    elif action == "rebutjar":
        st.write("Si rebutges aquesta cadena, **s'eliminarà per complet**.")
        st.error(
            "**Punt de no retorn:** Perdràs l'oportunitat d'acceptar aquesta combinació d'intercanvis "
            "per sempre (això és un munt de temps).",
            icon=":material/warning:",
        )
        confirm_label = "Rebutjar cadena"

        def action_callback():
            decline_chain(chain_id, item_id)

    elif action == "sortir de":
        st.write(
            "Et baixes del vaixell? Si decides sortir de la cadena, el teu article tornarà a estar "
            "lliure i disponible per rebre noves ofertes d'intercanvi."
        )
        st.info(
            "**Avís:** Perdràs el teu lloc en aquesta negociació actual i els altres usuaris "
            "podrein trobar una altra cadena per tancar el seu intercanvi.",
            icon=":material/warning:",
        )
        confirm_label = "Sortir de la cadena"

        def action_callback():
            leave_chain(chain_id, item_id)

    st.html("<br>")
    col_confirm, col_cancel = st.columns(2)

    with col_confirm:
        if st.button(
            confirm_label,
            key=f"confirm_{action}_{chain_id}",
            use_container_width=True,
        ):
            action_callback()
            st.rerun()

    with col_cancel:
        if st.button(
            "Tornar enrere",
            key=f"cancel_{action}_{chain_id}",
            use_container_width=True,
        ):
            st.rerun()


@st.dialog(
    "Vista completa de l'article", width="medium", icon=":material/visibility:"
)
def ampliar_imagen(ruta_imagen, item):
    """
    img_src = item["image"]
    # Si es URL de Supabase se descarga en memoria, si es ruta local se abre directo
    img_original = (
        Image.open(io.BytesIO(requests.get(img_src).content))
        if str(img_src).startswith("http")
        else Image.open(img_src)
    )
    st.image(img_original, use_container_width=True)
    """
    renderizar_imagen(item["image"], "img", (275, 200), "normal", False)

# FRAGMENTO INDIVIDUAL DE CADA CADENA PARA OPTIMIZACION
@st.fragment
def render_chain_card(chain_id, pasos, item_status, chain_status, star_size):
    
    st.markdown(
        """
        <style>
        div[class*="st-key-ok_"] button,
        div[class*="st-key-btn_leave_"] button,
        div[class*="st-key-confirm"] button {
            background-color: #0A0C10 !important;
            color: white !important;
            font-weight: bold !important;
        }
        div[class*="st-key-ok_"] button:hover,
        div[class*="st-key-btn_leave_"] button:hover,
        div[class*="st-key-confirm"] button:hover {
            background-color: #2C3649 !important;
            color: white !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    state_key = f"step_index_{chain_id}"
    if state_key not in st.session_state:
        st.session_state[state_key] = 0

    current_step = st.session_state[state_key]
    total_steps = len(pasos)
    rating = pasos[0]["chain_rating"]

    with st.container(border=True):
        col1, col2, col3, _ = st.columns([4, 3, 1, 7])

        with col1:
            st.subheader(f"Cadena d'intercanvi #{chain_id}")

        with col2:
            cols = st.columns(5, gap="xxsmall")
            for i, col in enumerate(cols, start=1):
                star_img = get_star_image(i, rating)
                #img_original = Image.open(star_img)
                #img_recortada = ImageOps.fit(
                #    img_original, (star_size, star_size)
                #)

                with col:
                    #st.image(img_recortada)
                    renderizar_imagen(star_img, "img_sistema", (star_size, star_size), "normal", False)

        with col3:
            st.subheader(rating)

        col_progress, col_btn = st.columns([4, 1])

        with col_progress:
            porcentaje_progreso = (current_step / (total_steps - 1)) * 100
            ancho_telon = 100 - porcentaje_progreso

            segmentos_html = ""
            for i in range(total_steps - 1):
                color_segmento = (
                    "#24b653"
                    if pasos[i]["status"] == "accepted"
                    else "#FF9F4B"
                )
                segmentos_html += f'<div class="progress-segment" style="background-color: {color_segmento};"></div>'

            nodos_html = ""
            for i in range(total_steps):
                status_nodo = pasos[i]["status"]
                clase_activa = "active" if i <= current_step else ""
                clase_viendo = "viendo" if i == current_step else ""
                clase_mine = "is-mine" if pasos[i].get("is_mine") else ""
                nodos_html += f'<div class="step-node {clase_activa} {status_nodo} {clase_viendo} {clase_mine}">{i+1}</div>'

            html_code = f"""
            <style>
            .stepper-container {{ position: relative; display: flex; justify-content: space-between; align-items: center; width: 90%; padding: 30px 15px 10px 15px; margin-bottom: 20px; box-sizing: border-box; }}
            .stepper-color-track {{ position: absolute; left: 12px; right: 12px; height: 4px; display: flex; z-index: 1; }}
            .progress-segment {{ flex-grow: 1; height: 100%; }}
            .stepper-curtain {{ position: absolute; right: 0; top: 0; bottom: 0; background-color: #E0E0E0; transition: width 0.4s ease-in-out; z-index: 2; }}
            .step-node {{ position: relative; width: 24px; height: 24px; border-radius: 50%; background-color: #E0E0E0; color: #888888; font-size: 13px; font-weight: bold; display: flex; justify-content: center !important; align-items: center !important; z-index: 3; box-shadow: 0 0 0 6px white; transition: all 0.3s ease-in-out; }}
            .step-node.is-mine::after {{ content: "Tu"; position: absolute; top: -20px; left: 50%; transform: translateX(-50%); font-size: 11px; font-weight: 800; color: #0A0C10; white-space: nowrap; }}
            .step-node.active {{ background-color: #FF9F4B; color: white; }}
            .step-node.accepted {{ background-color: #24b653 !important; color: white !important; }}
            .step-node.declined {{ background-color: #FF9F4B !important; color: white !important; }}
            .step-node.viendo {{ transform: scale(1.1); box-shadow: 0 0 0 3px white, 0 0 0 6px #000000 !important; z-index: 4; }}
            </style>

            <div class="stepper-container">
                <div class="stepper-color-track">
                    {segmentos_html}
                    <div class="stepper-curtain" style="width: {ancho_telon}%;"></div>
                </div>
                {nodos_html}
            </div>
            """
            st.markdown(html_code, unsafe_allow_html=True)
            st.write("")

        with col_btn:
            if item_status == "neutral" and chain_status == "pending":
                if st.button(
                    "Acceptar cadena",
                    key=f"ok_{chain_id}",
                    use_container_width=True,
                ):
                    confirm("acceptar", item_id, chain_id)
                if st.button(
                    "Rebutjar cadena",
                    key=f"ko_{chain_id}",
                    use_container_width=True,
                ):
                    confirm("rebutjar", item_id, chain_id)

            elif item_status == "accepted" and chain_status == "pending":
                if st.button(
                    "Sortir de la cadena",
                    key=f"btn_leave_{chain_id}",
                    use_container_width=True,
                ):
                    confirm("sortir de", item_id, chain_id)
                if st.button(
                    "Rebutjar cadena",
                    key=f"btn_reject_acc_{chain_id}",
                    use_container_width=True,
                ):
                    confirm("rebutjar", item_id, chain_id)

        item = get_item_from_item_id(pasos[current_step]["item_id"])

        (
            col_btn_previous,
            col_image,
            col_info,
            col_btn_next,
        ) = st.columns([1, 6, 6, 1], gap="medium")

        st.markdown(
            """
            <style>
            div[class*="st-key-prev_"] button,
            div[class*="st-key-next_"] button {
                height: 300px !important;
                background-color: #F0F2F6 !important;
                color: #555555 !important;
                border: none !important;
                border-radius: 8px !important;
                transition: all 0.3s ease !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                line-height: 1 !important;
            }
            div[class*="st-key-prev_"] button *,
            div[class*="st-key-next_"] button * {
                font-size: 35px !important;
                line-height: 1 !important;
                display: block !important;
            }
            div[class*="st-key-prev_"] button:hover,
            div[class*="st-key-next_"] button:hover {
                background-color: #D2D8E4 !important;
                color: #FF4B4B !important;
            }
            </style>
        """,
            unsafe_allow_html=True,
        )

        with col_btn_previous:
            st.button(
                "❮",
                key=f"prev_{chain_id}",
                use_container_width=True,
                on_click=prev_step,
                args=(state_key, current_step, total_steps),
            )

        with col_image:
            img_src = item.get("image_optimized") or item.get("image")
            """
            if img_src:
                # Descarga de la URL pública de Supabase
                img_original = (
                    Image.open(io.BytesIO(requests.get(img_src).content))
                    if str(img_src).startswith("http")
                    else Image.open(img_src)
                )
                img_recortada = ImageOps.fit(img_original, (500, 200))
                st.image(img_recortada, use_container_width=True)
            """
            renderizar_imagen(item.get("image_optimized"), "img_opt", (500, 200), "normal", False)

            if st.button(
                "Ampliar imatge",
                icon=":material/zoom_in:",
                key=f"{chain_id}_{item['item_id']}",
                use_container_width=True,
            ):
                ampliar_imagen(item["image"], item)

        with col_info:
            user = get_user_by_username(item["user"])
            st.write(
                f"**Usuari:** {item['user']} :grey[★ ({user['rating']})]"
            )
            st.write(f"**Ofereix:** {item['have']}")
            st.write(f"**Vol aconseguir:** {item['want']}")

            if pasos[current_step]["status"] == "neutral":
                st.write(
                    "**Què li sembla l'intercanvi?** :orange[Esperant resposta]"
                )
            elif pasos[current_step]["status"] == "accepted":
                st.write(
                    "**Què li sembla l'intercanvi?** :green[Accepta l'intercanvi]"
                )

            with st.expander("Veure descripció de l'article"):
                st.write(f"**Descripció:** {item['description']}")

        with col_btn_next:
            st.button(
                "❯",
                icon_position="right",
                key=f"next_{chain_id}",
                use_container_width=True,
                on_click=next_step,
                args=(state_key, current_step, total_steps),
            )

def chain_detail(item_id, chain_status, item_status, tab):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT have FROM items WHERE item_id = %s", (item_id,))
    have_text = c.fetchone()[0]
    conn.close()

    st.button(
        "Tornar",
        icon=":material/arrow_left_alt:",
        key="exit_detail_chain",
        type="secondary",
        on_click=exit_detail,
    )

    if tab == 1:
        st.header(f"Cadenes obertes amb el teu article {have_text}")
    elif tab == 2:
        st.header(f"Cadena que has acceptat amb el teu article {have_text}")
    elif tab == 3:
        st.header(f"Cadena d'intercanvi del teu article {have_text}")

    st.divider()

    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        SELECT ci.chain_id, ci.item_id, ci.position, i.have, i.want, i.user, ci.status, c.rating
        FROM chain_items ci
        JOIN items i ON ci.item_id = i.item_id
        JOIN chains c ON ci.chain_id = c.chain_id
        WHERE c.status = %s 
        AND ci.chain_id IN (
            SELECT chain_id 
            FROM chain_items 
            WHERE item_id = %s AND status = %s
        )
        ORDER BY c.rating DESC, ci.position ASC
    """,
        (chain_status, item_id, item_status),
    )
    lineas_cadenas = c.fetchall()
    conn.close()

    if not lineas_cadenas:
        st.info(
            "Ho sentim, no hi ha cadenes per a aquest article en aquesta secció.",
            icon=":material/info:",
        )

    chains = {}
    for (
        chain_id,
        c_item_id,
        pos,
        have,
        want,
        user,
        status,
        chain_rating,
    ) in lineas_cadenas:
        if chain_id not in chains:
            chains[chain_id] = []

        if user == st.session_state.user:
            user = f"{user} (tu)"
            is_mine = 1
        else:
            is_mine = 0

        if status == "neutral":
            texto_paso = f"**{user}** vol *'{want}'* i té *'{have}'* (esperant resposta)."
        elif status == "accepted":
            texto_paso = (
                f"**{user}** vol *'{want}'* i té *'{have}'* (accepta la cadena)."
            )
        elif status == "declined":
            texto_paso = f"**{user}** vol *'{want}'* i té *'{have}'* (rebutja la cadena)."

        chains[chain_id].append({
            "texto": texto_paso,
            "item_id": c_item_id,
            "status": status,
            "is_mine": is_mine,
            "chain_rating": chain_rating,
        })

    # Renderizamos cada tarjeta en su propio fragmento aislado
    for chain_id, pasos in chains.items():
        render_chain_card(chain_id, pasos, item_status, chain_status, star_size)

def render_chains():
    st.button(
        "Tornar",
        key="exit_chains",
        icon=":material/arrow_left_alt:",
        on_click=exit_chains,
    )

    st.header("Les teves cadenes d'intercanvi")

    if "user" not in st.session_state:
        st.warning(
            "Si us plau, inicia sessió per gestionar els teus intercanvis."
        )
        return

    tab1, tab2, tab3 = st.tabs(
        ["Cadenes obertes", "Cadenes que has acceptat", "Cadenes tancades"]
    )

    # TAB 1: Cadenas Abiertas
    with tab1:
        conn = get_conn()
        c = conn.cursor()
        c.execute(
            """
            SELECT i.item_id, i.have, COUNT(DISTINCT ci.chain_id) as num_cadenas
            FROM items i
            JOIN chain_items ci ON i.item_id = ci.item_id
            JOIN chains c ON ci.chain_id = c.chain_id
            WHERE i.user = %s AND ci.status = 'neutral' AND c.status = 'pending'
            GROUP BY i.item_id, i.have
        """,
            (st.session_state.user,),
        )
        items_in_open_chains = c.fetchall()
        conn.close()

        if not items_in_open_chains:
            st.info(
                "De moment, no hi ha noves cadenes d'intercanvi per als teus articles."
            )
        else:
            for row in items_in_open_chains:
                item_id, have_text, num_cadenas = row[0], row[1], row[2]
                with st.container(border=True):
                    col_text, col_btn = st.columns(
                        [4, 1], vertical_alignment="center"
                    )
                    with col_text:
                        msg = (
                            f"El teu article **{have_text}** ha entrat en **1** cadena d'intercanvi."
                            if num_cadenas == 1
                            else f"El teu article **{have_text}** ha entrat en **{num_cadenas}** cadenes d'intercanvi."
                        )
                        st.markdown(msg)
                    with col_btn:
                        if st.button(
                            "Veure cadena",
                            key=f"btn_cadenas_abiertas_{item_id}",
                            use_container_width=True,
                        ):
                            st.session_state.detail_chain = [
                                item_id,
                                "pending",
                                "neutral",
                                1,
                            ]
                            st.rerun()

    # TAB 2: Cadenas Aceptadas
    with tab2:
        conn = get_conn()
        c = conn.cursor()
        c.execute(
            """
            SELECT i.item_id, i.have, COUNT(DISTINCT ci.chain_id) as num_cadenas
            FROM items i
            JOIN chain_items ci ON i.item_id = ci.item_id
            JOIN chains c ON ci.chain_id = c.chain_id
            WHERE i.user = %s AND ci.status = 'accepted' AND c.status = 'pending'
            GROUP BY i.item_id, i.have
        """,
            (st.session_state.user,),
        )
        items_in_accepted_chains = c.fetchall()
        conn.close()

        if not items_in_accepted_chains:
            st.info("Les cadenes que acceptis apareixeran aquí.")
        else:
            for row in items_in_accepted_chains:
                item_id, have_text, num_cadenas = row[0], row[1], row[2]
                with st.container(border=True):
                    col_text, col_btn = st.columns(
                        [4, 1], vertical_alignment="center"
                    )
                    with col_text:
                        st.markdown(
                            f"Has acceptat participar en l'intercanvi del teu article **{have_text}**."
                        )
                    with col_btn:
                        if st.button(
                            "Veure cadena",
                            key=f"btn_cadenas_aceptadas_{item_id}",
                            use_container_width=True,
                        ):
                            st.session_state.detail_chain = [
                                item_id,
                                "pending",
                                "accepted",
                                2,
                            ]
                            st.rerun()

    # TAB 3: Cadenas Cerradas
    with tab3:
        conn = get_conn()
        c = conn.cursor()
        c.execute(
            """
            SELECT i.item_id, i.have, COUNT(DISTINCT ci.chain_id) as num_cadenas
            FROM items i
            JOIN chain_items ci ON i.item_id = ci.item_id
            JOIN chains c ON ci.chain_id = c.chain_id
            WHERE i.user = %s AND ci.status = 'accepted' AND c.status = 'accepted'
            GROUP BY i.item_id, i.have
        """,
            (st.session_state.user,),
        )
        items_in_closed_chains = c.fetchall()
        conn.close()

        if not items_in_closed_chains:
            st.info("Sembla que encara no hi ha cap cadena tancada.")
        else:
            for row in items_in_closed_chains:
                item_id, have_text, num_cadenas = row[0], row[1], row[2]
                with st.container(border=True):
                    col_text, col_btn = st.columns(
                        [4, 1], vertical_alignment="center"
                    )
                    with col_text:
                        st.markdown(
                            f"El teu article **{have_text}** està dins d'una cadena tancada!"
                        )
                    with col_btn:
                        if st.button(
                            "Veure cadena",
                            key=f"btn_cadenas_cerradas_{item_id}",
                            use_container_width=True,
                        ):
                            st.session_state.detail_chain = [
                                item_id,
                                "accepted",
                                "accepted",
                                3,
                            ]
                            st.rerun()
