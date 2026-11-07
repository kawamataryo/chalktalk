"""ChalkTalk のアプリアイコン（1024×1024 PNG）をレンダリングするスクリプト。

絵柄：緑の黒板に、チョークで描いた吹き出しと黄色の「…」。下に木の粉受けと、白いチョークが 1 本。
Talk（声で話す）を吹き出し、Chalk（黒板）を黒板とチョークで表す。

使い方（リポジトリのルートで）:
    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python avatar/build_chalktalk_icon.py

出力（ios/HomeTeacher/Resources/Assets.xcassets/AppIcon.appiconset/）:
    AppIcon.png          ふつうのアイコン（明るい緑の黒板）
    AppIcon-Dark.png     ダークモード用（暗い黒板）
    AppIcon-Tinted.png   ティント用（黒地に白黒。色は iOS がつける）
透過なし・角丸なし（角丸は iOS がつける）。
"""

import math
import os

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_DIR = os.path.join(ROOT, "ios", "HomeTeacher", "Resources", "Assets.xcassets", "AppIcon.appiconset")
SIZE = 1024


def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


VARIANTS = {
    "AppIcon": dict(board="#2F6A55", board_dark="#1E4A3B", chalk="#F7F4EA", dots="#F4C35A", wood="#B98457", wood_dark="#8A5C38",
                    key=3.2, world=0.45),
    "AppIcon-Dark": dict(board="#1C3B31", board_dark="#0F241D", chalk="#E9E5DA", dots="#E8B54C", wood="#6E4D33", wood_dark="#4A3220",
                         key=2.0, world=0.2),
    "AppIcon-Tinted": dict(board="#151515", board_dark="#050505", chalk="#F2F2F2", dots="#BDBDBD", wood="#3A3A3A", wood_dark="#222222",
                           key=2.4, world=0.3),
}


def principled(name, color, rough=0.8, emit=None, strength=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*srgb(color), 1)
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*srgb(emit), 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


def board_material(v):
    """黒板：消したあとのムラと細かいざらつき"""
    m = bpy.data.materials.new("board"); m.use_nodes = True; nt = m.node_tree; n = nt.nodes
    b = n["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.9
    tc = n.new("ShaderNodeTexCoord")
    smudge = n.new("ShaderNodeTexNoise"); smudge.inputs["Scale"].default_value = 2.2; smudge.inputs["Detail"].default_value = 3
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*srgb(v["board_dark"]), 1); ramp.color_ramp.elements[1].color = (*srgb(v["board"]), 1)
    ramp.color_ramp.elements[0].position = 0.3; ramp.color_ramp.elements[1].position = 0.75
    grain = n.new("ShaderNodeTexNoise"); grain.inputs["Scale"].default_value = 220; grain.inputs["Detail"].default_value = 2
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.08
    nt.links.new(tc.outputs["Object"], smudge.inputs["Vector"]); nt.links.new(smudge.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(tc.outputs["Object"], grain.inputs["Vector"]); nt.links.new(grain.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def chalk_material(name, color):
    """チョークの線：白く、少し光り、ところどころかすれる（透明の混ぜ）"""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; n = nt.nodes
    for x in list(n): n.remove(x)
    out = n.new("ShaderNodeOutputMaterial"); mix = n.new("ShaderNodeMixShader")
    bsdf = n.new("ShaderNodeBsdfPrincipled"); bsdf.inputs["Base Color"].default_value = (*srgb(color), 1)
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Emission Color"].default_value = (*srgb(color), 1); bsdf.inputs["Emission Strength"].default_value = 0.35
    tr = n.new("ShaderNodeBsdfTransparent")
    tc = n.new("ShaderNodeTexCoord"); noise = n.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 90; noise.inputs["Detail"].default_value = 6
    ramp = n.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].position = 0.38; ramp.color_ramp.elements[1].position = 0.5
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"]); nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(bsdf.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    try:
        m.blend_method = "HASHED"
    except Exception:
        pass
    return m


def stroke(name, points, width, mat, closed=True):
    """点列をチョークの太い線（曲線＋丸い断面）にする"""
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = width; cu.bevel_resolution = 4
    sp = cu.splines.new("POLY"); sp.points.add(len(points) - 1)
    for p, (x, y) in zip(sp.points, points):
        p.co = (x, 0, y, 1)
    sp.use_cyclic_u = closed
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    cu.materials.append(mat)
    return o


def build(variant, v):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng; break
        except TypeError:
            pass
    sc.render.resolution_x = sc.render.resolution_y = SIZE
    sc.render.film_transparent = False
    sc.eevee.taa_render_samples = 64
    sc.view_settings.view_transform = "Standard"

    # 黒板（画面いっぱい）
    bpy.ops.mesh.primitive_plane_add(size=2.4, location=(0, 0.02, 0), rotation=(math.pi / 2, 0, 0))
    bpy.context.object.data.materials.append(board_material(v))
    # 粉受け（下の木の棚）
    bpy.ops.mesh.primitive_cube_add(location=(0, -0.06, -0.86))
    led = bpy.context.object; led.scale = (1.3, 0.09, 0.075)
    bev = led.modifiers.new("b", "BEVEL"); bev.width = 0.02; bev.segments = 4
    led.data.materials.append(principled("wood", v["wood"], 0.6)); bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_cube_add(location=(0, -0.02, -0.955))
    lip = bpy.context.object; lip.scale = (1.3, 0.05, 0.03); lip.data.materials.append(principled("wood2", v["wood_dark"], 0.6))
    # チョーク（粉受けの上に 1 本）
    bpy.ops.mesh.primitive_cylinder_add(radius=0.055, depth=0.55, location=(0.36, -0.1, -0.735), rotation=(0, math.radians(90), math.radians(-12)), vertices=32)
    ch = bpy.context.object; ch.data.materials.append(principled("chalk", v["chalk"], 0.95)); bpy.ops.object.shade_smooth()
    bev = ch.modifiers.new("b", "BEVEL"); bev.width = 0.012; bev.segments = 3

    # 吹き出し（チョークの線）：角の丸い四角としっぽ
    cm = chalk_material("chalkline", v["chalk"])
    w, h, r = 1.25, 0.82, 0.3
    cx, cy = 0.0, 0.18
    pts = []
    corners = [(cx + w / 2 - r, cy + h / 2 - r, 0), (cx - w / 2 + r, cy + h / 2 - r, 90),
               (cx - w / 2 + r, cy - h / 2 + r, 180), (cx + w / 2 - r, cy - h / 2 + r, 270)]
    for i, (ax, ay, a0) in enumerate(corners):
        for k in range(10):
            a = math.radians(a0 + k * 10)
            pts.append((ax + r * math.cos(a), ay + r * math.sin(a)))
        pts.append((ax + r * math.cos(math.radians(a0 + 90)), ay + r * math.sin(math.radians(a0 + 90))))
        if i == 2:  # 下の辺の左寄りに、三角のしっぽ
            yb = cy - h / 2
            pts += [(cx - w / 2 + r + 0.02, yb), (cx - w / 2 + 0.16, yb - 0.26), (cx - w / 2 + r + 0.24, yb)]
    s = stroke("bubble", pts, 0.042, cm)
    s.location.y = -0.01
    # 黄色の「…」（チョークで打った点）
    dm = chalk_material("dots", v["dots"])
    for k in (-1, 0, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.085, location=(cx + k * 0.3, -0.02, cy), segments=32, ring_count=16)
        d = bpy.context.object; d.scale = (1, 0.25, 1); d.data.materials.append(dm); bpy.ops.object.shade_smooth()

    # 光：左上から柔らかく
    bpy.ops.object.light_add(type="AREA", location=(-1.2, -2.2, 1.6))
    key = bpy.context.object; key.data.energy = v["key"] * 100; key.data.size = 2.5
    key.rotation_euler = (math.radians(60), 0, math.radians(-30))
    w_ = bpy.data.worlds.new("w"); sc.world = w_; w_.use_nodes = True
    w_.node_tree.nodes["Background"].inputs["Strength"].default_value = v["world"]

    # カメラ（正面・平行投影）
    bpy.ops.object.camera_add(location=(0, -5, 0), rotation=(math.pi / 2, 0, 0))
    cam = bpy.context.object; cam.data.type = "ORTHO"; cam.data.ortho_scale = 2.1; sc.camera = cam

    sc.render.filepath = os.path.join(ICON_DIR, f"{variant}.png")
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"
    bpy.ops.render.render(write_still=True)


for name, v in VARIANTS.items():
    build(name, v)
print("ChalkTalk のアイコンを書き出した:", ICON_DIR)
