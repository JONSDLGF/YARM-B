# /assets/dec/css.py
# by JM
# date 02/10/2025

def parser_css(css_text):
    css_dict = {}
    lines = css_text.split("}")
    for line in lines:
        if "{" not in line: continue
        selector, props = line.split("{",1)
        selector = selector.strip()
        props_dict = {}
        for p in props.split(";"):
            if ":" not in p: continue
            k,v = p.split(":",1)
            props_dict[k.strip()]=v.strip()
        css_dict[selector] = props_dict
    return css_dict
