import pygame
import guitools

pygame.init()
screen = pygame.display.set_mode((800, 600))

URL="https://jonsdlgf.github.io/"

barr=guitools.Frame(fill="x", pady=5, padx=5, bg="white", side="top")
button=guitools.Button(barr, text="Recargar", command=lambda: reload(URL))
texto=guitools.Entry(barr, text=URL, width=70)
htmlgui=guitools.Frame(fill="all")

def reload(URL):
    guitools.reload(URL, htmlgui)



loop=True
while loop:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            loop = False
        for events in guitools.widgets:
            events.handle_event(event)

    screen.fill((255,255,255))

    for elements in guitools.widgets:
        elements.draw(screen)

    pygame.display.flip()