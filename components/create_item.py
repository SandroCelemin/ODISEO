# ACLARACIONS

# Quan s'escriu en un quadre de text (tinc, vull, descripció), el que hi ha escrit s'associa temporalment a key="..._input" ->
# aquests estats de session_state s'utilitzen per actualitzar en temps real la part de suggeriments i només són residuals ->
# on es guarda la informació definitiva és a "have", "want" i "description", que s'igualen al seu "..._input" respectiu en passar de pàgina

# ---------------------------------------------------------------------------
import streamlit as st
import os
import io

from db import get_items, add_item, add_chains, get_items_from_user
from models import row_to_item
from engine import find_all_chains
from components.marketplace import render_marketplace
from components.detail import render_detail
from PIL import Image, ImageOps

def optimize_image(file_bytes):
    # Abrir directamente los bytes usando io.BytesIO
    img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    img = ImageOps.fit(img, (550, 400))
    
    # Guardar en un buffer de memoria en vez del disco local
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=80, optimize=True)
    
    # Devolver los bytes optimizados
    return buffer.getvalue()
    
"""
def optimize_image(path, image):
    img = Image.open(path).convert("RGB")
    img = ImageOps.fit(img, (550, 400))
    
    name = f"img_{image.name}"
    path_opt = os.path.join("img_opt", name)

    # Es guarda la imatge amb .save perquè és de tipus Image Pillow i té aquesta propietat
    img.save(path_opt, quality=80, optimize=True)
    
    return path_opt
"""
def update_have():
    st.session_state.have = st.session_state.have_input

def update_description():
    st.session_state.description = st.session_state.description_input

def update_want():
    st.session_state.want = st.session_state.want_input

def update_image():
    # Si l'uploader té un fitxer, el guardem a la sessió
    if st.session_state.image_input is not None:
        st.session_state.image = st.session_state.image_input
    # Si l'usuari li ha donat a la "X", buidem la sessió
    else:
        st.session_state.image = None
        
def next_step():
    st.session_state.step += 1
    st.session_state.detail_item = None
    
def previous_step():
    st.session_state.step -= 1
    st.session_state.detail_item = None
    
def limpiar_y_regresar():
    st.session_state.show_create = False
    st.session_state.step = 0
    st.session_state.have = ""        
    st.session_state.want = ""
    st.session_state.description = ""
    st.session_state.image = None
    st.rerun()

def render_cancel_button():
    if st.button("Cancel·lar article", type="primary", use_container_width=True):
        limpiar_y_regresar()


@st.dialog("Creem un nou article!", width="large", dismissible=False, icon=":material/box_add:")
def show_onboarding():
    
    height = 400
    _, col1, col2, col3, col4, col5, _ = st.columns([1,5,2,5,2,5,1], vertical_alignment="center")
    
    with col1:
        with st.container(height=height):
            st.header("**PAS 1**")
            
            st.markdown("""
            * Introdueix el nom de l'article que vols intercanviar
            * Descriu l'article
            * Penja una imatge de l'article
            """)
            
    with col2:
        st.markdown(
        """
        <div style="text-align: center; font-size: 2.5rem; color: #6B7280; line-height: 1; margin: 0;">
            ❯
        </div>
        """, 
        unsafe_allow_html=True
    )
            
    with col3:
        with st.container(height=height):
            st.header("**PAS 2**")
            
            st.markdown("""
            * Introdueix el nom de l'article que vols aconseguir
            """)
            
    with col4:
        st.markdown(
        """
        <div style="text-align: center; font-size: 2.5rem; color: #6B7280; line-height: 1; margin: 0;">
            ❯
        </div>
        """, 
        unsafe_allow_html=True
    )
            
    with col5:
        with st.container(height=height):
            st.header("**PAS 3**")
            
            st.markdown("""
            * Revisa que tota la informació del teu article sigui correcta
            * I... A punt per publicar!
            """)
    
    st.divider()
    
    if st.button("Entès, comencem a crear!", type="primary", use_container_width=True):
        st.session_state.guia_vista = True
        st.session_state.step = 1
        st.rerun()

def render_create(items, supabase):

    #st.write(st.session_state.have)
    #st.write(st.session_state.want)
    #st.write(st.session_state.description)
    
    #aquest markdown serveix perquè el text de col_desc comenci a dalt de tot
    #hi ha un error en vertical_alignment="top" en actualitzar meves versions
    st.markdown("""
    <style>
    
    [data-testid="stHorizontalBlock"] {
        align-items: flex-start !important;
    }
    
    [data-testid="stColumn"] {
        min-width: 0 !important;
    }
    
    </style>
    """, unsafe_allow_html=True)
    
    if st.session_state.step == 0:
        show_onboarding()

    col_create, col_suggestions = st.columns([2,3], gap="medium")
    
    with col_create:
        
        # =====================================
        # PAS 1: tens
        # =====================================
        if st.session_state.step == 1:
            print("això és lo de have: ", st.session_state.get("have", "") )
            
            st.header("PAS " + str(st.session_state.step))
            st.subheader("Què tens per intercanviar?")
            
            st.text_input("Nom de l'article que intercanvies (motxilla, cotxe, ordinador...)",value=st.session_state.get("have", ""),key="have_input", on_change=update_have)
            st.text_area("Descripció de l'article", value=st.session_state.get("description", ""),key="description_input", on_change=update_description)
            
            uploaded_file = st.file_uploader("Imatge (png / jpg / jpeg)", type=["png", "jpg", "jpeg"], key="image_input", on_change=update_image)
            
            if st.session_state.get("image") is not None:
                img_original = Image.open(io.BytesIO(st.session_state.image.getvalue()))
                img_recortada = ImageOps.fit(img_original, (275, 200))
                st.image(img_recortada)
    
            col1, col2, col3 = st.columns(3)
            
            with col2:
                if st.button("Següent", icon=":material/arrow_right_alt:", icon_position="right", use_container_width=True):
                    next_step()
                    st.rerun()
                    
            with col3:
                render_cancel_button()
                    
        # =====================================
        # PAS 2: vols
        # =====================================
        if st.session_state.step == 2:
            
            st.header("PAS " + str(st.session_state.step))
            st.subheader("Què vols aconseguir?")

            st.text_input("Nom de l'article que vols (motxilla, cotxe, ordinador...)",value=st.session_state.get("want", ""),key="want_input", on_change=update_want)

            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Enrere", icon=":material/arrow_left_alt:", use_container_width=True):
                    previous_step()
                    st.rerun()
                    
            with col2:
                if st.button("Següent", icon=":material/arrow_right_alt:", icon_position="right", use_container_width=True):
                    next_step()
                    st.rerun()
                    
            with col3:
                render_cancel_button()
        
        # =====================================
        # PAS 3: confirmar
        # =====================================
        elif st.session_state.step == 3:

            st.header("PAS " + str(st.session_state.step))
            st.subheader("Confirma el teu intercanvi")
            
            articulo_tengo = st.session_state.get("have", "").strip() or ":red[Article no introduit]"
            descripcion = st.session_state.get("description", "").strip() or ":red[Descripció no introduïda]"
            articulo_quiero = st.session_state.get("want", "").strip() or ":red[Article no introduit]"

            with st.container(border=True):
                st.write(f"**Tens:** {articulo_tengo}")
                st.write(f"**Descripció (tens):** {descripcion}")
                st.write(f"**Vols:** {articulo_quiero}")
            
            if st.session_state.get("image") is not None:
                col_image, _ = st.columns([1, 2])
                with col_image:
                    st.image(st.session_state.image, use_container_width=True)

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("Enrere", icon=":material/arrow_left_alt:", use_container_width=True):
                    previous_step()
                    st.rerun()

            with col2:
                if st.button("Publicar", icon=":material/send:", use_container_width=True):
                    
                    # Controla que s'hagin introduït totes les dades
                    if not st.session_state.get("have", ""):
                        st.error("No has introduït l'article que **tens**.")
                    elif not st.session_state.get("description", ""):
                        st.error("No has introduït la **descripció** de l'article que tens.")
                    elif not st.session_state.get("want", ""):
                        st.error("No has introduït l'article que vols aconseguir.")
                    else:
                        image = st.session_state.get("image")
                        bucket_orig_name = "img"
                        bucket_opt_name = "img_opt"

                        #path = "imagenes/image_not_found.png"
                        #path_opt = "imagenes/image_not_found.png"
                        #image_optimized = "imagenes/image_not_found.png"
                        
                        if image:
                            #path = f"img_{image.name}"
                            #path = os.path.join("img", f"img_{image.name}")

                            file_bytes_orig = image.getvalue()
                            file_name_orig = f"orig_{st.session_state.user}_{image.name}"
                            
                            supabase.storage.from_(bucket_orig_name).upload(
                                path=file_name_orig,
                                file=file_bytes_orig,
                                file_options={"content-type": image.type, "upsert": "true"}
                            )
                            image_url = supabase.storage.from_(bucket_orig_name).get_public_url(file_name_orig)

                            # 2. Imatge Optimitzada
                            file_bytes_opt = optimize_image(file_bytes_orig)
                            file_name_opt = f"opt_{st.session_state.user}_{image.name}"

                            supabase.storage.from_(bucket_opt_name).upload(
                                path=file_name_opt,
                                file=file_bytes_opt,
                                file_options={"content-type": "image/jpeg", "upsert": "true"}
                            )
                            image_opt_url = supabase.storage.from_(bucket_opt_name).get_public_url(file_name_opt)

                        else:
                            # URL per defecte si l'usuari no penja cap imatge
                            image_url = supabase.storage.from_(bucket_orig_name).get_public_url("image_not_found.png")
                            image_opt_url = image_url
                            
                            # Es guarda la imatge al disc d'aquesta manera perquè image no té 
                            # la propietat .save ja que és d'un file uploader
                            #with open(path, "wb") as f:
                            #    f.write(image.getbuffer())
                            
                            #path_opt = optimize_image(path, image)
        
                        # add_item(user, have, description, image, image_optimized, want, category)
                        # Guardar en PostgreSQL les URLs públiques en comptes de camins locals
                        add_item(
                            st.session_state.user,
                            st.session_state.have,
                            st.session_state.description,
                            image_url,
                            image_opt_url,
                            st.session_state.want,
                            ""
                        )

                        st.success("Item creat")
                        
                        """
                        mis_items = [item for item in items if item["user"] == st.session_state.user] #NOMÉS amb els items D'AQUEST usuari
                        print("mis items", mis_items)
                        """
                        items = get_items()
                        mis_items = get_items_from_user(st.session_state.user)
                        #print("mis items", mis_items)
                        último_item_creado = mis_items[-1] # L'article que s'acaba de crear serà, per definició, l'ÚLTIM de la seva llista
                        
                        #print("AquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAquiAqui", último_item_creado)
                        
                        
                        cycles = find_all_chains("dfs_modified", "have", items, último_item_creado["item_id"])
                        #print("sale")
                        #print("ciclos", cycles)
                        
                        if cycles:
                            for cycle in cycles:
                                add_chains(cycle)
                                
                        else:
                            print("Ciclos no detectados")
                        
                        limpiar_y_regresar()
                    
            with col3:
                render_cancel_button()
                
    with col_suggestions:
        
        st.header("SUGGERIMENTS")
        
        have = st.session_state.get('have_input', '')
        want = st.session_state.get('want_input', '')
        
        if st.session_state.detail_item:
           render_detail(items)
           st.stop()
            
        if st.session_state.step == 1:
            if have == "":
                st.subheader("Introdueix un article per obtenir suggeriments")
            else:
                st.subheader(f"Articles que pots aconseguir amb {st.session_state.get('have_input', '')}")
                render_marketplace(items, "suggestions_have")
                
        elif st.session_state.step == 2:
            if want == "":
                st.subheader("Introdueix un article per obtenir suggeriments")
            else:
                st.subheader(f"Prem (Veure) per saber com aconseguir {st.session_state.get('want_input', '')}")
                render_marketplace(items, "suggestions_want")

"""
    st.subheader("➕ Crear intercanvi")

    have = st.text_input("Tinc", key="have_input")
    want = st.text_input("Vull", key="want_input")
    uploaded = st.file_uploader("Imatge")
    description = st.text_area("Descripció")
    category = st.text_input("Categoria (ex: electrònica, llibres...)")


    # ───── SUGGERIMENTS ─────
    st.markdown("### 💡 Suggeriments")

    # la funció row_to_items deixa els items igual, però et permet escollir quines files guardar. En aquest cas les guardem totes, però pot tenir sentit en un futur.
    raw = get_items()
    items = [row_to_item(r) for r in raw]

    if have or want:

        suggestions = [
            it for it in items
            if (want and it["have"] == want)
            or (have and it["want"] == have)
        ]

        if suggestions:
            for s in suggestions[:5]:
                st.write(f"🔁 {s['user']} té {s['have']} → vol {s['want']}")
        else:
            st.caption("Sense suggeriments encara")


    # ───── BOTONS ─────
    col1, col2 = st.columns(2)

    # PUBLICAR
    with col1:
        if st.button("📤 Publicar"):

            path = "image_not_found.png"
            if uploaded:
                path = f"img_{uploaded.name}"
                with open(path, "wb") as f:
                    f.write(uploaded.getbuffer())

            if not description:
                description = "Descripció no disponible."

            add_item(
                st.session_state.user,
                have,
                description,
                path,
                want,
                category
            )

            st.success("Item creat")
            st.session_state.show_create = False
            st.rerun()

    # TORNAR / CANCEL·LAR
    with col2:
        if st.button("⬅ Cancel·lar"):
            st.session_state.show_create = False
            st.rerun()
"""
