import logging
import math
import os
import time
import struct

import bpy
import mathutils

from generated.formats.ms2.compound.LodInfo import LodInfo
from generated.formats.ms2.compound.MaterialName import MaterialName
from generated.formats.ms2.compound.Object import Object
from generated.formats.ms2.compound.MeshData import MeshData
from plugin.modules_export.armature import get_armature, handle_transforms, export_bones_custom
from plugin.modules_export.collision import export_bounds
from plugin.modules_import.armature import get_bone_names
from generated.formats.ms2 import Mdl2File
from plugin.utils.matrix_util import evaluate_mesh
from plugin.utils.shell import get_collection, is_shell, is_fin

MAX_USHORT = 65535


def ensure_tri_modifier(ob):
	"""Makes sure that ob has a triangulation modifier in its stack."""
	for mod in ob.modifiers:
		if mod.type in ('TRIANGULATE',):
			break
	else:
		ob.modifiers.new('Triangulate', 'TRIANGULATE')


def has_objects_in_scene():
	if bpy.context.scene.objects:
		# operator needs an active object, set one if missing (eg. user had deleted the active object)
		if not bpy.context.view_layer.objects.active:
			bpy.context.view_layer.objects.active = bpy.context.scene.objects[0]
		# now enter object mode on the active object, if we aren't already in it
		bpy.ops.object.mode_set(mode="OBJECT")
		return True


def export_material(mdl2, b_mat):
	mat = MaterialName(mdl2.context)
	mat.some_index = get_property(b_mat, "some_index")
	mat.name = b_mat.name
	mdl2.model.materials.append(mat)


def export_model(mdl2, b_lod_coll, b_ob, b_me, bones_table, bounds, apply_transforms):
	logging.info(f"Exporting mesh {b_me.name}")
	# we get the corresponding mdl2 mesh
	mesh = MeshData(mdl2.context)
	# set data
	mesh.size_of_vertex = 48
	mesh.flag._value = get_property(b_me, "flag")
	mesh.unk_floats[:] = (get_property(b_me, "unk_f0"), get_property(b_me, "unk_f1"))

	mesh.update_dtype()
	num_uvs = mesh.get_uv_count()
	num_vcols = mesh.get_vcol_count()
	# ensure that these are initialized
	mesh.tri_indices = []
	mesh.verts = []
	mdl2.model.meshes.append(mesh)

	if not len(b_me.vertices):
		raise AttributeError(f"Mesh {b_ob.name} has no vertices!")

	if not len(b_me.polygons):
		raise AttributeError(f"Mesh {b_ob.name} has no polygons!")

	for len_type, num_type, name_type in (
			(len(b_me.uv_layers), num_uvs, "UV"),
			(len(b_me.vertex_colors), num_vcols, "Vertex Color")):
		logging.debug(f"{name_type} count: {num_type}")
		if len_type != num_type:
			raise AttributeError(f"Mesh {b_ob.name} has {len_type} {name_type} layers, but {num_type} were expected!")
	
	# make sure the mesh has a triangulation modifier
	ensure_tri_modifier(b_ob)
	eval_obj, eval_me = evaluate_mesh(b_ob)
	handle_transforms(eval_obj, eval_me, apply=apply_transforms)
	# print("Mesh slot", ind)
	bounds.append(eval_obj.bound_box)

	hair_length = get_hair_length(b_ob)
	mesh.fur_length = hair_length

	unweighted_vertices = []
	tris = []
	# tangents have to be pre-calculated
	# this will also calculate loop normal
	eval_me.calc_tangents()
	# stores values retrieved from blender, will be packed into array by pyffi
	verts = []
	# use a dict mapping dummy vertices to their index for fast lookup
	# this is used to convert blender vertices (several UVs, normals per face corner) to mdl2 vertices
	dummy_vertices = {}
	count_unique = 0
	count_reused = 0
	shell_ob = None
	shapekey = None
	# fin meshes have to grab tangents from shell
	# if mesh.flag == 565:
	if is_fin(b_ob):
		shell_obs = [ob for ob in b_lod_coll.objects if is_shell(ob) and ob is not b_ob]
		if shell_obs:
			shell_ob = shell_obs[0]
			logging.debug(f"Copying data for {b_ob.name} from base mesh {shell_ob.name}...")
			shell_eval_ob, shell_eval_me = evaluate_mesh(shell_ob)
			shell_eval_me.calc_tangents()
			shell_kd = fill_kd_tree(shell_eval_me)
			fin_uv_layer = eval_me.uv_layers[0].data

	# loop faces and collect unique and repeated vertices
	for face in eval_me.polygons:
		if len(face.loop_indices) != 3:
			# this is a bug - we are applying the triangulation modifier above
			raise AttributeError(f"Mesh {b_ob.name} is not triangulated!")
		# build indices into vertex buffer for the current face
		tri = []
		# loop over face loop to get access to face corner data (normals, uvs, vcols, etc)
		for loop_index in face.loop_indices:
			b_loop = eval_me.loops[loop_index]
			b_vert = eval_me.vertices[b_loop.vertex_index]

			# get the vectors
			position = b_vert.co
			if shell_ob:
				uv_co = fin_uv_layer[b_loop.index].uv.to_3d()
				co, index, dist = shell_kd.find(uv_co)
				shell_loop = shell_eval_me.loops[index]
				# print(tangent)
				tangent = shell_loop.tangent
				normal = shell_loop.normal
			else:
				tangent = b_loop.tangent
				normal = b_loop.normal

			# shape key morphing
			b_key = b_me.shape_keys
			if b_key and len(b_key.key_blocks) > 1:
				lod_key = b_key.key_blocks[1]
				# yes, there is a key object attached
				if lod_key.name.startswith("LOD"):
					shapekey = lod_key.data[b_loop.vertex_index].co

			uvs = [(layer.data[loop_index].uv.x, 1 - layer.data[loop_index].uv.y) for layer in eval_me.uv_layers]
			# create a dummy bytes str for indexing
			float_items = [*position, *[c for uv in uvs[:2] for c in uv], *tangent]
			dummy = struct.pack(f'<{len(float_items)}f', *float_items)
			# see if this dummy key exists
			try:
				# if it does - reuse it by grabbing its index from the dict
				v_index = dummy_vertices[dummy]
				count_reused += 1
			except KeyError:
				# it doesn't, so we have to fill in additional data
				v_index = count_unique
				if v_index > MAX_USHORT:
					raise OverflowError(
						f"{b_ob.name} has too many MDL2 verts. The limit is {MAX_USHORT}. "
						f"\nBlender vertices have to be duplicated on every UV seam, hence the increase.")
				dummy_vertices[dummy] = v_index
				count_unique += 1

				# now collect any missing vert data that was not needed for the splitting of blender verts

				# collect vertex colors
				vcols = [(x for x in layer.data[loop_index].color) for layer in eval_me.vertex_colors]

				bone_ids, bone_weights, fur_length, fur_width, residue, unk_0 = export_weights(
					b_ob, b_vert, bones_table, hair_length, unweighted_vertices)
				# store all raw blender data
				verts.append((position, residue, normal, unk_0, tangent, bone_ids[0], uvs, vcols, bone_ids,
					bone_weights, fur_length, fur_width, shapekey))
			tri.append(v_index)
		tris.append(tri)

	print("count_unique", count_unique)
	print("count_reused", count_reused)

	# report unweighted vertices
	if mesh.flag.weights:
		if unweighted_vertices:
			raise AttributeError(f"{b_ob.name} has {len(unweighted_vertices)} unweighted vertices!")

	# update vert & tri array
	mesh.base = mdl2.model_info.pack_offset
	# transfer raw verts into mesh data packed array
	try:
		mesh.set_verts(verts)
	except ValueError as err:
		raise AttributeError(f"Could not export {b_ob.name}!")

	mesh.tris = tris
	return mesh


def export_weights(b_ob, b_vert, bones_table, hair_length, unweighted_vertices):
	# defaults that may or may not be set later on
	unk_0 = 0
	residue = 1
	fur_length = 0
	fur_width = 0
	bone_index_cutoff = get_property(b_ob, "bone_index")
	# get the weights
	w = []
	for vertex_group in b_vert.groups:
		vgroup_name = b_ob.vertex_groups[vertex_group.group].name
		# get the unk0
		if vgroup_name == "unk0":
			unk_0 = vertex_group.weight
		elif vgroup_name == "residue":
			# if this is not rounded, somehow it affects the weights
			# might be a bug, but can't figure out where the rest is affected
			residue = int(round(vertex_group.weight))
		elif vgroup_name == "fur_length":
			fur_length = vertex_group.weight * hair_length
		elif vgroup_name == "fur_width":
			fur_width = vertex_group.weight
		elif vgroup_name in bones_table:
			# avoid dummy vertex groups without corresponding bones
			bone_index = bones_table[vgroup_name]
			if bone_index > bone_index_cutoff:
				logging.error(
					f"Mesh {b_ob.name} has weights for bone {vgroup_name} [{bone_index}] over the LOD's cutoff at {bone_index_cutoff}!"
					f"\nThis will cause distortions ingame!")
			w.append([bone_index, vertex_group.weight])
		else:
			logging.debug(f"Ignored extraneous vertex group {vgroup_name} on mesh {b_ob.name}!")
	# print(residue, unk_0)
	# get the 4 strongest influences on this vert
	w_s = sorted(w, key=lambda x: x[1], reverse=True)[0:4]
	# print(w_s)
	# pad the weight list to 4 bones, ie. add empty bones if missing
	for i in range(0, 4 - len(w_s)):
		w_s.append([0, 0])
	assert len(w_s) == 4
	# split the list of tuples into two separate lists
	bone_ids, bone_weights = zip(*w_s)
	# summed weights
	sw = sum(bone_weights)
	# print(sw)
	if sw > 0.0:
		# normalize
		bone_weights = [x / sw for x in bone_weights]
	elif b_vert.index not in unweighted_vertices:
		# print("Sum of weights",sw)
		unweighted_vertices.append(b_vert.index)
	return bone_ids, bone_weights, fur_length, fur_width, residue, unk_0


def get_property(ob, prop_name):
	"""Ensure that custom property is set or raise an intellegible error"""
	if prop_name in ob:
		return ob[prop_name]
	else:
		raise KeyError(f"Custom property '{prop_name}' missing from {ob.name} (data: {type(ob).__name__}). Add it!")


def save(filepath='', apply_transforms=False, edit_bones=False):
	messages = set()
	start_time = time.time()

	# ensure that we have objects in the scene
	if not has_objects_in_scene():
		raise AttributeError("No objects in scene, nothing to export!")

	print(f"\nExporting {filepath} into export subfolder...")
	if not os.path.isfile(filepath):
		raise FileNotFoundError(f"{filepath} does not exist. You must open an existing MDL2 file for exporting.")

	mdl2 = Mdl2File()
	mdl2.load(filepath, entry=True, read_bytes=True)
	mdl2.read_editable = True
	mdl2.clear()

	b_armature_ob = get_armature()
	if not b_armature_ob:
		raise AttributeError(f"No armature was found - did you delete it?")
	# clear pose
	for pbone in b_armature_ob.pose.bones:
		pbone.matrix_basis = mathutils.Matrix()

	scene = bpy.context.scene
	if not scene.cobra.pack_base:
		raise AttributeError(f"Set the pack base value for this scene!")
	mdl2.model_info.pack_offset = scene.cobra.pack_base
	mdl2.model_info.render_flag._value = get_property(scene, "render_flag")
	if edit_bones:
		export_bones_custom(b_armature_ob, mdl2)
	# used to get index from bone name for faster weights
	bones_table = dict(((b, i) for i, b in enumerate(get_bone_names(mdl2))))

	b_models = []
	b_materials = []
	bounds = []
	# mesh_objects = [ob for ob in bpy.data.objects if type(ob.data) == bpy.types.Mesh and not ob.rigid_body]
	for lod_i in range(6):
		lod_group_name = f"LOD{lod_i}"
		lod_coll = get_collection(lod_group_name)
		if not lod_coll:
			break
		m_lod = LodInfo(mdl2.context)
		m_lod.distance = math.pow(30+15*lod_i, 2)
		m_lod.first_object_index = len(mdl2.model.objects)
		m_lod.meshes = []
		m_lod.objects = []
		mdl2.model.lods.append(m_lod)
		for b_ob in lod_coll.objects:
			# store & set bone index for lod
			m_lod.bone_index = get_property(b_ob, "bone_index")

			b_me = b_ob.data
			if b_me not in b_models:
				b_models.append(b_me)
				m_mesh = export_model(mdl2, lod_coll, b_ob, b_me, bones_table, bounds, apply_transforms)
				m_mesh.lod_index = lod_i
			for b_mat in b_me.materials:
				if b_mat not in b_materials:
					b_materials.append(b_mat)
					export_material(mdl2, b_mat)
					if "." in b_mat.name:
						messages.add(f"Material {b_mat.name} seems to be an unwanted duplication!")
				# create one unique mesh per material
				m_ob = Object(mdl2.context)
				m_ob.mesh_index = b_models.index(b_me)
				m_ob.material_index = b_materials.index(b_mat)
				mdl2.model.objects.append(m_ob)
				m_lod.meshes.append(mdl2.model.meshes[m_ob.mesh_index])
				m_lod.objects.append(m_ob)
		m_lod.last_object_index = len(mdl2.model.objects)

	export_bounds(bounds, mdl2)
	mdl2.update_counts()

	# write modified mdl2
	mdl2.save(filepath)

	messages.add(f"Finished MDL2 export in {time.time() - start_time:.2f} seconds")
	return messages


def get_hair_length(ob):
	if ob.particle_systems:
		psys = ob.particle_systems[0]
		return psys.settings.hair_length
	return 0


def fill_kd_tree(me):
	size = len(me.loops)
	kd = mathutils.kdtree.KDTree(size)
	uv_layer = me.uv_layers[0].data
	for i, loop in enumerate(me.loops):
		kd.insert(uv_layer[loop.index].uv.to_3d(), i)
	kd.balance()
	return kd
