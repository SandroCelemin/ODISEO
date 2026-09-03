import streamlit as st
import os
import base64
import io
from PIL import Image, ImageOps

from db import get_digraph_data, get_user_by_username
from services.utils import get_pil_image  # Importamos el cargador unificado de imágenes
from streamlit_agraph import agraph, Node, Edge, Config


# 🚀 OPTIMITZACIÓ I ADAPTACIÓ D'IMATGES PER AL GRAF
@st.cache_data(show_spinner=False)
def obtener_imagen_base64(ruta_o_imagen, bucket=None, max_size=(90, 90)):
    """
    Carrega qualsevol imatge (ruta local, URL o Supabase), la retalla a format 
    quadrat (1:1) perfectament centrat i la converteix a Base64 JPEG.
    Això evita deformacions visuals en 'circularImage' i redueix la càrrega de dades.
    """
    if not ruta_o_imagen:
        return None

    try:
        # Intentem carregar la imatge fent servir la utilitat unificada
        img = get_pil_image(ruta_o_imagen, bucket=bucket)

        # Si no s'ha obtingut i és una ruta de fitxer local existent:
        if img is None and isinstance(ruta_o_imagen, str) and os.path.exists(ruta_o_imagen):
            img = Image.open(ruta_o_imagen)

        if img is None:
            return None

        # Convertim a RGB per evitar errors amb canals alfa (PNG) al guardar en JPEG
        img = img.convert("RGB")

        # 📐 RECURS CLAU: ImageOps.fit retalla mantenint la proporció 1:1 quadrada des del centre
        img_fit = ImageOps.fit(img, max_size, centering=(0.5, 0.5))

        # Guardem en un buffer en memòria comprimit
        buffer = io.BytesIO()
        img_fit.save(buffer, format="JPEG", quality=75)

        codificado = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{codificado}"

    except Exception as e:
        return None


@st.fragment
def render_digraph_detail(items, height_container, camino): # Funciona amb el camí invertit
    
    # 1. Obtenir imatge de perfil de l'usuari actual
    user_me_img = None
    if st.session_state.get("user"):
        user_me = get_user_by_username(st.session_state.user)
        if user_me:
            user_me_img = user_me.get("user_image")
            
    if not user_me_img:
        user_me_img = "imagenes_users/default_profile_image.png"

    nodes_data, arcs_data = get_digraph_data()

    agraph_nodes = []
    agraph_arcs = []

    # 2. GENERACIÓ DE NODES DINÀMICS PER ALS ÍTEMS
    for item in items:
        node_id = item["item_id"]
        
        # Valors per defecte
        node_color = "#34495E" 
        node_size = 25
        
        # Adaptació de la imatge de l'ítem a Base64 quadrat
        imagen_procesada = obtener_imagen_base64(item.get('image'), bucket="items")
        
        # Si la imatge s'ha processat correctament usem "circularImage"
        shape = "circularImage" if imagen_procesada else "dot"
        
        # Ressaltat si el node està en el camí seleccionat
        if camino is not None:
            if node_id in camino:
                node_color = "#FF4B4B" # Vermell destacat
                node_size = 38
            else:
                node_color = "#E0E0E0" # Gris apagat
                
        agraph_nodes.append(
            Node(
                id=node_id, 
                label=item.get("have", ""), 
                size=node_size, 
                shape=shape,
                image=imagen_procesada,
                color=node_color,
                title=f"{item.get('have')}"
            )
        )

    # 3. GENERACIÓ DEL NODE DE L'USUARI ACTUAL ("TU")
    if camino is not None and len(camino) > 0:
        # Adaptació de la imatge de l'usuari
        imagen_tu = obtener_imagen_base64(user_me_img, bucket="users")
        shape_tu = "circularImage" if imagen_tu else "dot"
        
        agraph_nodes.append(
            Node(
                id="user_node",
                label="TU 👤",
                size=48,
                shape=shape_tu,
                image=imagen_tu,
                color="#00FF87",       # Verd neó
                title="¡Tu tancaves el cercle d'intercanvis!"
            )
        )

    # 4. GENERACIÓ D'ARESTES DINÀMICS
    for source_id, target_id in arcs_data:
        edge_color = "#F8B500"
        edge_width = 2
        
        if camino is not None:
            if source_id in camino and target_id in camino:
                idx_src = camino.index(source_id)
                idx_tgt = camino.index(target_id)
                
                # Cadena construïda al revés [tgt <-- src]
                if idx_src == idx_tgt + 1:
                    edge_color = "#FF4B4B"
                    edge_width = 5
                else:
                    edge_color = "#EBF0F5"
            else:
                edge_color = "#EBF0F5"
                
        agraph_arcs.append(
            Edge(
                source=source_id,
                target=target_id,
                type="CURVE_SMOOTH",
                color=edge_color,
                width=edge_width,
                directed=True
            )
        )
    
    # 5. CONNEXIONS DE L'USUARI AMB ELS EXTREMS DE LA CADENA
    if camino is not None and len(camino) > 0:
        primer_nodo_id = camino[0]
        ultimo_nodo_id = camino[-1]
        
        # Tu -> Últim Node
        agraph_arcs.append(
            Edge(
                source="user_node",
                target=ultimo_nodo_id,
                type="CURVE_SMOOTH",
                color="#00FF87",
                width=4,
                directed=True
            )
        )
        
        # Primer Node -> Tu
        agraph_arcs.append(
            Edge(
                source=primer_nodo_id,
                target="user_node",
                type="CURVE_SMOOTH",
                color="#00FF87",
                width=4,
                directed=True
            )
        )

    # 6. CONFIGURACIÓ VISUAL I FÍSICA
    config = Config(
        width="100%",
        height=height_container - 70,
        directed=True,
        nodeHighlightBehavior=False,
        highlightColor="#F7A072",
        collapsible=True
    )
    
    config.physics = {
        "enabled": True,
        "solver": "barnesHut",
        "stabilization": {
            "enabled": True,
            "iterations": 100
        },
        "barnesHut": {
            "gravitationalConstant": -40000,
            "centralGravity": 1,
            "springLength": 1000,
            "springConstant": 0.0001,
            "damping": 0.08,
            "avoidOverlap": 1
        }
    }
    
    if agraph_nodes:
        with st.container(height=height_container, border=True, gap="xxsmall", vertical_alignment="center"):
            return agraph(nodes=agraph_nodes, edges=agraph_arcs, config=config)
    else:
        st.info("No hi ha ítems actius per mostrar.")
