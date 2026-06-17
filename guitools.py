# guitools.py
import pygame
import threading
from io import BytesIO
from PIL import Image as PILImage
import requests

pygame.font.init()
FONT_DEFAULT = pygame.font.SysFont(None, 24)
widgets = []

# =========================
# Clase base
# =========================
class Element:
    def __init__(self, x, y, width=0, height=0, bg=(255,255,255)):
        self.rect = pygame.Rect(x, y, width, height)
        self.bg = bg
        self.children = []

    def draw(self, surface, offset_y=0):
        rect_offset = self.rect.move(0, offset_y)
        if self.bg != (0,0,0,0):
            pygame.draw.rect(surface, self.bg, rect_offset)
        for c in self.children:
            c.draw(surface, offset_y)

    def add(self, element):
        self.children.append(element)

    def handle_event(self, event):
        for c in self.children:
            c.handle_event(event)

# =========================
# Frame
# =========================
class Frame(Element):
    def __init__(self, parent=None, x=0, y=0, width=800, height=600, bg=(255,255,255), fill=None, side=None, padx=0, pady=0):
        super().__init__(x, y, width, height, bg)
        if parent:
            parent.add(self)
        widgets.append(self)
        self.padx = padx
        self.pady = pady
        self.fill = fill
        self.side = side
        self.parent = parent
        self.current_y = pady

# =========================
# Texto
# =========================
class Text(Element):
    def __init__(self, parent, x=0, y=0, content="", font=FONT_DEFAULT, color=(0,0,0)):
        super().__init__(x, y)
        self.content = content
        self.font = font
        self.color = color
        if parent:
            parent.add(self)
        widgets.append(self)

    def draw(self, surface, offset_y=0):
        surf = self.font.render(self.content, True, self.color)
        surface.blit(surf, (self.rect.x, self.rect.y + offset_y))
        super().draw(surface, offset_y)

# =========================
# Button
# =========================
class Button(Element):
    def __init__(self, parent, x=0, y=0, width=100, height=30, content="Button", bg=(180,180,180), color=(0,0,0), command=None):
        super().__init__(x, y, width, height, bg)
        self.content = content
        self.command = command


    def draw(self, surface, offset_y=0):
        rect_offset = self.rect.move(0, offset_y)
        pygame.draw.rect(surface, self.bg, rect_offset)
        if isinstance(self.content, str):
            surf = self.font.render(self.content, True, self.color)
            surf_rect = surf.get_rect(center=rect_offset.center)
            surface.blit(surf, surf_rect)
        elif isinstance(self.content, pygame.Surface):
            img_rect = self.content.get_rect(center=rect_offset.center)
            surface.blit(self.content, img_rect)
        super().draw(surface, offset_y)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                if self.command:
                    self.command()
        super().handle_event(event)

# =========================
# Entry / Campo de texto
# =========================
class Entry(Element):
    def __init__(self, parent, x=0, y=0, width=300, height=25, text="", font=FONT_DEFAULT, color=(0,0,0), bg=(255,255,255)):
        super().__init__(x, y, width, height, bg)
        self.text = text
        self.font = font
        self.color = color
        self.active = False
        if parent:
            parent.add(self)
        widgets.append(self)

    def draw(self, surface, offset_y=0):
        rect_offset = self.rect.move(0, offset_y)
        pygame.draw.rect(surface, self.bg, rect_offset)
        pygame.draw.rect(surface, (0,0,0), rect_offset, 2 if self.active else 1)
        surf = self.font.render(self.text, True, self.color)
        surface.blit(surf, (rect_offset.x + 5, rect_offset.y + 5))
        super().draw(surface, offset_y)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if self.active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
        super().handle_event(event)

# =========================
# Imagen
# =========================
class Image(Element):
    def __init__(self, parent, x=0, y=0, src=None, max_size=(400,300)):
        super().__init__(x, y, 100, 100)
        self.image = None
        self.src = src
        self.max_size = max_size
        if parent:
            parent.add(self)
        widgets.append(self)
        if src:
            threading.Thread(target=self.load_image, daemon=True).start()

    def load_image(self):
        try:
            if isinstance(self.src, pygame.Surface):
                self.image = self.src
                self.rect.width, self.rect.height = self.image.get_size()
            elif self.src.startswith("http"):
                r = requests.get(self.src)
                r.raise_for_status()
                pil_img = PILImage.open(BytesIO(r.content))
                pil_img.thumbnail(self.max_size)
                mode = pil_img.mode
                size = pil_img.size
                data = pil_img.tobytes()
                self.image = pygame.image.fromstring(data, size, mode)
                self.rect.width, self.rect.height = self.image.get_size()
            else:
                pil_img = PILImage.open(self.src)
                pil_img.thumbnail(self.max_size)
                mode = pil_img.mode
                size = pil_img.size
                data = pil_img.tobytes()
                self.image = pygame.image.fromstring(data, size, mode)
                self.rect.width, self.rect.height = self.image.get_size()
        except Exception as e:
            print(f"Error cargando imagen: {e}")

    def draw(self, surface, offset_y=0):
        if self.image:
            surface.blit(self.image, (self.rect.x, self.rect.y + offset_y))
        super().draw(surface, offset_y)
