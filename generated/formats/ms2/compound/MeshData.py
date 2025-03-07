
import logging
import math
import numpy as np
import struct
from generated.formats.ms2.compound.packing_utils import *

FUR_OVERHEAD = 2


import numpy
import typing
from generated.array import Array
from generated.context import ContextReference
from generated.formats.ms2.bitfield.ModelFlag import ModelFlag


class MeshData:

	"""
	PZ and JWE have a ptr at the start instead of the stream index
	"""

	context = ContextReference()

	def __init__(self, context, arg=None, template=None):
		self.name = ''
		self._context = context
		self.arg = arg
		self.template = template
		self.io_size = 0
		self.io_start = 0

		# index into streamed buffers, streaming is not used for JWE or PZ
		self.stream_index = 0

		# always zero
		self.zeros = numpy.zeros((3), dtype='uint')

		# vertex count of model
		self.vertex_count = 0

		# number of index entries in the triangle index list; (not: number of triangles, byte count of tri buffer)
		self.tri_index_count = 0

		# always zero
		self.zero_0 = 0

		# power of 2 increasing with lod index
		self.poweroftwo = 0

		# byte offset from start of vert buffer (=start of buffer nr 2) in bytes
		self.vertex_offset = 0

		# usually 48
		self.size_of_vertex = 0

		# byte offset from start of tri buffer in bytes
		self.tri_offset = 0

		# always zero
		self.zero_1 = 0

		# some floats, purpose unknown
		self.unk_floats = numpy.zeros((2), dtype='float')

		# always zero
		self.zero_2 = 0

		# bitfield, determines vertex format
		self.flag = ModelFlag()
		self.set_defaults()

	def set_defaults(self):
		self.stream_index = 0
		self.zeros = numpy.zeros((3), dtype='uint')
		self.vertex_count = 0
		self.tri_index_count = 0
		self.zero_0 = 0
		self.poweroftwo = 0
		self.vertex_offset = 0
		self.size_of_vertex = 0
		self.tri_offset = 0
		self.zero_1 = 0
		self.unk_floats = numpy.zeros((2), dtype='float')
		self.zero_2 = 0
		self.flag = ModelFlag()

	def read(self, stream):
		self.io_start = stream.tell()
		self.stream_index = stream.read_uint()
		self.zeros = stream.read_uints((3))
		self.vertex_count = stream.read_uint()
		self.tri_index_count = stream.read_uint()
		self.zero_0 = stream.read_uint()
		self.poweroftwo = stream.read_uint()
		self.vertex_offset = stream.read_uint()
		self.size_of_vertex = stream.read_uint()
		self.tri_offset = stream.read_uint()
		self.zero_1 = stream.read_uint()
		self.unk_floats = stream.read_floats((2))
		self.zero_2 = stream.read_uint()
		self.flag = stream.read_type(ModelFlag)

		self.io_size = stream.tell() - self.io_start

	def write(self, stream):
		self.io_start = stream.tell()
		stream.write_uint(self.stream_index)
		stream.write_uints(self.zeros)
		stream.write_uint(self.vertex_count)
		stream.write_uint(self.tri_index_count)
		stream.write_uint(self.zero_0)
		stream.write_uint(self.poweroftwo)
		stream.write_uint(self.vertex_offset)
		stream.write_uint(self.size_of_vertex)
		stream.write_uint(self.tri_offset)
		stream.write_uint(self.zero_1)
		stream.write_floats(self.unk_floats)
		stream.write_uint(self.zero_2)
		stream.write_type(self.flag)

		self.io_size = stream.tell() - self.io_start

	def get_info_str(self):
		return f'MeshData [Size: {self.io_size}, Address: {self.io_start}] {self.name}'

	def get_fields_str(self):
		s = ''
		s += f'\n	* stream_index = {self.stream_index.__repr__()}'
		s += f'\n	* zeros = {self.zeros.__repr__()}'
		s += f'\n	* vertex_count = {self.vertex_count.__repr__()}'
		s += f'\n	* tri_index_count = {self.tri_index_count.__repr__()}'
		s += f'\n	* zero_0 = {self.zero_0.__repr__()}'
		s += f'\n	* poweroftwo = {self.poweroftwo.__repr__()}'
		s += f'\n	* vertex_offset = {self.vertex_offset.__repr__()}'
		s += f'\n	* size_of_vertex = {self.size_of_vertex.__repr__()}'
		s += f'\n	* tri_offset = {self.tri_offset.__repr__()}'
		s += f'\n	* zero_1 = {self.zero_1.__repr__()}'
		s += f'\n	* unk_floats = {self.unk_floats.__repr__()}'
		s += f'\n	* zero_2 = {self.zero_2.__repr__()}'
		s += f'\n	* flag = {self.flag.__repr__()}'
		return s

	def __repr__(self):
		s = self.get_info_str()
		s += self.get_fields_str()
		s += '\n'
		return s

	def read_bytes(self, buffer_2_offset, vertex_data_size, stream):
		"""Used to store raw binary vertex and tri data on the mesh, for merging"""
		# print("reading binary mesh data")
		# read a vertices of this mesh
		stream.seek(buffer_2_offset + self.vertex_offset)
		self.verts_bytes = stream.read(self.size_of_vertex * self.vertex_count)
		stream.seek(buffer_2_offset + vertex_data_size + self.tri_offset)
		self.tris_bytes = stream.read(2 * self.tri_index_count)

	# print(len(self.verts_bytes), len(self.tris_bytes))

	def read_bytes_map(self, buffer_2_offset, stream):
		"""Used to document byte usage of different vertex formats"""
		# read a vertices of this mesh
		stream.seek(buffer_2_offset + self.vertex_offset)
		# read the packed ms2_file
		ms2_file = np.fromfile(stream, dtype=np.ubyte, count=self.size_of_vertex * self.vertex_count)
		ms2_file = ms2_file.reshape((self.vertex_count, self.size_of_vertex))
		self.bytes_max = np.max(ms2_file, axis=0)
		self.bytes_min = np.min(ms2_file, axis=0)
		self.bytes_mean = np.mean(ms2_file, axis=0)
		if self.size_of_vertex != 48:
			raise AttributeError(f"size_of_vertex != 48: size_of_vertex {self.size_of_vertex}, flag {self.flag}", )

	def init_arrays(self):
		self.vertices = np.empty((self.vertex_count, 3), np.float32)
		self.normals = np.empty((self.vertex_count, 3), np.float32)
		self.tangents = np.empty((self.vertex_count, 3), np.float32)
		try:
			uv_shape = self.dt["uvs"].shape
			self.uvs = np.empty((self.vertex_count, *uv_shape), np.float32)
		except:
			self.uvs = None
		try:
			fur_shape = self.dt["fur_shell"].shape
			self.fur = np.empty((self.vertex_count, *fur_shape), np.float32)
		except:
			self.fur = None
		try:
			colors_shape = self.dt["colors"].shape
			self.colors = np.empty((self.vertex_count, *colors_shape), np.float32)
		except:
			self.colors = None
		try:
			shapekeys_shape = self.dt["shapekeys0"].shape
			self.shapekeys = np.empty((self.vertex_count, 3), np.float32)
		except:
			self.shapekeys = None
		self.weights = []

	def get_vcol_count(self, ):
		if "colors" in self.dt.fields:
			return self.dt["colors"].shape[0]
		return 0

	def get_uv_count(self, ):
		if "uvs" in self.dt.fields:
			return self.dt["uvs"].shape[0]
		return 0

	def update_dtype(self):
		"""Update MeshData.dt (numpy dtype) according to MeshData.flag"""
		# basic shared stuff
		dt = [
			("pos", np.uint64),
			("normal", np.ubyte, (3,)),
			("unk", np.ubyte),
			("tangent", np.ubyte, (3,)),
			("bone index", np.ubyte),
		]
		# uv variations
		if self.flag == 528:
			dt.extend([
				("uvs", np.ushort, (1, 2)),
				("zeros0", np.int32, (3,))
			])
		elif self.flag == 529:
			dt.extend([
				("uvs", np.ushort, (2, 2)),
				("zeros0", np.int32, (2,))
			])
		elif self.flag in (565,):
			dt.extend([
				("uvs", np.ushort, (2, 2)),
				("colors", np.ubyte, (1, 4)),  # these appear to be directional vectors
				("zeros0", np.int32, (1,))
			])
		elif self.flag in (821, 853, 885, 1013):
			dt.extend([
				("uvs", np.ushort, (1, 2)),
				("fur_shell", np.ushort, (2,)),
				("colors", np.ubyte, (1, 4)),  # these appear to be directional vectors
				("zeros0", np.int32, (1,))
			])
		elif self.flag == 533:
			dt.extend([
				# see walls_gate.mdl2, two uv layers
				("uvs", np.ushort, (2, 2)),
				("colors", np.ubyte, (1, 4)),
				("zeros2", np.int32, (1,))
			])
		elif self.flag == 513:
			dt.extend([
				("uvs", np.ushort, (2, 2)),
				# ("colors", np.ubyte, (1, 4)),
				("zeros2", np.uint64, (3,))
			])
		elif self.flag == 512:
			dt.extend([
				# tree_birch_white_03 - apparently 8 uvs
				("uvs", np.ushort, (8, 2)),
			])
		elif self.flag == 517:
			dt.extend([
				("uvs", np.ushort, (1, 2)),
				("shapekeys0", np.uint32, 1),
				("colors", np.ubyte, (1, 4)),  # this appears to be normals, or something similar
				("shapekeys1", np.uint32, 1),
				("colors1", np.ubyte, (4, 4)),
			])
		elif self.flag == 545:
			dt.extend([
				# cz_glasspanel_4m_02.mdl2
				("uvs", np.ushort, (1, 2)),
				("zeros2", np.uint32, (7,)),
			])

		# bone weights
		if self.flag in (528, 529, 533, 565, 821, 853, 885, 1013):
			dt.extend([
				("bone ids", np.ubyte, (4,)),
				("bone weights", np.ubyte, (4,)),
				("zeros1", np.uint64)
			])
		self.dt = np.dtype(dt)
		self.update_shell_count()
		if self.dt.itemsize != self.size_of_vertex:
			raise AttributeError(
				f"Vertex size for flag {self.flag} is wrong! Collected {self.dt.itemsize}, got {self.size_of_vertex}")

	def read_verts(self, stream):
		# read a vertices of this mesh
		stream.seek(self.buffer_2_offset + self.vertex_offset)
		logging.debug(f"Reading {self.vertex_count} verts at {stream.tell()}")
		# get dtype according to which the vertices are packed
		self.update_dtype()
		# read the packed ms2_file
		self.verts_data = np.fromfile(stream, dtype=self.dt, count=self.vertex_count)
		if len(self.verts_data) != self.vertex_count:
			raise BufferError(f"{len(self.verts_data)} were read into vertex buffer, should have {self.vertex_count}")
		# create arrays for the unpacked ms2_file
		self.init_arrays()
		# first cast to the float uvs array so unpacking doesn't use int division
		if self.uvs is not None:
			self.uvs[:] = self.verts_data[:]["uvs"]
			self.uvs = unpack_ushort_vector(self.uvs)
		self.fur_length = 0.0
		if self.fur is not None:
			self.fur[:] = self.verts_data[:]["fur_shell"]
			self.fur = unpack_ushort_vector(self.fur)
			# normalize with some overhead
			self.fur_length = np.max(self.fur[:, 0]) * FUR_OVERHEAD
			# fur length can be set to 0 for the whole mesh, so make sure we don't divide in that case
			if self.fur_length:
				# print("self.fur_length", self.fur_length)
				self.fur[:, 0] /= self.fur_length
			# value range of fur width is +-16 - squash it into 0 - 1
			self.fur[:, 1] = remap(self.fur[:, 1], -16, 16, 0, 1)
			# print("self.fur[0]", self.fur[0])
		if self.colors is not None:
			# first cast to the float colors array so unpacking doesn't use int division
			self.colors[:] = self.verts_data[:]["colors"]
			self.colors /= 255
		self.normals[:] = self.verts_data[:]["normal"]
		self.tangents[:] = self.verts_data[:]["tangent"]
		self.normals = (self.normals - 128) / 128
		# normalize
		self.normals /= np.linalg.norm(self.normals, axis=1, keepdims=True)
		self.tangents = (self.tangents - 128) / 128
		# unpack the shapekeys
		if self.shapekeys is not None:
			for i in range(self.vertex_count):
				first = self.verts_data[i]["shapekeys0"]
				second = self.verts_data[i]["shapekeys1"]
				packed = struct.pack("LL", first, second)
				unpacked = struct.unpack("Q", packed)[0]
				vert, residue = unpack_longint_vec(unpacked, self.base)
				self.shapekeys[i] = unpack_swizzle(vert)
			# print(self.shapekeys)

		for i in range(self.vertex_count):
			in_pos_packed = self.verts_data[i]["pos"]
			vert, residue = unpack_longint_vec(in_pos_packed, self.base)
			self.vertices[i] = unpack_swizzle(vert)
			self.normals[i] = unpack_swizzle(self.normals[i])
			self.tangents[i] = unpack_swizzle(self.tangents[i])
			self.weights.append(unpack_weights(self, i, residue))
		# if self.flag == 517:
		# 	print(self.verts_data)

	def write_verts(self, stream):
		stream.write(self.verts_data.tobytes())

	def read_tris(self, stream):
		# read all tri indices for this mesh
		stream.seek(self.buffer_2_offset + self.ms2_file.buffer_info.vertexdatasize + self.tri_offset)
		# read all tri indices for this mesh segment
		index_count = self.tri_index_count // self.shell_count
		logging.debug(f"Reading {index_count} indices at {stream.tell()}")
		self.tri_indices = np.fromfile(stream, dtype=np.uint16, count=index_count)
		if len(self.tri_indices) != index_count:
			raise BufferError(f"{len(self.tri_indices)} were read into tri index buffer, should have {index_count}")

	def write_tris(self, stream):
		tri_bytes = self.tri_indices.tobytes()
		# extend tri array according to shell count
		logging.debug(f"Writing {self.shell_count} shells of triangles")
		for shell in range(self.shell_count):
			stream.write(tri_bytes)

	@property
	def lod_index(self, ):
		try:
			lod_i = int(math.log2(self.poweroftwo))
		except:
			lod_i = 0
			logging.warning(f"math domain for lod {self.poweroftwo}")
		return lod_i

	@lod_index.setter
	def lod_index(self, lod_i):
		self.poweroftwo = int(math.pow(2, lod_i))

	def set_verts(self, verts):
		"""Update self.verts_data from list of new verts"""
		self.verts = verts
		self.verts_data = np.zeros(len(verts), dtype=self.dt)
		for i, (
				position, residue, normal, unk_0, tangent, bone_index, uvs, vcols, bone_ids, bone_weights,
				fur_length, fur_width, shapekey) in enumerate(
			verts):
			# print("shapekey", shapekey)
			self.verts_data[i]["pos"] = pack_longint_vec(pack_swizzle(position), residue, self.base)
			self.verts_data[i]["normal"] = pack_ubyte_vector(pack_swizzle(normal))
			self.verts_data[i]["tangent"] = pack_ubyte_vector(pack_swizzle(tangent))
			self.verts_data[i]["unk"] = unk_0 * 255
			self.verts_data[i]["bone index"] = bone_index
			if "bone ids" in self.dt.fields:
				self.verts_data[i]["bone ids"] = bone_ids
				# round is essential so the float is not truncated
				self.verts_data[i]["bone weights"] = list(round(w * 255) for w in bone_weights)
				# print(self.verts_data[i]["bone weights"], np.sum(self.verts_data[i]["bone weights"]))
				# additional double check
				d = np.sum(self.verts_data[i]["bone weights"]) - 255
				self.verts_data[i]["bone weights"][0] -= d
				assert np.sum(self.verts_data[i]["bone weights"]) == 255
			if "uvs" in self.dt.fields:
				self.verts_data[i]["uvs"] = list(pack_ushort_vector(uv) for uv in uvs)
			if "fur_shell" in self.dt.fields and fur_length is not None:
				self.verts_data[i]["fur_shell"] = pack_ushort_vector((fur_length, remap(fur_width, 0, 1, -16, 16)))
			if "colors" in self.dt.fields:
				self.verts_data[i]["colors"] = list(list(round(c * 255) for c in vcol) for vcol in vcols)
			if "shapekeys0" in self.dt.fields:
				# first pack it as uint64
				raw_packed = pack_longint_vec(pack_swizzle(shapekey), 0, self.base)
				if raw_packed < 0:
					logging.error(f"Shapekey {raw_packed} could not be packed into uint64")
					raw_packed = 0
				raw_bytes = struct.pack("Q", raw_packed)
				# unpack to 2 uints again and assign data
				first, second = struct.unpack("LL", raw_bytes)
				self.verts_data[i]["shapekeys0"] = first
				self.verts_data[i]["shapekeys1"] = second

	def update_shell_count(self):
		# 853 in aardvark is a shell mesh, but has no tri shells
		if self.flag.repeat_tris:
			self.shell_count = 6
		else:
			self.shell_count = 1

	@property
	def tris(self, ):
		# create non-overlapping tris from flattened tri indices
		tris_raw = np.reshape(self.tri_indices, (len(self.tri_indices)//3, 3))
		# reverse each tri to account for the flipped normals from mirroring in blender
		return np.flip(tris_raw, axis=-1)

	@tris.setter
	def tris(self, b_tris):
		# cast to uint16
		raw_tris = np.array(b_tris, dtype=np.uint16)
		# reverse tris
		raw_tris = np.flip(raw_tris, axis=-1)
		# flatten array
		self.tri_indices = np.reshape(raw_tris, len(raw_tris)*3)

	def populate(self, ms2_file, ms2_stream, buffer_2_offset, base=512):
		self.buffer_2_offset = buffer_2_offset
		self.ms2_file = ms2_file
		self.base = base
		self.read_verts(ms2_stream)
		self.read_tris(ms2_stream)
		self.validate_tris()

	def validate_tris(self):
		"""See if all tri indices point into the vertex buffer, raise an error if they don't"""
		# max_ind = np.max(self.tri_indices)
		# if max_ind >= len(self.verts_data):
		for max_ind in self.tri_indices:
			if max_ind >= len(self.verts_data):
				raise IndexError(f"Tri index {max_ind} does not point into {len(self.verts_data)} vertices")
		logging.debug("All tri indices are valid")

