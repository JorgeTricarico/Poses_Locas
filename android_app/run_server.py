import http.server
import ssl
import subprocess
import os

PORT = 8080

if not os.path.exists("cert.pem") or not os.path.exists("key.pem"):
    print("Generating self-signed certificate...")
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:4096",
        "-keyout", "key.pem", "-out", "cert.pem", "-days", "365",
        "-nodes", "-subj", "/CN=localhost"
    ])

print(f"Starting HTTPS server on https://0.0.0.0:{PORT}")
print("Para jugar, abre en tu celular la URL https://<TU-IP-DE-TAILSCALE>:8080")
print("Acepta la advertencia de seguridad (Avanzado -> Continuar) y dale permisos de cámara.")

server_address = ('0.0.0.0', PORT)
httpd = http.server.HTTPServer(server_address, http.server.SimpleHTTPRequestHandler)

context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

httpd.serve_forever()
