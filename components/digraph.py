#ACLARACIONS

#Al detail, la cadena es construeix al revés, e.g. [X <-- X <-- X <--...]
#Per això la construcció

#----------
import streamlit as st
import os
import base64
import io
from PIL import Image

from db import get_digraph_data, get_user_by_username
from streamlit_agraph import agraph, Node, Edge, Config
from st_link_analysis import st_link_analysis, NodeStyle, EdgeStyle
from st_link_analysis.component.icons import SUPPORTED_ICONS

# 🚀 OPTIMITZACIÓ CLAU: Redimensionar imatge a miniatura de 80x80 px i comprimir JPEG
@st.cache_data(show_spinner=False)
def obtener_imagen_base64(ruta_imagen, max_size=(80, 80)):
    """
    Llegeix una imatge, la redueix a mida icona (80x80 px) i la comprimeix a JPEG.
    Això redueix el pes per node de 3 MB a ~3 KB (Evita el MessageSizeError).
    """
    if not ruta_imagen:
        return None
        
    if ruta_imagen.startswith("http://") or ruta_imagen.startswith("https://") or ruta_imagen.startswith("data:"):
        return ruta_imagen
        
    if os.path.exists(ruta_imagen):
        try:
            with Image.open(ruta_imagen) as img:
                img = img.convert("RGB")
                img.thumbnail(max_size)  # Redueix mantenint l'aspecte proporcional
                
                # Guardar en buffer en format JPEG meitat/comprimit al 70% de qualitat
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=70)
                
                codificado = base64.b64encode(buffer.getvalue()).decode("utf-8")
                return f"data:image/jpeg;base64,{codificado}"
        except Exception as e:
            st.warning(f"Error processant la imatge '{ruta_imagen}': {e}")
            return None
            
    return None

@st.fragment
def render_digraph1():
    
    nodes_data, arcs_data = get_digraph_data()

    agraph_nodes = []
    agraph_arcs = []

    # 2. Mapejar els teus diccionaris a objectes Node de agraph
    for item in nodes_data:
        
        # Convertim la ruta de la imatge a Base64 abans d'assignar-la
        imagen_procesada = obtener_imagen_base64(item.get('image'))
        
        # Si té imatge vàlida usem "circularImage", en cas contrari "dot" (un punt clàssic)
        if imagen_procesada is not None:
            tipo_forma = "circularImage"
        else:
            tipo_forma = "dot"
        
        agraph_nodes.append(
            Node(
                id=item['item_id'],
                label=item['user'],
                # Tooltip interactiu en passar el ratolí:
                title=f"{item['have']}",
                size=30,
                shape=tipo_forma,
                image=imagen_procesada,
                color="#00ADB5"
            )
        )

    # 3. Mapejar les teves arestes processades a objectes Edge de agraph
    for source_id, target_id in arcs_data:
        agraph_arcs.append(
            Edge(
                source=source_id,
                target=target_id,
                type="CURVE_SMOOTH",
                color="#F8B500",
                directed=True#, # Fetxa orientada de "tinc" a "vull"
                #length=750
            )
        )

    # 4. Configuració de la interfície del graf
    config = Config(
        width="100%",
        height=300,
        directed=True,
        #physics=True,
        #linkLength=2,
        
        nodeHighlightBehavior=False,
        highlightColor="#F7A072",
        collapsible=True
    )
    
    config.physics = {
        "enabled": True,               # ¡Crucial! Si no, el graf es queda congelat
        "solver": "barnesHut",
        "stabilization": {
            "enabled": True,
            # 👈 ¡LA CLAU! Augmentem el número d'iteracions d'estabilització
            # obliguem el graf a "pensar" i separar-se abans d'enquadrar la vista.
            "iterations": 500
        },
        "barnesHut": {
            "gravitationalConstant": -40000, # Força d'imant amb la qual es repulsen (més negatiu = més separats)
            "centralGravity": 1,         # Força d'atracció al centre (suau = floten més lliures)
            "springLength": 1000,            # Distància base de les molles globals
            "springConstant": 0.0001,         # Rigidesa de la molla (¡Súper baix = molt elàstic i rebotador!)
            "damping": 0.08,                # Esmorteïment del moviment (fluid, com si flotessin en aigua)
            "avoidOverlap": 1               # Evita per complet que les imatges se solapin entre si
        }
    }
    
    if agraph_nodes:
        
        #st.write(f"Connexions detectades: {len(agraph_arcs)}")
        with st.container(height=350,border=True, gap="xxsmall", vertical_alignment="center"):
            return agraph(nodes=agraph_nodes, edges=agraph_arcs, config=config)
    else:
        st.info("No hi ha ítems actius per mostrar.")
    
    #return agraph(nodes=agraph_nodes, edges=agraph_arcs, config=config)

@st.fragment
def render_digraph_detail(items, height_container, camino): # Funciona amb el camí invertit
    
    if st.session_state.user:
        user_me = get_user_by_username(st.session_state.user)
        user_me_img = user_me["user_image"]
    else:
        user_me_img = "imagenes_users/default_profile_image.png"
        
    #print("camino", camino)
    
    nodes_data, arcs_data = get_digraph_data()
    #print("arcs data", arcs_data)
    
    #camino = st.session_state.camino_resaltado # Capturem si hi ha alguna cosa seleccionada
    
    agraph_nodes = []
    agraph_arcs = []

    # 1. GENERACIÓ DE NODES DINÀMICS
    for item in items:
        node_id = item["item_id"]
        
        # Valors per defecte per a un graf normal
        node_color = "#34495E" 
        node_size = 25
        
        # Convertim la ruta de la imatge a Base64 abans d'assignar-la
        imagen_procesada = obtener_imagen_base64(item.get('image'))
        
        # Si té imatge vàlida usem "circularImage", en cas contrari "dot" (un punt clàssic)
        shape = "circularImage" if imagen_procesada else "dot"
        
        # Si hi ha un camí actiu...
        if camino is not None:
            if node_id in camino:
                # Si el node pertany al recorregut seleccionat, el ressaltem
                node_color = "#FF4B4B" # Vermell Streamlit o el color que vulguis
                node_size = 40         # El fem un poc més gran
            else:
                # Si no hi pertany, el "paguem" visualment (el tornem gris clar)
                node_color = "#E0E0E0"
                
        agraph_nodes.append(
            Node(
                id=node_id, 
                label=item["have"], 
                size=node_size, 
                shape=shape,
                image=imagen_procesada,
                color=node_color)
        )

    if camino is not None and len(camino) > 0:
        # Pots posar aquí una foto teva per defecte o un avatar genial
        imagen_tú = obtener_imagen_base64(user_me_img) # O posar None
        shape = "circularImage" if imagen_tú else "dot"
        
        agraph_nodes.append(
            Node(
                id="user_node",
                label="TU 👤",
                size=50,               # Et fem lleugerament més gran per destacar
                shape="circularImage",
                image=imagen_tú,
                color="#00FF87",       # Verd neó súper cridaner per a l'usuari
                title="¡Tu tancaves el cercle d'intercanvis!"
            )
        )

    # 2. GENERACIÓ D'ARESTES DINÀMIQUES
    for source_id, target_id in arcs_data:
        edge_color = "#F8B500" # Groc per defecte
        edge_width = 2
        
        # Si hi ha un camí actiu, comprovem si aquesta connexió (aresta) forma part d'ell
        if camino is not None:
            # Una aresta està en el camí si tots dos nodes hi són 
            # i a més són consecutius en la llista del recorregut
            if source_id in camino and target_id in camino:
                idx_src = camino.index(source_id)
                idx_tgt = camino.index(target_id)
                
                # Comprovem si són veïns consecutius en la cadena
                if idx_src == idx_tgt+1: # target està a l'esquerra de source: [tgt <-- src]
                #if idx_tgt == idx_src+1:
                #if abs(idx_src-idx_tgt) == 1:
                    edge_color = "#FF4B4B" # Ressaltem la fletxa en vermell
                    edge_width = 5         # La fem més gruixuda
                else:
                    edge_color = "#EBF0F5" # Connexió secundària apagada
            else:
                edge_color = "#EBF0F5"     # Aresta completament fora del camí
                
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
        
        # 1. Tu -> Últim Node:
        # L'últim usuari de la cadena cerca el que TU tens. Tu li dones el teu objecte.
        agraph_arcs.append(
            Edge(
                source="user_node",
                target=ultimo_nodo_id,
                type="CURVE_SMOOTH",
                color="#00FF87",       # Línia verd brillant
                width=4,
                directed=True
            )
        )
        
        # 2. Primer Node -> Tu:
        # El primer usuari de la cadena té l'objecte que tu volies inicialment. Ell te'l dóna a tu.
        agraph_arcs.append(
            Edge(
                source=primer_nodo_id,
                target="user_node",
                type="CURVE_SMOOTH",
                color="#00FF87",       # Línia verd brillant
                width=4,
                directed=True
            )
        )
    
    # 4. Configuració de la interfície del graf
    config = Config(
        width="100%",
        height=height_container-70,
        directed=True,
        #physics=True,
        #linkLength=2,
        
        nodeHighlightBehavior=False,
        highlightColor="#F7A072",
        collapsible=True
    )
    
    config.physics = {
        "enabled": True,               # ¡Crucial! Si no, el graf es queda congelat
        "solver": "barnesHut",
        "stabilization": {
            "enabled": True,
            # 👈 ¡LA CLAU! Augmentem el número d'iteracions d'estabilització
            # obliguem el graf a "pensar" i separar-se abans d'enquadrar la vista.
            "iterations": 100
        },
        "barnesHut": {
            "gravitationalConstant": -40000, # Força d'imant amb la qual es repulsen (més negatiu = més separats)
            "centralGravity": 1,         # Força d'atracció al centre (suau = floten més lliures)
            "springLength": 1000,            # Distància base de les molles globals
            "springConstant": 0.0001,         # Rigidesa de la molla (¡Súper baix = molt elàstic i rebotador!)
            "damping": 0.08,                # Esmorteïment del moviment (fluid, com si flotessin en aigua)
            "avoidOverlap": 1               # Evita per complet que les imatges se solapin entre si
        }
    }
    
    if agraph_nodes:
        
        #st.write(f"Connexions detectades: {len(agraph_arcs)}")
        with st.container(height=height_container, border=True, gap="xxsmall", vertical_alignment="center"):
            return agraph(nodes=agraph_nodes, edges=agraph_arcs, config=config)
    else:
        st.info("No hi ha ítems actius per mostrar.")
"""
def render_digraph2():

    nodes_data, arcs_data = get_digraph_data()

    st.write(", ".join(SUPPORTED_ICONS))

    # 2. Formatejar les teves dades per a l'estàndard de st-link-analysis
    elements = {
        "nodes": [
            {
                "data": {
                    "id": str(item['item_id']),
                    "label": "Usuari",  # Selector per aplicar estil
                    "Usuari": item['user'],
                    "Ofereix": item['have'],
                    "Vol": item['want']#,
                    #"Categoria": item['category']
                }
            } for item in nodes_data
        ],
        "edges": [
            {
                "data": {
                    "id": f"edge-{src}-{tgt}",
                    "label": "Match",   # Selector per aplicar estil
                    "source": str(src),
                    "target": str(tgt)
                }
            } for src, tgt in arcs_data
        ]
    }

    # 3. Definir els estils visuals (Es defineixen per "label" en comptes d'un a un)
    node_styles = [
        NodeStyle(
            "Usuari",
            color="#00ADB5",
            caption="Usuari",  # Propietat que es pintarà sota el node
            icon="sell"
        )
    ]

    edge_styles = [
        EdgeStyle(
            "Match",
            color="#F8B500",
            directed=True,
            labeled=False
        )
    ]

    # 4. Configuració del Layout (cose és fantàstic per a auto-organitzar)
    layout = {"name": "cose", "animate": "end"}

    # 5. Renderitzat dins del teu contenidor personalitzat
        # El component s'adapta al 100% del contenidor de forma nativa
    st_link_analysis(
        elements, 
        node_styles=node_styles, 
        edge_styles=edge_styles, 
        layout=layout,
        height=300,
        key="grafo_intercambios"
    )
"""