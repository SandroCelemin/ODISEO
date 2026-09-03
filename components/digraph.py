import streamlit as st
import os
import base64
import io
from PIL import Image, ImageOps

from db import get_digraph_data, get_user_by_username
from services.utils import get_pil_image  # Integración de la función de utils
from streamlit_agraph import agraph, Node, Edge, Config


# 🚀 OPTIMITZACIÓ I CARGA D'IMATGES (SUPABASE + LOCAL)
@st.cache_data(show_spinner=False)
def obtener_imagen_base64(ruta_imagen, bucket=None, max_size=(90, 90)):
    """
    Carrega la imatge fent servir 'get_pil_image' (Supabase/URL/Local),
    la retalla a format quadrat 1:1 i la converteix a Base64.
    """
    if not ruta_imagen:
        return None
        
    if isinstance(ruta_imagen, str) and (ruta_imagen.startswith("http://") or ruta_imagen.startswith("https://") or ruta_imagen.startswith("data:")):
        return ruta_imagen

    img = None
    
    # 1. Intentem carregar la imatge des de Supabase / URL
    try:
        img = get_pil_image(ruta_imagen, bucket_name=bucket)
    except Exception:
        pass

    # 2. Si falla, intentem si és un fitxer local
    if img is None and isinstance(ruta_imagen, str) and os.path.exists(ruta_imagen):
        try:
            img = Image.open(ruta_imagen)
        except Exception:
            pass

    # 3. Processament i conversió a Base64
    if img is not None:
        try:
            img = img.convert("RGB")
            # ImageOps.fit retalla la imatge en format quadrat centrat (evita deformacions)
            img_fit = ImageOps.fit(img, max_size, centering=(0.5, 0.5))
            
            buffer = io.BytesIO()
            img_fit.save(buffer, format="JPEG", quality=75)
            
            codificado = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{codificado}"
        except Exception as e:
            return None
            
    return None


@st.fragment
def render_digraph1():
    
    nodes_data, arcs_data = get_digraph_data()

    agraph_nodes = []
    agraph_arcs = []

    for item in nodes_data:
        imagen_procesada = obtener_imagen_base64(item.get('image'), bucket="items")
        tipo_forma = "circularImage" if imagen_procesada else "dot"
        
        agraph_nodes.append(
            Node(
                id=item['item_id'],
                label=item['user'],
                title=f"{item['have']}",
                size=30,
                shape=tipo_forma,
                image=imagen_procesada,
                color="#00ADB5"
            )
        )

    for source_id, target_id in arcs_data:
        agraph_arcs.append(
            Edge(
                source=source_id,
                target=target_id,
                type="CURVE_SMOOTH",
                color="#F8B500",
                directed=True
            )
        )

    # Configuració sense els paràmetres que causaven l'error de JS
    config = Config(
        width="100%",
        height=300,
        directed=True,
        collapsible=True
    )
    
    config.physics = {
        "enabled": True,
        "solver": "barnesHut",
        "stabilization": {
            "enabled": True,
            "iterations": 500
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
        with st.container(height=350, border=True, gap="xxsmall", vertical_alignment="center"):
            return agraph(nodes=agraph_nodes, edges=agraph_arcs, config=config)
    else:
        st.info("No hi ha ítems actius per mostrar.")


@st.fragment
def render_digraph_detail(items, height_container, camino):
    
    if st.session_state.get("user"):
        user_me = get_user_by_username(st.session_state.user)
        user_me_img = user_me.get("user_image") if user_me else "imagenes_users/default_profile_image.png"
    else:
        user_me_img = "imagenes_users/default_profile_image.png"
        
    nodes_data, arcs_data = get_digraph_data()
    
    agraph_nodes = []
    agraph_arcs = []

    # 1. GENERACIÓ DE NODES DINÀMICS
    for item in items:
        node_id = item["item_id"]
        node_color = "#34495E" 
        node_size = 25
        
        # Cerca la imatge de l'ítem a Supabase (bucket='items')
        raw_img = item.get('image') or item.get('image_url')
        imagen_procesada = obtener_imagen_base64(raw_img, bucket="items")
        
        shape = "circularImage" if imagen_procesada else "dot"
        
        if camino is not None:
            if node_id in camino:
                node_color = "#FF4B4B"
                node_size = 40
            else:
                node_color = "#E0E0E0"
                
        agraph_nodes.append(
            Node(
                id=node_id, 
                label=item.get("have", ""), 
                size=node_size, 
                shape=shape,
                image=imagen_procesada,
                color=node_color
            )
        )

    # Node de l'usuari actual
    if camino is not None and len(camino) > 0:
        imagen_tu = obtener_imagen_base64(user_me_img, bucket="users")
        shape_tu = "circularImage" if imagen_tu else "dot"
        
        agraph_nodes.append(
            Node(
                id="user_node",
                label="TU 👤",
                size=50,
                shape=shape_tu,
                image=imagen_tu,
                color="#00FF87",
                title="¡Tu tancaves el cercle d'intercanvis!"
            )
        )

    # 2. GENERACIÓ D'ARESTES DINÀMIQUES
    for source_id, target_id in arcs_data:
        edge_color = "#F8B500"
        edge_width = 2
        
        if camino is not None:
            if source_id in camino and target_id in camino:
                idx_src = camino.index(source_id)
                idx_tgt = camino.index(target_id)
                
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
    
    if camino is not None and len(camino) > 0:
        primer_nodo_id = camino[0]
        ultimo_nodo_id = camino[-1]
        
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

    # 4. Configuració corregida
    config = Config(
        width="100%",
        height=height_container - 70,
        directed=True,
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
