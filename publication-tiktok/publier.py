"""Publie la vidéo v4 sur tous les réseaux connectés d'un profil Upload-Post.

Prérequis : la variable d'environnement UPLOAD_POST_API_KEY (clé d'API Upload-Post).
Usage : python3 publier.py [nom_du_profil] [--test]
  --test : n'envoie rien, affiche seulement les profils, les réseaux et les champs qui seraient envoyés.
"""
import json, os, re, sys, urllib.request, mimetypes, uuid

API = "https://api.upload-post.com/api"
KEY = os.environ.get("UPLOAD_POST_API_KEY")
if not KEY:
    sys.exit("Clé absente : ajoutez UPLOAD_POST_API_KEY dans les secrets de l'environnement, puis relancez dans une nouvelle session.")
HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.join(HERE, "..", "video", "cest-possible-tiktok-v4.mp4")
LEGENDES = open(os.path.join(HERE, "legendes.md"), encoding="utf-8").read()
TEST = "--test" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]

def section(nom):
    m = re.search(r"^## " + re.escape(nom) + r"[^\n]*\n(.*?)(?=^## |\Z)", LEGENDES, re.S | re.M)
    return m.group(1).strip() if m else ""

def api(path, data=None, files=None):
    boundary = uuid.uuid4().hex
    if data is None:
        req = urllib.request.Request(API + path, headers={"Authorization": f"Apikey {KEY}"})
    else:
        body = b""
        for k, v in data:
            body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n").encode()
        for k, (fname, blob) in (files or {}).items():
            ctype = mimetypes.guess_type(fname)[0] or "application/octet-stream"
            body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{fname}\"\r\nContent-Type: {ctype}\r\n\r\n").encode() + blob + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        req = urllib.request.Request(API + path, data=body, method="POST",
            headers={"Authorization": f"Apikey {KEY}", "Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode())

# 1. profils et réseaux connectés
prof = api("/uploadposts/users")
profils = prof.get("profiles", prof if isinstance(prof, list) else [])
print("== Profils Upload-Post ==")
for p in profils:
    ok = [k for k, v in (p.get("social_accounts") or {}).items() if v]
    print("-", p.get("username"), "→", ", ".join(ok) or "aucun réseau connecté")
if not profils:
    sys.exit("Aucun profil trouvé sur ce compte Upload-Post.")
profil = args[0] if args else profils[0]["username"]
p = next((x for x in profils if x.get("username") == profil), None)
if not p:
    sys.exit(f"Profil « {profil} » introuvable.")
connectes = [k for k, v in (p.get("social_accounts") or {}).items() if v]
cibles = [k for k in connectes if k in ("tiktok", "instagram", "linkedin", "youtube", "facebook", "x", "threads", "bluesky")]
print(f"\n== Cibles pour « {profil} » : {', '.join(cibles) or 'aucune'} ==")
if not cibles:
    sys.exit("Aucun réseau publiable n'est connecté à ce profil.")

# 2. légendes par réseau
yt = section("YouTube").splitlines()
yt_title = yt[0].replace("Titre : ", "") if yt else ""
yt_desc = "\n".join(yt[1:]).replace("Description : ", "")
champs = [
    ("user", profil),
    ("title", "L'IA peut-elle lancer ta chaîne YouTube ? Claude Code a vérifié"),
    ("is_ai_generated", "true"),
    ("tiktok_title", section("TikTok")), ("privacy_level", "PUBLIC_TO_EVERYONE"),
    ("instagram_title", section("Instagram")), ("media_type", "REELS"),
    ("linkedin_title", "L'IA peut-elle lancer une chaîne YouTube rentable ? Vérification par Claude Code"),
    ("linkedin_description", section("LinkedIn")), ("visibility", "PUBLIC"),
    ("youtube_title", yt_title), ("youtube_description", yt_desc), ("privacyStatus", "public"), ("containsSyntheticMedia", "true"),
    ("x_title", section("X")), ("threads_title", section("Threads")),
    ("facebook_title", section("Facebook")), ("bluesky_title", section("Threads")),
] + [("platform[]", c) for c in cibles]

if TEST:
    print("\n== Mode test : rien n'est envoyé. Champs qui seraient envoyés ==")
    for k, v in champs:
        print(f"{k}: {v[:90]!r}{'…' if len(v) > 90 else ''}")
    sys.exit(0)

# 3. envoi
print("\n== Envoi de la vidéo… ==")
with open(VIDEO, "rb") as f:
    blob = f.read()
rep = api("/upload", champs, {"video": (os.path.basename(VIDEO), blob)})
json.dump(rep, open(os.path.join(HERE, "reponse-upload-post.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(rep, ensure_ascii=False, indent=1))
print("\nRéponse enregistrée dans publication/reponse-upload-post.json")
