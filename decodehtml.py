# descodehtml.py
import requests
from bs4 import BeautifulSoup, Tag, NavigableString
from PIL import Image, ImageTk
from io import BytesIO
import urllib.parse
import tkinter as tk
from decodecss import aplicar_estilos, estilos_globales, parse_css
from utils import debug
import threading

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/116.0.0.0 Safari/537.36"
}

imagenes = []
SOLO_TEXTO = False
path_url: str = ""

# -----------------------------
# Funciones principales
# -----------------------------
def limpiar_canvas(container, imagenes_list):
    for widget in container.winfo_children():
        widget.destroy()
    imagenes_list.clear()

def cargar_url(url, container, update_url_callback=None, root=None):
    global path_url
    path_url = url
    if update_url_callback:
        update_url_callback(url)
    limpiar_canvas(container, imagenes)

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        mostrar_html_progresivo(r.text, base_url=url, container=container, update_url_callback=update_url_callback, root=root)
    except Exception as e:
        tk.Label(container, text=f"Error cargando URL:\n{e}", fg="red", justify="left", wraplength=750).pack(anchor="w", pady=5)

def html_to_dict(elem):
    if isinstance(elem, NavigableString):
        text = str(elem)
        if not text.strip(): return None
        return {"tag": None, "attrs": {}, "children": [], "text": text}
    if isinstance(elem, Tag):
        children = [html_to_dict(c) for c in elem.children if html_to_dict(c)]
        return {"tag": elem.name, "attrs": dict(elem.attrs), "children": children, "text": elem.get_text()}
    return None

def mostrar_html_progresivo(html, base_url, container, update_url_callback=None, root=None):
    limpiar_canvas(container, imagenes)
    soup = BeautifulSoup(html, "html.parser")

    # Extraer <style> y aplicar
    for style_tag in soup.find_all("style"):
        if style_tag.string:
            estilos_globales.update(parse_css(style_tag.string))

    # Actualizar título
    title_tag = soup.find("title")
    if title_tag and root:
        root.title(f"Mini HTML Viewer - {title_tag.get_text()}")

    document_node = {"tag":"document","attrs":{},"children":[],"text":""}
    for child in soup.contents:
        if isinstance(child, Tag) and child.name in ["style","title","script"]:
            continue
        child_dict = html_to_dict(child)
        if child_dict: document_node["children"].append(child_dict)

    procesar_elemento(document_node, container, base_url, container, update_url_callback, root)

# -----------------------------
# Renderizado de elementos
# -----------------------------
def procesar_elemento(elem, parent, base_url, container, update_url_callback=None, root=None):
    tag = elem["tag"]

    # Texto plano
    if tag is None:
        text = elem["text"].replace("\xa0"," ")
        if text:
            lbl = tk.Label(parent, text=text, font=("Arial",12), wraplength=750, justify="left")
            lbl.pack(anchor="w", pady=2)
            id_ = elem.get("attrs",{}).get("id")
            class_ = elem.get("attrs",{}).get("class")
            if isinstance(class_, list): class_ = " ".join(class_)
            aplicar_estilos(lbl, tag=None, id_=id_, class_=class_, estilos=estilos_globales)
            inline_style = elem.get("attrs",{}).get("style")
            if inline_style:
                aplicar_estilos(lbl, estilos=parse_css(inline_style))
        return

    # Contenedores y recursión
    if tag in ["document","div","header","section","main","body","p","span"]:
        frame = tk.Frame(parent)
        frame.pack(anchor="w", fill="x", pady=2)
        id_ = elem.get("attrs",{}).get("id")
        class_ = elem.get("attrs",{}).get("class")
        if isinstance(class_, list): class_ = " ".join(class_)
        aplicar_estilos(frame, tag=tag, id_=id_, class_=class_, estilos=estilos_globales)
        inline_style = elem.get("attrs",{}).get("style")
        if inline_style: aplicar_estilos(frame, estilos=parse_css(inline_style))
        for child in elem["children"]:
            procesar_elemento(child, frame, base_url, container, update_url_callback, root)
        return

    if tag=="br":
        tk.Label(parent,text="").pack()
        return
    if tag=="hr":
        hr = tk.Frame(parent,height=2,bg="black",relief="sunken")
        hr.pack(fill="x", pady=5)
        aplicar_estilos(hr, tag="hr", estilos=estilos_globales)
        return

    # Listas
    if tag in ["ul","ol"]:
        for i, child in enumerate([c for c in elem["children"] if c["tag"]=="li"], start=1):
            row = tk.Frame(parent)
            row.pack(anchor="w", fill="x")
            bullet = "•" if tag=="ul" else f"{i}."
            tk.Label(row,text=bullet,font=("Arial",12,"bold")).pack(side="left",padx=(10,5))
            text_frame = tk.Frame(row)
            text_frame.pack(side="left", fill="x")
            for subchild in child["children"]:
                procesar_elemento(subchild,text_frame,base_url,container,update_url_callback,root)
        return

    # Texto estilizado
    if tag in ["b","strong","i","em","u"]:
        lbl = tk.Label(parent, text=elem["text"], font=("Arial",12,{"b":"bold","strong":"bold","i":"italic","em":"italic","u":"underline"}[tag]))
        lbl.pack(anchor="w")
        id_ = elem.get("attrs",{}).get("id")
        class_ = elem.get("attrs",{}).get("class")
        if isinstance(class_, list): class_ = " ".join(class_)
        aplicar_estilos(lbl, tag=tag, id_=id_, class_=class_, estilos=estilos_globales)
        inline_style = elem.get("attrs",{}).get("style")
        if inline_style: aplicar_estilos(lbl, estilos=parse_css(inline_style))
        return

    # Imágenes en hilo
    if tag=="img" and not SOLO_TEXTO:
        src = resolver_url(base_url, elem.get("attrs",{}).get("src",""))
        threading.Thread(target=cargar_imagen, args=(src,parent,elem), daemon=True).start()
        return

    # Inputs
    if tag=="input":
        input_type = elem.get("attrs",{}).get("type","").lower()
        if input_type=="text":
            entry = tk.Entry(parent)
            entry.pack(anchor="w", pady=2)
            id_ = elem.get("attrs",{}).get("id")
            class_ = elem.get("attrs",{}).get("class")
            if isinstance(class_, list): class_ = " ".join(class_)
            aplicar_estilos(entry, tag=tag, id_=id_, class_=class_, estilos=estilos_globales)
        return

    # Links
    if tag=="a":
        url_link = resolver_url(base_url, elem.get("attrs",{}).get("href",""))
        btn = tk.Button(parent, text="", fg="blue", cursor="hand2", relief="flat", underline=True,
                        command=(lambda u=url_link: cargar_url(u,container,update_url_callback,root)) if url_link else None)
        btn.pack(anchor="w", pady=5)
        for child in elem["children"]:
            if child["tag"]=="img" and not SOLO_TEXTO:
                src = resolver_url(base_url, child.get("attrs",{}).get("src",""))
                threading.Thread(target=cargar_imagen, args=(src,btn,child), daemon=True).start()
            else:
                procesar_elemento(child,btn,base_url,container,update_url_callback,root)
        return

    # Ignorar <style> y <script>
    if tag in ["style","script"]:
        return

    # Otros tags
    for child in elem["children"]:
        procesar_elemento(child,parent,base_url,container,update_url_callback,root)

# -----------------------------
# Cargar imagen con estilos
# -----------------------------
def cargar_imagen(src,parent,elem=None,max_size=(750,400)):
    try:
        debug(f"Cargando imagen: {src}")
        r = requests.get(src, headers=headers, timeout=10)
        r.raise_for_status()
        pil_img = Image.open(BytesIO(r.content))
        width = height = None

        if elem:
            props = {}
            tag = elem.get("tag")
            id_ = elem.get("attrs",{}).get("id")
            class_ = elem.get("attrs",{}).get("class")
            if isinstance(class_, list): class_ = " ".join(class_)
            props.update(estilos_globales.get(tag,{}))
            if id_: props.update(estilos_globales.get(f"#{id_}",{}))
            if class_:
                for c in class_.split():
                    props.update(estilos_globales.get(f".{c}",{}))
            inline_style = elem.get("attrs",{}).get("style")
            if inline_style: props.update(parse_css(inline_style).get(tag,{}))

            if "width" in props: width=int(props["width"].replace("px",""))
            if "height" in props: height=int(props["height"].replace("px",""))

        if width and height: pil_img = pil_img.resize((width,height))
        else: pil_img.thumbnail(max_size)

        tk_img = ImageTk.PhotoImage(pil_img)
        if isinstance(parent,tk.Button):
            parent.config(image=tk_img,compound="left")
            parent.image=tk_img
        else:
            lbl = tk.Label(parent,image=tk_img)
            lbl.image=tk_img
            lbl.pack(anchor="w", pady=5)

        imagenes.append(tk_img)
        return tk_img
    except Exception as e:
        debug(f"Error cargando imagen: {e}")
        tk.Label(parent,text=f"[Imagen no se pudo cargar: {src}]",fg="red").pack(anchor="w", pady=5)
        return None

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
