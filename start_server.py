import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os, ssl, http.server, socketserver

PORT    = 8443
CERT    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.pem")
WEBROOT = os.path.dirname(os.path.abspath(__file__))

# -- create cert if missing --
if not os.path.exists(CERT):
    print("[*] creating SSL cert...")
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    import datetime, ipaddress

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, u"neot-local")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject).issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName([
            x509.DNSName(u"localhost"),
            x509.IPAddress(ipaddress.IPv4Address("192.168.1.220")),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]), critical=False)
        .sign(key, hashes.SHA256(), default_backend())
    )
    with open(CERT, "wb") as f:
        f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print("[+] cert created: " + CERT)

# -- start server --
os.chdir(WEBROOT)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(CERT)

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    print("=" * 50)
    print("HTTPS server running!")
    print("Open on mobile:")
    print("https://192.168.1.220:" + str(PORT) + "/Neot_Kedumim_GIS_Mobile.html")
    print("=" * 50)
    httpd.serve_forever()
