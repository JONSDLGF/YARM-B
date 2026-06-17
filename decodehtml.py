import requests
from bs4 import BeautifulSoup, Tag, NavigableString
from PIL import Image, ImageTk
from io import BytesIO
import urllib.parse
import tkinter as tk
from utils import debug

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/116.0.0.0 Safari/537.36"
}

imagenes = []  # Mantener referencias a imágenes
SOLO_TEXTO = False
path_url: str = ""


# -----------------------------
# Funciones principales
# -----------------------------
def limpiar_canvas(container, imagenes_list):
    """Limpia completamente el contenedor y referencias de imágenes."""
    for widget in container.winfo_children():
        widget.destroy()
    imagenes_list.clear()


def cargar_url(url, container):
    """Carga una URL y renderiza el HTML en el contenedor Tkinter."""
    global path_url
    path_url = url
    limpiar_canvas(container, imagenes)  # limpieza total
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        mostrar_html_progresivo(r.text, base_url=url, container=container)
    except Exception as e:
        tk.Label(container, text=f"Error cargando URL:\n{e}",
                 fg="red", justify="left", wraplength=750).pack(anchor="w", pady=5)


def html_to_dict(elem):
    """Convierte nodos BeautifulSoup en un diccionario navegable."""
    if isinstance(elem, NavigableString):
        text = str(elem)
        if not text.strip():
            return None
        return {"tag": None, "attrs": {}, "children": [], "text": text}

    if isinstance(elem, Tag):
        children = []
        for c in elem.children:
            child_dict = html_to_dict(c)  # <-- una sola llamada
            if child_dict:
                children.append(child_dict)
        return {"tag": elem.name, "attrs": dict(elem.attrs), "children": children, "text": elem.get_text()}

    return None


def mostrar_html_progresivo(html, base_url, container):
    """Parsea el HTML y envía al procesador de elementos."""
    limpiar_canvas(container, imagenes)
    soup = BeautifulSoup(html, "html.parser")
    document_node = {"tag": "document", "attrs": {}, "children": [], "text": ""}
    for child in soup.contents:
        child_dict = html_to_dict(child)
        if child_dict:
            document_node["children"].append(child_dict)
    procesar_elemento(document_node, container, base_url)


# -----------------------------
# Renderizado de elementos
# -----------------------------
def procesar_elemento(elem, parent, base_url):
    tag = elem["tag"]

    # Texto plano
    if tag is None:
        text = elem["text"].replace("\xa0", " ")
        if text:
            tk.Label(parent, text=text, font=("Courier New", 12),
                     wraplength=750, justify="left").pack(anchor="w", pady=2)
        return

    # Contenedores
    if tag in ["document", "div", "header", "section", "main", "body", "p", "span"]:
        frame = tk.Frame(parent)
        frame.pack(anchor="w", fill="x", pady=2)
        for child in elem["children"]:
            procesar_elemento(child, frame, base_url)
        return

    # Saltos de línea y reglas horizontales
    if tag == "br":
        tk.Label(parent, text="").pack()
        return
    if tag == "hr":
        tk.Frame(parent, height=2, bg="black", relief="sunken").pack(fill="x", pady=5)
        return

    # Listas <ul>/<ol>
    if tag in ["ul", "ol"]:
        for i, child in enumerate([c for c in elem["children"] if c["tag"] == "li"], start=1):
            row = tk.Frame(parent)
            row.pack(anchor="w", fill="x")
            bullet = "•" if tag == "ul" else f"{i}."
            tk.Label(row, text=bullet, font=("Arial", 12, "bold")).pack(side="left", padx=(10, 5))
            text_frame = tk.Frame(row)
            text_frame.pack(side="left", fill="x")
            for subchild in child["children"]:
                procesar_elemento(subchild, text_frame, base_url)
        return

    # Texto estilizado
    if tag in ["b", "strong", "i", "em", "u"]:
        styles = {"b": "bold", "strong": "bold", "i": "italic", "em": "italic", "u": "underline"}
        tk.Label(parent, text=elem["text"], font=("Arial", 12, styles[tag])).pack(anchor="w")
        return

    # Imágenes
    if tag == "img" and not SOLO_TEXTO:
        src = resolver_url(base_url, elem["attrs"].get("src", ""))
        cargar_imagen(src, parent)
        return

    # Inputs
    if tag == "input":
        input_type = elem["attrs"].get("type", "").lower()
        if input_type == "text":
            tk.Entry(parent).pack(anchor="w", pady=2)
        return

    # Links y botones
    if tag == "a":
        url = resolver_url(base_url, elem["attrs"].get("href", ""))
        btn = tk.Button(parent, text="", fg="blue", cursor="hand2",
                        relief="flat", underline=True,
                        command=(lambda u=url: cargar_url(u, parent)) if url else None)
        btn.pack(anchor="w", pady=5)
        for child in elem["children"]:
            if child["tag"] == "img" and not SOLO_TEXTO:
                src = resolver_url(base_url, child["attrs"].get("src", ""))
                tk_img = cargar_imagen(src, btn, max_size=(200, 200))
                if tk_img:
                    btn.config(image=tk_img, compound="left")
                    btn.image = tk_img
            else:
                procesar_elemento(child, btn, base_url)
        return

    if tag == "button":
        tk.Button(parent, text=elem["text"] or "Botón", relief="raised").pack(anchor="w", pady=5)
        return

    # Tablas
    if tag == "table":
        table = tk.Frame(parent, relief="groove", bd=1)
        table.pack(anchor="w", pady=5)
        for child in elem["children"]:
            procesar_elemento(child, table, base_url)
        return
    if tag == "tr":
        row = tk.Frame(parent)
        row.pack(anchor="w", fill="x")
        for child in elem["children"]:
            procesar_elemento(child, row, base_url)
        return
    if tag == "td":
        cell = tk.Frame(parent, relief="ridge", bd=1, padx=5, pady=5)
        cell.pack(side="left", padx=2, pady=2)
        for child in elem["children"]:
            procesar_elemento(child, cell, base_url)
        return

    # Encabezados
    if tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        sizes = {"h1": 32, "h2": 28, "h3": 24, "h4": 20, "h5": 16, "h6": 14}
        size = sizes.get(tag, 16)
        tk.Label(parent, text=elem["text"], font=("Arial", size, "bold"),
                 wraplength=750, justify="left").pack(anchor="w", pady=5)
        return

    # Iframes
    if tag == "iframe":
        src = resolver_url(base_url, elem["attrs"].get("src", ""))
        if src:
            sub_frame = tk.Frame(parent, relief="sunken", bd=1)
            sub_frame.pack(anchor="w", fill="x", pady=5)
            cargar_url(src, sub_frame)
        return

    # Formularios
    if tag == "form":
        action = resolver_url(base_url, elem["attrs"].get("action", ""))
        method = elem["attrs"].get("method", "get").lower()
        form_frame = tk.Frame(parent, relief="groove", bd=2, padx=5, pady=5)
        form_frame.pack(anchor="w", fill="x", pady=5)
        form_inputs = {}

        for child in elem["children"]:
            if child["tag"] == "input":
                input_type = child["attrs"].get("type", "text").lower()
                name = child["attrs"].get("name", "")
                if input_type == "text":
                    entry = tk.Entry(form_frame)
                    entry.pack(anchor="w", pady=2)
                    form_inputs[name] = entry
                elif input_type == "submit":
                    tk.Button(form_frame, text=child["attrs"].get("value", "Enviar"),
                              command=lambda a=action, m=method, i=form_inputs: enviar_form(a, m, i, base_url, parent)
                              ).pack(anchor="w", pady=5)
        return

    # Otros tags → procesar hijos
    for child in elem["children"]:
        procesar_elemento(child, parent, base_url)


# -----------------------------
# Utilidades
# -----------------------------
def cargar_imagen(src, parent, max_size=(750, 400)):
    """Carga una imagen y mantiene referencias."""
    try:
        debug(f"Intentando cargar imagen: {src}")
        r = requests.get(src, headers=headers)
        r.raise_for_status()
        pil_img = Image.open(BytesIO(r.content))
        pil_img.thumbnail(max_size)
        tk_img = ImageTk.PhotoImage(pil_img)

        if isinstance(parent, tk.Button):
            parent.config(image=tk_img, compound="left")
            parent.image = tk_img
        else:
            lbl = tk.Label(parent, image=tk_img)
            lbl.image = tk_img
            lbl.pack(anchor="w", pady=5)

        imagenes.append(tk_img)
        debug(f"Imagen cargada en Tkinter: {src}")
        return tk_img

    except Exception as e:
        debug(f"Error cargando imagen: {src} | Exception: {e}")
        tk.Label(parent, text=f"[Imagen no se pudo cargar: {src}]", fg="red").pack(anchor="w", pady=5)
        return None


def enviar_form(action, method, inputs, base_url, container):
    """Envía formularios GET/POST y renderiza respuesta."""
    data = {name: widget.get() for name, widget in inputs.items()}
    url = resolver_url(base_url, action)
    try:
        if method == "post":
            r = requests.post(url, data=data, headers=headers)
        else:
            r = requests.get(url, params=data, headers=headers)
        r.raise_for_status()
        mostrar_html_progresivo(r.text, base_url=url, container=container)
    except Exception as e:
        tk.Label(container, text=f"Error enviando formulario:\n{e}", fg="red").pack(anchor="w", pady=5)


def resolver_url(base_url, path):
    """Une base_url + path asegurando carpeta/archivo correcto."""
    if not path:
        return base_url
    url = urllib.parse.urljoin(base_url, path)
    parsed = urllib.parse.urlparse(url)
    folder, file = parsed.path.rsplit('/', 1) if '/' in parsed.path else ('', parsed.path)
    clean_path = urllib.parse.urljoin(folder + '/', file)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, clean_path,
                                    parsed.params, parsed.query, parsed.fragment))
