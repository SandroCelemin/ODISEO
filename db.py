import sqlite3
import uuid
import math
import streamlit as st

from services.match import directional_match_want, directional_match_have

DB_NAME = "database.db"

#=============================
# FUNCIONES PARA INICIAR LA DB
#=============================
def get_conn():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        user_image TEXT,
        rating REAL DEFAULT 5.0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS items (
        item_id TEXT PRIMARY KEY,
        user TEXT,
        have TEXT,
        description TEXT,
        image TEXT,
        image_optimized TEXT,
        want TEXT,
        category TEXT,
        status TEXT DEFAULT 'active',  -- (active, locked, traded)
        FOREIGN KEY (user) REFERENCES users(username) ON DELETE CASCADE
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS chains (
        chain_id TEXT PRIMARY KEY,
        status TEXT DEFAULT 'pending', -- (pending, accepted, declined)
        rating REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS chain_items (
        chain_id TEXT,
        item_id TEXT,
        position INTEGER,  -- Para saber el orden del intercambio (A -> B -> C -> A)
        status TEXT DEFAULT 'neutral', -- (neutral, accepted, declined)
        PRIMARY KEY (chain_id, item_id),
        FOREIGN KEY (chain_id) REFERENCES chains(chain_id) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE
    )
    """)
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        item_id TEXT,
        message TEXT,
        is_read INTEGER DEFAULT 0,  -- 0 = No leída, 1 = Notificada como toast pero no leida, 2 = Vista en notificaciones
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user) REFERENCES users(username) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()


# ===============================
# FUNCIONES PARA NOTIFICACIONES
# ===============================
def add_notification(user, item_id, message, cursor=None): # No dona error si es crida des d'una altra funció amb una connexió oberta a la BD
    """Guarda una nueva notificación reusando la transacción si se pasa un cursor."""
    query = """
        INSERT INTO notifications (user, item_id, message) 
        VALUES (?, ?, ?)
    """
    if cursor:
        cursor.execute(query, (user, item_id, message))
    else:
        conn = get_conn()
        c = conn.cursor()
        
        try:
            c.execute(query, (user, item_id, message))
            conn.commit()
        except Exception as e:
            print(f"Error al añadir notificación: {e}")
            conn.rollback()
        finally:
            conn.close()

def get_notifications(user, intent):
    """Recupera las notificaciones de un usuario en formato diccionario."""
    conn = get_conn()
    c = conn.cursor()
    
    try:
        
        if intent == "toast":
            
            c.execute("""
                SELECT *
                FROM notifications
                WHERE user = ? AND is_read = 0
                ORDER BY created_at DESC
            """, (user,))
            
            rows = c.fetchall()
            columns = [desc[0] for desc in c.description]
            
            new_notifications = [dict(zip(columns, row)) for row in rows]
            
            if new_notifications:
                
                notif_ids = [n["notification_id"] for n in new_notifications]
                placeholders = ",".join("?" for _ in notif_ids)
                
                c.execute(f"""
                    UPDATE notifications
                    SET is_read = 1
                    WHERE notification_id IN ({placeholders})
                """, notif_ids)
                
                conn.commit()
                
            c.execute("""
                SELECT COUNT(*) FROM notifications
                WHERE user = ? AND is_read = 1
            """, (user,))
                
            pending_notifications = c.fetchone()[0]
                
            return new_notifications, pending_notifications
            
        elif intent == "show_notifications":
            
            c.execute("""
                SELECT *
                FROM notifications
                WHERE user = ?
                ORDER BY created_at DESC
            """, (user,))
            
            rows = c.fetchall()
            columns = [desc[0] for desc in c.description]
            
            return [dict(zip(columns, row)) for row in rows]
    
    except Exception as e:
        print(f"Error al recoger las notificaciones: {e}")
        conn.rollback()
        return [], False
    finally:
        c.close()
        conn.close()

def mark_notifications_as_read(user):
    """Marca todas las notificaciones pendientes de un usuario como leídas."""
    conn = get_conn()
    c = conn.cursor()
    
    c.execute("""
        UPDATE notifications 
        SET is_read = 2
        WHERE user = ? AND is_read = 1
    """, (user,))
    
    conn.commit()
    conn.close()
    
def vaciar_notificaciones():
    # Conecta a tu archivo de base de datos
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        # 1. Borramos los datos
        cursor.execute("DELETE FROM notifications;")
        # 2. Reiniciamos el contador de IDs
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='notifications';")
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al vaciar la tabla: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


#=============================
# FUNCIONES PARA USERS
#=============================
def get_password():
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT * FROM users")
    rows = c.fetchall()
    print(rows)

def get_user_image_by_item_id(item_id):
    conn = get_conn()
    c = conn.cursor()

    try:
        c.execute("""
            SELECT u.user_image
            FROM users u
            JOIN items i ON u.username = i.user
            WHERE i.item_id = ?
        """, (item_id,))
        
        row = c.fetchone()
        
        return row[0]
            
        #return "image_not_found.png"
        
    except Exception as e:
        print(f"Error al consultar imagen del usuario: {e}")
        return "image_not_found.png"
        
    finally:
        conn.close()
    
def get_user_by_username(username):
    conn = get_conn()
    c = conn.cursor()

    try:
        c.execute("""
            SELECT *
            FROM users
            WHERE username = ?
        """, (username,))
                
        row = c.fetchone()

        # nombres de columnas
        columns = [desc[0] for desc in c.description]

        # convertir a dict
        return dict(zip(columns, row))
        
    except Exception as e:
        print(f"Error al consultar el usuario desde get_user_by_username: {e}")
        return None
        
    finally:
        conn.close()

def add_user(username, password, user_image):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO users (username, password, user_image)
            VALUES (?,?,?)
        """, (username, password, user_image))
        
        conn.commit()
        conn.close()

        message = f"Hola {username} :partying:! Benvingut a ODISEO. A punt per començar a intercanviar :wink:?"
        add_notification(username, None, message, cursor=c)
        
        return True
        
    except Exception as e:
        print(f"Error al crear el usuario: {e}") # 👈 Imprime el error real en la terminal
        conn.rollback()
        return False
        
    finally:
        conn.close()

def update_image_profile(username, new_image):
    conn = get_conn()
    c = conn.cursor()
    
    try:
        c.execute("""
            UPDATE users
            SET user_image = ?
            WHERE username = ?
        """, (new_image, username))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error en update_image_profile: {e}")
        conn.rollback() # Si algo falla, deshace todo para no dejar datos corruptos
        return False
        
    finally:
        conn.close()

#=============================
# FUNCIONES PARA ITEMS
#=============================
def add_item(user, have, description, image, image_optimized, want, category):
    conn = get_conn()
    c = conn.cursor()
    try:
        item_id = f"it_{str(uuid.uuid4())[:8]}"
        c.execute("""
            INSERT INTO items (user, item_id, have, description, image, image_optimized, want, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user, item_id, have, description, image, image_optimized, want, category))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_items():
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT * FROM items")
    rows = c.fetchall()

    # nombres de columnas
    columns = [desc[0] for desc in c.description]

    conn.close()

    # convertir a dict
    return [dict(zip(columns, row)) for row in rows]

def get_item_from_item_id(item_id):
    conn = get_conn()
    c = conn.cursor()
    
    c.execute("SELECT * FROM items i WHERE i.item_id = ?", (item_id,))        
    
    row = c.fetchone()
    columns = [desc[0] for desc in c.description]
    
    conn.close()
    
    return dict(zip(columns, row))

def get_items_from_user(user):
    conn = get_conn()
    c = conn.cursor()

    # Buscamos filtrando por el usuario de forma segura
    c.execute("SELECT * FROM items WHERE user = ? AND status = 'active'", (user,))
    
    rows = c.fetchall()
    # nombres de columnas
    columns = [desc[0] for desc in c.description]

    conn.close()

    # convertir a dict
    return [dict(zip(columns, row)) for row in rows]
    
def is_item_accepted_in_any_chain(item_id):
    conn = get_conn()
    c = conn.cursor()
    
    # Cuenta si este item tiene alguna participación con status 'accepted'
    c.execute("""
        SELECT COUNT(*) 
        FROM chain_items 
        WHERE item_id = ? AND status = 'accepted'
    """, (item_id,))
    
    count = c.fetchone()[0]
    
    c.close()
    conn.close()
    
    return count > 0
    
def get_reserved_items(items):
    conn = get_conn()
    c = conn.cursor()

    item_ids = [item["item_id"] for item in items]

    if not item_ids:
        return set()

    placeholders = ",".join("?" * len(item_ids))

    c.execute(f"""
        SELECT DISTINCT item_id
        FROM chain_items
        WHERE status = 'accepted'
          AND item_id IN ({placeholders})
    """, item_ids)

    reserved_items = {row[0] for row in c.fetchall()}

    c.close()
    conn.close()

    return reserved_items
    
def delete_item(item_id):
    conn = get_conn()
    c = conn.cursor()
        
    try:
        # 1. Buscamos todas las cadenas en las que participa este item
        c.execute("""
            SELECT DISTINCT chain_id 
            FROM chain_items 
            WHERE item_id = ?
        """, (item_id,))
        
        affected_chain_ids = [row[0] for row in c.fetchall()]
        
        # 2. Si el artículo pertenecía a alguna cadena, las cancelamos y notificamos
        if affected_chain_ids:
            # Construimos los marcadores de posición (?, ?, ...) para la consulta IN
            placeholders = ','.join('?' * len(affected_chain_ids))

            # Marcamos las cadenas afectadas como 'declined'
            c.execute(f"""
                UPDATE chains 
                SET status = 'declined' 
                WHERE chain_id IN ({placeholders})
            """, affected_chain_ids)
            
            # Actualizamos también el estado dentro de chain_items
            c.execute(f"""
                UPDATE chain_items 
                SET status = 'declined' 
                WHERE chain_id IN ({placeholders})
            """, affected_chain_ids)

            # Obtenemos los ítems, usuarios y las cadenas afectadas
            # Opcional: filtramos 'WHERE i.item_id != ?' para no notificar al usuario que borró el ítem
            c.execute(f"""
                SELECT DISTINCT ci.chain_id, i.user, i.item_id, i.have
                FROM items i
                JOIN chain_items ci ON i.item_id = ci.item_id
                WHERE ci.chain_id IN ({placeholders})
            """, affected_chain_ids)
            
            affected_items = c.fetchall()
            
            # Enviar notificaciones vinculando cada usuario con su respectiva cadena e ítem
            for row in affected_items:
                chain_id, affected_user, affected_item_id, affected_item_name = row
                
                message = f"El teu article '{affected_item_name}' ha sortit de la cadena #{chain_id} perquè un dels articles s'ha eliminat."
                add_notification(affected_user, affected_item_id, message, cursor=c)

        # 3. Finalmente eliminamos el item
        c.execute("DELETE FROM items WHERE item_id = ?", (item_id,))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# =======================
# FUNCIONS PER A CADENES
# =======================
def calculate_chain_rating(item_ids, hypothetical):
    conn = get_conn()
    c = conn.cursor()

    # Obtener media de puntuaciones de los items de la cadena
    placeholders = ','.join('?' * len(item_ids))
    
    c.execute(f"""
        SELECT AVG(u.rating) 
        FROM items i
        JOIN users u ON i.user = u.username 
        WHERE i.item_id IN ({placeholders})
    """, item_ids)
    
    avg_items_rating = c.fetchone()[0]

    if hypothetical:
        avg_items_rating = (avg_items_rating * len(item_ids) + st.session_state.user_rating)/(len(item_ids) + 1)
        chain_length = len(item_ids) + 1
    else:
        chain_length = len(item_ids)

    conn.close()

    # Variables per a calcular length_score
    k = 1
    x0 = 6
    
    length_score = 5.0 / (1.0 + math.exp(k * (chain_length - x0)))
    
    # Ponderación: 40% longitud + 60% media de puntuaciones
    rating = round((0.60 * length_score) + (0.40 * avg_items_rating), 1)
    
    return rating

def add_chains(item_ids):
    if not item_ids:
        return None

    conn = get_conn()
    c = conn.cursor()
    
    try:
        chain_id = f"ch_{str(uuid.uuid4())[:8]}"
        rating = calculate_chain_rating(item_ids, False)
        
        c.execute(
            "INSERT INTO chains (chain_id, rating) VALUES (?, ?)", 
            (chain_id, rating)
        )
        
        for position, item_id in enumerate(item_ids):
            c.execute("""
                INSERT INTO chain_items (chain_id, item_id, position)
                VALUES (?, ?, ?)
            """, (chain_id, item_id, position))
            
        conn.commit()
        return chain_id
        
    except Exception as e:
        conn.rollback()
        print(f"Error al guardar la cadena: {e}")
        return None
        
    finally:
        conn.close()

def accept_chain(chain_id, item_id):
    conn = get_conn()
    c = conn.cursor()

    try:
        # Cambiamos el estado de participación a accepted del usuario en la cadena que acaba de aceptar
        c.execute("""
            UPDATE chain_items
            SET status = 'accepted'
            WHERE chain_id = ? AND item_id = ?
        """, (chain_id, item_id))
        
        # Cambiamos el estado de participación a neutral del usuario en el resto de cadenas en las que está su item (solo puede aceptar una a la vez)
        c.execute("""
            UPDATE chain_items
            SET status = 'neutral'
            WHERE chain_id != ? AND item_id = ?
        """, (chain_id, item_id))
        
        # Recogemos los usuarios que tienen un articulo involucrado en la cadena que se acaba de aceptar
        c.execute("""
            SELECT i.user, ci.item_id, i.have, ci.status
            FROM chain_items ci
            JOIN items i ON ci.item_id = i.item_id
            WHERE ci.chain_id = ?
        """, (chain_id,))
        
        acc_affected_items = c.fetchall()
        total_number_users_in_chain = len(acc_affected_items)
        accepted_number_users_in_chain = sum(1 for item in acc_affected_items if item[3] == 'accepted')
        
        # Entra en el if si la cadena no ha sido aceptada por todos sus participantes
        if accepted_number_users_in_chain < total_number_users_in_chain:
        
            for item in acc_affected_items:
            
                affected_user = item[0]
                affected_item_id = item[1]
                affected_item_name = item[2]
                
                message = f"El teu article '{affected_item_name}' està més a prop de l'intercanvi! Ja han acceptat {accepted_number_users_in_chain} de {total_number_users_in_chain} usuaris a la cadena #{chain_id}."
                add_notification(affected_user, affected_item_id, message, cursor=c)
                
        # Entra en el elif si la cadena ha sido aceptada por todos sus participantes
        elif accepted_number_users_in_chain == total_number_users_in_chain:
                
            # Cambiamos el estado de la cadena a accepted
            c.execute("""
                UPDATE chains
                SET status = 'accepted'
                WHERE chain_id = ?
            """, (chain_id,))
            
            for item in acc_affected_items:
            
                affected_user = item[0]
                affected_item_id = item[1]
                affected_item_name = item[2]
                
                message = f"Felicitats! El teu article '{affected_item_name}' està a punt per intercanviar! Tots els usuaris de la cadena #{chain_id} han acceptat l'intercanvi."
                add_notification(affected_user, affected_item_id, message, cursor=c)
            
                # Cambiamos el estado de participacion a declined del usuario que tiene el mismo item en alguna otra cadena
                c.execute("""
                    UPDATE chain_items
                    SET status = 'declined'
                    WHERE chain_id != ? AND item_id = ?
                """, (chain_id, affected_item_id))
            
                # Cambiamos el estado del resto de las cadenas en la que el usuario tiene el mismo item involucrado a declined (para que no se pueda aceptar una cadena y después salir)
                c.execute("""
                    UPDATE chains
                    SET status = 'declined'
                    WHERE chain_id IN (
                        SELECT chain_id 
                        FROM chain_items 
                        WHERE chain_id != ? AND item_id = ?
                    )
                """, (chain_id, affected_item_id))
            
                # Cambiamos el estado de ese item a locked
                c.execute("""
                    UPDATE items
                    SET status = 'locked'
                    WHERE item_id = ?
                """, (affected_item_id,))
            
                # Seleccionamos a los usuarios de las cadenas que se acaban de rechazar en el execute anterior para notificarlas
                c.execute("""
                    SELECT i.user, ci.item_id, i.have, ci.chain_id
                    FROM chain_items ci
                    JOIN items i ON ci.item_id = i.item_id
                    WHERE ci.item_id != ? AND ci.chain_id IN (
                        SELECT chain_id 
                        FROM chain_items 
                        WHERE chain_id != ? AND item_id = ?
                    )
                """, (affected_item_id, chain_id, affected_item_id))
            
                den_affected_items = c.fetchall()
                
                for den_item in den_affected_items:
                    
                    d_affected_user = den_item[0]
                    d_affected_item_id = den_item[1]
                    d_affected_item_name = den_item[2]
                    d_affected_chain_id = den_item[3]
                    
                    message = f"El teu article {d_affected_item_name} ha sortit de la cadena {d_affected_chain_id} perquè un usuari ha tancat un altre intercanvi."
                    add_notification(d_affected_user, d_affected_item_id, message, cursor=c)
            
        conn.commit()

    except Exception as e:
        print(f"Error al aceptar la cadena: {e}")
        conn.rollback() # Si algo falla, deshace todo para no dejar datos corruptos
        return False
        
    finally:
        c.close()
        conn.close()

def leave_chain(chain_id, item_id):
    conn = get_conn()
    c = conn.cursor()
    
    try:
        # Cambiamos el estado de participacion del item en esa cadena a neutral
        c.execute("""
            UPDATE chain_items
            SET status = 'neutral'
            WHERE chain_id = ? AND item_id = ?
        """, (chain_id, item_id))
        
        # Recogemos todos los usuarios que participan en la cadena para notificar
        c.execute("""
            SELECT i.user, ci.item_id, i.have, ci.status
            FROM chain_items ci
            JOIN items i ON ci.item_id = i.item_id
            WHERE ci.chain_id = ?
        """, (chain_id,))
        
        affected_items = c.fetchall()
        total_number_users_in_chain = len(affected_items)
        accepted_number_users_in_chain = sum(1 for item in affected_items if item[3] == 'accepted')
        
        for item in affected_items:
            
            affected_user = item[0]
            affected_item_id = item[1]
            affected_item_name = item[2]
            
            message = f"Vaja, un usuari ha sortit de la cadena {chain_id}! En total han acceptat {accepted_number_users_in_chain} de {total_number_users_in_chain} usuaris a la cadena #{chain_id}."
            add_notification(affected_user, affected_item_id, message, cursor=c)
            
        conn.commit()

    except Exception as e:
        print(f"Error al aceptar la cadena: {e}")
        conn.rollback() # Si algo falla, deshace todo para no dejar datos corruptos
        return False
        
    finally:
        c.close()
        conn.close()

def decline_chain(chain_id, item_id):
    conn = get_conn()
    c = conn.cursor()
    
    try:
        c.execute("""
            UPDATE chains 
            SET status = 'declined' 
            WHERE chain_id = ?
        """, (chain_id,))

        c.execute("""
            UPDATE chain_items
            SET status = 'declined'
            WHERE chain_id = ? AND item_id = ?
        """, (chain_id, item_id))
        
        c.execute("""
            SELECT i.user, ci.item_id, i.have 
            FROM chain_items ci
            JOIN items i ON ci.item_id = i.item_id
            WHERE ci.chain_id = ?
        """, (chain_id,))
        
        affected_items = c.fetchall()
        
        for item in affected_items:
            
            affected_user = item[0]
            affected_item_id = item[1]
            affected_item_name = item[2]
            
            message = f"Vaja! El teu article {affected_item_name} ha sortit de la cadena #{chain_id} perquè un usuari l'ha trencada :scream:. No et preocupis, seguirem treballant en el teu intercanvi :grin:."
            add_notification(affected_user, affected_item_id, message, cursor=c)
            
        conn.commit()
    
    except Exception as e:
        print(f"Error al declinar la cadena: {e}")
        conn.rollback() # Si algo falla, deshace todo para no dejar datos corruptos
        return False
        
    finally:
        c.close()
        conn.close()

#=============================
# FUNCIONES PARA DIGRAFO
#=============================
@st.cache_data(show_spinner=False) # ¡Crucial per al rendiment de Streamlit!
def get_digraph_data():
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT * FROM items WHERE items.status = 'active'")
    rows = c.fetchall()
    columns = [desc[0] for desc in c.description]
    
    nodes = [dict(zip(columns, row)) for row in rows]
    
    conn.close()
    
    arcs = []
    
    for current in nodes:
        for candidate in nodes:
            if current['item_id'] == candidate['item_id'] or current['user'] == candidate['user']:
                continue
            
            # Passem els dos ítems SENCERS tal com surten de la base de dades
            if directional_match_have(current, candidate):
                # Si hi ha coincidència, guardem l'aresta (origen -> destí)
                arcs.append((current['item_id'], candidate['item_id']))
                
    return nodes, arcs