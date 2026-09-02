import streamlit as st
from PIL import Image, ImageOps, ImageDraw
from db import get_conn, add_user

def make_circle_image(image, size=(200, 200)):
    # 1. Redimensionar i enquadrar perquè no es deformi
    img = ImageOps.fit(image, size, centering=(0.5, 0.5)).convert("RGBA")
    
    # 2. Crear una màscara en blanc i negre (L) amb un cercle blanc
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    
    # 3. Aplicar la màscara com a canal Alfa (transparència)
    img.putalpha(mask)
    return img

def update_image():
    # Si l'uploader té un fitxer, el guardem a la sessió
    if st.session_state.reg_image is not None:
        st.session_state.image = st.session_state.reg_image
    # Si l'usuari li ha donat a la "X", buidem la sessió
    else:
        st.session_state.image = None

def render_auth(supabase):
    rc = False
    
    if st.session_state.show_login and not st.session_state.user:
        rc = True

        if st.button("Tornar", icon=":material/arrow_left_alt:"):
            st.session_state.show_login = None
            st.rerun()

        st.markdown("## :material/lock_person: Accés")

        tab1, tab2 = st.tabs(["Iniciar sessió", "Crear compte"])

        # =========
        # LOGIN
        # =========
        with tab1:
            u = st.text_input("Usuari", key="login_user")
            p = st.text_input("Contrasenya", type="password", key="login_pass")

            if st.button("Iniciar sessió"):

                conn = get_conn()
                c = conn.cursor()

                c.execute(
                    "SELECT * FROM users WHERE username=%s AND password=%s",
                    (u, p)
                )

                row = c.fetchone()
                
                if row:
                    columns = [desc[0] for desc in c.description]
                    user = dict(zip(columns, row))

                #if user:
                    st.session_state.user = u
                    st.session_state.user_rating = user["rating"]
                    st.session_state.show_login = False
                    st.rerun()
                else:
                    st.error(f"Login incorrecte. L'usuari {u} no està registrat.")
                
                conn.close()

        # =========
        # REGISTER
        # =========
        with tab2:
            new_user = st.text_input("Usuari", key="reg_user")
            new_pass = st.text_input("Contrasenya", type="password", key="reg_pass")
            new_image = st.file_uploader("Imatge (png / jpg / jpeg)", type=["png", "jpg", "jpeg"], key="reg_image", on_change=update_image)
            
            if st.session_state.get("image") is not None:
                img_original = Image.open(st.session_state.image)
                img_circular = make_circle_image(img_original, size=(200, 200))
                st.image(img_circular)

            if st.button("Crear compte"):
                
                image = st.session_state.get("image")
                bucket_name = "imagenes_users"
                #path = "imagenes_users/default_profile_image.png"

                try:
                    if image:
                        # Leer los bytes del archivo cargado
                        file_bytes = image.getvalue()
                        file_name = f"img_{new_user}_{image.name}"

                        # Subir archivo al bucket de Supabase
                        supabase.storage.from_(bucket_name).upload(
                            path=file_name,
                            file=file_bytes,
                            file_options={"content-type": image.type, "upsert": "true"}
                        )

                        # Obtener la URL pública para guardar en PostgreSQL
                        image_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
                    else:
                        # URL de la imagen por defecto alojada en Supabase Storage
                        image_url = supabase.storage.from_(bucket_name).get_public_url("default_profile_image.png")
                        
                    add_user(new_user, new_pass, image_url)
                    st.success(f"Usuari *{new_user}* creat amb èxit!")
                    
                    st.session_state.user = new_user
                    st.session_state.show_login = False
                    st.rerun()
                except:
                    st.error(f"L'usuari *{new_user}* ja existeix. Per favor, tria un altre nom.")

    return rc
