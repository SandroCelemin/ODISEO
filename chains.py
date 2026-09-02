# ACLARACIONS

# Barra de progrés a la cadena:

    # Hi ha 3 capes: (ci)

# --------------------
import streamlit as st
from db import get_conn, get_items, get_item_from_item_id, accept_chain, leave_chain, decline_chain, get_user_by_username
from components.detail import render_detail
from PIL import Image, ImageOps

IMG_FULL = "star_full.png"    # Estrella groga
IMG_HALF = "star_half.png"    # Mitja estrella
IMG_EMPTY = "star_empty.png"  # Estrella grisa
star_size = 50

def get_star_image(position, score):
    """
    Determina quina imatge d'estrella utilitzar per a la posició (1 a 5) donada la puntuació.
    """
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
def confirm(action, item_id, chain_id): # action -> 'acceptar', 'rebutjar', 'sortir de'
    
    st.subheader(f"Estàs segur que vols {action} la cadena d'intercanvi (#{chain_id})?")
    
    if action == 'acceptar':
        st.write(
            "Tingues en compte que el teu article només pot estar actiu en **una cadena alhora**. "
            "En acceptar aquesta proposta, et desvincularàs automàticament de qualsevol altra cadena on estiguessis participant amb aquest objecte."
        )
        
        st.warning(
            "**Punt de no retorn:** Si la resta d'usuaris d'aquesta cadena també l'accepten, "
            "el tracte es tancarà i ja no podràs canviar d'opinió.",
            icon=":material/warning:"
        )
        
        confirm_label = "Acceptar cadena"
        
        def action_callback():
            accept_chain(chain_id, item_id)
        """
        col_confirm, col_cancel = st.columns(2)
        
        with col_confirm:
            if st.button("Acceptar cadena", key=f"confirm_{chain_id}", use_container_width=True):
                accept_chain(chain_id, item_id)
                st.rerun()
                
        with col_cancel:
            if st.button("Cancel·lar", key=f"cancelar", use_container_width=True):
                #accept_chain(chain_id, item_id)
                st.rerun()
        """
    elif action == 'rebutjar':
        st.write(
            "Si rebutges aquesta cadena, **s'eliminarà per complet**."
        )
        st.error(
            "**Punt de no retorn:** Perdràs l'oportunitat d'acceptar aquesta combinació d'intercanvis "
            "per sempre (això és un munt de temps).",
            icon=":material/warning:"
        )        

        confirm_label = "Rebutjar cadena"
        
        def action_callback():
            decline_chain(chain_id, item_id)        
        """
        col_confirm, col_cancel = st.columns(2)
        
        with col_confirm:
            if st.button("Rebutjar cadena", key=f"confirm_{chain_id}", use_container_width=True):
                decline_chain(chain_id, item_id)                        
                st.rerun()
                
        with col_cancel:
            if st.button("Cancel·lar", key=f"cancelar", use_container_width=True):
                #accept_chain(chain_id, item_id)
                st.rerun()
        """
    elif action == 'sortir de':
        st.write(
            "Et baixes del vaixell? Si decides sortir de la cadena, el teu article tornarà a estar "
            "lliure i disponible per rebre noves ofertes d'intercanvi."
        )
        st.info(
            "**Avís:** Perdràs el teu lloc en aquesta negociació actual i els altres usuaris "
            "podrien trobar una altra cadena per tancar el seu intercanvi.",
            icon=":material/warning:"
        )        
        
        confirm_label = "Sortir de la cadena"
        
        def action_callback():
            leave_chain(chain_id, item_id)
        """
        col_confirm, col_cancel = st.columns(2)
        
        with col_confirm:
            if st.button("Sortir de la cadena", key=f"confirm_{chain_id}", use_container_width=True):
                # leave_chain(chain_id, item_id)
                st.rerun()
                
        with col_cancel:
            if st.button("Cancel·lar", key=f"cancelar", use_container_width=True):
                #accept_chain(chain_id, item_id)
                st.rerun()
        """
        
    st.html("<br>")
    
    col_confirm, col_cancel = st.columns(2)
    
    with col_confirm:
        if st.button(confirm_label, key=f"confirm_{action}_{chain_id}", use_container_width=True,):
            #with st.spinner("Processant..."):
            #if action_callback:
            action_callback()
            st.rerun()
            
    with col_cancel:
        if st.button("Tornar enrere", key=f"cancel_{action}_{chain_id}", use_container_width=True):
            st.rerun()
    
@st.dialog("Vista completa de l'article", width="medium", icon=":material/visibility:")
def ampliar_imagen(ruta_imagen, item):
    
    img_original = Image.open(item["image"])
    st.image(img_original, use_container_width=True)
    #st.caption("Utilitza les fletxes de la cantonada superior dreta si vols veure-la encara més gran.")

def chain_detail(item_id, chain_status, item_status, tab):

    conn = get_conn()
    c = conn.cursor()
    
    try:
        c.execute("""
            SELECT i.have
            FROM items i
            WHERE i.item_id = ?
        """, (item_id,))
        
        result = c.fetchone()
        have_text = result[0] if result else "Desconegut"
        
    except Exception as e:
        st.error(f"Error en cercar l'article: {e}")
        have_text = None
    finally:
        conn.close()

    st.button("Tornar", icon=":material/arrow_left_alt:", key="exit_detail_chain", type="secondary", on_click=exit_detail)
    
    if tab == 1:
        st.header(f"Cadenes obertes amb el teu article {have_text}")
    elif tab == 2:
        st.header(f"Cadena que has acceptat amb el teu article {have_text}")
    elif tab == 3:
        st.header(f"Cadena d'intercanvi del teu article {have_text}")

    st.divider()
    
    conn = get_conn()
    c = conn.cursor()
    
    try:
        
        c.execute("""
            SELECT ci.chain_id, ci.item_id, ci.position, i.have, i.want, i.user, ci.status, c.rating
            FROM chain_items ci
            JOIN items i ON ci.item_id = i.item_id
            JOIN chains c ON ci.chain_id = c.chain_id
            WHERE c.status = ? 
            AND ci.chain_id IN (
                SELECT chain_id 
                FROM chain_items 
                WHERE item_id = ? AND status = ?
            )
            ORDER BY c.rating DESC, ci.position ASC
        """, (chain_status, item_id, item_status))        
        
        lineas_cadenas = c.fetchall()
        
    except Exception as e:
        st.error(f"Error en carregar el detall: {e}")
        lineas_cadenas = []
    finally:
        conn.close()
    
    if not lineas_cadenas:
        st.info("Ho sentim, no hi ha cadenes per a aquest article en aquesta secció.", icon=":material/info:")
    
    # Agrupem les dades per cada chain_id únic en un diccionari
    chains = {}
    for chain_id, c_item_id, pos, have, want, user, status, chain_rating in lineas_cadenas:
        
        if chain_id not in chains:
            chains[chain_id] = []
            
        #if user == st.session_state.user:
            
        if user == st.session_state.user:
            user = f"{user} (tu)"
            is_mine = 1
        else:
            is_mine = 0
        
        if status == 'neutral':
            #chains[chain_id].append(f"**{user}** vol *'{want}'* i té *'{have}'* (esperant resposta).")
            texto_paso = (f"**{user}** vol *'{want}'* i té *'{have}'* (esperant resposta).")
        elif status == 'accepted':
            #chains[chain_id].append(f"**{user}** vol *'{want}'* i té *'{have}'* (accepta).")
            texto_paso = (f"**{user}** vol *'{want}'* i té *'{have}'* (accepta la cadena).")
        elif status == 'declined':
            #chains[chain_id].append(f"**{user}** vol *'{want}'* i té *'{have}'* (rebutja).")
            texto_paso = (f"**{user}** vol *'{want}'* i té *'{have}'* (rebutja la cadena).")

        chains[chain_id].append({
            "texto": texto_paso,
            "item_id": c_item_id,
            "status": status,
            "is_mine": is_mine,
            "chain_rating": chain_rating
        })
        
    # Dibuixem cada cadena disponible de forma independent
    for chain_id, pasos in chains.items():
        
        st.markdown("""
            <style>
            
            /* Botons Positius: Acceptar (ok_) i Sortir (btn_leave_) */
            div[class*="st-key-ok_"] button,
            div[class*="st-key-btn_leave_"] button,
            div[class*="st-key-confirm"] button {
                background-color: #0A0C10 !important;
                color: white !important;
                font-weight: bold !important;
            }
            /* Hover: en passar el ratolí, s'enfosqueix */
            div[class*="st-key-ok_"] button:hover,
            div[class*="st-key-btn_leave_"] button:hover,
            div[class*="st-key-confirm"] button:hover {
                background-color: #2C3649 !important;
                color: white !important;
            }
            
            /* Botons Negatius: Rebutjar (ko_) i Rebutjar Acceptat (btn_reject_acc_) */
            /*div[class*="st-key-ko_"] button,
            div[class*="st-key-btn_reject_acc_"] button {
                border-radius: 5px !important;
                background-color: transparent !important;
                color: black !important;
                border: 2px solid #99A7C2 !important;
                font-weight: bold !important;
            }
            /* Hover: en passar el ratolí, es reomple de vermell */
            div[class*="st-key-ko_"] button:hover,
            div[class*="st-key-btn_reject_acc_"] button:hover {
                background-color: #C2C2C2 !important;
                color: black !important;
            }*/
            
            </style>
            
        """, unsafe_allow_html=True)
        
        state_key = f"step_index_{chain_id}"
        if state_key not in st.session_state:
            st.session_state[state_key] = 0
            
        current_step = st.session_state[state_key]
        total_steps = len(pasos)
        rating = chains[chain_id][0]["chain_rating"]

        #porcentaje_progreso = (current_step / (total_steps - 1)) * 100

        with st.container(border=True):
            
            col1, col2, col3, _ = st.columns([4,3,1,7])
            
            with col1:
                st.subheader(f"Cadena d'intercanvi #{chain_id}")
                        
            with col2:
                cols = st.columns(5, gap="xxsmall")
                
                for i, col in enumerate(cols, start=1):
                    star_img = get_star_image(i, rating)
                    
                    img_original = Image.open(star_img)
                    img_recortada = ImageOps.fit(img_original, (star_size, star_size)) # ImageOps.fit s'encarrega que no es deformi la foto en retallar-la
                    
                    with col:
                        st.image(img_recortada)
                
            with col3:
                st.subheader(rating)
            
            col_progress, col_btn = st.columns([4,1])
            
            with col_progress:
                
                # 1. Calculem la posició del teló gris (l'animació fluïda en bloc)
                #if total_steps > 1:
                porcentaje_progreso = (current_step / (total_steps - 1)) * 100
                #else:
                #    porcentaje_progreso = 0

                ancho_telon = 100 - porcentaje_progreso

                # 2. Pista de colors fixos (El tram pren EXACTAMENT el color del botó anterior)
                segmentos_html = ""
                for i in range(total_steps - 1):
                    # Avaluem pasos[i], que és el botó d'on NAIX la línia
                    color_segmento = "#24b653" if pasos[i]['status'] == 'accepted' else "#FF9F4B"
                    segmentos_html += f'<div class="progress-segment" style="background-color: {color_segmento};"></div>'

                # 3. Nodes (Cercles)
                nodos_html = ""
                for i in range(total_steps):
                    status_nodo = pasos[i]['status']
                    clase_activa = "active" if i <= current_step else ""
                    clase_viendo = "viendo" if i == current_step else ""
                    clase_mine = "is-mine" if pasos[i].get("is_mine") else ""
                    
                    nodos_html += f'<div class="step-node {clase_activa} {status_nodo} {clase_viendo} {clase_mine}">{i+1}</div>'

                # 4. Injecció HTML ESTRICTA: TOT APEGAT A LA ESQUERRA
                html_code = f"""
<style>
.stepper-container {{
    position: relative;
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 90%;
    padding: 30px 15px 10px 15px;
    margin-bottom: 20px;
    box-sizing: border-box;
}}
.stepper-color-track {{
    position: absolute;
    left: 12px; 
    right: 12px; 
    height: 4px;
    display: flex;
    z-index: 1;
}}
.progress-segment {{
    flex-grow: 1;
    height: 100%;
}}
.stepper-curtain {{
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    background-color: #E0E0E0;
    transition: width 0.4s ease-in-out;
    z-index: 2;
}}
.step-node {{
    position: relative;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background-color: #E0E0E0;
    color: #888888;
    font-size: 13px;
    font-weight: bold;
    display: flex;
    justify-content: center !important;
    align-items: center !important;
    z-index: 3;
    box-shadow: 0 0 0 6px white;
    transition: all 0.3s ease-in-out;
}}
/* 🎯 LABEL "Tu" SOBRE EL CERCLE */
.step-node.is-mine::after {{
    content: "Tu";
    position: absolute;
    top: -20px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 11px;
    font-weight: 800;
    color: #0A0C10;
    white-space: nowrap;
}}
.step-node.active {{ background-color: #FF9F4B; color: white; }}
.step-node.accepted {{ background-color: #24b653 !important; color: white !important; }}
.step-node.declined {{ background-color: #FF9F4B !important; color: white !important; }}

.step-node.viendo {{
    transform: scale(1.1);
    box-shadow: 0 0 0 3px white, 0 0 0 6px #000000 !important;
    z-index: 4;
}}
</style>

<div class="stepper-container">
    <div class="stepper-color-track">
        {segmentos_html}
        <div class="stepper-curtain" style="width: {ancho_telon}%;"></div>
    </div>
    {nodos_html}
</div>
"""
                # Netejem i renderitzem
                st.markdown(html_code, unsafe_allow_html=True)

                st.write("") # Espaiador
            
            with col_btn:
                if item_status == 'neutral' and chain_status == 'pending':

                    if st.button("Acceptar cadena", key=f"ok_{chain_id}", use_container_width=True):
                        #accept_chain(chain_id, item_id)
                        #st.rerun()
                        confirm('acceptar', item_id, chain_id)
                        
                    if st.button("Rebutjar cadena", key=f"ko_{chain_id}", use_container_width=True):
                        #decline_chain(chain_id, item_id)                        
                        #st.rerun()
                        confirm('rebutjar', item_id, chain_id)
                        
                elif item_status == 'accepted' and chain_status == 'pending':

                    if st.button("Sortir de la cadena", key=f"btn_leave_{chain_id}", use_container_width=True):
                        # leave_chain(chain_id, item_id)
                        #st.rerun()
                        confirm('sortir de', item_id, chain_id)
                        
                    if st.button("Rebutjar cadena", key=f"btn_reject_acc_{chain_id}", use_container_width=True):
                        #decline_chain(chain_id, item_id)                        
                        #st.rerun()
                        confirm('rebutjar', item_id, chain_id)
            
            #st.html("<br>")
            
            item = get_item_from_item_id(pasos[current_step]['item_id'])

            col_btn_previous, col_image, col_info, col_btn_next = st.columns([1,6,6,1], gap="medium")

            st.markdown("""
                <style>
                /* Estil unificat per als botons de navegació */
                div[class*="st-key-prev_"] button,
                div[class*="st-key-next_"] button {
                    height: 300px !important; /* Ajustat als 150px d'alt que mesura la teva imatge */
                    background-color: #F0F2F6 !important;
                    color: #555555 !important;
                    border: none !important;
                    border-radius: 8px !important;
                    transition: all 0.3s ease !important;
                    
                    /* Centrat absolut del text intern */
                    display: flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                    line-height: 1 !important;
                }
                
                /* 2. 🎯 EL TRUC: Forcem la mida al TEXT intern (paràgraf o div) */
                div[class*="st-key-prev_"] button *,
                div[class*="st-key-next_"] button * {
                    font-size: 35px !important; /* Ara sí o sí es fa gran */
                    line-height: 1 !important;
                    display: block !important;
                }

                /* Efecte hover (en passar el ratolí) */
                div[class*="st-key-prev_"] button:hover,
                div[class*="st-key-next_"] button:hover {
                    background-color: #D2D8E4 !important;
                    color: #FF4B4B !important; /* Vermell Conixberg */
                }
                </style>
            """, unsafe_allow_html=True)

            with col_btn_previous:
                st.button("❮", key=f"prev_{chain_id}", use_container_width=True, on_click=prev_step, args=(state_key, current_step, total_steps))
                    #st.session_state[state_key] = (current_step - 1) % total_steps
                    #st.rerun()
                    
            with col_image:
                if item["image"]:
                    img_original = Image.open(item["image_optimized"])
                    img_recortada = ImageOps.fit(img_original, (500, 200)) 
                    st.image(img_recortada, use_container_width=True)
                    
                # Corregit un petit error de cometes duplicades a la teva f-string original de Python
                if st.button("Ampliar imatge", icon=":material/zoom_in:", key=f"{chain_id}_{item['item_id']}", use_container_width=True):
                    ampliar_imagen(item["image"], item)
                    
            with col_info:    
                # Representació visual de l'intercanvi
                user = get_user_by_username(item['user'])
                
                st.write(f"**Usuari:** {item['user']} :grey[★ ({user["rating"]})]")
                st.write(f"**Ofereix:** {item['have']}")
                st.write(f"**Vol aconseguir:** {item['want']}")
                
                if pasos[current_step]["status"] == "neutral":
                    st.write(f"**Què li sembla l'intercanvi?** :orange[Esperant resposta]")
                elif pasos[current_step]["status"] == "accepted":
                    st.write(f"**Què li sembla l'intercanvi?** :green[Accepta l'intercanvi]")
                
                with st.expander("Veure descripció de l'article"):
                    st.write(f"**Descripció:** {item['description']}")

            with col_btn_next:
                st.button("❯", icon_position="right", key=f"next_{chain_id}", use_container_width=True, on_click=next_step, args=(state_key, current_step, total_steps))
                    #st.session_state[state_key] = (current_step + 1) % total_steps
                    #st.rerun()

def render_chains():
    
    st.button("Tornar", key="exit_chains", icon=":material/arrow_left_alt:", on_click=exit_chains)
        #st.session_state.show_chains = None
        #st.rerun()

    st.header("Les teves cadenes d'intercanvi")
        
    if "user" not in st.session_state:
        st.warning("Si us plau, inicia sessió per gestionar els teus intercanvis.")
        return
        
    # ───── TABS ─────
    tab1, tab2, tab3 = st.tabs(["Cadenes obertes", "Cadenes que has acceptat", "Cadenes tancades"])
    
    st.markdown("""
        <style>
        /* Botons Positius: Acceptar (ok_) i Sortir (btn_leave_) */
        div[class*="st-key-btn_cadenas_"] button{
            /*border-radius: 5px !important;*/
            background-color: #f0f2f6 !important;
            color: black !important;
            
            /*font-weight: bold !important;*/
        }
        /* Hover: en passar el ratolí, es reomple de verd */
        /*div[class*="st-key-ok_"] button:hover,*/
        div[class*="st-key-btn_cadenas_"] button:hover {
            background-color: #D2D8E4 !important;
            color: black !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # ==========================================
    # TAB 1: CADENES DISPONIBLES
    # ==========================================
    with tab1:
    
        # 2. Consulta a la base de dades per agrupar cadenes per article
        conn = get_conn()
        c = conn.cursor()

        try:
            # Busquem els articles de l'usuari actual que estan en cadenes "pending"
            # i que l'usuari no ha acceptat (status = neutral dins de chain_items)
            c.execute("""
                SELECT i.item_id, i.have, COUNT(DISTINCT ci.chain_id) as num_cadenas
                FROM items i
                JOIN chain_items ci ON i.item_id = ci.item_id
                JOIN chains c ON ci.chain_id = c.chain_id
                WHERE i.user = ? AND ci.status = 'neutral' AND c.status = 'pending'
                GROUP BY i.item_id, i.have
            """, (st.session_state.user,))
            
            items_in_open_chains = c.fetchall()
            
        except Exception as e:
            st.error(f"Error en carregar les cadenes: {e}")
            items_in_open_chains = []
        finally:
            conn.close()

        # 3. Si no hi ha cadenes, mostrem un missatge buit amable
        if not items_in_open_chains:
            st.info("De moment, no hi ha noves cadenes d'intercanvi per als teus articles.")
        
        else:
            # 4. Renderitzat de les files (una per cada article involucrat)
            for row in items_in_open_chains:
                
                item_id = row[0]
                have_text = row[1]
                num_cadenas = row[2]
                
                with st.container(border=True):
                    
                    col_text, col_btn = st.columns([4, 1], vertical_alignment="center")
                    
                    with col_text:
                        # Icona cridanera i missatge dinàmic
                        if num_cadenas == 1:
                            st.markdown(f"El teu article **{have_text}** ha entrat en **1** cadena d'intercanvi.")
                        else:
                            st.markdown(f"El teu article **{have_text}** ha entrat en **{num_cadenas}** cadenes d'intercanvi.")
                            
                    with col_btn:
                        # Botó per navegar a la vista de detall d'aquestes cadenes específiques
                        if st.button("Veure cadena", key=f"btn_cadenas_abiertas_{item_id}", use_container_width=True):
                            # Guardem en sessió quin article volem revisar i recarreguem
                            st.session_state.detail_chain = [item_id, 'pending', 'neutral', 1]
                            st.rerun()
                            
    # ==========================================
    # TAB 2: CADENES ACCEPTADES PERÒ OBERTES
    # ==========================================
    with tab2:
            
        conn = get_conn()
        c = conn.cursor()

        try:
            c.execute("""
                SELECT i.item_id, i.have, COUNT(DISTINCT ci.chain_id) as num_cadenas
                FROM items i
                JOIN chain_items ci ON i.item_id = ci.item_id
                JOIN chains c ON ci.chain_id = c.chain_id
                WHERE i.user = ? AND ci.status = 'accepted' AND c.status = 'pending'
                GROUP BY i.item_id, i.have
            """, (st.session_state.user,))
            
            items_in_accepted_chains = c.fetchall()
            
        except Exception as e:
            st.error(f"Error en carregar les cadenes: {e}")
            items_in_accepted_chains = []
        finally:
            conn.close()

        if not items_in_accepted_chains:
            st.info("Les cadenes que acceptis apareixeran aquí.")
        else:
            
            for row in items_in_accepted_chains:
                
                item_id = row[0]
                have_text = row[1]
                num_cadenas = row[2]
                
                with st.container(border=True):
                    
                    col_text, col_btn = st.columns([4, 1], vertical_alignment="center")
                    
                    with col_text:
                        st.markdown(f"Has acceptat participar en l'intercanvi del teu article **{have_text}**.")
                            
                    with col_btn:
                        # El botó ara guarda l'item_id individual d'AQUESTA fila
                        if st.button("Veure cadena", key=f"btn_cadenas_aceptadas_{item_id}", use_container_width=True):
                            st.session_state.detail_chain = [item_id, 'pending', 'accepted', 2]
                            st.rerun()
        
    # ==========================================
    # TAB 3: CADENES TANCADES
    # ==========================================
    with tab3:

        conn = get_conn()
        c = conn.cursor()

        try:
            # Busquem els articles de l'usuari actual que estan en cadenes "pending"
            # i que l'usuari no ha acceptat (status = neutral dins de chain_items)
            c.execute("""
                SELECT i.item_id, i.have, COUNT(DISTINCT ci.chain_id) as num_cadenas
                FROM items i
                JOIN chain_items ci ON i.item_id = ci.item_id
                JOIN chains c ON ci.chain_id = c.chain_id
                WHERE i.user = ? AND ci.status = 'accepted' AND c.status = 'accepted'
                GROUP BY i.item_id, i.have
            """, (st.session_state.user,))
            
            items_in_closed_chains = c.fetchall()
            
        except Exception as e:
            st.error(f"Error en carregar les cadenes: {e}")
            items_in_closed_chains = []
        finally:
            conn.close()

        # 3. Si no hi ha cadenes, mostrem un missatge buit amable
        if not items_in_closed_chains:
            st.info("Sembla que encara no hi ha cap cadena tancada.")
        else:
            # 4. Renderitzat de les files (una per cada article involucrat)
            for row in items_in_closed_chains:
                
                item_id = row[0]
                have_text = row[1]
                num_cadenas = row[2]
                
                with st.container(border=True):
                    
                    col_text, col_btn = st.columns([4, 1], vertical_alignment="center")
                    
                    with col_text:
                        # Icona cridanera i missatge dinàmic
                        st.markdown(f"El teu article **{have_text}** està dins d'una cadena tancada!")
                            
                    with col_btn:
                        # Botó per navegar a la vista de detall d'aquestes cadenes específiques
                        if st.button("Veure cadena", key=f"btn_cadenas_cerradas_{item_id}", use_container_width=True):
                            # Guardem en sessió quin article volem revisar i recarreguem
                            st.session_state.detail_chain = [item_id, 'accepted', 'accepted', 3]
                            #st.session_state["mode"] = "review_specific_chains"
                            st.rerun()