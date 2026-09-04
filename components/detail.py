# ACLARACIONS

# @st.dialog() escrit abans d'una funció fa que el que es mostri en aquesta aparegui com un pop-up

#---------------------------
import streamlit as st
from PIL import Image, ImageOps, ImageDraw

from engine import find_all_chains, get_items_from_have_chains
from db import is_item_accepted_in_any_chain, get_user_by_username, calculate_chain_rating
from services.utils import similarity, get_image_url, get_pil_image, renderizar_imagen
from components.digraph import *

st.set_page_config(layout="wide")

height = 500
height_first_container = int(height*0.7)
height_chain_container = 350

IMG_FULL = "star_full.png"    # Estrella groga
IMG_HALF = "star_half.png"    # Mitja estrella
IMG_EMPTY = "star_empty.png"  # Estrella grisa


# ==========================================
# 1. FUNCIONS AUXILIARS AMB CAXÓ (PIL)
# ==========================================
def load_and_crop_image(img_input: Image.Image | str, size: tuple[int, int], bucket: str = None) -> Image.Image | None:
    """Acepta un objeto PIL o una ruta/URL y lo recorta al tamaño indicado."""
    img = img_input if isinstance(img_input, Image.Image) else get_pil_image(img_input, bucket)
    if not img:
        return None
    return ImageOps.fit(img, size)
    
def make_circle_image(img_input: Image.Image | str, size=(200, 200), bucket: str = None) -> Image.Image | None:
    """Acepta un objeto PIL o una ruta/URL y le aplica una máscara circular."""
    img_raw = img_input if isinstance(img_input, Image.Image) else get_pil_image(img_input, bucket)
    if not img_raw:
        return None

    img = ImageOps.fit(img_raw, size, centering=(0.5, 0.5)).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    img.putalpha(mask)
    return img

"""
@st.cache_data(show_spinner=False)
def open_image(path):
    return Image.open(path).convert("RGB")
"""
def get_star_image(position, score):
    diff = float(score) - (position - 1)
    if diff >= 0.75:
        return IMG_FULL
    elif diff >= 0.25:
        return IMG_HALF
    else:
        return IMG_EMPTY


# ==========================================
# 2. COMPONENTS I DIÀLEGS
# ==========================================
@st.dialog("Vista completa de l'article", width="medium", icon=":material/visibility:")
def ampliar_imagen(ruta_o_key, bucket: str = "img"):
    """
    img_original = get_pil_image(ruta_o_key, bucket)
    if img_original:
        st.image(img_original, use_container_width=True)
    else:
        st.error("No s'ha pogut carregar la imatge.")
    """
    renderizar_imagen(ruta_o_key, bucket, (275, 200), "normal", False, False)
        
def see_cycle(chain):
    st.session_state.camino_resaltado = chain
    st.session_state.route_current_step = 0

def go_create_callback(registro_have, registro_want):
    
    #st.session_state.detail = None
    
    if st.session_state.user:
        st.session_state.have = registro_have
        st.session_state.want = registro_want
        st.session_state.show_create = True
    else:
        st.session_state.show_login = True

@st.fragment
def show_rute(item_dict):
    
    chain_raw = st.session_state.camino_resaltado
    
    caminos = list(reversed(chain_raw))
    num_items_chain = len(caminos)
    total_steps = num_items_chain + 1 # Passos de la cadena + el pas "Tu"
    
    # Validem que el pas actual estigui dins del rang
    current_step = st.session_state.route_current_step
    if current_step >= total_steps:
        current_step = 0
        st.session_state.route_current_step = 0

    chain_id = "_".join(caminos)
        
    # ACLARACIÓ: Si len(caminos) = 3, num_items_chain = 3 i total_steps = 4 (0,1,2,3)
    # Per això, en aquesta comprovació es mira que el current step (que va des de 0 fins a num_items_chain)
    # sigui menor a aquest número
    if current_step < num_items_chain:
        item_id_actual = caminos[current_step]
        current_item = item_dict[item_id_actual]
    # El pas final amb el vèrtex fantasma
    else:
        first_item = item_dict[caminos[0]]            
        last_item = item_dict[caminos[-1]]
        
        if st.session_state.user:
            user_data = get_user_by_username(st.session_state.user)
            user_img = user_data["user_image"]
            username = f"{st.session_state.user} (Tu)"
        else:
            user_img = "imagenes_users/default_profile_image.png"
            username = "Tu"
        #user_raw_img = user_data["user_image"]
        
        current_item = {
            "item_id": "lore_ipsum",
            "user": f"{st.session_state.user} (Tu)",
            "have": first_item["want"],
            "image": user_img,
            "want": last_item["have"],
        }

    if not current_item:
        st.warning("Article no trobat al sistema.")
        return

    # Estils CSS
    st.markdown("""
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
    """, unsafe_allow_html=True)

    col_btn_previous, col_image, col_info, col_btn_next = st.columns([1, 6, 6, 1], gap="medium")

    # Botó Pas Anterior
    with col_btn_previous:
        if st.button("❮", key=f"prev_{chain_id}", use_container_width=True):
            st.session_state.route_current_step = (current_step - 1) % total_steps
            st.rerun(scope="fragment")

    # Imatge de l'item actual
    with col_image:
        if current_item["image"]:
            #img_original = Image.open(current_item["image"])
            
            if current_step < num_items_chain:
                #img_final = ImageOps.fit(img_original, (500, 200))
                """
                img_opt_PIL = get_pil_image(current_item["image_optimized"], "img_opt")
                img_final = load_and_crop_image(img_opt_PIL, (500, 200), "img_opt")
                st.image(img_final, use_container_width=True)
                """
                renderizar_imagen(current_item["image_optimized"], "img_opt", (500, 200), "normal", False, True)

            else:
                #img_final = make_circle_image(current_item["image"], size=(300, 300))
                
                _, col_center, _ = st.columns([1,2.3,1])
            
                with col_center:
                    #st.image(img_final, use_container_width=True)
                    renderizar_imagen(current_item["image"], "imagenes_users", (300, 300), "circular", False, True)
        
        if current_step < num_items_chain:
            if st.button("Ampliar imatge", icon=":material/zoom_in:", key=f"zoom_{chain_id}_{current_item['item_id']}", use_container_width=True):
                ampliar_imagen(current_item["image"])

    # Informació del pas actual
    with col_info:
        st.caption(f"Pas {current_step + 1} de {total_steps}")
        st.write(f"**Usuari:** {current_item['user']}")
        st.write(f"**Ofereix:** {current_item['have']}")
        st.write(f"**Vol aconseguir:** {current_item['want']}")
        
        if current_step < num_items_chain:
            with st.expander("Veure descripció de l'article"):
                st.write(f"**Descripció:** {current_item.get('description', 'Sense descripció')}")
        else:
            st.info("Aquest és l'article que necessites per poder tancar aquesta cadena. T'agradaria? Només cal prem el botó vermell al costat d'aquesta cadena.")

    # Botó Pas Següent
    with col_btn_next:
        if st.button("❯", key=f"next_{chain_id}", use_container_width=True):
            st.session_state.route_current_step = (current_step + 1) % total_steps
            st.rerun(scope="fragment")

def chains_container(chains_raw, item_dict):
    """Renderitza la llista de cadenes d'intercanvi."""
    with st.container(height=height_chain_container):
    
        if not chains_raw:
            st.info("No hi ha cadenes d'intercanvi disponibles")
            return

        for chain_raw in chains_raw:
            
            chain = list(reversed(chain_raw)) # En el flux correcte [X --> X -->...]
            
            last_item = item_dict[chain[-1]]
            first_item = item_dict[chain[0]]
            # Utilitzem una clau única combinant els IDs de la cadena perquè Streamlit no es confongui
            button_key = f"{'_'.join(chain)}"
            
            chain_rating = calculate_chain_rating(chain, True)
            
            st.markdown(f"**DISTÀNCIA {int(len(chain)+1)}** ★ ({chain_rating})")

            col_text, col_btn_see_cycle, col_btn_go_create = st.columns([6,1,1])
            
            with col_text:
                st.write(f"Si tens **{first_item['want']}**, pots aconseguir **{last_item['have']}**")
                
            with col_btn_see_cycle:
                # Icona de mapa per indicar "visualitzar"
                st.button(
                    "", 
                    key=f"btn_map_{button_key}", 
                    icon=":material/map:", 
                    help="Ressaltar aquest recorregut a la xarxa", 
                    use_container_width=True, 
                    on_click=see_cycle,
                    args=(chain_raw,)
                )

            with col_btn_go_create:
                # Icona de caixa + per indicar "crear"
                st.button(
                    "", 
                    key=f"btn_create_{button_key}", 
                    icon=":material/box_add:", 
                    type="primary", 
                    help="Tanca la cadena", 
                    use_container_width=True,
                    on_click=go_create_callback,
                    args=(first_item['want'], last_item['have'])
                )
                """
                if st.button("", key=button_key, icon=":material/box_add:", type="primary", help="Tanca la cadena", use_container_width=True):
                    # Desem la llista d'IDs que formen aquest camí
                    st.session_state.have = registro['want']
                    st.session_state.want = registro['have']
                    st.session_state.show_create = True
                    st.rerun()
                """


# ==========================================
# 3. VISTA PRINCIPAL (DETALL)
# ==========================================
def render_detail(items):    
    # Índex únic en memòria per a lectures O(1)
    item_dict = {x["item_id"]: x for x in items}
    
    selected_item_id = st.session_state.get("detail_item")
    item = item_dict.get(selected_item_id)

    if not item:
        st.error("Item no trobat")
        st.stop()

    reserved = is_item_accepted_in_any_chain(item["item_id"])
    owner_user = get_user_by_username(item["user"])
    
    star_size = 50
    
    # Aquest markdown serveix perquè el text de col_desc comenci a dalt de tot
    # Hi ha un error a vertical_alignment="top" en actualitzar versions
    st.markdown("""
    <style>
    
    div[data-testid="stDialog"] span[data-testid="stIconMaterial"] {
        font-size: 30px !important;
        vertical-align: middle;
        margin-right: 8px;
    }
    
    [data-testid="stHorizontalBlock"] {
        align-items: flex-start !important;
    }
    
    </style>
    """, unsafe_allow_html=True)

    #item = item_dict.get(st.session_state.detail_item)
    #reserved = is_item_accepted_in_any_chain(item["item_id"])
    #print("en detail",st.session_state.detail_item)

    # Botó Tornar
    if st.button("Tornar", icon=":material/arrow_left_alt:"):
        st.session_state.detail_item = None
        st.session_state.camino_resaltado = []
        st.rerun()

    col_img, col_info = st.columns(2, gap="medium")
    
    with col_img:
        #img_original = Image.open(item["image"])
        #img_recortada = ImageOps.fit(img_original, (650, height-20)) # ImageOps.fit s'encarrega que no es deformi la foto en retallar-la
        """
        img_recortada = load_and_crop_image(item["image"], (650, height - 20))
        st.image(img_recortada, use_container_width=True)
        """
        """
        img_opt_PIL = get_pil_image(item["image_optimized"], "img_opt")
        st.image(img_opt_PIL, use_container_width=True)
        """
        renderizar_imagen(item["image_optimized"], "img_opt", (300, 300), "normal", False, True)
        
        if st.button("Ampliar imatge", icon=":material/zoom_in:", use_container_width=True):
            # Cridem la funció del diàleg passant-li la ruta original
            ampliar_imagen(item["image"])
        
    with col_info:
        with st.container(height=height_first_container):
            st.header(item["have"])
            st.write(f"*{item['user']} vol aconseguir {item['want']} amb aquest objecte*")
            st.write(f"**Descripció:** {item['description']}")
            
            if item["status"] == "locked":
                state_text = ":red[No disponible]"
                #st.write(f"**Estat:** :orange[Reservat]")
            elif reserved == 1:
                state_text = ":orange[Reservat]"
                #st.write(f"**Estat:** :orange[Reservat]")
            else:
                state_text = ":green[Disponible]"
                
            st.write(f"**Estat:** {state_text}")
        
        # Targeta de l'Usuari Propietari
        with st.container(border=True): #height=height-height_first_container
            col_avatar, col_user = st.columns([1,4])
            
            with col_avatar:
                #user = get_user_by_username(item["user"])
                
                #img_path = user["user_image"]
                
                #img_original = Image.open(img_path)
                #img_circular = make_circle_image(img_original, size=(height-height_first_container, height-height_first_container))
                """
                img_user_PIL = get_pil_image(owner_user["user_image"], "imagenes_users")
                img_circular = make_circle_image(
                    img_user_PIL, 
                    size=(height - height_first_container, height - height_first_container)
                )
                st.image(img_circular)
                """
                renderizar_imagen(owner_user["user_image"], "imagenes_users", (height - height_first_container, height - height_first_container), "circular", False, True)

            with col_user:
                col_user_name, col_user_btn = st.columns(2)
                
                with col_user_name:
                    st.header(owner_user["username"])
                    
                    col1, col2 = st.columns([4,1])
                    
                    with col1:
                        cols = st.columns(5, gap="xxsmall")
                        
                        for i, col in enumerate(cols, start=1):
                            star_img = get_star_image(i, owner_user["rating"])
                            
                            #img_original = Image.open(star_img)
                            #img_recortada = ImageOps.fit(img_original, (star_size, star_size)) # ImageOps.fit s'encarrega que no es deformi la foto en retallar-la
                            """
                            img_star_PIL = get_pil_image(star_img, "img_sistema")
                            img_recortada = load_and_crop_image(img_star_PIL, (star_size, star_size), "img_sistema")
                            """
                            
                            with col:
                                #st.image(img_recortada)
                                renderizar_imagen(star_img, "img_sistema", (star_size, star_size), "normal", False, True)
                                
                    with col2:
                        st.subheader(owner_user["rating"])

                with col_user_btn:
                    if st.button("Veure usuari", use_container_width=True):
                        st.session_state.show_user = item["user"]
                        st.session_state.detail_item = None
                        st.rerun()

    st.html("<br>")

    # Càlcul de Cadenes
    chains = find_all_chains("bfs_modified", "want", items, item["item_id"]) # és una llista d'ids
    #digraph_items = get_items_from_have_chains(items, item["want"], "want")

    chains_according_to_search = []
    other_chains = []

    col_chains, col_graph = st.columns(2)
    
    with col_chains:
        
        digraph_items = []
        stored_ids = set()
        
        # Si es busca per tinc
        if st.session_state.search_text_mode == "have" and st.session_state.search_text != "":
            
            #chains_according_to_search = []
            height_graph_container = height_chain_container*2+105
            
            for chain in chains:
                
                registro = item_dict[chain[-1]] # Item al qual tu li dones

                if similarity(st.session_state.search_text, registro['want']) >= 0.6:
                    chains_according_to_search.append(chain)
                else:
                    other_chains.append(chain)
            
                for item_id in chain:
                    if item_id not in stored_ids:
                        digraph_items.append(item_dict[item_id])
                        stored_ids.add(item_id)
            
            st.markdown(f"##### :material/conversion_path: Com aconseguir aquest item amb {st.session_state.search_text}")
            chains_container(chains_according_to_search, item_dict)
            
            st.html("<br>")
            
            st.markdown("##### :material/conversion_path: Altres formes d'aconseguir aquest item")
            chains_container(other_chains, item_dict)
            
        # Si es busca per vull
        else:
            height_graph_container = height_chain_container
            
            for chain in chains:
                for item_id in chain:
                    if item_id not in stored_ids:
                        digraph_items.append(item_dict[item_id])
                        stored_ids.add(item_id)
            
            st.markdown("##### :material/conversion_path: Com aconseguir aquest item")
            chains_container(chains, item_dict)

    with col_graph:
        st.html("<br>")
        with st.spinner("Carregant la visualització de la xarxa..."):
            render_digraph_detail(digraph_items, height_graph_container, st.session_state.camino_resaltado)

    #st.write(st.session_state.camino_resaltado)
    st.html("<br>")
    
    if st.session_state.camino_resaltado:
        show_rute(item_dict)
