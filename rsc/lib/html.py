# /assets/classes/dec/html.py
# by JM
# date 07/10/2025

import requests
import threading
import dnstools
import pygame
from bs4 import BeautifulSoup, NavigableString, Tag
from io import BytesIO
from urllib.parse import parse_qs, urljoin, urlparse, urlunparse
import assets.classes.guitools as guitools
from css import parser_css

# -----------------------------
# Configuración global
# -----------------------------
SOLO_TEXTO    = False
css_tags      = {}
base_url      = ""
base_host     = ""
base_query    = ""
base_fragment = ""
head          = {
    "User-Agent": "TynicBrowser/2.0 (engine=webpy)"
}
current_windows = None

# -----------------------------
# Funciones auxiliares CSS
# -----------------------------
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    lv = len(hex_color)
    if lv == 6:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    elif lv == 3:
        return tuple(int(hex_color[i]*2, 16) for i in range(3))
    return (0,0,0)

# -----------------------------
# Funciones de parseo HTML
# -----------------------------
def html_to_dict(elem):
    if isinstance(elem, NavigableString):
        text = str(elem)
        if not text.strip():
            return None
        return {
            "tag": None,
            "attrs": {},
            "children": [],
            "text": text
        }

    if isinstance(elem, Tag):
        children = []
        for c in elem.children:
            child = html_to_dict(c)
            if child:
                children.append(child)
        return {
            "tag": elem.name,
            "attrs": dict(elem.attrs),
            "children": children,
            "text": elem.get_text(strip=True)
        }
    return None

# -----------------------------
# Renderizado recursivo con referencia al contenedor padre y soporte de porcentajes
# -----------------------------
def procesar_elemento(elem, parent):
    global base_url, base_host, base_query, base_fragment
    tag = elem["tag"]

    if tag == "title":
        return

    # Texto plano
    if tag is None:
        text = elem.get("text","").replace("\xa0"," ").strip()
        if text:
            lines = text.split("\n")  # dividir por saltos de línea
            for line in lines:
                if line:  # solo líneas con contenido
                    widget = guitools.Text(parent, content=line)
        return

    # Encabezados
    if tag in ["h1","h2","h3","h4","h5","h6"]:
        size = 32 - (int(tag[1])-1)*4
        widget = guitools.Text(parent, content=elem.get("text",""), font_size=size, style="bold")
        return

    # Contenedores
    if tag in ["document","div","header","section","main","body","p","span"]:
        print(elem["attrs"])
        bg=hex_to_rgb(elem["attrs"].get("bgcolor","#FFF"))

        # Crear container con padding inicial
        frame = guitools.Container(parent,bg=bg)

        # Renderizar hijos usando el frame correcto
        for child in elem.get("children", []):
            procesar_elemento(child, frame)

        return

    # Saltos de línea y separadores
    if tag == "br":
        guitools.Text(parent, content="")
        return

    if tag == "hr":
        guitools.Separator(parent)
        return

    # Listas
    if tag in ["ul","ol"]:
        row = guitools.Container(parent, gap=5, padx=20)
        for li in elem.get("children",[]):
            if li["tag"]=="li":
                guitools.Text(row, content=li.get("text",""))
        return

    # Texto estilizado
    if tag in ["b","strong","i","em","u"]:
        style_map = {"b":"bold","strong":"bold","i":"italic","em":"italic","u":"underline"}
        widget = guitools.Text(parent, content=elem.get("text",""), style=style_map[tag])
        return

    # Imágenes
    if tag == "img" and not SOLO_TEXTO:
        src = elem.get("attrs", {}).get("src")
        if src:
            if ".com" in base_host:
                cache_base_host=base_url+"://"+"www."+base_host+"/"
            else:
                cache_base_host=base_url+"://"+base_host+"/"
            full_src = urljoin(cache_base_host, src)  # Normalizar a absoluta
            img_elem = guitools.Image(parent, src=full_src)
            if "width" in elem["attrs"]: img_elem.rect.width = int(elem["attrs"]["width"])
            if "height" in elem["attrs"]: img_elem.rect.height = int(elem["attrs"]["height"])
        return

    # Inputs
    if tag == "input":
        input_type = elem.get("attrs",{}).get("type","").lower()
        if input_type == "text":
            widget = guitools.Input(parent)
        return

    if tag == "textarea":
        widget = guitools.Input(parent)
        return

    # Botones
    if tag == "button":
        text = elem.get("text","Button")
        widget = guitools.Button(parent, content=text, command=None)
        return

    # Enlaces
    if tag == "a":
        href = elem.get("attrs", {}).get("href")
        children = elem.get("children", [])  # elementos anidados dentro del <a>
        link_text = elem.get("text", "")

        if href:
            if isinstance(getattr(children,"tag",None),str):  # hay más HTML dentro
                # Crear un container dentro del parent para agrupar los elementos del <a>
                container = guitools.Container(parent)
                # Puedes marcar el container con la URL si quieres que actúe como link
                container.url = href

                # Renderizar todos los elementos hijos dentro del container
                for child in children:
                    procesar_elemento(child, container)  # render_element es tu función recursiva

            else:  # solo texto
                widget = guitools.Link(parent, text=link_text, url=href)

        return

    # Tablas
    if tag == "table":
        table_container = guitools.Container(parent)
        for tr in [c for c in elem.get("children",[]) if c["tag"]=="tr"]:
            row = guitools.Container(table_container, display="inline")
            for td in [c for c in tr.get("children",[]) if c["tag"]=="td"]:
                procesar_elemento(td, row)
        return

    # Citas y código
    if tag == "blockquote":
        widget = guitools.Text(parent, content=elem.get("text",""), style="italic")
        return
    if tag == "code":
        widget = guitools.Text(parent, content=elem.get("text",""), font_name="monospace")
        return

    # Ignorar scripts y estilos
    if tag in ["script","style"]:
        return

    # style
    if tag == "style":
        print(elem)
        css_tags.update(
            parser_css()
        )

    # Otros tags: procesar recursivamente
    for child in elem.get("children",[]):
        procesar_elemento(child, parent)

# -----------------------------
# Función principal de renderizado
# -----------------------------
def dechtml(html: str, frame, current=None):
    global current_windows
    current_windows=current
    soup = BeautifulSoup(html, "html.parser")

    # Convertir HTML a dict
    document_node = {"tag":"document","attrs":{},"children":[],"text":""}
    for child in soup.contents:
        child_dict = html_to_dict(child)
        if child_dict:
            document_node["children"].append(child_dict)

    # Renderizar recursivamente
    procesar_elemento(document_node, frame)


# -----------------------------
# Funciones de red y recarga
# -----------------------------
def getsrc(url: str) -> str:
    global base_url, base_host, base_query, base_fragment, head

    # Aseguramos esquema
    if '://' not in url:
        url = 'http://' + url

    # Parseamos URL
    parsed   = urlparse(url)
    scheme   = parsed.scheme
    netloc   = parsed.netloc
    path     = parsed.path
    query    = parsed.query
    fragment = parsed.fragment

    # Limpiar host (sin userinfo ni puerto)
    if '@' in netloc:
        netloc = netloc.split('@', 1)[1]
    base_host = netloc.split(':', 1)[0]

    # Guardar query y fragment en globales
    base_query    = parse_qs(query)    # dict con listas
    base_fragment = fragment           # normalmente #ancla
    base_url = scheme

    # -----------------------------
    # Lectura de archivos locales
    # -----------------------------
    if scheme == "file":
        path = url[7:]
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error al leer archivo {path}: {e}")
            return ""

    # -----------------------------
    # HTTP / HTTPS
    # -----------------------------
    if scheme in ("http", "https"):
        hostname = netloc
        ip = None
        headers = head.copy()

        # DNS manual para http
        if scheme == "http":
            ip = dnstools.dns_manual(hostname)
            if ip:
                # Reemplazar hostname por IP en la URL, pero mantener Host header
                url_ip = urlunparse((scheme, ip, path, '', '', ''))
                headers["Host"] = hostname
                print(f"DNS manual: {hostname} -> {ip}")
            else:
                url_ip = urlunparse((scheme, hostname, path, '', '', ''))
        else:
            url_ip = urlunparse((scheme, hostname, path, '', '', ''))

        try:
            # Usamos requests con params (la query en dict)
            r = requests.get(
                url_ip,
                headers=headers,
                timeout=10,
                params=base_query,
                verify=True
            )
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            print(f"Error al obtener {url}: {e}")
            return f"<html><body><h1>Error HTTP</h1><p>{e}</p></body></html>"

    # -----------------------------
    # Otros esquemas
    # -----------------------------
    print(f"URL no soportada: {url}")
    return f"<html><body><h1>Error</h1><p>URL no soportada: {url}</p></body></html>"

def reload(url: str, frame):
    frame.children.clear()
    frame.current_x = frame.padx
    frame.current_y = frame.pady
    html = getsrc(url)
    dechtml(html, frame)
