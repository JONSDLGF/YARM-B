# decodehtml.py
import requests
from bs4 import BeautifulSoup, Tag, NavigableString
from PIL import Image, ImageTk
from io import BytesIO
import urllib.parse
import tkinter as tk
from utils import debug, limpiar_canvas

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/116.0.0.0 Safari/537.36"
}

imagenes = []  # Mantener referencias a imágenes

# -----------------------------
# Funciones principales
# -----------------------------
def cargar_url(url, container):
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        html = r.text
        mostrar_html_progresivo(html, base_url=url, container=container)
    except Exception as e:
        limpiar_canvas(container, imagenes)
        lbl = tk.Label(container, text=f"Error cargando URL:\n{e}", fg="red", justify="left", wraplength=750)
        lbl.pack(anchor="w", pady=5)

def html_to_dict(elem):
    if isinstance(elem, NavigableString):
        text = str(elem).strip()
        if not text:
            return None
        return {"tag": None, "attrs": {}, "children": [], "text": text}

    if isinstance(elem, Tag):
        children = [html_to_dict(c) for c in elem.children]
        children = [c for c in children if c is not None]
        return {
            "tag": elem.name,
            "attrs": dict(elem.attrs),
            "children": children,
            "text": elem.get_text()
        }
    return None

def mostrar_html_progresivo(html, base_url, container):
    limpiar_canvas(container, imagenes)
    soup = BeautifulSoup(html, "html.parser")
    document_node = {"tag": "document", "attrs": {}, "children": [], "text": ""}

    for child in soup.contents:
        child_dict = html_to_dict(child)
        if child_dict:
            document_node["children"].append(child_dict)

    procesar_elemento(document_node, container, base_url)

# -----------------------------
# Atributos antiguos
# -----------------------------
def aplicar_atributos_html_antiguos(elem, widget):
    attrs = elem.get("attrs", {})

    if "bgcolor" in attrs:
        widget.config(bg=attrs["bgcolor"])
    if "text" in attrs:
        widget.config(fg=attrs["text"])

    align = attrs.get("align", "").lower()
    if align in ["left", "center", "right"]:
        if isinstance(widget, tk.Label):
            widget.config(justify=align)
        elif isinstance(widget, tk.Frame):
            anchor = {"left": "w", "center": "center", "right": "e"}[align]
            widget.pack_configure(anchor=anchor)

# -----------------------------
# Renderizado de elementos (corregido)
# -----------------------------
def procesar_elemento(elem, parent, base_url):
    if elem["tag"] is None:
        if elem["text"].strip():
            lbl = tk.Label(parent, text=elem["text"], wraplength=750, justify="left")
            lbl.pack(anchor="w", pady=2)
        return

    tag = elem["tag"]

    # Contenedores genéricos
    if tag in ["document","div","header","section","main","body"]:
        frame = tk.Frame(parent)
        frame.pack(anchor="w", fill="x", pady=5)
        for child in elem["children"]:
            procesar_elemento(child, frame, base_url)
        aplicar_atributos_html_antiguos(elem, frame)
        return

    # Imágenes
    if tag == "img":
        src = urllib.parse.urljoin(base_url, elem["attrs"].get("src", ""))
        cargar_imagen(src, parent)
        return

    # Inputs de texto
    if tag == "input":
        input_type = elem["attrs"].get("type", "").lower()
        if input_type == "text":
            entry = tk.Entry(parent)
            entry.pack(anchor="w", pady=2)
        return

    # Botones y enlaces
    if tag in ["button", "a"]:
        btn = tk.Button(parent, text="", fg="blue" if tag=="a" else "black",
                        cursor="hand2" if tag=="a" else "arrow")
        btn.pack(anchor="w", pady=5)
        if tag == "a":
            url = elem["attrs"].get("href", "")
            if url:
                btn.config(command=lambda u=url: cargar_url(u, parent))
        for child in elem["children"]:
            if child["tag"] == "img":
                src = urllib.parse.urljoin(base_url, child["attrs"].get("src", ""))
                tk_img = cargar_imagen(src, btn, max_size=(200,200))
                if tk_img:
                    btn.config(image=tk_img, compound="left")
                    btn.image = tk_img
            else:
                procesar_elemento(child, btn, base_url)
        return

    # Tablas
    if tag == "table":
        frame = tk.Frame(parent, relief="groove", bd=1)
        frame.pack(anchor="w", pady=5)
        for child in elem["children"]:
            procesar_elemento(child, frame, base_url)
        return

    if tag == "tr":
        row_frame = tk.Frame(parent)
        row_frame.pack(anchor="w", fill="x")
        for child in elem["children"]:
            procesar_elemento(child, row_frame, base_url)
        return

    if tag == "td":
        cell_frame = tk.Frame(parent, relief="ridge", bd=1, padx=5, pady=5)
        cell_frame.pack(side="left", padx=2, pady=2)
        for child in elem["children"]:
            procesar_elemento(child, cell_frame, base_url)
        return

    # Encabezados h1-h6
    if tag in ["h1","h2","h3","h4","h5","h6"]:
        h_sizes = {
            "h1": 32,
            "h2": 28,
            "h3": 24,
            "h4": 20,
            "h5": 16,
            "h6": 14
        }
        size = h_sizes.get(tag, 16)
        frame = tk.Frame(parent)
        frame.pack(anchor="w", fill="x", pady=5)
        lbl = tk.Label(frame, text=elem["text"], font=("Arial", size, "bold"), wraplength=750, justify="left")
        lbl.pack(anchor="w")
        return

    # Otros tags desconocidos
    for child in elem["children"]:
        procesar_elemento(child, parent, base_url)

# -----------------------------
# Cargar imagen con debug
# -----------------------------
def cargar_imagen(src, parent, max_size=(750,400)):
    """Carga una imagen con debug y mantiene referencias."""
    try:
        debug(f"Intentando cargar imagen: {src}")
        r = requests.get(src, headers=headers)
        r.raise_for_status()
        debug(f"HTTP OK: {src} | Tamaño bytes: {len(r.content)}")

        pil_img = Image.open(BytesIO(r.content))
        debug(f"PIL abierto: {src} | Formato: {pil_img.format} | Tamaño: {pil_img.size}")

        pil_img.thumbnail(max_size)
        tk_img = ImageTk.PhotoImage(pil_img)

        # Label o Button como padre
        if isinstance(parent, tk.Button):
            parent.config(image=tk_img, compound="left")
            parent.image = tk_img
        else:
            lbl = tk.Label(parent, image=tk_img)
            lbl.image = tk_img
            lbl.pack(anchor="w", pady=5)

        imagenes.append(tk_img)
        debug(f"Imagen cargada en Tkinter: {src}")

        return tk_img  # retornar referencia para botones/enlaces

    except Exception as e:
        debug(f"Error cargando imagen: {src} | Exception: {e}")
        lbl = tk.Label(parent, text=f"[Imagen no se pudo cargar: {src}]", fg="red")
        lbl.pack(anchor="w", pady=5)
        return None
