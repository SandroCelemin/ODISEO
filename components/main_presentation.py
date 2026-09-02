import streamlit as st
#import base64
#import os

def render_presentation(supabase):
    """
    # 1. Cerca de la carpeta d'imatges
    possible_paths = [
        "imagenes_main",
        os.path.join(os.path.dirname(__file__), "..", "imagenes_main"),
        os.path.join(os.path.dirname(__file__), "imagenes_main")
    ]
    
    folder_path = None
    for path in possible_paths:
        if os.path.exists(path) and os.path.isdir(path):
            folder_path = path
            break

    if not folder_path:
        st.error("No s'ha trobat la carpeta 'imagenes_main'.")
        return

    # 2. Càrrega automàtica de fitxers
    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp')
    found_files = [f for f in sorted(os.listdir(folder_path)) if f.lower().endswith(valid_extensions)]

    images_b64 = []
    for file_name in found_files:
        full_path = os.path.join(folder_path, file_name)
        try:
            with open(full_path, "rb") as f:
                b64_str = base64.b64encode(f.read()).decode("utf-8")
                ext = file_name.split(".")[-1].lower()
                mime = "jpeg" if ext in ["jpg", "jpeg"] else ext
                images_b64.append(f"data:image/{mime};base64,{b64_str}")
        except Exception:
            pass

    num_images = len(images_b64)

    if num_images == 0:
        st.warning(f"No s'han trobat imatges a la carpeta '{folder_path}'.")
        return
    """
    # 1. Obtener lista de imágenes desde el bucket
    bucket_name = "imagenes_main"
    try:
        files = supabase.storage.from_(bucket_name).list()
        valid_ext = ('.jpg', '.jpeg', '.png', '.webp')
        found_files = [f['name'] for f in files if f['name'].lower().endswith(valid_ext)]
    except Exception as e:
        st.error(f"Error al conectar con Supabase: {e}")
        return

    if not found_files:
        st.warning("No hay imágenes en el bucket.")
        return

    # 2. Generar URLs públicas
    images_urls = [
        supabase.storage.from_(bucket_name).get_public_url(f_name)
        for f_name in sorted(found_files)
    ]
    num_images = len(images_urls)
    
    # 3. Temps de l'animació
    time_per_image = 3.5  # Segons que la foto es queda fixa
    fade_time = 0.8       # Segons que triga la nova foto en aparèixer a sobre
    total_duration = max(num_images * time_per_image, 3.5)

    img_tags = ""
    css_delays = ""

    if num_images > 1:
        fade_pct = round((fade_time / total_duration) * 100, 2)
        hold_pct = round((time_per_image / total_duration) * 100, 2)
        visible_end_pct = round(hold_pct + fade_pct, 2)
        visible_end_pct_plus = round(visible_end_pct + 0.01, 2)

        for i, img_url in enumerate(images_urls):
            delay = round(i * time_per_image, 2)
            img_tags += f'<img src="{img_url}" class="carousel-img img-{i}" alt="Banner">'
            css_delays += f"""
            .carousel-img.img-{i} {{
                animation: seamlessCrossfade {total_duration}s infinite;
                animation-delay: {delay}s;
            }}
            """

        # Keyframe amb 3 nivells de capes (z-index) per evitar transparències al fons
        keyframes_css = f"""
        @keyframes seamlessCrossfade {{
            0% {{ opacity: 0; z-index: 3; }}
            {fade_pct}% {{ opacity: 1; z-index: 3; }}
            {visible_end_pct}% {{ opacity: 1; z-index: 2; }}
            {visible_end_pct_plus}% {{ opacity: 0; z-index: 1; }}
            100% {{ opacity: 0; z-index: 1; }}
        }}
        """
    else:
        img_tags = f'<img src="{images_urls[0]}" class="carousel-img single" alt="Banner">'
        css_delays = ".carousel-img.single { opacity: 1; z-index: 2; }"
        keyframes_css = ""

    # 4. Renderitzat final
    html_content = f"""
    <style>
    .presentation-banner {{
        display: flex;
        width: 100%;
        height: 280px;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
        margin-bottom: 0.5rem;
    }}
    .banner-side {{
        background-color: #FF6F1D;
        padding: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
    }}
    .banner-left {{ flex: 1.2; }}
    
    .banner-center {{ 
        flex: 3; 
        height: 100%; 
        position: relative;
        overflow: hidden;
        background-color: #FF6F1D;
    }}
    
    .carousel-img {{
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        opacity: 0;
        z-index: 1;
    }}

    {css_delays}
    {keyframes_css}

    .banner-right {{ flex: 1.2; }}
    .banner-text {{
        font-size: 22px;
        line-height: 1.3;
        color: #111111;
        font-family: system-ui, -apple-system, sans-serif;
        font-weight: 400;
    }}
    .banner-text strong {{ font-weight: 800; }}
    </style>

    <div class="presentation-banner">
        <div class="banner-side banner-left">
            <div class="banner-text">
                <strong>Intercanvia</strong> i aconsegueix articles de segona mà
            </div>
        </div>
        
        <div class="banner-center">
            {img_tags}
        </div>
        
        <div class="banner-side banner-right">
            <div class="banner-text">
                <strong>Explora</strong> i participa en una gran <strong>xarxa</strong> d'intercanvis!
            </div>
        </div>
    </div>
    """

    st.html(html_content)
