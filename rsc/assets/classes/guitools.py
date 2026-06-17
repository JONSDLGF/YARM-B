# /assets/classes/guitools.py
# by JM
# date 07/10/2025

import pygame
import threading
import requests
from urllib.parse import urljoin
from io import BytesIO

pygame.font.init()
FONT_DEFAULT = pygame.font.SysFont(None, 24)
widgets = []

def resolve_src(base_url: str, src: str) -> str:
    """
    Convierte una ruta de recurso (src, href, etc.) en absoluta
    usando la URL base de la página.
    """
    if not src:
        return ""
    return urljoin(base_url, src)

# =========================
# Clase base
# =========================
class Element:
    def __init__(self, x=0, y=0, width=100, height=30, bg=(255,255,255)):
        self.rect = pygame.Rect(x, y, width, height)
        self.bg = bg
        self.children = []

    def draw(self, surface, offset_y=0):
        rect_offset = self.rect.move(0, offset_y)
        if self.bg != (0,0,0,0):
            pygame.draw.rect(surface, self.bg, rect_offset)

        # Dibujar hijos
        for child in self.children:
            child.draw(surface, offset_y)

    def handle_event(self, event):
        for c in self.children:
            c.handle_event(event)

    def add(self, element):
        self.children.append(element)

    def get_dimensions(self):
        return self.rect.width, self.rect.height, self.rect.topleft

    # -----------------------
    # Eliminación recursiva
    # -----------------------
    def delete_all(self):
        # Eliminar recursivamente hijos
        for child in self.children:
            if hasattr(child, "delete_all"):
                child.delete_all()
            if hasattr(child, "delete_me"):
                child.delete_me()

        # Limpiar lista de hijos
        self.children.clear()

        # Resetear posiciones internas
        if hasattr(self, "current_x"):
            self.current_x = getattr(self, "padx", 0)
        if hasattr(self, "current_y"):
            self.current_y = getattr(self, "pady", 0)
        if hasattr(self, "_max_row_height"):
            self._max_row_height = 0

    def delete_me(self):
        # Primero eliminar todos los hijos recursivamente
        self.delete_all()
        
        # Quitar esta instancia de la lista global
        if 'widgets' in globals() and self in widgets:
            widgets.remove(self)
        
        # Quitar referencias al padre si existe
        if hasattr(self, 'parent') and self.parent:
            if self in self.parent.children:
                self.parent.children.remove(self)
            if hasattr(self.parent, 'sidebar_children') and self in self.parent.sidebar_children:
                self.parent.sidebar_children.remove(self)
        
        # Finalmente eliminar cualquier atributo que pueda mantener referencia
        self.children = []
        if hasattr(self, 'sidebar_children'):
            self.sidebar_children = []
        self.parent = None

# =========================
# Container (Frame flexible)
# =========================
class Container(Element):
    def __init__(self, parent=None, x=0, y=0, width=800, height=500, bg=(255,255,255),
                 padx=5, pady=5, display="block", gap=5, wrap=False, hover_bg=None,
                 border_color=(0,0,0), border_width=0, border_radius=0,
                 sidebar=False, sidebar_bg=(220,220,220)):
        super().__init__(x, y, width, height, bg)
        self.padx = padx
        self.pady = pady
        self.display = display
        self.gap = gap
        self.wrap = wrap
        self.current_x = self.padx
        self.current_y = self.pady
        self._max_row_height = 0
        self.hover_bg = hover_bg
        self.border_color = border_color
        self.border_width = border_width
        self.border_radius = border_radius

        # Barra lateral con scroll
        self.sidebar = sidebar
        self.sidebar_bg = sidebar_bg
        self.sidebar_scroll = 0  # desplazamiento vertical
        self.sidebar_scroll_speed = 20  # píxeles por rueda

        if parent:
            parent.add(self)
        else:
            widgets.append(self)

    def draw(self, surface, offset_y=0):
        rect_offset = self.rect.move(0, offset_y)

        # Dibujar fondo principal
        draw_color = self.bg
        if self.hover_bg and rect_offset.collidepoint(pygame.mouse.get_pos()):
            draw_color = self.hover_bg
        if draw_color != (0,0,0,0):
            pygame.draw.rect(surface, draw_color, rect_offset, border_radius=self.border_radius)
        # Borde
        if self.border_width > 0:
            pygame.draw.rect(surface, self.border_color, rect_offset, width=self.border_width, border_radius=self.border_radius)

        # Dibujar barra lateral con scroll
        if self.sidebar:
            # Dibujar hijos con desplazamiento
            y_offset = -self.sidebar_scroll + self.pady
            total_height = sum(c.rect.height + self.gap for c in self.children)
            visible_height = self.rect.height

            for element in self.children:
                element.draw(surface, offset_y=y_offset)
                y_offset += element.rect.height + self.gap

            # Dibujar barra de scroll
            #scrollbar_height = (self.rect.y-8) + (visible_height/total_height)
            #scrollbar_y = self.rect.y + self.sidebar_scroll
            scrollbar_height = (self.rect.y-8) + (
                self.rect.height + sum(c.rect.height + self.pady for c in self.children)
            )
            scrollbar_y = self.rect.y + self.sidebar_scroll
            #print(scrollbar_height,scrollbar_y)
            scrollbar_rect = pygame.Rect(
                0,  # 10px ancho de scrollbar desde el borde derecho
                scrollbar_y,
                8,  # ancho del scrollbar
                scrollbar_height
            )
            pygame.draw.rect(surface, (150,150,150), scrollbar_rect, border_radius=4)


        if not self.sidebar:
            # Dibujar hijos normales
            for element in self.children:
                element.draw(surface, offset_y)

    def add(self, element):
        if element is None:
            return
        w, h, _ = element.get_dimensions()
        if self.display=="inline":
            if self.wrap and self.current_x + w > self.rect.width - self.padx:
                self.current_x = self.padx
                self.current_y += self._max_row_height + self.gap
                self._max_row_height = 0
            element.rect.topleft = (self.rect.x + self.current_x, self.rect.y + self.current_y)
            self.current_x += w + self.gap
            self._max_row_height = max(self._max_row_height, h)
        else:
            element.rect.topleft = (self.rect.x + self.padx, self.rect.y + self.current_y)
            self.current_y += h + self.gap
        self.children.append(element)

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            self.sidebar_scroll -= event.y * self.sidebar_scroll_speed
            #max_scroll = max(0, sum(c.rect.height + self.gap for c in self.children))
            self.sidebar_scroll = max(0,self.sidebar_scroll)
            # el self.sidebar_scroll no se referencia en self.draw
            # osea que no le llega y se pone en 0
        for widget in self.children:
            widget.handle_event(event)

    def delete_all(self):
        # Llamar a delete_me() de cada hijo si existe
        for child in self.children:
            child.delete_me()

        # Limpiar listas de hijos
        self.children.clear()

        # Resetear posiciones internas
        self.current_x = self.padx
        self.current_y = self.pady
        self._max_row_height = 0

    def delete_me(self):
        self.delete_all()
        if self in widgets:
            widgets.remove(self)

# =========================
# Input de texto
# =========================
class Input(Element):
    def __init__(self, parent=None, x=0, y=0, width=300, height=25, text="", font=FONT_DEFAULT,
                 color=(0,0,0), bg=(255,255,255), hover_bg=None,
                 border_color=(0,0,0), border_width=1, border_radius=0,
                 list_of_words=[], list_of_words_bg=(255,255,255), list_of_words_border_color=(0,0,0),
                 list_of_words_border_width=1, list_of_words_border_radius=0,
                 list_of_words_font=FONT_DEFAULT, list_of_words_color=(0,0,0),
                 list_position="up", backspace_repeat_delay=400, backspace_repeat_interval=50):
        super().__init__(x, y, width, height, bg)
        self.text = text
        self.font = font
        self.color = color
        self.active = False
        self.cursor_visible = True
        self.cursor_counter = 0
        self.cursor_pos = len(text)
        self.bg_hover = hover_bg
        self.border_color = border_color
        self.border_width = border_width
        self.border_radius = border_radius

        # Lista de autocompletado
        self.list_of_words = list_of_words
        self.list_of_words_bg = list_of_words_bg
        self.list_of_words_border_color = list_of_words_border_color
        self.list_of_words_border_width = list_of_words_border_width
        self.list_of_words_border_radius = list_of_words_border_radius
        self.list_of_words_font = list_of_words_font
        self.list_of_words_color = list_of_words_color
        self.show_list = False
        self.list_position = list_position

        # Variables para backspace repetido
        self.backspace_pressed = False
        self.backspace_timer = 0
        self.backspace_repeat_delay = backspace_repeat_delay
        self.backspace_repeat_interval = backspace_repeat_interval

        if parent:
            parent.add(self)
        else:
            widgets.append(self)

    def draw(self, surface, offset_y=0):
        # Dibuja el input y cursor
        rect_offset = self.rect.move(0, offset_y)
        draw_color = self.bg
        if self.bg_hover and rect_offset.collidepoint(pygame.mouse.get_pos()):
            draw_color = self.bg_hover
        pygame.draw.rect(surface, draw_color, rect_offset, border_radius=self.border_radius)
        pygame.draw.rect(surface, self.border_color, rect_offset, width=self.border_width, border_radius=self.border_radius)

        # Texto del input
        surf = self.font.render(self.text, True, self.color)
        surface.blit(surf, (rect_offset.x + 5, rect_offset.y + (rect_offset.height - surf.get_height()) // 2))

        # Cursor
        if self.active:
            self.cursor_counter += 1
            if self.cursor_counter % 60 < 30:
                cursor_x = rect_offset.x + 5 + self.font.size(self.text[:self.cursor_pos])[0]
                pygame.draw.line(surface, self.color, (cursor_x, rect_offset.y+5),
                                 (cursor_x, rect_offset.y + rect_offset.height-5), 2)

        # Lista de sugerencias
        if self.show_list and self.list_of_words:
            for i, word in enumerate(self.list_of_words):
                if self.list_position == "down":
                    y_pos = rect_offset.y + rect_offset.height + i*rect_offset.height
                else:
                    y_pos = rect_offset.y - (i+1)*rect_offset.height
                item_rect = pygame.Rect(rect_offset.x, y_pos, rect_offset.width, rect_offset.height)
                pygame.draw.rect(surface, self.list_of_words_bg, item_rect, border_radius=self.list_of_words_border_radius)
                pygame.draw.rect(surface, self.list_of_words_border_color, item_rect, width=self.list_of_words_border_width,
                                 border_radius=self.list_of_words_border_radius)
                word_surf = self.list_of_words_font.render(word, True, self.list_of_words_color)
                surface.blit(word_surf, (item_rect.x + 5, item_rect.y + (item_rect.height - word_surf.get_height()) // 2))

    def handle_event(self, event):
        # Manejo de clicks
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Detectar click en la lista
            if self.show_list:
                for i, word in enumerate(self.list_of_words):
                    if self.list_position == "down":
                        y_pos = self.rect.y + self.rect.height + i*self.rect.height
                    else:
                        y_pos = self.rect.y - (i+1)*self.rect.height
                    item_rect = pygame.Rect(self.rect.x, y_pos, self.rect.width, self.rect.height)
                    if item_rect.collidepoint(event.pos):
                        self.text = word
                        self.cursor_pos = len(word)
                        self.show_list = False
            if self.rect.collidepoint(event.pos):
                self.active = True
                self.show_list = True
            else:
                self.active = False
                self.show_list = False

        # Teclado
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_TAB:
                # Autocompletado con el primero de la lista
                if self.list_of_words:
                    self.text = self.list_of_words[0]
                    self.cursor_pos = len(self.text)
                    self.show_list = False
            elif event.key == pygame.K_LEFT:
                self.cursor_pos = max(0, self.cursor_pos - 1)
            elif event.key == pygame.K_BACKSPACE:
                self.backspace_pressed = True
                self.backspace_timer = pygame.time.get_ticks()
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_CTRL:
                    # Ctrl + Backspace: borra todo
                    self.text = ""
                    self.cursor_pos = 0
                elif self.cursor_pos > 0:
                    self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
                    self.cursor_pos -= 1
            elif event.key == pygame.K_DELETE:
                if self.cursor_pos < len(self.text):
                    self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos+1:]
            else:
                # parece que esto tambies es para ir a rigth y agregar un elemento nuevo XD
                # osea que hace un doble funcion
                if event.unicode.isprintable():
                    self.text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                    self.cursor_pos = min(self.cursor_pos + 1, len(self.text))

        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_BACKSPACE:
                self.backspace_pressed = False

    def update(self):
        # Manejo de backspace prolongado
        if self.backspace_pressed and self.cursor_pos > 0:
            now = pygame.time.get_ticks()
            if now - self.backspace_timer > self.backspace_repeat_delay:
                self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
                self.cursor_pos -= 1
                self.backspace_timer = now - (self.backspace_repeat_delay - self.backspace_repeat_interval)

# =========================
# Button
# =========================
class Button(Element):
    def __init__(self, parent=None, x=0, y=0, width=100, height=30, content="Button",
                 font=FONT_DEFAULT, color=(0,0,0), bg=(180,180,180), hover_bg=None,
                 border_color=(0,0,0), border_width=0, border_radius=0, command=None):
        super().__init__(x, y, width, height, bg)
        self.content = content
        self.font = font
        self.color = color
        self.hover_bg = hover_bg
        self.border_color = border_color
        self.border_width = border_width
        self.border_radius = border_radius
        self.command = command
        if parent:
            parent.add(self)
        widgets.append(self)

    def draw(self, surface, offset_y=0):
        rect_offset = self.rect.move(0, offset_y)
        draw_color = self.bg
        if self.hover_bg and rect_offset.collidepoint(pygame.mouse.get_pos()):
            draw_color = self.hover_bg
        if draw_color != (0,0,0,0):
            pygame.draw.rect(surface, draw_color, rect_offset, border_radius=self.border_radius)
        if self.border_width > 0:
            pygame.draw.rect(surface, self.border_color, rect_offset, width=self.border_width, border_radius=self.border_radius)
        surf = self.font.render(self.content, True, self.color)
        surf_rect = surf.get_rect(center=rect_offset.center)
        surface.blit(surf, surf_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            # Ejecutar callback Python
            if self.command:
                self.command()

# =========================
# Text
# =========================
class Text(Element):
    FONT_SIZES = {1: 36, 2: 30, 3: 24, 4: 20, 5: 16, 6: 12}

    def __init__(self, parent=None, x=0, y=0, width=400, height=40, font_size=32, content="", color=(0,0,0), bg=(255,255,255), style=None):
        super().__init__(x, y, width, height, bg)
        self.content = content
        self.color = color
        self.style = style
        self.font = pygame.font.SysFont(None, font_size)
        if parent:
            parent.add(self)
        else:
            widgets.append(self)

    def draw(self, surface, offset_y=0):
        rect_offset = self.rect.move(0, offset_y)
        if self.bg != (0,0,0,0):
            pygame.draw.rect(surface, self.bg, rect_offset)
        surf = self.font.render(self.content, True, self.color)
        surface.blit(surf, (rect_offset.x + 5, rect_offset.y + (rect_offset.height - surf.get_height()) // 2))

# =========================
# Image con carga en hilo
# =========================
class Image(Element):
    def __init__(self, parent, src="", width=100, height=100):
        super().__init__(0, 0, width, height)
        self.parent = parent
        self.src = src
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.loaded = False
        if src:
            # Solo descargar en hilo
            threading.Thread(target=self._load_image_thread, daemon=True).start()

    def _load_image_thread(self):
        try:
            if self.src.startswith(("http://","https://")):
                r = requests.get(self.src, timeout=5)
                r.raise_for_status()
                img_data = BytesIO(r.content)
                surface = pygame.image.load(img_data).convert_alpha()
            else:
                surface = pygame.image.load(self.src).convert_alpha()
            # Escalado si necesario
            surface = pygame.transform.scale(surface, (self.rect.width, self.rect.height))
            # Asignar la surface en el hilo principal usando una bandera
            self.loaded_surface = surface
            self.loaded = True
        except Exception as e:
            print(f"Error cargando imagen {self.src}: {e}")

    def draw(self, target_surface, offset_y=0):
        if self.loaded:
            self.surface.blit(self.loaded_surface, (0, 0))
        # Dibujar la surface de este elemento sobre el surface de la ventana
        print((self.rect.x, self.rect.y + offset_y))
        target_surface.blit(self.surface, (self.rect.x, self.rect.y + offset_y))

# =========================
# Link
# =========================
class Link(Text):
    link = None

    def __init__(self, parent=None, x=0, y=0, width=200, height=30, text="", url="", color=(0,0,255)):
        super().__init__(parent, x, y, width, height, content=text, color=color)
        self.url = url
        self.link = type(self).link  # referencia de clase para callback
        self.children = []           # hijos internos

    def add(self, widget):
        """Agrega un widget hijo al link"""
        self.children.append(widget)

    def handle_event(self, event):
        # Si hay hijos, propagar evento recursivamente
        for child in self.children:
            if hasattr(child, "handle_event"):
                child.handle_event(event)

        # Comportamiento de click del link
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                if self.url and self.link:
                    self.link(self.url)

    def draw(self, surface, offset_y=0):
        # Si tiene hijos, comportarse como container recursivo
        if self.children:
            for child in self.children:
                if hasattr(child, "draw"):
                    child.draw(surface, offset_y + self.rect.y)
        else:
            # Solo texto
            super().draw(surface, offset_y)

# =========================
# Separator (línea horizontal)
# =========================
class Separator(Element):
    def __init__(self, parent=None, x=0, y=0, width=400, height=2, color=(0,0,0)):
        super().__init__(x, y, width, height, bg=color)
        if parent:
            parent.add(self)
        else:
            widgets.append(self)

    def draw(self, surface, offset_y=0):
        rect_offset = self.rect.move(0, offset_y)
        pygame.draw.rect(surface, self.bg, rect_offset)
