# main.py
import tkinter as tk
from tkinter import ttk
from decodehtml import cargar_url
import threading

# ---- Ventana ----
root = tk.Tk()
root.geometry("800x600")
root.title("Mini HTML Viewer")

# barra de URL
barr = tk.Frame(root)
barr.pack(side="top", fill="x")

url_entry = tk.Entry(barr)
url_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
url_entry.insert(0, "https://jonsdlgf.github.io/")

# Canvas y frame scrollable
canvas = tk.Canvas(root)
scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
scrollbar.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)
canvas.configure(yscrollcommand=scrollbar.set)

container = tk.Frame(canvas)
canvas.create_window((0,0), window=container, anchor="nw")

def on_configure(event):
    canvas.configure(scrollregion=canvas.bbox("all"))

container.bind("<Configure>", on_configure)

def actualizar_url_entry(url):
    url_entry.delete(0, tk.END)
    url_entry.insert(0, url)

def cargar_url_hilo(url):
    threading.Thread(target=cargar_url, args=(url, container, actualizar_url_entry, root), daemon=True).start()

btn_go = tk.Button(barr, text="Go", command=lambda: cargar_url_hilo(url_entry.get()))
btn_go.pack(side="left", padx=5, pady=5)

# Cargar página inicial
cargar_url_hilo(url_entry.get())

root.mainloop()
