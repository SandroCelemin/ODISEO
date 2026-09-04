#ACLARACIONS

# El "results" de "toast_notification" és de la forma ([llista de dicts], num): els dicts de la llista retornen totes les línies de la taula notificacions
# amb is_read = 0 (els que encara no s'han ensenyat com a toast) i el num retorna el número de notificacions que ja s'han mostrat
# com a toast però que encara no s'han anat a veure expressament a la pàgina de notificacions.

#-----------
import streamlit as st

from services.utils import renderizar_imagen
from datetime import datetime, date, timedelta
from db import get_notifications, mark_notifications_as_read
from engine import find_all_chains

from PIL import Image, ImageOps


def exit_notifications():
    st.session_state.show_notifications = False

def toast_notification():

    # aquest results és de la forma ([llista], num)
    new_notifications, pending_notifications = get_notifications(st.session_state.user, "toast")
    
    if new_notifications:
        
        for notification in new_notifications:
            
            notif_id = notification["notification_id"]
            st.toast(notification["message"], icon=":material/notifications_active:", duration="long")
            
    elif pending_notifications > 0:
        print("entra a pending notifications")
        if pending_notifications != st.session_state.new_notifications[0]:
            st.toast(f"Tens **{pending_notifications}** notificació sense revisar", icon=":material/notifications_active:", duration="short")
            st.session_state.new_notifications[0] = pending_notifications
            st.session_state.new_notifications[1] = True
            
        #print(st.session_state.shown_toasts, pending_notifications)

def render_notifications():
    
    st.button("Tornar", key="exit_notifications", icon=":material/arrow_left_alt:", on_click=exit_notifications)     
    st.header("Les teves notificacions")
    st.divider()
    
    all_notifications = get_notifications(st.session_state.user, "show_notifications")
    
    if not all_notifications:
        st.info("No tens notificacions pel moment.", icon=":material/info:")
        return

    hoy = date.today()
    ayer = hoy - timedelta(days=1)
    
    notificaciones_agrupadas = {}
    
    """
    for notif in all_notifications:
        
        created_at = notif["created_at"]
        message = notif["message"]
        is_read = notif["is_read"]
        
        # Created_at retorna alguna cosa amb l'estructura "2026-07-08 13:21:49". Separem en dos
        notification_date_str = created_at.split(" ")[0]
        notification_time_str = created_at.split(" ")[1]
        
        # Es converteix cada part separada (data i hora) a date i time, 
        #associant amb strptime cadascuna amb la naturalesa dels seus elements
        notification_date = datetime.strptime(notification_date_str, "%Y-%m-%d").date()
        notification_time = datetime.strptime(notification_time_str, "%H:%M:%S").time()
    """
    
    for notif in all_notifications:

        created_at = notif["created_at"]
        message = notif["message"]
        is_read = notif["is_read"]

        # Si viene como string se convierte, si ya es datetime se usa directamente
        if isinstance(created_at, str):
            # Limpiamos posibles milisegundos si la BD los incluye
            created_at_clean = created_at.split(".")[0] 
            created_dt = datetime.strptime(created_at_clean, "%Y-%m-%d %H:%M:%S")
        else:
            created_dt = created_at

        notification_date = created_dt.date()
        notification_time = created_dt.time()
        
        
        #print(notification_time)

        if notification_date == hoy:
            date_text = "Avui"
            
        elif notification_date == ayer:
            #date_text = "Ieri" # o "Ahir"
            date_text = "Ahir"
            
        else:
            # Format net sense zeros a l'esquerra (ex: 3-4-2010)
            date_text = f"{notification_date.day}-{notification_date.month}-{notification_date.year}"
            
        time_text = notification_time.strftime("%H:%M:%S")
            
        if date_text not in notificaciones_agrupadas:
            notificaciones_agrupadas[date_text] = []
            
        # date_text actua com un identificador de grup i dins de cada grup es posen
        # la informació de missatge i el seu estat. alguna cosa com: ([{},{},{},...],[{},{},{},...],...)
        notificaciones_agrupadas[date_text].append({"message": message, "is_read": is_read, "time": time_text})
        
    # 2. RENDERITZAT VISUAL
    for date_text, lista_notif in notificaciones_agrupadas.items():
        
        st.markdown(f"#### {date_text}")
        #st.divider(width=200)
        for n in lista_notif:
            
            with st.container(border=True):
                
                col_icon, col_text, col_time = st.columns([1, 12, 1], vertical_alignment="center")
                
                with col_icon:
                    # Si no s'ha vist en aquesta pestanya (0 o 1), mostrem el punt blau de "Nova"
                    if n["is_read"] < 2:
                        """
                        img_original = Image.open("new_ca.jpg")
                        img_recortada = ImageOps.fit(img_original, (500, 200)) #ImageOps.fit s'encarrega que no es deformi la foto en retallar-la
                        st.image(img_recortada, use_container_width=True)
                        """
                        renderizar_imagen("new_ca.jpg", "img_sistema", (500, 200), "normal", False, True)

                    else:
                        st.markdown(":material/mail:")
                    
                with col_text:
                    # Destaquem el text en negreta si la notificació és nova
                    if n["is_read"] < 2:
                        st.markdown(f"**{n['message']}**")
                    else:
                        st.write(n["message"])
                        
                with col_time:

                    st.write(n["time"])
                    
        st.html("<br>") # Espaiador estètic entre blocs de dies
        
    mark_notifications_as_read(st.session_state.user)
    st.session_state.new_notifications[1] = False
