import bpy, sys, math
from mathutils import Vector
glb, out, samples, resx, resy = sys.argv[sys.argv.index("--") + 1:][:5]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
center = (lo + hi) / 2; size = hi - lo
print("BOUNDS", lo, hi, size)
scene = bpy.context.scene
cam_data = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_data); scene.collection.objects.link(cam); scene.camera = cam
cam_data.lens = 85
height = size.z; dist = max(size) * 3.0
cam.location = center + Vector((dist * 0.42, -dist * 0.9, height * 0.30))
target = bpy.data.objects.new("target", None); scene.collection.objects.link(target); target.location = center
con = cam.constraints.new("TRACK_TO"); con.target = target; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
nt = world.node_tree; env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load("/home/avopti/.cache/blender-benchmark-launcher/blender-versions/96f6c181a30f4950607839dc84d42a354b250d8a0231b098b59b7bc69c351c48/blender-5.2.0-linux-x64/5.2/datafiles/studiolights/world/studio.exr")
bg = nt.nodes["Background"]; bg.inputs[1].default_value = 0.85; nt.links.new(env.outputs[0], bg.inputs[0])
key = bpy.data.lights.new("key", "AREA"); key.energy = 120 * max(size) ** 2; key.size = max(size) * 2
ko = bpy.data.objects.new("key", key); scene.collection.objects.link(ko); ko.location = center + Vector((-dist * 0.5, -dist * 0.6, height * 0.9))
kc = ko.constraints.new("TRACK_TO"); kc.target = target; kc.track_axis = "TRACK_NEGATIVE_Z"; kc.up_axis = "UP_Y"
scene.render.engine = "CYCLES"; scene.cycles.samples = int(samples); scene.cycles.use_denoising = True
scene.render.film_transparent = True
scene.render.resolution_x = int(resx); scene.render.resolution_y = int(resy)
scene.render.image_settings.file_format = "PNG"; scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "AgX"
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
