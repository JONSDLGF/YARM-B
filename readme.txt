Tynic Browser v2.0.0 BU 8 JM - 07/10/2025

engine:  webpy
name:    Tynic Browser
version: 2.0.0
backup:  8
header: {
    "User-Agent": "TynicBrowser/2.0 (engine=webpy)"
}

descripcion:
    es un navegador web hecho por JM.
    salio de la idea de hacer algo nuebo casero y gratis,
    ademas que no consuma demasiado ;p.

layout:
    barra task
    html
    barra input < GO >

tester:
    os         V / X
    windows 10   V
    linux        /
    macos        /

excepciones:
    tec                 V / X
    DNS manual            V
    config gui            V
    config buttons pos    V
    in links              V
    historial             V
    historial de pestañas V
    scroll                V
    html                  /
    css                   /
    multi task            /
    images                /
    js                    X
    php                   X
    webVBS                X
    webVMjava             X
    webflash              X
    webpy                 X
    webasm                X
    webgl                 X
    webbrfuk              X
    3D                    X

limitaciones:
    no hay soporte de cookies
    css csai limitado
    no hay soporte multimedia (<video>, <audio>)
    ademas que no es multi jstask

memoria:
    windows 10:
        iniciado/normal: 43.9 MB
        4 pestañas de google: 50.5 MB
        despues de cerrarlos: 48.9 MB

files:
    /main.py:
        es este el archibo que inicia los elementos y la primera url
        y inicia el layout como barra de url y button "Go" ademas
        de que el tiene el bucle principal de loop y ebentos

    /classes/guitools.py:
        es el que proporciona los elementos que no estan en pygame como:
            buttons, input_text y mas ademas de que ofrece el frame que guarda los hijos para
            despues separarlos si estan en el mismo (x,y) y ademas de que los separarlos
            para que no se superpusieran
        ademas de proporcionar la funcion raload_screen que recarga todo el web screen y
        elimina la lista que tenia de elementos
        elemento padre es:
            class Element:...
        y los sub elementos son:
            class Container(Element):...
            class Input(Element):...
            class Button(Element):...
            class Text(Element):...
            class Image(Element):...
            class Separator(Element):...
        otros:
            class Link(Text):...

    /classes/dec/*:
        este folder esta especificado para
        descodificar y ejecutar* codigo como:
            los unicos que no son codigo: html, css
            lenguajes de programacion: python, php, js...

    /classes/dec/html.py:
        def dechtml(html: str, frame, tab_dict=None):...
            solo despedaza el html para llebarlo a procesar_elemento
        def procesar_elemento(elem, parent):
            este es el encargado de poner los elementos en la pantalla

    
    /classes/dec/css.py:
        descodifioca el style de el elemento apyaciente
        o que si es un <style>...</style> lo agrega a una lista
        algo como {"@body": [["bgcolor","#000"]], "@body.hola": [["color","#FFF"]]}
        y lo ba repasando en el html passer

roots:
    root                        stado
    /main.py                    ok
    /assets/hist.sql            ok
    /assets/dns_fallback.txt    ok
    /assets/dec/html.py         ok
    /assets/dec/css.py          ok
    /assets/classes/dnstools.py ok
    /assets/classes/guitools.py ok

ident:
    en la cabecera de el archibo tendra
    # root + name file
    # by names
    # date
    <space>
    <imports>
    <code>

reports:
    JM - 04/10/2025 2 note:
      el scroll no funciona
    JM - 04/10/2025 1 note:
      se necesita ver si el container esta vien porque
      no hace offset a sus hijos

credits:
        code
         JM
     beta tester
         JM
     gui designer
         JM