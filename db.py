import uuid
import math
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

from services.match import directional_match_want, directional_match_have


# =============================
# FUNCIONES PARA INICIAR LA DB
# =============================
def get_conn():
    """Establece la conexión con la base de datos PostgreSQL de Supabase."""
    conn = psycopg2.connect(
        host=st.secrets["supabase"]["host"],
        database=st.secrets["supabase"]["database"],
        user=st.secrets["supabase"]["user"],
        password=st.secrets["supabase"]["password"],
        port=st.secrets["supabase"]["port"]
    )
    return conn

def init_db():
    """Crea las tablas en PostgreSQL si no existen."""
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username VARCHAR PRIMARY KEY,
        password VARCHAR,
        user_image VARCHAR,
        rating REAL DEFAULT 5.0
    );
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS items (
        item_id VARCHAR PRIMARY KEY,
        "user" VARCHAR,
        have VARCHAR,
        description TEXT,
        image TEXT,
        image_optimized TEXT,
        want VARCHAR,
        category VARCHAR,
        status VARCHAR DEFAULT 'active',  -- (active, locked, traded)
        FOREIGN KEY ("user") REFERENCES users(username) ON DELETE CASCADE
    );
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS chains (
        chain_id VARCHAR PRIMARY KEY,
        status VARCHAR DEFAULT 'pending', -- (pending, accepted, declined)
        rating REAL
    );
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS chain_items (
        chain_id VARCHAR,
        item_id VARCHAR,
        position INTEGER,
        status VARCHAR DEFAULT 'neutral', -- (neutral, accepted, declined)
        PRIMARY KEY (chain_id, item_id),
        FOREIGN KEY (chain_id) REFERENCES chains(chain_id) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE
    );
    """)
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        notification_id SERIAL PRIMARY KEY,
        "user" VARCHAR,
        item_id VARCHAR,
        message TEXT,
        is_read INTEGER DEFAULT 0,  -- 0 = No leída, 1 = Notificada como toast, 2 = Vista
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY ("user") REFERENCES users(username) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    c.close()
    conn.close()


# ===============================
# FUNCIONES PARA NOTIFICACIONES
# ===============================
def add_notification(user, item_id, message, cursor=None):
    query = """
        INSERT INTO notifications ("user", item_id, message) 
        VALUES (%s, %s, %s);
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
            c.close()
            conn.close()

def get_notifications(user, intent):
    conn = get_conn()
    c = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        if intent == "toast":
            c.execute("""
                SELECT *
                FROM notifications
                WHERE "user" = %s AND is_read = 0
                ORDER BY created_at DESC;
            """, (user,))
            
            new_notifications = c.fetchall()
            
            if new_notifications:
                notif_ids = [n["notification_id"] for n in new_notifications]
                placeholders = ",".join("%s" for _ in notif_ids)
                
                c.execute(f"""
                    UPDATE notifications
                    SET is_read = 1
                    WHERE notification_id IN ({placeholders});
                """, tuple(notif_ids))
                
                conn.commit()
                
            c.execute("""
                SELECT COUNT(*) as count FROM notifications
                WHERE "user" = %s AND is_read = 1;
            """, (user,))
                
            row = c.fetchone()
            pending_notifications = row["count"] if row else 0
                
            return new_notifications, pending_notifications
            
        elif intent == "show_notifications":
            c.execute("""
                SELECT *
                FROM notifications
                WHERE "user" = %s
                ORDER BY created_at DESC;
            """, (user,))
            
            return c.fetchall()

        return ([], 0) if intent == "toast" else []

    except Exception as e:
        print(f"Error al recoger las notificaciones: {e}")
        conn.rollback()
        return ([], 0) if intent == "toast" else []
    finally:
        c.close()
        conn.close()

def mark_notifications_as_read(user):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("""
            UPDATE notifications 
            SET is_read = 2
            WHERE "user" = %s AND is_read = 1;
        """, (user,))
        conn.commit()
    except Exception as e:
        print(f"Error al marcar notificaciones como leídas: {e}")
        conn.rollback()
    finally:
        c.close()
        conn.close()

def vaciar_notificaciones():
    conn = get_conn()
    c = conn.cursor()
    try:
        # En PostgreSQL RESTART IDENTITY borra los registros y reinicia el contador SERIAL a 1
        c.execute("TRUNCATE TABLE notifications RESTART IDENTITY;")
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al vaciar la tabla: {e}")
        conn.rollback()
        return False
    finally:
        c.close()
        conn.close()


# =============================
# FUNCIONES PARA USERS
# =============================
def get_password():
    conn = get_conn()
    c = conn.cursor(cursor_factory=RealDictCursor)
    try:
        c.execute("SELECT username, password FROM users;")
        return c.fetchall()
    except Exception as e:
        print(f"Error al obtener contraseñas: {e}")
        return []
    finally:
        c.close()
        conn.close()

def get_user_image_by_item_id(item_id):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("""
            SELECT u.user_image
            FROM users u
            JOIN items i ON u.username = i."user"
            WHERE i.item_id = %s;
        """, (item_id,))
        
        row = c.fetchone()
        if row and row[0]:
            return row[0]
        return "image_not_found.png"
    except Exception as e:
        print(f"Error al consultar imagen del usuario: {e}")
        return "image_not_found.png"
    finally:
        c.close()
        conn.close()

def get_user_by_username(username):
    conn = get_conn()
    c = conn.cursor(cursor_factory=RealDictCursor)
    try:
        c.execute("""
            SELECT *
            FROM users
            WHERE username = %s;
        """, (username,))
                
        return c.fetchone()
    except Exception as e:
        print(f"Error al consultar el usuario desde get_user_by_username: {e}")
        return None
    finally:
        c.close()
        conn.close()

def add_user(username, password, user_image):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO users (username, password, user_image)
            VALUES (%s, %s, %s);
        """, (username, password, user_image))

        message = f"Hola {username} 🎉! Benvingut a ODISEO. A punt per començar a intercanviar 😉?"
        add_notification(username, None, message, cursor=c)
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al crear el usuario: {e}")
        conn.rollback()
        return False
    finally:
        c.close()
        conn.close()

def update_image_profile(username, new_image):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("""
            UPDATE users
            SET user_image = %s
            WHERE username = %s;
        """, (new_image, username))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error en update_image_profile: {e}")
        conn.rollback()
        return False
    finally:
        c.close()
        conn.close()


# =============================
# FUNCIONES PARA ITEMS
# =============================
def add_item(user, have, description, image, image_optimized, want, category):
    conn = get_conn()
    c = conn.cursor()
    try:
        item_id = f"it_{str(uuid.uuid4())[:8]}"
        c.execute("""
            INSERT INTO items ("user", item_id, have, description, image, image_optimized, want, category)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """, (user, item_id, have, description, image, image_optimized, want, category))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al añadir item: {e}")
        conn.rollback()
        return False
    finally:
        c.close()
        conn.close()

def get_items():
    conn = get_conn()
    c = conn.cursor(cursor_factory=RealDictCursor)
    try:
        c.execute("SELECT * FROM items;")
        return c.fetchall()
    except Exception as e:
        print(f"Error al obtener items: {e}")
        return []
    finally:
        c.close()
        conn.close()

def get_item_from_item_id(item_id):
    conn = get_conn()
    c = conn.cursor(cursor_factory=RealDictCursor)
    try:
        c.execute("SELECT * FROM items WHERE item_id = %s;", (item_id,))        
        return c.fetchone()
    except Exception as e:
        print(f"Error al obtener item por ID: {e}")
        return None
    finally:
        c.close()
        conn.close()

def get_items_from_user(user):
    conn = get_conn()
    c = conn.cursor(cursor_factory=RealDictCursor)
    try:
        c.execute('SELECT * FROM items WHERE "user" = %s AND status = \'active\';', (user,))
        return c.fetchall()
    except Exception as e:
        print(f"Error al obtener items del usuario: {e}")
        return []
    finally:
        c.close()
        conn.close()
    
def is_item_accepted_in_any_chain(item_id):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("""
            SELECT COUNT(*) 
            FROM chain_items 
            WHERE item_id = %s AND status = 'accepted';
        """, (item_id,))
        count = c.fetchone()[0]
        return count > 0
    except Exception as e:
        print(f"Error al consultar estado del item en cadenas: {e}")
        return False
    finally:
        c.close()
        conn.close()
    
def get_reserved_items(items):
    conn = get_conn()
    c = conn.cursor()

    item_ids = [item["item_id"] for item in items]

    if not item_ids:
        conn.close()
        return set()

    try:
        placeholders = ",".join("%s" for _ in item_ids)
        c.execute(f"""
            SELECT DISTINCT item_id
            FROM chain_items
            WHERE status = 'accepted'
              AND item_id IN ({placeholders});
        """, tuple(item_ids))

        reserved_items = {row[0] for row in c.fetchall()}
        return reserved_items
    except Exception as e:
        print(f"Error al obtener items reservados: {e}")
        return set()
    finally:
        c.close()
        conn.close()
    
def delete_item(item_id):
    conn = get_conn()
    c = conn.cursor()
        
    try:
        c.execute("""
            SELECT DISTINCT chain_id 
            FROM chain_items 
            WHERE item_id = %s;
        """, (item_id,))
        
        affected_chain_ids = [row[0] for row in c.fetchall()]
        
        if affected_chain_ids:
            placeholders = ','.join('%s' for _ in affected_chain_ids)

            c.execute(f"""
                UPDATE chains 
                SET status = 'declined' 
                WHERE chain_id IN ({placeholders});
            """, tuple(affected_chain_ids))
            
            c.execute(f"""
                UPDATE chain_items 
                SET status = 'declined' 
                WHERE chain_id IN ({placeholders});
            """, tuple(affected_chain_ids))

            c.execute(f"""
                SELECT DISTINCT ci.chain_id, i."user", i.item_id, i.have
                FROM items i
                JOIN chain_items ci ON i.item_id = ci.item_id
                WHERE ci.chain_id IN ({placeholders});
            """, tuple(affected_chain_ids))
            
            affected_items = c.fetchall()
            
            for row in affected_items:
                chain_id, affected_user, affected_item_id, affected_item_name = row
                message = f"El teu article '{affected_item_name}' ha sortit de la cadena #{chain_id} perquè un dels articles s'ha eliminat."
                add_notification(affected_user, affected_item_id, message, cursor=c)

        c.execute("DELETE FROM items WHERE item_id = %s;", (item_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error al eliminar el item: {e}")
        return False
    finally:
        c.close()
        conn.close()


# =======================
# FUNCIONS PER A CADENES
# =======================
def calculate_chain_rating(item_ids, hypothetical):
    if not item_ids and not hypothetical:
        return 5.0

    conn = get_conn()
    c = conn.cursor()

    try:
        if item_ids:
            placeholders = ','.join('%s' for _ in item_ids)
            c.execute(f"""
                SELECT AVG(u.rating) 
                FROM items i
                JOIN users u ON i."user" = u.username 
                WHERE i.item_id IN ({placeholders});
            """, tuple(item_ids))
            avg_items_rating = c.fetchone()[0]
        else:
            avg_items_rating = 5.0

        if avg_items_rating is None:
            avg_items_rating = 5.0

        user_rating = st.session_state.get("user_rating", 5.0)

        if hypothetical:
            avg_items_rating = (avg_items_rating * len(item_ids) + user_rating) / (len(item_ids) + 1)
            chain_length = len(item_ids) + 1
        else:
            chain_length = len(item_ids)

        k = 1
        x0 = 6
        length_score = 5.0 / (1.0 + math.exp(k * (chain_length - x0)))
        rating = round((0.60 * length_score) + (0.40 * float(avg_items_rating)), 1)
        
        return rating
    except Exception as e:
        print(f"Error al calcular rating de cadena: {e}")
        return 5.0
    finally:
        c.close()
        conn.close()

def add_chains(item_ids):
    if not item_ids:
        return None

    conn = get_conn()
    c = conn.cursor()
    
    try:
        chain_id = f"ch_{str(uuid.uuid4())[:8]}"
        rating = calculate_chain_rating(item_ids, False)
        
        c.execute(
            "INSERT INTO chains (chain_id, rating) VALUES (%s, %s);", 
            (chain_id, rating)
        )
        
        for position, item_id in enumerate(item_ids):
            c.execute("""
                INSERT INTO chain_items (chain_id, item_id, position)
                VALUES (%s, %s, %s);
            """, (chain_id, item_id, position))
            
        conn.commit()
        return chain_id
    except Exception as e:
        conn.rollback()
        print(f"Error al guardar la cadena: {e}")
        return None
    finally:
        c.close()
        conn.close()

def accept_chain(chain_id, item_id):
    conn = get_conn()
    c = conn.cursor()

    try:
        c.execute("""
            UPDATE chain_items
            SET status = 'accepted'
            WHERE chain_id = %s AND item_id = %s;
        """, (chain_id, item_id))
        
        c.execute("""
            UPDATE chain_items
            SET status = 'neutral'
            WHERE chain_id != %s AND item_id = %s;
        """, (chain_id, item_id))
        
        c.execute("""
            SELECT i."user", ci.item_id, i.have, ci.status
            FROM chain_items ci
            JOIN items i ON ci.item_id = i.item_id
            WHERE ci.chain_id = %s;
        """, (chain_id,))
        
        acc_affected_items = c.fetchall()
        total_number_users_in_chain = len(acc_affected_items)
        accepted_number_users_in_chain = sum(1 for item in acc_affected_items if item[3] == 'accepted')
        
        if accepted_number_users_in_chain < total_number_users_in_chain:
            for item in acc_affected_items:
                affected_user = item[0]
                affected_item_id = item[1]
                affected_item_name = item[2]
                
                message = f"El teu article '{affected_item_name}' està més a prop de l'intercanvi! Ja han acceptat {accepted_number_users_in_chain} de {total_number_users_in_chain} usuaris a la cadena #{chain_id}."
                add_notification(affected_user, affected_item_id, message, cursor=c)
                
        elif accepted_number_users_in_chain == total_number_users_in_chain:
            c.execute("""
                UPDATE chains
                SET status = 'accepted'
                WHERE chain_id = %s;
            """, (chain_id,))
            
            for item in acc_affected_items:
                affected_user = item[0]
                affected_item_id = item[1]
                affected_item_name = item[2]
                
                message = f"Felicitats! El teu article '{affected_item_name}' està a punt per intercanviar! Tots els usuaris de la cadena #{chain_id} han acceptat l'intercanvi."
                add_notification(affected_user, affected_item_id, message, cursor=c)
            
                c.execute("""
                    UPDATE chain_items
                    SET status = 'declined'
                    WHERE chain_id != %s AND item_id = %s;
                """, (chain_id, affected_item_id))
            
                c.execute("""
                    UPDATE chains
                    SET status = 'declined'
                    WHERE chain_id IN (
                        SELECT chain_id 
                        FROM chain_items 
                        WHERE chain_id != %s AND item_id = %s
                    );
                """, (chain_id, affected_item_id))
            
                c.execute("""
                    UPDATE items
                    SET status = 'locked'
                    WHERE item_id = %s;
                """, (affected_item_id,))
            
                c.execute("""
                    SELECT i."user", ci.item_id, i.have, ci.chain_id
                    FROM chain_items ci
                    JOIN items i ON ci.item_id = i.item_id
                    WHERE ci.item_id != %s AND ci.chain_id IN (
                        SELECT chain_id 
                        FROM chain_items 
                        WHERE chain_id != %s AND item_id = %s
                    );
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
        return True

    except Exception as e:
        print(f"Error al aceptar la cadena: {e}")
        conn.rollback()
        return False
    finally:
        c.close()
        conn.close()

def leave_chain(chain_id, item_id):
    conn = get_conn()
    c = conn.cursor()
    
    try:
        c.execute("""
            UPDATE chain_items
            SET status = 'neutral'
            WHERE chain_id = %s AND item_id = %s;
        """, (chain_id, item_id))
        
        c.execute("""
            SELECT i."user", ci.item_id, i.have, ci.status
            FROM chain_items ci
            JOIN items i ON ci.item_id = i.item_id
            WHERE ci.chain_id = %s;
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
        return True

    except Exception as e:
        print(f"Error al salir de la cadena: {e}")
        conn.rollback()
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
            WHERE chain_id = %s;
        """, (chain_id,))

        c.execute("""
            UPDATE chain_items
            SET status = 'declined'
            WHERE chain_id = %s AND item_id = %s;
        """, (chain_id, item_id))
        
        c.execute("""
            SELECT i."user", ci.item_id, i.have 
            FROM chain_items ci
            JOIN items i ON ci.item_id = i.item_id
            WHERE ci.chain_id = %s;
        """, (chain_id,))
        
        affected_items = c.fetchall()
        
        for item in affected_items:
            affected_user = item[0]
            affected_item_id = item[1]
            affected_item_name = item[2]
            
            message = f"Vaja! El teu article {affected_item_name} ha sortit de la cadena #{chain_id} perquè un usuari l'ha trencada 😱. No et preocupis, seguirem treballant en el teu intercanvi 😁."
            add_notification(affected_user, affected_item_id, message, cursor=c)
            
        conn.commit()
        return True
    
    except Exception as e:
        print(f"Error al declinar la cadena: {e}")
        conn.rollback()
        return False
    finally:
        c.close()
        conn.close()


# =============================
# FUNCIONES PARA DIGRAFO
# =============================
@st.cache_data(show_spinner=False)
def get_digraph_data():
    conn = get_conn()
    c = conn.cursor(cursor_factory=RealDictCursor)

    try:
        c.execute("SELECT * FROM items WHERE status = 'active';")
        nodes = c.fetchall()
    finally:
        c.close()
        conn.close()
    
    arcs = []
    
    for current in nodes:
        for candidate in nodes:
            if current['item_id'] == candidate['item_id'] or current['user'] == candidate['user']:
                continue
            
            if directional_match_have(current, candidate):
                arcs.append((current['item_id'], candidate['item_id']))
                
    return nodes, arcs
