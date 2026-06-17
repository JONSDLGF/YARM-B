# main.py
import pygame
import threading
from tools import Button, Entry, Label
from decodehtml import cargar_url

pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Mini HTML Viewer")

clock = pygame.time.Clock()
running = True

# Barra de URL
url_entry = Entry((10,10,600,30), text="https://jonsdlgf.github.io/")
btn_go = Button((620,10,80,30), "Go", command=lambda: cargar_url_hilo(url_entry.text))

widgets = [url_entry, btn_go]

def actualizar_url_entry(url):
    url_entry.text = url

def cargar_url_hilo(url):
    threading.Thread(target=cargar_url, args=(url, widgets, actualizar_url_entry, screen), daemon=True).start()

# Cargar página inicial
cargar_url_hilo(url_entry.text)

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        for w in widgets:
            w.handle_event(event)

    screen.fill((255,255,255))
    for w in widgets:
        w.draw(screen)
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
