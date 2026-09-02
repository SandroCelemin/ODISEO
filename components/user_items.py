import streamlit as st

from db import delete_item, get_items_from_user
from PIL import Image, ImageOps

@st.dialog("Vista completa de l'article", width="medium", icon=":material/visibility:")
def ampliar_imagen(ruta_imagen, item):
    
    img_original = Image.open(item["image"])
    st.image(img_original, use_container_width=True)
    #st.caption("Utilitza les fletxes de la cantonada superior dreta si vols veure-la encara més gran.")

def render_user_items():
    
    st.markdown(
        """
        <style>
        div[data-testid="stImage"] img {
            
            object-fit: cover;
            border-radius: 10px;
        }

        .truncate {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            display: block;
            max-width: 100%;
        }

        .truncate-small {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            display: block;
            max-width: 100%;
            font-size: 0.8rem;
            color: #888;
        }

        /* botó més net */
        div[data-testid="stButton"] > button {
            border-radius: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    if st.button("Tornar", icon=":material/arrow_left_alt:"):
        st.session_state.show_user_items = None
        st.rerun()
            
    st.subheader("Aquests són els teus articles publicats")
    
    num_columnas = 2
    
    filtered_items = get_items_from_user(st.session_state.user) # Artícles de l'usuari que no estan en cadenes d'intercanvi tancades
    
    for i in range(0, len(filtered_items), num_columnas):

        row = filtered_items[i:i + num_columnas]
        cols = st.columns(num_columnas, gap="medium")

        for col, item in zip(cols, row):
        
            with col:
        
                with st.container(border=True):
                    
                    col_image, col_info = st.columns(2)
                    
                    with col_image:
                        
                        if item["image"]:
                            img_original = Image.open(item["image"])
                            img_recortada = ImageOps.fit(img_original, (275, 200)) # ImageOps.fit s'encarrega que no es deformi la foto en retallar-la
                            st.image(img_recortada, use_container_width=True)
                            
                        if st.button("Ampliar imatge", icon=":material/zoom_in:", key=item["item_id"], use_container_width=True):
                            # Cridem la funció del diàleg passant-li la ruta original
                            ampliar_imagen(item["image"], item)
                            
                    with col_info:

                        st.write(f"**Tens:** {item['have']}")
                        st.write(f"**Vols:** {item['want']}")
                        
                        if item["status"] == "active":
                            st.write(f"**Estat actual:** Lliure")
                        # No es mostrarà mai com a bloquejat pel filtre de "filtered_items"
                        elif item["status"] == "locked":
                            st.write(f"**Estat actual:** Bloquejat")
                            
                        with st.expander("Veure descripció de l'article"):
                            st.write(f"**Descripció:** {item['description']}")
                            
                    _, col_btn = st.columns([2,1])
                    
                    with col_btn:
                        
                        if st.button("Eliminar article", icon=":material/delete:", type="primary", key=f"delete_{item['item_id']}", use_container_width=True):
                            delete_item(item["item_id"])
                            st.rerun()