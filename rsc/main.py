# /main.py
# by JM
# date 06/10/2025

import pygame
import sys
import json
import os
import sqlite3

# -----------------------------
# Imports y setup
# -----------------------------

# ruta absoluta del directorio donde está este script
ROOT = os.path.dirname(os.path.abspath(__file__))

# construimos rutas seguras relativas al script principal
sys.path.extend([
    os.path.join(ROOT, "assets"),
    os.path.join(ROOT, "assets", "classes"),
    os.path.join(ROOT, "assets", "classes", "dec")
])

import assets.classes.guitools as guitools
import assets.classes.dec.html as dec_html

pygame.init()

# -----------------------------
# Configuración inicial
# -----------------------------
screen_width, screen_height = 900, 650
name, ver = "Tynic Browser", "v2.0.0 BU 6 by JM"
pygame.display.set_caption(f"{name} {ver}")
screen = pygame.display.set_mode((screen_width, screen_height))
clock = pygame.time.Clock()

history = []
FILE_HIST_DB = "hist.db"
history_index = -1  # posición actual en el historial
ROOT = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(ROOT, "assets", FILE_HIST_DB)
path = os.path.normpath(path)
HIST_DB = path

# -----------------------------
# Cargar conf y estilos
# -----------------------------

def load_conf(path="conf.json"):
    ROOT = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(ROOT, "assets", path)
    path = os.path.normpath(path)
    with open(path, "r") as f:
        conf = json.load(f)

    casual_url = conf.get("casual_url", "https://google.com")
    default_style_name = conf.get("default_style", "white")
    styles = conf.get("styles", {})
    style_conf = styles.get(default_style_name, {})

    defaults = {
        "barra_bg": (250,240,240), "barra_hover_bg": (220,220,220),
        "barra_border_color": (0,0,0), "barra_border_width": 0, "barra_border_radius": 0,
        "input_bg": (255,255,255), "input_hover_bg": (230,230,230), "input_color": (0,0,0),
        "input_border_color": (0,0,0), "input_border_width": 1, "input_border_radius": 5,
        "button_bg": (180,180,180), "button_hover_bg": (150,200,255), "button_color": (0,0,0),
        "button_border_color": (0,0,0), "button_border_width": 1, "button_border_radius": 5,
        "close_button_bg": (200,50,50), "close_button_hover_bg": (255,80,80), "close_button_color": (255,255,255),
        "close_button_border_color": (0,0,0), "close_button_border_width": 1, "close_button_border_radius": 5,
        "screen_bg": (245,245,245), "font_size": 24
    }

    active_style = {k: tuple(style_conf.get(k, v)) if isinstance(v, (tuple,list)) else style_conf.get(k, v)
                    for k,v in defaults.items()}

    ui_conf = {
        "input_width": conf.get("input_width", 500),
        "button_width": conf.get("button_width", 100),
        "barr_height": conf.get("barr_height", 50),
        "add_window_button": conf.get("add_window_button", "right")
    }

    save_history = conf.get("save_history", False)
    buttons_list = conf.get("button_list", [0, 1, 2])

    return casual_url, styles, active_style, ui_conf, save_history, buttons_list

casual_URL, styles, style, ui_conf, save_history, buttons_list = load_conf()

# -----------------------------
# Variables globales de UI
# -----------------------------
input_width = ui_conf["input_width"]
button_width = ui_conf["button_width"]
barr_height = ui_conf["barr_height"]
add_window_button = ui_conf["add_window_button"]
font_size = style["font_size"]

# -----------------------------
# UI Inicial
# -----------------------------
barr_task_height = 50
barr_task = guitools.Container(
    x=0, y=0, width=screen_width, height=barr_task_height,
    bg=style["barra_bg"], padx=5, pady=5, display="inline", gap=5
)

barr = guitools.Container(
    x=0, y=screen_height-barr_height, width=screen_width, height=barr_height,
    bg=style["barra_bg"], padx=5, pady=5, display="inline", gap=5
)

input_url = guitools.Input(
    parent=barr,
    width=input_width, height=40,
    bg=style["input_bg"], hover_bg=style["input_hover_bg"], color=style["input_color"],
    text=casual_URL,
    border_color=style["input_border_color"], border_width=style["input_border_width"], border_radius=style["input_border_radius"]
)

# -----------------------------
# Historial
# -----------------------------
def add_to_history(url):
    # Historial global
    conn = sqlite3.connect(HIST_DB)
    c = conn.cursor()
    c.execute("SELECT visits FROM history WHERE url=?", (url,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE history SET visits=visits+1, last_visit=CURRENT_TIMESTAMP WHERE url=?", (url,))
    else:
        c.execute("INSERT INTO history (url) VALUES (?)", (url,))
    conn.commit()
    conn.close()

    # Historial por pestaña
    current = windows[active_window]
    history = current["history"]
    history_index = current["history_index"]

    # eliminar "futuro" si index < len(history)-1
    if history_index < len(history) - 1:
        history = history[:history_index+1]

    # agregar nueva URL
    history.append(url)
    history_index = len(history) - 1

    # guardar de nuevo
    current["history"] = history
    current["history_index"] = history_index

    input_url.list_of_words = history[::-1]

def navigate_history(step: int):
    current = windows[active_window]
    history = current["history"]
    history_index = current["history_index"]

    if 0 <= history_index + step < len(history):
        history_index += step
        url = history[history_index]
        current["history_index"] = history_index
        input_url.text = url
        recargar(url, add_history=False)  # No agregamos al historial otra vez

def save_history_to_sql():
    """
    Guarda el historial en la base de datos SQLite,
    actualizando visitas si la URL ya existía.
    """
    if not save_history:
        return

    conn = sqlite3.connect(HIST_DB)
    c = conn.cursor()

    # Crear tabla si no existe
    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            visits INTEGER DEFAULT 1,
            last_visit DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    for url in history:
        # Intentar actualizar visitas si ya existe
        c.execute("SELECT visits FROM history WHERE url=?", (url,))
        row = c.fetchone()
        if row:
            c.execute("UPDATE history SET visits=visits+1, last_visit=CURRENT_TIMESTAMP WHERE url=?", (url,))
        else:
            c.execute("INSERT INTO history (url) VALUES (?)", (url,))

    conn.commit()
    conn.close()
    print("Historial guardado en SQL.")

def load_history_from_sql():
    """
    Carga el historial desde SQLite, evita duplicados y
    muestra las 10 URLs más visitadas al iniciar.
    """
    global history, history_index
    if not save_history:
        return

    conn = sqlite3.connect(HIST_DB)
    c = conn.cursor()
    
    # Crear tabla con contador de visitas
    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            visits INTEGER DEFAULT 1,
            last_visit DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Seleccionar las 10 URLs más visitadas
    c.execute("SELECT url FROM history ORDER BY visits DESC, last_visit DESC LIMIT 10")
    rows = c.fetchall()
    
    # Guardar en memoria para autocompletado y navegación
    history = [row[0] for row in rows]
    history_index = len(history) - 1 if history else -1
    input_url.list_of_words = history[::-1]
    
    conn.close()
    print("Historial cargado desde SQL (top 10 más visitados).")

# -----------------------------
# Funciones eventos y recarga
# -----------------------------
def recargar(url=None, add_history=True):
    current = windows[active_window]
    history = current["history"]
    index = current["history_index"]

    if url:
        if add_history:
            add_to_history(url)
        else:
            # solo actualizar la posición actual sin agregar al historial
            if index == -1:
                # si no hay historial aún
                current["history"].append(url)
                current["history_index"] = 0
            else:
                history[index] = url
        url = current["history"][current["history_index"]]
    elif index >= 0:
        url = history[index]
    else:
        url = ""  # por si no hay historial aún

    frame = current["screen"]
    frame.delete_all()
    print(f"Recargando {url}...")
    html = dec_html.getsrc(url)
    dec_html.dechtml(html, frame, current)
    create_tab_buttons()

def link_clicked(url):
    print(f"Link clicked: {url}")
    input_url.text = url
    add_to_history(url)
    recargar()

# ok
guitools.Link.link = link_clicked

# -----------------------------
# Gestión de pestañas
# -----------------------------
windows, active_window, tab_buttons = [], 0, []

def add_window(url: str):
    global active_window
    screen_elem = guitools.Container(
        x=0, y=barr_task_height,
        width=screen_width, height=screen_height-barr_height-barr_task_height,
        bg=style["screen_bg"], sidebar = True
    )
    windows.append({
        "screen": screen_elem,
        "history": [url],           # el historial empieza con la URL inicial
        "history_index": 0          # posición inicial
    })
    active_window = len(windows)-1
    create_tab_buttons()
    input_url.text = url
    input_url.list_of_words = [url]

def close_window(idx):
    global active_window
    if 0 <= idx < len(windows):
        windows[idx]["screen"].delete_me()
        del windows[idx]["screen"]
        windows.pop(idx)
        if active_window >= len(windows): active_window = len(windows)-1
        create_tab_buttons()

def switch_window(idx):
    global active_window
    if 0 <= idx < len(windows):
        active_window = idx
        # actualizar input_url según la ventana seleccionada
        hist = windows[idx]["history"]
        index = windows[idx]["history_index"]
        if 0 <= index < len(hist):
            input_url.text = hist[index]
        else:
            input_url.text = ""
        # actualizar autocompletado al historial de la pestaña
        input_url.list_of_words = hist[::-1] if "history" in windows[idx] else []

def create_tab_buttons():
    barr_task.delete_all()
    tab_buttons.clear()
    x_offset = barr_task.padx
    font = pygame.font.SysFont(None,font_size)

    if add_window_button=="left":
        btn_add = guitools.Button(parent=barr_task, x=0, y=0, width=30, height=25, content="+",
                                  bg=style["button_bg"], hover_bg=style["button_hover_bg"],
                                  color=style["button_color"], border_color=style["button_border_color"],
                                  border_width=style["button_border_width"], border_radius=style["button_border_radius"],
                                  command=lambda: add_window(casual_URL))
        btn_add.rect.topleft=(x_offset,barr_task.pady)
        x_offset += btn_add.rect.width + barr_task.gap
        tab_buttons.append(btn_add)

    for i, w in enumerate(windows):
        title = w.get("title","loading...")[:10] if i==active_window else w.get("title","loading...")[:15]
        text_width,_=font.size(title)
        size = text_width+10
        wind = guitools.Container(parent=barr_task,
            width=size+42,height=25,display="inline",gap=2,bg=style["barra_hover_bg"],
                                  border_color=style["button_border_color"], border_width=style["button_border_width"],
                                  border_radius=style["button_border_radius"])
        wind.rect.topleft=(x_offset,barr_task.pady)

        btn_title = guitools.Button(parent=wind, x=0, y=0, width=size, height=25, content=title,
                                    bg=style["button_bg"], hover_bg=style["button_hover_bg"], color=style["button_color"],
                                    border_color=style["button_border_color"], border_width=style["button_border_width"],
                                    border_radius=style["button_border_radius"], command=lambda idx=i: switch_window(idx))
        btn_close = guitools.Button(parent=wind, x=0, y=0, width=30, height=25, content="x",
                                    bg=style["close_button_bg"], hover_bg=style["close_button_hover_bg"],
                                    color=style["close_button_color"], border_color=style["close_button_border_color"],
                                    border_width=style["close_button_border_width"], border_radius=style["close_button_border_radius"],
                                    command=lambda idx=i: close_window(idx))

        tab_buttons.append(wind)
        x_offset += wind.rect.width + barr_task.gap

    if add_window_button=="right":
        btn_add = guitools.Button(parent=barr_task, x=0, y=0, width=30, height=25, content="+",
                                  bg=style["button_bg"], hover_bg=style["button_hover_bg"], color=style["button_color"],
                                  border_color=style["button_border_color"], border_width=style["button_border_width"],
                                  border_radius=style["button_border_radius"], command=lambda: add_window(casual_URL))
        btn_add.rect.topleft=(x_offset,barr_task.pady)
        tab_buttons.append(btn_add)

# -----------------------------
# Botones Go / Back / Next
# -----------------------------
button_back = guitools.Button(
    width=button_width, height=40, content="<",
    bg=style["button_bg"], hover_bg=style["button_hover_bg"], color=style["button_color"],
    border_color=style["button_border_color"], border_width=style["button_border_width"],
    border_radius=style["button_border_radius"],
    command=lambda: navigate_history(-1)
)

button_go = guitools.Button(
    width=button_width, height=40, content="Go",
    bg=style["button_bg"], hover_bg=style["button_hover_bg"], color=style["button_color"],
    border_color=style["button_border_color"], border_width=style["button_border_width"],
    border_radius=style["button_border_radius"],
    command=lambda: add_to_history(input_url.text) or recargar()
)

button_next = guitools.Button(
    width=button_width, height=40, content=">",
    bg=style["button_bg"], hover_bg=style["button_hover_bg"], color=style["button_color"],
    border_color=style["button_border_color"], border_width=style["button_border_width"],
    border_radius=style["button_border_radius"],
    command=lambda: navigate_history(1)
)

# -----------------------------
# Lista dinámica de botones
# -----------------------------
buttons_list2 = []
buttons_list1 = [button_back, button_go, button_next]

for i in buttons_list:
    buttons_list2.append(buttons_list1[i])

for widg in buttons_list2:
    barr.add(widg)

# -----------------------------
# recargar el historial
# -----------------------------
load_history_from_sql()

# -----------------------------
# Inicializar primera pestaña
# -----------------------------
add_window(casual_URL)
recargar()

# -----------------------------
# Estilos rápidos
# -----------------------------
style_shortcuts = {
    (pygame.K_d, pygame.KMOD_CTRL): "dark",
    (pygame.K_w, pygame.KMOD_CTRL): "white",
    (pygame.K_p, pygame.KMOD_CTRL): "pastel"
}

def set_style(style_name):
    global style
    # Actualizar el diccionario de estilos
    style.update({k: tuple(styles[style_name].get(k,v)) if isinstance(v,(tuple,list)) else styles[style_name].get(k,v)
                  for k,v in style.items()})
    
    # Actualizar Containers
    barr_task.bg = barr.bg = style["barra_bg"]
    barr_task.hover_bg = barr.hover_bg = style["barra_hover_bg"]

    # Actualizar Input
    input_url.bg = style["input_bg"]
    input_url.bg_hover = style["input_hover_bg"]
    input_url.color = style["input_color"]
    input_url.border_color = style["input_border_color"]
    input_url.border_width = style["input_border_width"]
    input_url.border_radius = style["input_border_radius"]

    # Actualizar botones
    for btn in [button_go, button_back, button_next]:
        btn.bg = style["button_bg"]
        btn.hover_bg = style["button_hover_bg"]
        btn.color = style["button_color"]
        btn.border_color = style["button_border_color"]
        btn.border_width = style["button_border_width"]
        btn.border_radius = style["button_border_radius"]
    for i in range(len(windows)):
        windows[i]["screen"].bg=style["screen_bg"]

    # Actualizar pestañas
    create_tab_buttons()

# -----------------------------
# Loop principal
# -----------------------------
id_barr_task = 0
id_windows   = 1
id_barr      = 2
root_widgets:list = [None, None, None]
root_widgets[id_barr_task ] = barr_task
root_widgets[id_windows   ] = windows[active_window]["screen"]
root_widgets[id_barr      ] = barr

loop = True
while loop:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_history_to_sql()
            loop = False
        elif event.type == pygame.KEYDOWN:
            for (key, mod), style_name in style_shortcuts.items():
                if event.key == key and (event.mod & mod):
                    set_style(style_name)
                    print(f"Cambiando a estilo: {style_name}")

        # Manejar eventos
        root_widgets[id_barr_task].handle_event(event)
        root_widgets[id_barr].handle_event(event)
        # no tocar si lo tocas se rompe el scroll asi que no mover de aqui
        # link no ok sige dando none
        if getattr(event, "pos", None) is not None:
            offset_y=windows[active_window]["screen"].sidebar_scroll
            x,y=event.pos
            event.pos=(x,y+offset_y)
        windows[active_window]["screen"].handle_event(event)

    root_widgets[id_windows] = windows[active_window]["screen"]

    # Dibujar
    screen.fill(style["screen_bg"])
    windows[active_window]["screen"].draw(screen)
    root_widgets[id_barr_task].draw(screen)
    root_widgets[id_barr].draw(screen)

    pygame.display.flip()
    clock.tick(60)
