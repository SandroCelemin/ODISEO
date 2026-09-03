import base64
import io
import os
from PIL import Image, ImageOps
import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

from db import get_digraph_data, get_user_by_username
from services.utils import get_pil_image


# 🚀 OPTIMIZACIÓN Y CARGA DE IMÁGENES INTEGRADA CON TU GET_PIL_IMAGE
@st.cache_data(show_spinner=False)
def obtener_imagen_base64(ruta_imagen, bucket=None, max_size=(90, 90)):
  if not ruta_imagen:
    return None

  # Si ya es una cadena Base64
  if isinstance(ruta_imagen, str) and ruta_imagen.startswith("data:"):
    return ruta_imagen

  img = None

  # 1. Si es un archivo local en el disco (ej. default_profile_image.png)
  if isinstance(ruta_imagen, str) and os.path.exists(ruta_imagen):
    try:
      img = Image.open(ruta_imagen)
    except Exception:
      pass

  # 2. Si no es archivo local, llamamos a tu get_pil_image (Supabase / URL)
  if img is None:
    try:
      img = get_pil_image(ruta_imagen, bucket_name=bucket)
    except Exception:
      pass

  # 3. Procesamiento y conversión a Base64 (en PNG para soportar RGBA)
  if img is not None:
    try:
      img = img.convert("RGBA")
      img_fit = ImageOps.fit(img, max_size, centering=(0.5, 0.5))

      buffer = io.BytesIO()
      # Guardamos como PNG para soportar el canal RGBA que devuelve get_pil_image
      img_fit.save(buffer, format="PNG")

      codificado = base64.b64encode(buffer.getvalue()).decode("utf-8")
      return f"data:image/png;base64,{codificado}"
    except Exception as e:
      return None

  return None


@st.fragment
def render_digraph1():
  nodes_data, arcs_data = get_digraph_data()

  agraph_nodes = []
  agraph_arcs = []

  for item in nodes_data:
    raw_img = item.get("image") or item.get("image_url")
    imagen_procesada = obtener_imagen_base64(raw_img, bucket="items")

    if imagen_procesada:
      node = Node(
          id=item["item_id"],
          label=str(item["user"]),
          title=f"{item['have']}",
          size=30,
          shape="circularImage",
          image=imagen_procesada,
          color="#00ADB5",
      )
    else:
      node = Node(
          id=item["item_id"],
          label=str(item["user"]),
          title=f"{item['have']}",
          size=30,
          shape="dot",
          color="#00ADB5",
      )

    agraph_nodes.append(node)

  for source_id, target_id in arcs_data:
    agraph_arcs.append(
        Edge(
            source=source_id,
            target=target_id,
            type="CURVE_SMOOTH",
            color="#F8B500",
            directed=True,
        )
    )

  config = Config(width="100%", height=300, directed=True, collapsible=True)

  config.physics = {
      "enabled": True,
      "solver": "barnesHut",
      "stabilization": {"enabled": True, "iterations": 500},
      "barnesHut": {
          "gravitationalConstant": -40000,
          "centralGravity": 1,
          "springLength": 1000,
          "springConstant": 0.0001,
          "damping": 0.08,
          "avoidOverlap": 1,
      },
  }

  if agraph_nodes:
    with st.container(
        height=350, border=True, gap="xxsmall", vertical_alignment="center"
    ):
      return agraph(nodes=agraph_nodes, edges=agraph_arcs, config=config)
  else:
    st.info("No hi ha ítems actius per mostrar.")


@st.fragment
def render_digraph_detail(items, height_container, camino):
  if st.session_state.get("user"):
    user_me = get_user_by_username(st.session_state.user)
    user_me_img = (
        user_me.get("user_image")
        if user_me
        else "imagenes_users/default_profile_image.png"
    )
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

    raw_img = item.get("image") or item.get("image_url")
    imagen_procesada = obtener_imagen_base64(raw_img, bucket="items")

    if camino is not None:
      if node_id in camino:
        node_color = "#FF4B4B"
        node_size = 40
      else:
        node_color = "#E0E0E0"

    if imagen_procesada:
      node = Node(
          id=node_id,
          label=str(item.get("have", "")),
          size=node_size,
          shape="circularImage",
          image=imagen_procesada,
          color=node_color,
      )
    else:
      node = Node(
          id=node_id,
          label=str(item.get("have", "")),
          size=node_size,
          shape="dot",
          color=node_color,
      )

    agraph_nodes.append(node)

  # Node de l'usuari actual
  if camino is not None and len(camino) > 0:
    imagen_tu = obtener_imagen_base64(user_me_img, bucket="users")

    if imagen_tu:
      user_node = Node(
          id="user_node",
          label="TU 👤",
          size=50,
          shape="circularImage",
          image=imagen_tu,
          color="#00FF87",
          title="¡Tu tancaves el cercle d'intercanvis!",
      )
    else:
      user_node = Node(
          id="user_node",
          label="TU 👤",
          size=50,
          shape="dot",
          color="#00FF87",
          title="¡Tu tancaves el cercle d'intercanvis!",
      )

    agraph_nodes.append(user_node)

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
            directed=True,
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
            directed=True,
        )
    )

    agraph_arcs.append(
        Edge(
            source=primer_nodo_id,
            target="user_node",
            type="CURVE_SMOOTH",
            color="#00FF87",
            width=4,
            directed=True,
        )
    )

  config = Config(
      width="100%", height=height_container - 70, directed=True, collapsible=True
  )

  config.physics = {
      "enabled": True,
      "solver": "barnesHut",
      "stabilization": {"enabled": True, "iterations": 100},
      "barnesHut": {
          "gravitationalConstant": -40000,
          "centralGravity": 1,
          "springLength": 1000,
          "springConstant": 0.0001,
          "damping": 0.08,
          "avoidOverlap": 1,
      },
  }

  if agraph_nodes:
    with st.container(
        height=height_container,
        border=True,
        gap="xxsmall",
        vertical_alignment="center",
    ):
      return agraph(nodes=agraph_nodes, edges=agraph_arcs, config=config)
  else:
    st.info("No hi ha ítems actius per mostrar.")
