"""導入の 3D の部屋（リアル版）。Poly Haven（CC0）の家具と質感を使う。

使い方:
  Blender -b --python scene2.py -- still 60 300 600      # 静止画の確認（フレーム番号）
  Blender -b --python scene2.py -- anim 1 885            # 連番 PNG を書き出す（frames2/）
  環境変数 ENGINE=cycles で Cycles、SAMPLES で品質
時間割（30fps）: 0-5 夕方 / 5.6 親 / 11 ？ / 13.6-16.4 時計が速く回る / 16.9 そばにいたら / 20.4-22 ため
                22 以降は iPad のアップ（子どもが話しかける → iPad が光ってあいさつ）
"""
import bpy, math, random, sys, os, glob
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
PH = os.path.abspath(os.path.join(HERE, "..", "ph", "dl"))  # video/ph/dl（phget.py で取る。リポジトリには入れない）
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["still", "60"]
FPS = 30
def F(t): return int(round(t * FPS)) + 1
T_PARENT, T_Q, T_FAST, T_IF, T_PAUSE, T_CUT, T_ON, T_END = 5.6, 11.0, 13.6, 16.9, 20.4, 22.0, 24.2, 29.5

# ---------- 初期化 ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
ENGINE = os.environ.get("ENGINE", "eevee")
if ENGINE == "cycles":
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"; prefs.get_devices()
    for d in prefs.devices: d.use = True
    sc.cycles.device = "GPU"; sc.cycles.samples = int(os.environ.get("SAMPLES", "96"))
    sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 6; sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False
    sc.cycles.sample_clamp_indirect = 6
else:
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = eng; break
        except TypeError:
            pass
    sc.eevee.taa_render_samples = int(os.environ.get("SAMPLES", "64"))
    for k, v in (("use_shadows", True), ("use_raytracing", os.environ.get("RT", "0") == "1")):
        try: setattr(sc.eevee, k, v)
        except Exception: pass

sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, F(T_END)
sc.view_settings.view_transform = "AgX"
looks = [l.identifier for l in bpy.types.ColorManagedViewSettings.bl_rna.properties["look"].enum_items]
sc.view_settings.look = "AgX - Medium High Contrast" if "AgX - Medium High Contrast" in looks else "None"
sc.render.film_transparent = False
sc.view_settings.exposure = float(os.environ.get("EXPOSURE", "1.0"))

def srgb(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)

# ---------- 材質 ----------
def mat(name, color, rough=0.6, emit=None, strength=0.0, metal=0.0, sss=0.0, coat=0.0, spec=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss; b.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
        b.inputs["Subsurface Scale"].default_value = 0.02
    if coat: b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = strength
    return m

def pbr(name, folder, scale=1.0, tint=None, rough_add=0.0, normal=1.0, proj="BOX", rot=0.0):
    """Poly Haven の質感。Object 座標で箱投影する"""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; n = nt.nodes; L = nt.links
    b = n["Principled BSDF"]; d = f"{PH}/tex/{folder}"
    tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale); mp.inputs["Rotation"].default_value = (0, 0, rot)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    def tex(f, cs):
        t = n.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(f"{d}/{f}"); t.image.colorspace_settings.name = cs
        t.projection = proj; t.projection_blend = 0.25; L.new(mp.outputs["Vector"], t.inputs["Vector"]); return t
    col = tex("Diffuse.jpg", "sRGB").outputs["Color"]
    if tint:
        mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 1.0
        L.new(col, mx.inputs[6]); mx.inputs[7].default_value = (*tint, 1); col = mx.outputs[2]
    L.new(col, b.inputs["Base Color"])
    r = tex("Rough.jpg", "Non-Color").outputs["Color"]
    if rough_add:
        ma = n.new("ShaderNodeMath"); ma.operation = "ADD"; ma.inputs[1].default_value = rough_add; L.new(r, ma.inputs[0]); r = ma.outputs[0]
    L.new(r, b.inputs["Roughness"])
    nm = n.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = normal
    L.new(tex("nor_gl.jpg", "Non-Color").outputs["Color"], nm.inputs["Color"]); L.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m

M = dict(
    floor=pbr("floor", "laminate_floor_02", 0.55),
    wall=pbr("wall", "painted_plaster_wall", 0.6, tint=srgb("#c9cfdc"), normal=0.6),
    wall2=pbr("wall2", "painted_plaster_wall", 0.6, tint=srgb("#e9dcc8"), normal=0.6),
    desk=pbr("desk", "white_oak_veneer", 1.2, rough_add=-0.05),
    walnut=pbr("walnut", "walnut_veneer", 1.5),
    curtain=pbr("curtain", "rough_linen", 3.0, tint=srgb("#9fb4c9")),
    hoodie=pbr("hoodie", "jogging_melange", 6.0, tint=srgb("#5d7fb0"), normal=0.8),
    pants=pbr("pants", "denim_fabric", 6.0, tint=srgb("#7f8aa0")),
    shirt=pbr("shirt", "jogging_melange", 6.0, tint=srgb("#f1ece2"), normal=0.6),
    frame=mat("frame", srgb("#f2efe8"), 0.45, coat=0.2), skirting=mat("skirting", srgb("#efece6"), 0.5),
    hair=mat("hair", srgb("#1d1714"), 0.45), skin=mat("skin", srgb("#e8bf9e"), 0.5, sss=0.25),
    phair=mat("phair", srgb("#2c1f19"), 0.45),
    metal=mat("metal", srgb("#c9ccd2"), 0.28, metal=1.0), dark_metal=mat("dmetal", srgb("#2a2c31"), 0.35, metal=0.9),
    alu=mat("alu", srgb("#b9bcc2"), 0.3, metal=1.0), black_glass=mat("bglass", srgb("#08090b"), 0.08, coat=1.0),
    paper=mat("paper", srgb("#f5f2ea"), 0.85), mug=mat("mug", srgb("#f3efe8"), 0.25, coat=0.6),
    bubble=mat("bubble", srgb("#fbf8f1"), 0.5, emit=srgb("#fbf8f1"), strength=1.4),
    qmark=mat("qmark", srgb("#e0482f"), 0.5, emit=srgb("#e0482f"), strength=1.2),
    laptop_screen=mat("lscreen", (0, 0, 0), 0.2, emit=srgb("#d8e8ff"), strength=4.0),
    rug=pbr("rug", "rough_linen", 1.5, tint=srgb("#b9a58c"), normal=1.5),
)

# ---------- 形の道具 ----------
def finish(o, m, smooth=True):
    if m: o.data.materials.append(m)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    return o

def box(name, loc, size, m, bevel=0.0, rot=(0, 0, 0), seg=3):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        md = o.modifiers.new("bev", "BEVEL"); md.width = bevel; md.segments = seg; md.limit_method = "ANGLE"
        o.data.materials.append(m)
        for p in o.data.polygons: p.use_smooth = True
        try: o.data.set_sharp_from_angle(angle=math.radians(40))
        except Exception: pass
        return o
    return finish(o, m, smooth=False)

def sphere(name, loc, r, m, scale=(1, 1, 1), seg=64):
    bpy.ops.mesh.primitive_uv_sphere_add(location=loc, radius=r, segments=seg, ring_count=seg // 2)
    o = bpy.context.object; o.name = name; o.scale = scale; return finish(o, m)

def cyl(name, loc, r, depth, m, rot=(0, 0, 0), verts=64, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(location=loc, radius=r, depth=depth, rotation=rot, vertices=verts)
    o = bpy.context.object; o.name = name; finish(o, m)
    if bevel:
        md = o.modifiers.new("bev", "BEVEL"); md.width = bevel; md.segments = 3; md.limit_method = "ANGLE"
    try: o.data.set_sharp_from_angle(angle=math.radians(40))
    except Exception: pass
    return o

def subsurf(o, lv=2):
    md = o.modifiers.new("sub", "SUBSURF"); md.levels = lv; md.render_levels = lv; return o

def import_asset(aid, loc=(0, 0, 0), rot_z=0.0, scale=1.0, only=None):
    d = f"{PH}/{aid}"; f = (glob.glob(d + "/*.gltf") + glob.glob(d + "/*.fbx"))[0]
    before = set(bpy.data.objects)
    (bpy.ops.import_scene.gltf if f.endswith("gltf") else bpy.ops.import_scene.fbx)(filepath=f)
    new = [o for o in bpy.data.objects if o not in before]
    keep = []
    for o in new:
        if only and o.type == "MESH" and not any(s in o.name for s in only):
            bpy.data.objects.remove(o, do_unlink=True); continue
        keep.append(o)
    root = bpy.data.objects.new(aid + "_root", None); sc.collection.objects.link(root)
    for o in keep:
        if o.parent is None or o.parent not in keep:
            o.parent = root
    root.location = loc; root.rotation_euler = (0, 0, rot_z); root.scale = (scale,) * 3
    return root, keep

R = random.Random(7)

# ---------- 部屋（カメラも中に入る、閉じた部屋） ----------
ROOM_X0, ROOM_X1, ROOM_Y0, ROOM_Y1, ROOM_H = -3.05, 3.4, -3.8, 2.55, 2.75
box("floor", (0.15, -0.6, -0.05), (6.6, 6.8, 0.1), M["floor"])
box("ceiling", (0.15, -0.6, ROOM_H + 0.05), (6.6, 6.8, 0.1), M["wall2"])
WIN = (-1.25, -0.15, 1.15, 2.05)  # 窓：x0, x1, z0, z1
WY = 2.6  # 奥の壁の中心（厚さ 0.1）
for nm, cx, cz, sx, sz in (("wall_l", (ROOM_X0 + WIN[0]) / 2, ROOM_H / 2, WIN[0] - ROOM_X0, ROOM_H),
                           ("wall_bot", (WIN[0] + WIN[1]) / 2, WIN[2] / 2, WIN[1] - WIN[0], WIN[2]),
                           ("wall_top", (WIN[0] + WIN[1]) / 2, (WIN[3] + ROOM_H) / 2, WIN[1] - WIN[0], ROOM_H - WIN[3]),
                           ("wall_mid", (WIN[1] + 1.45) / 2, ROOM_H / 2, 1.45 - WIN[1], ROOM_H),
                           ("wall_door_top", 1.8, (2.3 + ROOM_H) / 2, 0.7, ROOM_H - 2.3),
                           ("wall_r", (2.15 + ROOM_X1) / 2, ROOM_H / 2, ROOM_X1 - 2.15, ROOM_H)):
    box(nm, (cx, WY, cz), (sx, 0.12, sz), M["wall"])
box("wall_side", (ROOM_X0 - 0.05, -0.6, ROOM_H / 2), (0.1, 6.8, ROOM_H), M["wall"])
box("wall_right", (ROOM_X1 + 0.05, -0.6, ROOM_H / 2), (0.1, 6.8, ROOM_H), M["wall"])
box("wall_front", (0.15, ROOM_Y0 - 0.05, ROOM_H / 2), (6.6, 0.1, ROOM_H), M["wall"])
for nm, loc, size in (("sk_back", (0.15, WY - 0.07, 0.04), (6.4, 0.015, 0.08)), ("sk_left", (ROOM_X0 + 0.01, -0.6, 0.04), (0.015, 6.8, 0.08))):
    box(nm, loc, size, M["skirting"])
box("rug", (-0.6, 1.1, 0.004), (2.2, 1.6, 0.008), M["rug"], bevel=0.003)

# 窓枠・ガラス・窓台
fw = 0.05
for nm, loc, size in (("wf_b", ((WIN[0] + WIN[1]) / 2, WY, WIN[2] + fw / 2), (WIN[1] - WIN[0], 0.14, fw)),
                      ("wf_t", ((WIN[0] + WIN[1]) / 2, WY, WIN[3] - fw / 2), (WIN[1] - WIN[0], 0.14, fw)),
                      ("wf_l", (WIN[0] + fw / 2, WY, (WIN[2] + WIN[3]) / 2), (fw, 0.14, WIN[3] - WIN[2])),
                      ("wf_r", (WIN[1] - fw / 2, WY, (WIN[2] + WIN[3]) / 2), (fw, 0.14, WIN[3] - WIN[2])),
                      ("wf_mv", ((WIN[0] + WIN[1]) / 2, WY + 0.02, (WIN[2] + WIN[3]) / 2), (0.035, 0.05, WIN[3] - WIN[2])),
                      ("sill", ((WIN[0] + WIN[1]) / 2, WY - 0.12, WIN[2] - 0.015), (WIN[1] - WIN[0] + 0.16, 0.2, 0.03))):
    box(nm, loc, size, M["frame"], bevel=0.004)
glass = bpy.data.materials.new("glass"); glass.use_nodes = True
gb = glass.node_tree.nodes["Principled BSDF"]; gb.inputs["Roughness"].default_value = 0.02; gb.inputs["Alpha"].default_value = 0.12
gb.inputs["Base Color"].default_value = (0.9, 0.95, 1.0, 1)
try:
    glass.surface_render_method = "BLENDED"
except Exception:
    pass
bpy.ops.mesh.primitive_plane_add(size=1, location=((WIN[0] + WIN[1]) / 2, WY + 0.03, (WIN[2] + WIN[3]) / 2), rotation=(math.pi / 2, 0, 0))
bpy.data.objects.remove(bpy.context.object, do_unlink=True)

# カーテン（ひだを重ねて、裾を少し広げる）
def curtain(name, x0, x1, gathered):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=160, y_subdivisions=60, size=1, location=(0, 0, 0))
    c = bpy.context.object; c.name = name
    top, bot = 2.25, 0.95
    for v in c.data.vertices:
        u, w = v.co.x + 0.5, v.co.y + 0.5  # 0..1
        x = x0 + (x1 - x0) * u
        z = bot + (top - bot) * w
        amp = 0.03 + 0.02 * (1 - w)
        y = WY - 0.13 - amp * math.sin(u * gathered * math.pi * 2 + 0.6 * math.sin(u * 7)) - 0.01 * math.sin(u * 47)
        v.co = Vector((x, y, z))
    md = c.modifiers.new("sol", "SOLIDIFY"); md.thickness = 0.006
    return finish(c, M["curtain"])
curtain("curtain_l", WIN[0] - 0.42, WIN[0] + 0.02, 7)
curtain("curtain_r", WIN[1] - 0.02, WIN[1] + 0.4, 7)
cyl("rod", ((WIN[0] + WIN[1]) / 2, WY - 0.13, 2.28), 0.012, 2.0, M["dark_metal"], rot=(0, math.pi / 2, 0), verts=24)

# ---------- 窓の外：空と街 ----------
skym = bpy.data.materials.new("sky"); skym.use_nodes = True; nt = skym.node_tree; n = nt.nodes; Ln = nt.links
for x_ in list(n): n.remove(x_)
out = n.new("ShaderNodeOutputMaterial"); em = n.new("ShaderNodeEmission"); tc = n.new("ShaderNodeTexCoord")
sep = n.new("ShaderNodeSeparateXYZ"); r1 = n.new("ShaderNodeValToRGB"); r2 = n.new("ShaderNodeValToRGB")
mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"
r1.color_ramp.elements[0].color = (*srgb("#f6a35e"), 1); r1.color_ramp.elements[0].position = 0.25
r1.color_ramp.elements[1].color = (*srgb("#6a5a9a"), 1); r1.color_ramp.elements[1].position = 0.85
e = r1.color_ramp.elements.new(0.5); e.color = (*srgb("#d9767a"), 1)
r2.color_ramp.elements[0].color = (*srgb("#2c3366"), 1); r2.color_ramp.elements[0].position = 0.2
r2.color_ramp.elements[1].color = (*srgb("#070a1c"), 1); r2.color_ramp.elements[1].position = 0.9
Ln.new(tc.outputs["Generated"], sep.inputs["Vector"]); Ln.new(sep.outputs["Y"], r1.inputs["Fac"]); Ln.new(sep.outputs["Y"], r2.inputs["Fac"])
Ln.new(r1.outputs["Color"], mix.inputs[6]); Ln.new(r2.outputs["Color"], mix.inputs[7])
# 雲（ノイズで少し明るさを変える）
noise = n.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 3.0; noise.inputs["Detail"].default_value = 8
mpn = n.new("ShaderNodeMapping"); mpn.inputs["Scale"].default_value = (1, 3.5, 1); Ln.new(tc.outputs["Generated"], mpn.inputs["Vector"]); Ln.new(mpn.outputs["Vector"], noise.inputs["Vector"])
cl = n.new("ShaderNodeMix"); cl.data_type = "RGBA"; cl.blend_type = "OVERLAY"; cl.inputs[0].default_value = 0.35
Ln.new(mix.outputs[2], cl.inputs[6]); Ln.new(noise.outputs["Fac"], cl.inputs[7])
Ln.new(cl.outputs[2], em.inputs["Color"]); em.inputs["Strength"].default_value = 2.2
Ln.new(em.outputs["Emission"], out.inputs["Surface"])
skyfac = mix.inputs[0]
skyfac.default_value = 0.0; skyfac.keyframe_insert("default_value", frame=F(2.0))
skyfac.default_value = 1.0; skyfac.keyframe_insert("default_value", frame=F(9.0))
sst = em.inputs["Strength"]; sst.default_value = 1.1; sst.keyframe_insert("default_value", frame=F(2.0)); sst.default_value = 1.4; sst.keyframe_insert("default_value", frame=F(9.0))
bpy.ops.mesh.primitive_plane_add(size=1, location=(-0.4, 9.6, 2.5), rotation=(math.pi / 2, 0, 0))
skyo = bpy.context.object; skyo.scale = (16, 7, 1); skyo.data.materials.append(skym)
skyo.visible_shadow = False
# 星と月
starm = mat("star", (1, 1, 1), emit=(1, 0.97, 0.9), strength=0.0)
sb = starm.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
sb.default_value = 0.0; sb.keyframe_insert("default_value", frame=F(6)); sb.default_value = 25.0; sb.keyframe_insert("default_value", frame=F(10))
for i in range(90):
    sphere(f"star{i}", (R.uniform(-4, 3), 9.5, R.uniform(2.6, 5.5)), R.uniform(0.006, 0.014), starm, seg=8)
sphere("moon", (-0.1, 9.5, 3.9), 0.16, mat("moon", (1, 1, 1), emit=srgb("#fff3d6"), strength=8.0))

# 建物：3 列。窓の明かりはレンガ模様で作り、夜になると点く
def bldg_mat(name, base, seed):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; n = nt.nodes; L = nt.links
    b = n["Principled BSDF"]; b.inputs["Base Color"].default_value = (*base, 1); b.inputs["Roughness"].default_value = 0.9
    tc = n.new("ShaderNodeTexCoord"); br = n.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 14.0; br.inputs["Mortar Size"].default_value = 0.35; br.offset = 0.0
    br.inputs["Color1"].default_value = (1, 1, 1, 1); br.inputs["Color2"].default_value = (0, 0, 0, 1); br.inputs["Brick Width"].default_value = 0.5
    br.inputs["Row Height"].default_value = 0.5; br.squash = 1.0
    mpb = n.new("ShaderNodeMapping"); mpb.inputs["Rotation"].default_value = (math.pi / 2, 0, 0)
    L.new(tc.outputs["Object"], mpb.inputs["Vector"]); L.new(mpb.outputs["Vector"], br.inputs["Vector"])
    # 窓ごとのランダム：レンガの色の揺らぎ（Color1/2 の間）を使う
    th = n.new("ShaderNodeMath"); th.operation = "GREATER_THAN"; th.inputs[1].default_value = 0.5
    L.new(br.outputs["Color"], th.inputs[0])
    inv = n.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0; L.new(br.outputs["Fac"], inv.inputs[1])
    mm = n.new("ShaderNodeMath"); mm.operation = "MULTIPLY"; L.new(th.outputs[0], mm.inputs[0]); L.new(inv.outputs[0], mm.inputs[1])
    cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*srgb("#ffd08a"), 1); cr.color_ramp.elements[1].color = (*srgb("#cfe2ff"), 1)
    L.new(br.outputs["Color"], cr.inputs["Fac"])
    L.new(cr.outputs["Color"], b.inputs["Emission Color"])
    sm = n.new("ShaderNodeMath"); sm.operation = "MULTIPLY"; L.new(mm.outputs[0], sm.inputs[0])
    sm.inputs[1].default_value = 0.0
    sm.inputs[1].keyframe_insert("default_value", frame=F(3.5)); sm.inputs[1].default_value = 7.0; sm.inputs[1].keyframe_insert("default_value", frame=F(8.5))
    L.new(sm.outputs[0], b.inputs["Emission Strength"])
    br.color1 if False else None
    br.inputs["Color1"].default_value = (0.85, 0.85, 0.85, 1); br.inputs["Color2"].default_value = (0.1, 0.1, 0.1, 1)
    return m
layers = [(5.5, (-0.4, 0.5), "#2a2f45", (0.25, 0.6)), (7.0, (0.1, 1.1), "#232840", (0.3, 0.8)), (8.5, (0.4, 1.7), "#1c2036", (0.35, 1.0))]
bdark = [mat(f"bd{li}", srgb(c), 0.9) for li, c in enumerate(("#2a2f45", "#232840", "#1c2036"))]
winm = []
for nm, c in (("warm", "#ffcf8a"), ("cool", "#d6e6ff"), ("amber", "#ffb36b")):
    m_ = mat("win_" + nm, (0.02, 0.02, 0.02), 0.5, emit=srgb(c), strength=0.0)
    es_ = m_.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    es_.default_value = 0.0; es_.keyframe_insert("default_value", frame=F(3.5)); es_.default_value = 6.0; es_.keyframe_insert("default_value", frame=F(8.5))
    winm.append(m_)
wv, wf, wmi = [], [], []
for li, (y, tops, col, wr) in enumerate(layers):
    x = -5.0
    while x < 1.0:
        w = R.uniform(*wr); top = R.uniform(*tops); zb = -3.0
        box(f"b{li}", (x + w / 2, y, (zb + top) / 2), (w, 0.4, top - zb), bdark[li])
        ws, hs = 0.026 + 0.006 * li, 0.034 + 0.008 * li  # 窓の大きさ
        gx, gz = ws * 2.1, hs * 1.9
        nx = int((w - 0.06) / gx)
        zz = top - 0.08
        while zz > -0.6:
            for kx in range(nx):
                if R.random() < 0.38:
                    x0 = x + 0.04 + kx * gx; yy = y - 0.205
                    b0 = len(wv); wv += [(x0, yy, zz - hs), (x0 + ws, yy, zz - hs), (x0 + ws, yy, zz), (x0, yy, zz)]
                    wf.append((b0, b0 + 1, b0 + 2, b0 + 3)); wmi.append(R.choice((0, 0, 0, 1, 2)))
            zz -= gz
        x += w + R.uniform(0.0, 0.08)
me_ = bpy.data.meshes.new("city_windows"); me_.from_pydata(wv, [], wf)
for m_ in winm: me_.materials.append(m_)
for pi_, poly in enumerate(me_.polygons): poly.material_index = wmi[pi_]
cw = bpy.data.objects.new("city_windows", me_); sc.collection.objects.link(cw)
# 遠くの街の明かり（地平線のぼんやりした光）
glow = mat("glow", (0, 0, 0), emit=srgb("#ffb070"), strength=0.0)
gs = glow.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
gs.default_value = 0.0; gs.keyframe_insert("default_value", frame=F(4)); gs.default_value = 1.2; gs.keyframe_insert("default_value", frame=F(9))
bpy.ops.mesh.primitive_plane_add(size=1, location=(-0.4, 9.0, 1.15), rotation=(math.pi / 2, 0, 0))
bpy.data.objects.remove(bpy.context.object, do_unlink=True)

# ---------- 時計（Poly Haven の wall_clock） ----------
CLK = Vector((0.6, WY - 0.08, 2.2))
croot, cobjs = import_asset("wall_clock", loc=CLK, rot_z=0.0)
minute = [o for o in cobjs if "minute" in o.name][0]
hour = [o for o in cobjs if "hours" in o.name][0]
second = [o for o in cobjs if "second" in o.name][0]
for h_ in (minute, hour, second):
    h_.rotation_mode = "XYZ"
def set_min(t, ang):
    minute.rotation_euler = (0, ang, 0); minute.keyframe_insert("rotation_euler", frame=F(t))
    hour.rotation_euler = (0, math.radians(-165) + ang / 12, 0); hour.keyframe_insert("rotation_euler", frame=F(t))
base_m = minute.rotation_euler[1]
set_min(0, math.radians(0)); set_min(T_FAST, math.radians(40)); set_min(T_FAST + 2.8, math.radians(40 + 360 + 60)); set_min(T_END, math.radians(40 + 360 + 100))
second.rotation_euler = (0, 0, 0); second.keyframe_insert("rotation_euler", frame=1)
second.rotation_euler = (0, math.radians(6 * T_END * 1.0) * 1, 0); second.keyframe_insert("rotation_euler", frame=F(T_END))

def all_fcurves(action):
    if action is None: return []
    if hasattr(action, "fcurves"):
        try: return list(action.fcurves)
        except Exception: pass
    out = []
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                out += list(cb.fcurves)
    return out
for o in (minute, hour, second):
    for fc in all_fcurves(o.animation_data.action):
        for kp in fc.keyframe_points: kp.interpolation = "LINEAR"

# ---------- 本棚（左の壁）と本 ----------
sroot, sobjs = import_asset("wooden_display_shelves_01", loc=(ROOM_X0 + 0.2, 0.9, 0.0), rot_z=0.0)
_, books = import_asset("decorative_book_set_01", only=["book_", "catalogue_", "magazine_"])
for o in books:
    o.parent = None
bk = [o for o in books if o.name.startswith("book_")]; R.shuffle(bk)
others = [o for o in books if o not in bk]
for o in others: bpy.data.objects.remove(o, do_unlink=True)
# 棚の 3 段 × 3 列のうち、上の 2 段に本を並べる（棚は y 方向に 1.078、高さ 1.556）
used = 0
for row_z in (0.53, 1.04):
    for col in range(3):
        y = 0.9 - 0.5 + 0.05 + col * 0.345
        yend = y + R.uniform(0.18, 0.3)
        while y < yend and used < len(bk):
            o = bk[used]; used += 1
            o.rotation_euler = (0, 0, math.pi / 2); th = o.dimensions[0]
            o.location = (ROOM_X0 + 0.22, y + th / 2, row_z)
            y += th + 0.002
        if R.random() < 0.6 and used < len(bk):  # 斜めに倒した本
            o = bk[used]; used += 1
            o.rotation_euler = (math.radians(-18), 0, math.pi / 2); o.location = (ROOM_X0 + 0.22, y + 0.04, row_z + 0.005)
for o in bk[used:]: bpy.data.objects.remove(o, do_unlink=True)

# ---------- 机 ----------
DESK_Z = 0.72
DX0, DX1, DY0, DY1 = -1.9, 0.5, 1.78, 2.45
box("desk_top", ((DX0 + DX1) / 2, (DY0 + DY1) / 2, DESK_Z - 0.015), (DX1 - DX0, DY1 - DY0, 0.03), M["desk"], bevel=0.004)
box("desk_side_l", (DX0 + 0.02, (DY0 + DY1) / 2, (DESK_Z - 0.03) / 2), (0.03, DY1 - DY0 - 0.04, DESK_Z - 0.03), M["desk"], bevel=0.003)
box("desk_drawers", (DX1 - 0.22, (DY0 + DY1) / 2 + 0.01, (DESK_Z - 0.03) / 2), (0.42, DY1 - DY0 - 0.06, DESK_Z - 0.03), M["desk"], bevel=0.003)
for k in range(3):
    zc = 0.12 + k * 0.215
    box("drawer_front", (DX1 - 0.22, DY0 + 0.015, zc), (0.4, 0.012, 0.2), M["desk"], bevel=0.003)
    box("handle", (DX1 - 0.22, DY0 + 0.004, zc + 0.06), (0.12, 0.012, 0.012), M["metal"], bevel=0.004)
box("desk_back", ((DX0 + DX1) / 2, DY1 - 0.02, (DESK_Z - 0.03) / 2 + 0.15), (DX1 - DX0 - 0.1, 0.02, DESK_Z - 0.33), M["desk"])
# デスクライト（アーム式）：影が出る暖かいスポット
LB = Vector((DX0 + 0.3, DY1 - 0.1, DESK_Z))
lroot, lobjs = import_asset("desk_lamp_arm_01", loc=LB, rot_z=math.radians(-112))
bpy.context.view_layer.update()
lamp = lobjs[0]
SHADE = lroot.matrix_world @ Vector((-0.002, 0.174, 0.693))
for ms in lamp.material_slots:
    if ms.material and ms.material.name.endswith("_light"):
        bb = ms.material.node_tree.nodes.get("Principled BSDF")
        if bb:
            bb.inputs["Emission Color"].default_value = (*srgb("#ffd9a8"), 1); bb.inputs["Emission Strength"].default_value = 30.0
bpy.ops.object.light_add(type="SPOT", location=SHADE + Vector((0, 0, -0.06)))
spot = bpy.context.object; spot.data.energy = 45; spot.data.color = srgb("#ffc78a"); spot.data.spot_size = math.radians(110); spot.data.spot_blend = 0.5
spot.data.shadow_soft_size = 0.03
tgt = Vector((-0.85, 2.0, DESK_Z))
spot.rotation_mode = "QUATERNION"; spot.rotation_quaternion = (tgt - spot.location).to_track_quat("-Z", "Y")
bpy.ops.object.light_add(type="POINT", location=SHADE + Vector((0, 0, 0.02)))
lfill = bpy.context.object; lfill.data.energy = 6; lfill.data.color = srgb("#ffbd80"); lfill.data.shadow_soft_size = 0.05

# 机の上：ノート、教科書、文房具
_, pads = import_asset("office_notepads", only=["a4_a", "a4_b", "yellow_pad"])
for o in pads: o.parent = None
pa = [o for o in pads if "a4_a" in o.name][0]; pb = [o for o in pads if "a4_b" in o.name][0]
pa.location = (-0.98, 2.0, DESK_Z + 0.002); pa.rotation_euler = (0, 0, math.radians(8))
pb.location = (-0.76, 2.03, DESK_Z + 0.002); pb.rotation_euler = (0, 0, math.radians(10))
for o in pads:
    if o not in (pa, pb): o.location = (-1.55, 2.25, DESK_Z + 0.002); o.rotation_euler = (0, 0, math.radians(-20))
_, st = import_asset("stationery_supplies")
for o in st: o.parent = None
cup = [o for o in st if "pencilcup" in o.name][0]; cup.location = (0.25, 2.32, DESK_Z + 0.042); cup.rotation_euler = (0, 0, 0)
pens = [o for o in st if any(k in o.name for k in ("pen_blue", "pen_red", "pencil_new_a", "pencil_new_b"))]
for i, o in enumerate(pens):
    o.rotation_euler = (0, math.radians(-75 + i * 6), math.radians(i * 70)); o.location = (0.25 + 0.012 * math.cos(i * 1.7), 2.32 + 0.012 * math.sin(i * 1.7), DESK_Z + 0.1)
used_pen = [o for o in st if "pencil_used" in o.name][0]; used_pen.location = (-0.66, 1.94, DESK_Z + 0.006); used_pen.rotation_euler = (0, 0, math.radians(35))
er = [o for o in st if "eraser" in o.name][0]; er.location = (-0.58, 2.1, DESK_Z + 0.006); er.rotation_euler = (0, 0, math.radians(-15))
for o in st:
    if o not in pens + [cup, used_pen, er]: bpy.data.objects.remove(o, do_unlink=True)
for i, c in enumerate(["#b5524a", "#3f6f9a", "#d6b25a"]):
    box("textbook", (-1.48, 1.98, DESK_Z + 0.012 + i * 0.022), (0.26, 0.19, 0.02), mat("tb", srgb(c), 0.55), rot=(0, 0, math.radians(-6 + i * 5)), bevel=0.003)
box("mug_d", (0, 0, 0), (0.001, 0.001, 0.001), None)
cyl("mug", (-1.75, 2.0, DESK_Z + 0.05), 0.04, 0.095, M["mug"], verts=48, bevel=0.003)

# 窓台の植木、部屋の隅の大きな植木
_, pl4 = import_asset("potted_plant_04", loc=(-0.95, WY - 0.12, WIN[2]))
_, pl2 = import_asset("potted_plant_02", loc=(1.05, 2.15, 0.0), scale=1.25)
# 椅子（学校の椅子）
_, chair = import_asset("SchoolChair_01", loc=(-0.72, 1.42, 0.0), rot_z=math.pi, scale=0.86)

# ---------- iPad とスタンド ----------
IP = Vector((-0.1, 2.12, DESK_Z + 0.14))
TILT = math.radians(-18)
box("stand_base", (IP.x, IP.y + 0.04, DESK_Z + 0.006), (0.14, 0.13, 0.012), M["alu"], bevel=0.005)
box("stand_arm", (IP.x, IP.y + 0.055, DESK_Z + 0.05), (0.05, 0.012, 0.1), M["alu"], bevel=0.005, rot=(math.radians(-25), 0, 0))
ipad = box("ipad", IP, (0.36, 0.0065, 0.25), M["alu"], bevel=0.011, rot=(TILT, 0, 0), seg=5)
bez = box("ipad_glass", IP + Vector((0, -0.0036, 0)), (0.352, 0.0006, 0.242), M["black_glass"], bevel=0.008, rot=(TILT, 0, 0))
scrm = bpy.data.materials.new("screen"); scrm.use_nodes = True; nt = scrm.node_tree; n = nt.nodes
for x_ in list(n): n.remove(x_)
o_ = n.new("ShaderNodeOutputMaterial"); e_ = n.new("ShaderNodeEmission"); tex = n.new("ShaderNodeTexImage")
img = bpy.data.images.load(f"{HERE}/screen.mp4"); img.source = "MOVIE"; tex.image = img
tex.image_user.frame_duration = 210; tex.image_user.frame_start = F(T_ON); tex.image_user.use_auto_refresh = True
nt.links.new(tex.outputs["Color"], e_.inputs["Color"]); nt.links.new(e_.outputs["Emission"], o_.inputs["Surface"])
es = e_.inputs["Strength"]; es.default_value = 0.0; es.keyframe_insert("default_value", frame=F(22.3))
es.default_value = 0.22; es.keyframe_insert("default_value", frame=F(22.6))  # 話しかけられて、うすく目を覚ます
es.default_value = 0.22; es.keyframe_insert("default_value", frame=F(T_ON))
es.default_value = 0.5; es.keyframe_insert("default_value", frame=F(T_ON + 0.4))
bpy.ops.mesh.primitive_plane_add(size=1, location=IP + Vector((0, -0.0042, 0)), rotation=(math.radians(90) + TILT, 0, 0))
scr = bpy.context.object; scr.name = "screen"; scr.scale = (0.336, 0.232, 1); scr.data.materials.append(scrm)
bpy.ops.object.light_add(type="AREA", location=IP + Vector((0, -0.1, 0)))
ipl = bpy.context.object; ipl.data.shape = "RECTANGLE"; ipl.data.size, ipl.data.size_y = 0.34, 0.24; ipl.data.color = srgb("#e2ecff")
ipl.rotation_euler = (math.radians(90) + TILT, 0, math.pi)
ipl.data.energy = 0.0; ipl.data.keyframe_insert("energy", frame=F(T_ON)); ipl.data.energy = 4.0; ipl.data.keyframe_insert("energy", frame=F(T_ON + 0.4))
# 子どもが話しかける瞬間：画面の端がうすく光る（聞いているしるし）
bpy.ops.object.light_add(type="POINT", location=IP + Vector((0, -0.06, 0.0)))
lis = bpy.context.object; lis.data.color = srgb("#b9d4ff"); lis.data.shadow_soft_size = 0.15
lis.data.energy = 0.0; lis.data.keyframe_insert("energy", frame=F(22.4)); lis.data.energy = 6.0; lis.data.keyframe_insert("energy", frame=F(22.9))
lis.data.energy = 6.0; lis.data.keyframe_insert("energy", frame=F(T_ON)); lis.data.energy = 0.0; lis.data.keyframe_insert("energy", frame=F(T_ON + 0.5))

# ---------- 人：スキンモディファイアでなめらかな体を作る ----------
def skin_body(name, pts, edges, radii, m, sub=2, wrinkle=0.004):
    me = bpy.data.meshes.new(name); me.from_pydata([Vector(p) for p in pts], edges, [])
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    sk = o.modifiers.new("skin", "SKIN"); sk.use_smooth_shade = True; sk.branch_smoothing = 0.6
    for i, r in enumerate(radii):
        o.data.skin_vertices[0].data[i].radius = r if isinstance(r, tuple) else (r, r)
    o.data.skin_vertices[0].data[0].use_root = True
    subsurf(o, sub)
    if wrinkle:
        t = bpy.data.textures.new(name + "_w", "CLOUDS"); t.noise_scale = 0.05
        d = o.modifiers.new("wr", "DISPLACE"); d.texture = t; d.strength = wrinkle; d.texture_coords = "GLOBAL"
    o.data.materials.append(m)
    return o

def add_hair(head, count=1800, length=0.045, color_mat=None, region=None, down=0.6, lift=0.004, thick=0.0016):
    """頭の上と後ろから髪を生やす（カーブの毛。重力の方向へ頭に沿って流す）"""
    bpy.context.view_layer.update()
    mw = head.matrix_world; c = mw.translation
    cu = bpy.data.curves.new(head.name + "_hair", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = thick; cu.bevel_resolution = 1
    cu.use_fill_caps = False; cu.resolution_u = 3
    rr = random.Random(hash(head.name) % 1000)
    # 球の表面を均等にサンプルして、頭のメッシュの外形に合わせる
    golden = math.pi * (3 - math.sqrt(5)); made = 0
    sx, sy, sz = head.scale; rad = head.dimensions.x / 2 / sx if sx else 0.1
    for i in range(count * 3):
        if made >= count: break
        yy = 1 - (i / (count * 3 - 1)) * 2; r_ = math.sqrt(max(0, 1 - yy * yy)); th = golden * i
        u = Vector((math.cos(th) * r_, math.sin(th) * r_, yy))  # 単位球
        local = Vector((u.x * rad, u.y * rad, u.z * rad))
        pw = mw @ local; nrm = (mw.to_3x3() @ u).normalized()
        if not region(pw - c): continue
        g = Vector((0, 0, -1)) * down + Vector((0, -0.25, 0))  # 下と少し後ろへ流れる
        t = (g - nrm * g.dot(nrm)); t = t.normalized() if t.length > 1e-4 else Vector((0, 0, -1))
        t = (t + Vector((rr.uniform(-.35, .35), rr.uniform(-.35, .35), rr.uniform(-.2, .2)))).normalized()
        L_ = length * rr.uniform(0.7, 1.15)
        pts = []
        for k_, f in enumerate((0.0, 0.35, 0.7, 1.0)):
            q = pw + nrm * (lift * (1 - f) + 0.001) + t * L_ * f + nrm * (-0.006 * f * f)
            pts.append(q)
        sp = cu.splines.new("POLY" if False else "NURBS"); sp.points.add(len(pts) - 1)
        for k_, q in enumerate(pts):
            sp.points[k_].co = (q.x, q.y, q.z, 1); sp.points[k_].radius = 1.0 - 0.85 * (k_ / (len(pts) - 1))
        sp.use_endpoint_u = True; sp.order_u = 3
        made += 1
    o = bpy.data.objects.new(head.name + "_hair", cu); sc.collection.objects.link(o)
    if color_mat: cu.materials.append(color_mat)
    return o

# 子ども（後ろ姿、パーカー）。机に向かって +Y を向く
K = Vector((-0.72, 1.5, 0))
def k(x, y, z): return tuple(K + Vector((x, y, z)))
# 体：腰→胸→首。腕は 肩→二の腕→ひじ→前腕→手首（袖はゆったり、手首で細く）
up_pts = [k(0, 0.02, 0.52), k(0, 0.035, 0.66), k(0, 0.06, 0.79), k(0, 0.085, 0.9)]
up_r = [(0.15, 0.11), (0.158, 0.112), (0.168, 0.118), (0.068, 0.068)]
up_edges = [(0, 1), (1, 2), (2, 3)]
for sgn in (-1, 1):  # 腕は別の物体にする（スキンの分かれ目でクラッシュするため）
    arm = [(sgn * 0.09, 0.06, 0.87, 0.07), (sgn * 0.16, 0.06, 0.865, 0.074), (sgn * 0.205, 0.15, 0.835, 0.066), (sgn * 0.225, 0.255, 0.8, 0.06),
           (sgn * 0.185, 0.34, 0.792, 0.056), (sgn * 0.125, 0.415, 0.785, 0.044)]
    skin_body(f"kid_arm{sgn}", [k(x_, y_, z_) for x_, y_, z_, r_ in arm], [(j, j + 1) for j in range(len(arm) - 1)],
              [(r_, r_ * 0.93) for *_, r_ in arm], M["hoodie"], wrinkle=0.004)
kid_up = skin_body("kid_upper", up_pts, up_edges, up_r, M["hoodie"], wrinkle=0.005)
lo_pts = [k(0, 0.02, 0.52), k(-0.09, 0.03, 0.5), k(-0.1, 0.36, 0.52), k(-0.1, 0.4, 0.09), k(-0.1, 0.5, 0.04),
          k(0.09, 0.03, 0.5), k(0.1, 0.36, 0.52), k(0.1, 0.4, 0.09), k(0.1, 0.5, 0.04)]
lo_edges = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8)]
lo_r = [0.13, 0.085, 0.07, 0.05, 0.045, 0.085, 0.07, 0.05, 0.045]
kid_lo = skin_body("kid_lower", lo_pts, lo_edges, lo_r, M["pants"], wrinkle=0.004)
# 手・首・頭・耳
for s in (-1, 1):
    sphere("kid_hand", k(s * 0.105, 0.465, 0.785), 0.036, M["skin"], scale=(0.85, 1.3, 0.62))
    bpy.ops.mesh.primitive_torus_add(location=k(s * 0.128, 0.41, 0.786), major_radius=0.042, minor_radius=0.011, major_segments=48, minor_segments=12)
    cuff = bpy.context.object; cuff.rotation_mode = "QUATERNION"; cuff.rotation_quaternion = Vector((-s * 0.06, 0.075, 0)).to_track_quat("Z", "Y"); finish(cuff, M["hoodie"])
    sphere("kid_ear", k(s * 0.12, 0.1, 1.035), 0.027, M["skin"], scale=(0.45, 0.85, 1.15))
sphere("kid_neck", k(0, 0.09, 0.95), 0.05, M["skin"])
head = sphere("kid_head", k(0, 0.11, 1.045), 0.118, M["skin"], scale=(0.93, 1.02, 1.08), seg=96)
head.rotation_euler = (math.radians(14), 0, 0)
bpy.context.view_layer.update()
# 髪：ベース（短い髪のかたまり）＋毛
hb = sphere("kid_hairbase", k(0, 0.095, 1.062), 0.124, M["hair"], scale=(0.95, 1.04, 1.04), seg=96)
hb.rotation_euler = (math.radians(14), 0, 0)
bpy.context.view_layer.update()
hb.data.materials.append(M["hair"])
def kid_scalp(p):  # 顔（+Y の前側の下半分）を避ける
    return p.z > -0.03 and not (p.y > 0.05 and p.z < 0.05)
add_hair(hb, count=2600, length=0.042, color_mat=M["hair"], region=kid_scalp, down=0.9)
# フード（首の後ろのふくらみ）
# フード：上が開いた袋の形（背中にたれている）
bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 0), radius=0.105, segments=64, ring_count=32)
hood = bpy.context.object; hood.name = "hood"
import bmesh
bm_ = bmesh.new(); bm_.from_mesh(hood.data)
bmesh.ops.delete(bm_, geom=[v for v in bm_.verts if v.co.z > 0.03], context="VERTS"); bm_.to_mesh(hood.data); bm_.free()
finish(hood, M["hoodie"]); sol_ = hood.modifiers.new("sol", "SOLIDIFY"); sol_.thickness = 0.012; subsurf(hood, 1)
hood.location = k(0, -0.035, 0.885); hood.scale = (1.2, 0.62, 0.95); hood.rotation_euler = (math.radians(-28), 0, 0)
t_ = bpy.data.textures.new("hood_w", "CLOUDS"); t_.noise_scale = 0.03
d_ = hood.modifiers.new("wr", "DISPLACE"); d_.texture = t_; d_.strength = 0.01

# 「？」の吹き出し（T_Q でぽんと出る）。いつもカメラのほうを向く平らな円と、太い丸い字の「？」
bubble_root = bpy.data.objects.new("bubble_root", None); sc.collection.objects.link(bubble_root)
bubble_root.location = k(-0.2, 0.1, 1.42)
bpy.ops.mesh.primitive_cylinder_add(radius=0.115, depth=0.012, vertices=96, location=(0, 0, 0))
bub = bpy.context.object; bub.name = "bubble"; finish(bub, M["bubble"]); bub.parent = bubble_root
md_ = bub.modifiers.new("bev", "BEVEL"); md_.width = 0.005; md_.segments = 4
for nm_, (bx_, by_), br_ in (("bubble_t1", (0.075, -0.13), 0.026), ("bubble_t2", (0.11, -0.19), 0.015)):
    bpy.ops.mesh.primitive_cylinder_add(radius=br_, depth=0.01, vertices=48, location=(bx_, by_, 0))
    t_o = bpy.context.object; t_o.name = nm_; finish(t_o, M["bubble"]); t_o.parent = bubble_root
bpy.ops.object.text_add(location=(0, 0, 0.008))
q = bpy.context.object; q.parent = bubble_root
try:
    q.data.font = bpy.data.fonts.load("/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf")
except Exception:
    pass
q.data.body = "?"; q.data.size = 0.16; q.data.extrude = 0.004; q.data.align_x = "CENTER"; q.data.align_y = "CENTER"
q.data.materials.append(M["qmark"])
S_FULL = Vector((1, 1, 1))
bubble_root.scale = S_FULL * 0.0001
def pop(o, full, t_in, t_out):
    o.keyframe_insert("scale", frame=F(t_in) - 1)
    o.scale = Vector(full) * 1.15; o.keyframe_insert("scale", frame=F(t_in + 0.18))
    o.scale = full; o.keyframe_insert("scale", frame=F(t_in + 0.3))
    o.keyframe_insert("scale", frame=F(t_out))
    o.scale = Vector(full) * 0.0001; o.keyframe_insert("scale", frame=F(t_out + 0.4))
pop(bubble_root, S_FULL, T_Q, T_IF + 2.5)

# ---------- 奥の部屋と親 ----------
box("room2_floor", (1.8, 3.6, -0.04), (1.9, 2.1, 0.08), M["floor"])
box("room2_back", (1.8, 4.65, 1.4), (1.9, 0.1, 2.8), M["wall2"])
box("room2_side", (2.75, 3.6, 1.4), (0.1, 2.1, 2.8), M["wall2"])
box("room2_side2", (0.85, 3.6, 1.4), (0.1, 2.1, 2.8), M["wall2"])
box("room2_ceiling", (1.8, 3.6, 2.8), (2.0, 2.2, 0.1), M["wall2"])
for nm, loc, size in (("door_l", (1.47, WY, 1.15), (0.05, 0.16, 2.3)), ("door_r", (2.13, WY, 1.15), (0.05, 0.16, 2.3)), ("door_t", (1.8, WY, 2.32), (0.71, 0.16, 0.05))):
    box(nm, loc, size, M["frame"], bevel=0.004)
# 開いたドア
box("door_leaf", (2.14, WY + 0.38, 1.1), (0.035, 0.72, 2.2), M["frame"], bevel=0.004, rot=(0, 0, math.radians(8)))
box("table2", (1.72, 3.75, 0.72), (0.9, 0.6, 0.035), M["walnut"], bevel=0.004)
for dx in (-0.4, 0.4):
    for dy in (-0.25, 0.25):
        box("t2leg", (1.72 + dx, 3.75 + dy, 0.35), (0.035, 0.035, 0.7), M["walnut"], bevel=0.003)
P0 = Vector((2.2, 3.72, 0))  # 親は右に座り、左のパソコンを見る（-X を向く）
def p(x, y, z): return tuple(P0 + Vector((x, y, z)))
box("pchair", p(0.02, 0, 0.45), (0.4, 0.4, 0.04), M["walnut"], bevel=0.008)
box("pchair_b", p(0.2, 0, 0.75), (0.03, 0.38, 0.5), M["walnut"], bevel=0.008)
# 親の体：胴と首。腕は別の物体（子どもと同じ。分かれ目のあるスキンは Blender 5.2 で崩れる）
pu_pts = [p(0.02, 0, 0.52), p(0.0, 0, 0.7), p(-0.04, 0, 0.88), p(-0.06, 0, 1.02)]
pu_r = [(0.13, 0.17), (0.13, 0.17), (0.13, 0.19), (0.06, 0.06)]
skin_body("parent_upper", pu_pts, [(0, 1), (1, 2), (2, 3)], pu_r, M["shirt"], wrinkle=0.004)
for sgn in (-1, 1):
    arm = [(-0.03, sgn * 0.13, 0.97, 0.058), (-0.05, sgn * 0.18, 0.93, 0.056), (-0.15, sgn * 0.2, 0.83, 0.05),
           (-0.24, sgn * 0.18, 0.78, 0.046), (-0.36, sgn * 0.13, 0.775, 0.04), (-0.43, sgn * 0.11, 0.775, 0.036)]
    skin_body(f"parent_arm{sgn}", [p(x_, y_, z_) for x_, y_, z_, r_ in arm], [(j, j + 1) for j in range(len(arm) - 1)],
              [(r_, r_ * 0.95) for *_, r_ in arm], M["shirt"], wrinkle=0.003)
pl_pts = [p(0.02, 0, 0.52), p(0.0, -0.09, 0.5), p(-0.36, -0.09, 0.5), p(-0.38, -0.09, 0.07), p(-0.48, -0.09, 0.03),
          p(0.0, 0.09, 0.5), p(-0.36, 0.09, 0.5), p(-0.38, 0.09, 0.07), p(-0.48, 0.09, 0.03)]
skin_body("parent_lower", pl_pts, lo_edges, [0.13, 0.085, 0.065, 0.05, 0.045, 0.085, 0.065, 0.05, 0.045], M["pants"])
for s in (-1, 1):
    sphere("p_hand", p(-0.445, s * 0.108, 0.775), 0.034, M["skin"], scale=(1.35, 0.85, 0.5))
sphere("p_neck", p(-0.06, 0, 1.06), 0.05, M["skin"])
ph = sphere("p_head", p(-0.08, 0, 1.18), 0.1, M["skin"], scale=(1.05, 0.92, 1.1), seg=96)
phb = sphere("p_hairbase", p(-0.06, 0, 1.2), 0.106, M["phair"], scale=(1.05, 0.95, 1.08), seg=96)
bpy.context.view_layer.update()
add_hair(phb, count=2200, length=0.06, color_mat=M["phair"], region=lambda q_: q_.z > -0.02 and not (q_.x < -0.04 and q_.z < 0.06), down=1.2)
sphere("p_bun", p(0.05, 0, 1.29), 0.05, M["phair"], scale=(1, 1, 0.9))
# ノートパソコン（アルミ）
box("lap_base", (1.62, 3.75, 0.745), (0.31, 0.22, 0.012), M["alu"], bevel=0.004)
lid = box("lap_lid", (1.47, 3.75, 0.85), (0.008, 0.22, 0.2), M["alu"], bevel=0.004, rot=(0, math.radians(-12), 0))
bpy.ops.mesh.primitive_plane_add(size=1, location=(1.4755, 3.75, 0.85), rotation=(0, math.radians(90 - 12), 0))
lsc = bpy.context.object; lsc.scale = (0.18, 0.2, 1); lsc.data.materials.append(M["laptop_screen"])
cyl("mug2", (1.86, 3.98, 0.79), 0.035, 0.09, M["mug"], verts=48, bevel=0.003)
bpy.ops.object.light_add(type="AREA", location=(1.55, 3.75, 0.95))
lpl = bpy.context.object; lpl.data.size = 0.25; lpl.data.color = srgb("#cfe2ff"); lpl.rotation_euler = (0, math.radians(-90), 0)
bpy.ops.object.light_add(type="AREA", location=(1.8, 3.7, 2.6))
pl = bpy.context.object; pl.data.size = 0.6; pl.data.color = srgb("#ffd6a8")
for L_, e0 in ((lpl, 12), (pl, 70)):
    L_.data.energy = 0.0; L_.data.keyframe_insert("energy", frame=F(T_PARENT - 0.1)); L_.data.energy = e0; L_.data.keyframe_insert("energy", frame=F(T_PARENT + 1.0))
lse = M["laptop_screen"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
lse.default_value = 0.0; lse.keyframe_insert("default_value", frame=F(T_PARENT - 0.1)); lse.default_value = 4.0; lse.keyframe_insert("default_value", frame=F(T_PARENT + 0.8))

# ---------- 光：夕方の窓の光 → 夜の月明かり、部屋のうすい明かり ----------
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (*srgb("#1a2238"), 1); bg.inputs["Strength"].default_value = 0.15
bpy.ops.object.light_add(type="AREA", location=((WIN[0] + WIN[1]) / 2, WY + 0.25, (WIN[2] + WIN[3]) / 2), rotation=(math.radians(-90), 0, 0))
win_l = bpy.context.object; win_l.data.shape = "RECTANGLE"; win_l.data.size, win_l.data.size_y = WIN[1] - WIN[0], WIN[3] - WIN[2]
win_l.data.color = srgb("#ffb27a"); win_l.data.energy = 140; win_l.data.keyframe_insert("energy", frame=F(2.5))
win_l.data.color = srgb("#ffb27a"); win_l.data.keyframe_insert("color", frame=F(2.5))
win_l.data.energy = 18; win_l.data.keyframe_insert("energy", frame=F(9)); win_l.data.color = srgb("#8fa8ff"); win_l.data.keyframe_insert("color", frame=F(9))
bpy.ops.object.light_add(type="SUN", location=(0, 6, 4), rotation=(math.radians(-55), 0, math.radians(180 + 25)))
sun = bpy.context.object; sun.data.color = srgb("#ffae6b"); sun.data.angle = math.radians(1.5)
sun.data.energy = 3.0; sun.data.keyframe_insert("energy", frame=F(2)); sun.data.keyframe_insert("color", frame=F(2))
sun.data.energy = 0.25; sun.data.color = srgb("#9fb6ff"); sun.data.keyframe_insert("energy", frame=F(9)); sun.data.keyframe_insert("color", frame=F(9))
# カメラ側からのうすい明かり（真っ暗にしない）
bpy.ops.object.light_add(type="AREA", location=(1.2, -2.2, 2.5), rotation=(math.radians(60), 0, math.radians(25)))
amb = bpy.context.object; amb.data.size = 3; amb.data.energy = 110; amb.data.color = srgb("#93a6d8")
# 子どもの輪郭を出す光（窓側から）
bpy.ops.object.light_add(type="AREA", location=(-1.3, 2.3, 1.6), rotation=(math.radians(-110), 0, math.radians(-30)))
rim = bpy.context.object; rim.data.size = 0.5; rim.data.energy = 8; rim.data.color = srgb("#aac0ff")

# ---------- カメラ ----------
bpy.ops.object.camera_add()
cam = bpy.context.object; sc.camera = cam; cam.data.lens = 40; cam.data.sensor_width = 36
cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 2.4; cam.data.dof.aperture_blades = 7
target = bpy.data.objects.new("target", None); sc.collection.objects.link(target)
tr = cam.constraints.new("TRACK_TO"); tr.target = target; tr.track_axis = "TRACK_NEGATIVE_Z"; tr.up_axis = "UP_Y"
bt = bubble_root.constraints.new("TRACK_TO"); bt.target = cam; bt.track_axis = "TRACK_Z"; bt.up_axis = "UP_Y"
def key(t, cam_loc, tgt, lens=None):
    cam.location = cam_loc; cam.keyframe_insert("location", frame=F(t))
    target.location = tgt; target.keyframe_insert("location", frame=F(t))
    if lens:
        cam.data.lens = lens; cam.data.keyframe_insert("lens", frame=F(t))
key(0.0, (2.6, -2.9, 2.3), (-0.2, 2.2, 1.0), 32)
key(9.0, (2.0, -2.2, 2.1), (-0.1, 2.15, 1.05), 34)
key(15.0, (0.9, -1.0, 1.7), (-0.5, 2.0, 1.05), 38)
key(T_CUT - 0.02, (0.25, -0.35, 1.45), (-0.55, 2.0, 1.08), 40)
key(T_CUT, (-0.38, 0.92, 1.32), (-0.14, 2.12, 0.91), 46)
key(T_END, (-0.35, 1.04, 1.30), (-0.14, 2.12, 0.91), 48)
for ob in (cam, target):
    for fc in all_fcurves(ob.animation_data.action):
        for kp in fc.keyframe_points:
            if abs(kp.co.x - F(T_CUT)) < 0.5 or abs(kp.co.x - F(T_CUT - 0.02)) < 0.5:
                kp.interpolation = "CONSTANT"
# 手持ちのような、ごくわずかな揺れ
for fc in all_fcurves(cam.animation_data.action):
    if fc.data_path == "location":
        nm = fc.modifiers.new("NOISE"); nm.scale = 90; nm.strength = 0.012; nm.phase = fc.array_index * 13.7
dof = cam.data.dof
dof.focus_distance = 4.0; dof.keyframe_insert("focus_distance", frame=F(0))
dof.focus_distance = 3.6; dof.keyframe_insert("focus_distance", frame=F(9.0))
dof.focus_distance = 2.3; dof.keyframe_insert("focus_distance", frame=F(15.0))
dof.focus_distance = 1.5; dof.keyframe_insert("focus_distance", frame=F(T_CUT - 0.02))
dof.focus_distance = 1.24; dof.keyframe_insert("focus_distance", frame=F(T_CUT))
for fc in all_fcurves(cam.data.animation_data.action):
    for kp in fc.keyframe_points:
        if abs(kp.co.x - F(T_CUT - 0.02)) < 0.5: kp.interpolation = "CONSTANT"

# ---------- 書き出し ----------
mode = argv[0]
OUTD = os.environ.get("OUTD", f"{HERE}/frames2")
if mode == "save":
    bpy.ops.wm.save_as_mainfile(filepath=f"{HERE}/intro2.blend")
elif mode == "still":
    import time
    for fr in argv[1:]:
        t0 = time.time()
        sc.frame_set(int(fr)); sc.render.filepath = f"{HERE}/s2_{ENGINE}_{int(fr):04d}.png"
        bpy.ops.render.render(write_still=True)
        print(f"RENDERTIME frame {fr}: {time.time() - t0:.1f}s", flush=True)
elif mode == "anim":
    sc.frame_start, sc.frame_end = int(argv[1]), int(argv[2])
    sc.render.filepath = f"{OUTD}/f_"; sc.render.image_settings.file_format = "PNG"
    sc.render.use_overwrite = False; sc.render.use_placeholder = True
    bpy.ops.render.render(animation=True)
