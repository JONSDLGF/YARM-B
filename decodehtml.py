# descodehtml.py
import requests
from bs4 import BeautifulSoup, Tag, NavigableString
from io import BytesIO
from PIL import Image
import urllib.parse
import threading
from tools import Frame, ScrollFrame, Label, Button, Entry, ImageWidget, FONT_DEFAULT
from decodecss import aplicar_estilos, estilos_globales, parse_css
from utils import debug
import pygame

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/116.0.0.0 Safari/537.36"
}

widgets = []
SOLO_TEXTO = False
path_url: str = ""

# -----------------------------
# Funciones principales
# -----------------------------
def limpiar_widgets(container_list):
    container_list.clear()

def cargar_url(url, container_list, update_url_callback=None):
    global path_url
    path_url = url
    if update_url_callback:
        update_url_callback(url)
    limpiar_widgets(container_list)
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        mostrar_html_progresivo(r.text, base_url=url, container_list=container_list, update_url_callback=update_url_callback)
    except Exception as e:
        debug(f"Error cargando URL: {e}")

def html_to_dict(elem):
    if isinstance(elem, NavigableString):
        text = str(elem)
        if not text.strip(): return None
        return {"tag": None, "attrs": {}, "children": [], "text": text}
    if isinstance(elem, Tag):
        children = [html_to_dict(c) for c in elem.children if html_to_dict(c)]
        return {"tag": elem.name, "attrs": dict(elem.attrs), "children": children, "text": elem.get_text()}
    return None

def mostrar_html_progresivo(html, base_url, container_list, update_url_callback=None):
    soup = BeautifulSoup(html, "html.parser")

    # Extraer <style> y aplicar
    for style_tag in soup.find_all("style"):
        if style_tag.string:
            estilos_globales.update(parse_css(style_tag.string))

    document_node = {"tag":"document","attrs":{},"children":[],"text":""}
    for child in soup.contents:
        if isinstance(child, Tag) and child.name in ["style","title","script"]:
            continue
        child_dict = html_to_dict(child)
        if child_dict: document_node["children"].append(child_dict)

    # Crear scrollable container principal
    main_frame = ScrollFrame((0,50,800,550), bg=(255,255,255))
    procesar_elemento(document_node, main_frame, base_url, container_list, update_url_callback)
    container_list.append(main_frame)

# -----------------------------
# Procesar elementos HTML
# -----------------------------
def procesar_elemento(elem, parent, base_url, container_list, update_url_callback=None):
    tag = elem["tag"]

    # Texto plano
    if tag is None:
        text = elem["text"].replace("\xa0"," ")
        if text:
            lbl = Label((0,0,750,20), text=text, font=FONT_DEFAULT, fg=(0,0,0))
            parent.add(lbl)
        return

    # Contenedores
    if tag in ["document","div","header","section","main","body","p","span"]:
        frame = Frame((0,0,750,10), bg=(255,255,255))
        parent.add(frame)
        for child in elem["children"]:
            procesar_elemento(child, frame, base_url, container_list, update_url_callback)
        return

    if tag=="br":
        parent.add(Label((0,0,750,10), text=""))
        return
    if tag=="hr":
        parent.add(Label((0,0,750,2), text="", bg=(0,0,0)))
        return

    # Listas
    if tag in ["ul","ol"]:
        for i, child in enumerate([c for c in elem["children"] if c["tag"]=="li"], start=1):
            bullet = "•" if tag=="ul" else f"{i}."
            row_frame = Frame((0,0,750,20))
            parent.add(row_frame)
            row_frame.add(Label((0,0,20,20), text=bullet))
            text_frame = Frame((20,0,730,20))
            row_frame.add(text_frame)
            for subchild in child["children"]:
                procesar_elemento(subchild, text_frame, base_url, container_list, update_url_callback)
        return

    # Texto estilizado
    if tag in ["b","strong","i","em","u"]:
        lbl = Label((0,0,750,20), text=elem["text"], font=FONT_DEFAULT)
        parent.add(lbl)
        return

    # Imágenes
    if tag=="img" and not SOLO_TEXTO:
        src = resolver_url(base_url, elem.get("attrs",{}).get("src",""))
        threading.Thread(target=cargar_imagen, args=(src,parent), daemon=True).start()
        return

    # Inputs
    if tag=="input":
        input_type = elem.get("attrs",{}).get("type","").lower()
        if input_type=="text":
            entry = Entry((0,0,300,25))
            parent.add(entry)
        return

    # Links
    if tag=="a":
        url_link = resolver_url(base_url, elem.get("attrs",{}).get("href",""))
        btn = Button((0,0,100,25), text=elem.get("text","Link"), command=lambda u=url_link: cargar_url(u, container_list))
        parent.add(btn)
        return

    # Otros tags
    for child in elem["children"]:
        procesar_elemento(child, parent, base_url, container_list, update_url_callback)

# -----------------------------
# Cargar imagen con PIL
# -----------------------------
def cargar_imagen(src, parent, max_size=(750,400)):
    try:
        debug(f"Cargando imagen: {src}")
        r = requests.get(src, headers=headers, timeout=10)
        r.raise_for_status()
        pil_img = Image.open(BytesIO(r.content))
        pil_img.thumbnail(max_size)
        mode = pil_img.mode
        size = pil_img.size
        data = pil_img.tobytes()
        py_img = pygame.image.fromstring(data, size, mode)
        widget_img = ImageWidget((0,0,py_img.get_width(), py_img.get_height()), py_img)
        parent.add(widget_img)
    except Exception as e:
        debug(f"Error cargando imagen: {e}")

# -----------------------------
# Resolver URL relativa
# -----------------------------
def resolver_url(base_url, path):
    if not path: return base_url
    url = urllib.parse.urljoin(base_url, path)
    parsed = urllib.parse.urlparse(url)
    folder,file = parsed.path.rsplit('/',1) if '/' in parsed.path else ('', parsed.path)
    clean_path = urllib.parse.urljoin(folder+'/', file)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, clean_path, parsed.params, parsed.query, parsed.fragment))
