# libpip
import urllib.parse

# libpy
import os
import socket
import requests

DNS_PUBLIC = [
    "8.8.8.8", # DNS Google
    "1.1.1.1"  # DNS Cloudflare
]

DNS_FALLBACK = {}
ROOT = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(ROOT, "../", "dns_fallback.txt")
path = os.path.normpath(path)
with open(path, "r") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        host, ips = parts[0], parts[1:]
        if len(ips) == 1:
            DNS_FALLBACK[host] = ips[0]
        else:
            DNS_FALLBACK[host] = ips

def dns_manual(hostname):
    def check_http(ip, port=80):
        try:
            with socket.create_connection((ip, port), timeout=2) as sock:
                request = f"HEAD / HTTP/1.1\r\nHost: {hostname}\r\n\r\n"
                sock.sendall(request.encode())
                data = sock.recv(1024)
                return b"HTTP" in data
        except Exception:
            return False

    # 1️⃣ Intentar con el diccionario de fallback
    if hostname in DNS_FALLBACK:
        ips = DNS_FALLBACK[hostname]
        ip:str
        for ip in (ips if isinstance(ips, list) else [ips]):
            if check_http(ip):
                return ip
        print(f"Ninguna IP de fallback para {hostname} respondió correctamente.")

    # 2️⃣ Intentar resolver con el DNS del sistema
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        pass

    # 3️⃣ Intentar con servidores DNS públicos
    for dns_server in DNS_PUBLIC:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(2)

                # Construir query DNS básica
                query_id = b'\x12\x34'
                flags = b'\x01\x00'
                qdcount = b'\x00\x01'
                ancount = b'\x00\x00'
                nscount = b'\x00\x00'
                arcount = b'\x00\x00'
                header = query_id + flags + qdcount + ancount + nscount + arcount

                qname = b''.join(bytes([len(part)]) + part.encode() for part in hostname.split('.')) + b'\x00'
                qtype_qclass = b'\x00\x01\x00\x01'  # Type A, Class IN
                query = header + qname + qtype_qclass

                sock.sendto(query, (dns_server, 53))
                data, _ = sock.recvfrom(512)

                if len(data) < 12:
                    continue

                # Saltar header y pregunta
                offset = 12
                while data[offset] != 0:
                    offset += data[offset] + 1
                offset += 5  # 1 byte null + 2 bytes QTYPE + 2 bytes QCLASS

                # Leer respuestas
                ancount_int = int.from_bytes(data[6:8], 'big')
                for _ in range(ancount_int):
                    if offset + 12 > len(data):
                        break
                    if data[offset] & 0xC0 == 0xC0:  # puntero
                        offset += 2
                    else:
                        while data[offset] != 0:
                            offset += data[offset] + 1
                        offset += 1

                    rtype = int.from_bytes(data[offset:offset+2], 'big')
                    rclass = int.from_bytes(data[offset+2:offset+4], 'big')
                    rdlength = int.from_bytes(data[offset+8:offset+10], 'big')
                    rdata_offset = offset + 10

                    if rtype == 1 and rclass == 1 and rdlength == 4:  # IPv4
                        ip_bytes = data[rdata_offset:rdata_offset+4]
                        return '.'.join(str(b) for b in ip_bytes)

                    offset = rdata_offset + rdlength

        except Exception as e:
            print(f"Error resolviendo {hostname} con {dns_server}: {e}")

    # 4️⃣ Si todo falla
    print(f"No se pudo resolver {hostname}")
    return "default"

def resolver_url(base_url, path):
    if not path:
        return base_url

    url = urllib.parse.urljoin(base_url, path)
    parsed = urllib.parse.urlparse(url)

    # Resolver hostname con dns_manual()
    hostname = parsed.hostname
    if hostname:
        ip = dns_manual(hostname)
    else:
        ip = None

    # Reconstruir con IP si fue resuelto
    folder, file = parsed.path.rsplit('/', 1) if '/' in parsed.path else ('', parsed.path)
    clean_path = urllib.parse.urljoin(folder+'/', file)

    return urllib.parse.urlunparse((
        parsed.scheme,
        f"{ip or parsed.netloc}",  # usar IP si disponible
        clean_path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))


CACHE_FOLDER = "./cache"

def getresources(url: str):
    os.makedirs(CACHE_FOLDER, exist_ok=True)
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        filename = os.path.join(CACHE_FOLDER, os.path.basename(url.split("?")[0]))
        with open(filename, "wb") as f:
            f.write(r.content)
        return filename
    except Exception as e:
        print(f"[getresources] Error descargando {url}: {e}")
        return None
