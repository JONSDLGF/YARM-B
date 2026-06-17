# utils.py

import config

def debug(msg):
    if config.DEBUG_MODE:
        print(msg)

def limpiar_canvas(container, imagenes):
    for widget in container.winfo_children():
        widget.destroy()
    imagenes.clear()
