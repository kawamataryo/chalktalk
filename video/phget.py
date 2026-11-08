"""Poly Haven（CC0）の素材を取る。導入の 3D（blender/scene2.py）が使う。
使い方: python3 phget.py ph/dl model:desk_lamp_arm_01:1k model:wall_clock:1k model:wooden_display_shelves_01:1k \
  model:decorative_book_set_01:1k model:stationery_supplies:1k model:office_notepads:1k model:potted_plant_04:1k \
  model:potted_plant_02:1k model:SchoolChair_01:1k tex:laminate_floor_02:2k tex:painted_plaster_wall:2k \
  tex:white_oak_veneer:2k tex:rough_linen:1k tex:jogging_melange:1k tex:denim_fabric:1k tex:walnut_veneer:1k
"""
import json, sys, urllib.request, os
UA = {"User-Agent": "chalktalk-video/1.0"}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120).read()
def save(u, p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if not os.path.exists(p): open(p, "wb").write(get(u))
root = sys.argv[1]
for spec in sys.argv[2:]:
    kind, aid, res = spec.split(":")
    f = json.loads(get(f"https://api.polyhaven.com/files/{aid}"))
    if kind == "model":
        fm = "gltf" if "gltf" in f else "fbx"
        g = f[fm][res][fm]; d = f"{root}/{aid}"
        save(g["url"], f"{d}/{aid}.{fm}")
        for rel, v in g.get("include", {}).items(): save(v["url"], f"{d}/{rel}")
    elif kind == "tex":
        d = f"{root}/tex/{aid}"
        for m in ("Diffuse", "nor_gl", "Rough", "AO", "arm"):
            if m in f and res in f[m]:
                fmt = "jpg" if "jpg" in f[m][res] else "png"; save(f[m][res][fmt]["url"], f"{d}/{m}.{fmt}")
    elif kind == "hdri":
        save(f["hdri"][res]["hdr"]["url"], f"{root}/hdri/{aid}_{res}.hdr")
    print("ok", spec, flush=True)
