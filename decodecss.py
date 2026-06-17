# decodecss.py
import re
import tkinter as tk

estilos_globales = {}

def parse_css(css_text):
    """
    Convierte CSS simple en diccionario:
    { 'body': {'background-color':'#000', 'color':'#fff'} }
    """
    css_rules = {}
    pattern = re.compile(r'([^\{\}]+)\{([^\{\}]+)\}')
    for selector, body in pattern.findall(css_text):
        selector = selector.strip()
        props = {}
        for prop in body.split(';'):
            if ':' in prop:
                k, v = prop.split(':',1)
                props[k.strip()] = v.strip()
        css_rules[selector] = props
    return css_rules

def aplicar_estilos(widget, tag=None, id_=None, class_=None, estilos=None):
    if not estilos:
        return
    # Por tag
    if tag and tag in estilos:
        _aplicar_props(widget, estilos[tag])
    # Por id
    if id_ and f"#{id_}" in estilos:
        _aplicar_props(widget, estilos[f"#{id_}"])
    # Por class
    if class_:
        for c in class_.split():
            key = f".{c}"
            if key in estilos:
                _aplicar_props(widget, estilos[key])

def _aplicar_props(widget, props):
    # Colores
    if "background-color" in props:
        try: widget.config(bg=props["background-color"])
        except: pass
    if "color" in props:
        try: widget.config(fg=props["color"])
        except: pass
    # Fuente
    if "font-size" in props or "font-family" in props:
        try:
            current = widget.cget("font") if "font" in widget.keys() else ("Arial", 12)
            family = props.get("font-family", current[0])
            size = int(props.get("font-size", str(current[1])).replace("px",""))
            widget.config(font=(family, size))
        except: pass
    # Tamaño de widget
    if "width" in props:
        try: widget.config(width=int(props["width"].replace("px","")))
        except: pass
    if "height" in props:
        try: widget.config(height=int(props["height"].replace("px","")))
        except: pass
    # Padding
    if "padding" in props:
        try:
            p = int(props["padding"].replace("px",""))
            widget.pack_configure(padx=p, pady=p)
        except: pass
    # Margin (simula con padding del contenedor)
    if "margin" in props:
        try:
            m = int(props["margin"].replace("px",""))
            widget.pack_configure(padx=m, pady=m)
        except: pass
    # Text-align
    if "text-align" in props and hasattr(widget, "config"):
        align = props["text-align"]
        justify_map = {"left":"left", "center":"center", "right":"right"}
        if isinstance(widget, tk.Label):
            widget.config(justify=justify_map.get(align,"left"))
