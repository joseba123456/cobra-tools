
from generated.formats.ovl.compound.Triplet import Triplet
from generated.formats.ovl.versions import *
from hashes import constants_jwe, constants_pz, constants_jwe2


from generated.context import ContextReference


class MimeEntry:

	"""
	Description of one mime type or file class.
	Inside the archive not the stored mime hash is used but the extension hash, has to be generated, eg. djb("bani") == 2090104799
	"""

	context = ContextReference()

	def __init__(self, context, arg=None, template=None):
		self.name = ''
		self._context = context
		self.arg = arg
		self.template = template
		self.io_size = 0
		self.io_start = 0

		# offset in the header's Names block
		self.offset = 0

		# usually zero
		self.unknown = 0

		# changes with game version; hash of this file extension; same across all files, but not used anywhere else in the archive
		self.mime_hash = 0

		# usually increments with game
		self.mime_version = 0

		# Id of this class type. Later in the file there is a reference to this Id; offset into FileEntry list in number of files
		self.file_index_offset = 0

		# Number of entries of this class in the file.; from 'file index offset', this many files belong to this file extension
		self.file_count = 0

		# constant per mime, grab this many triplets
		self.triplet_count = 0

		# index into triplets list
		self.triplet_offset = 0
		self.set_defaults()

	def set_defaults(self):
		self.offset = 0
		self.unknown = 0
		self.mime_hash = 0
		self.mime_version = 0
		self.file_index_offset = 0
		self.file_count = 0
		if self.context.version >= 20:
			self.triplet_count = 0
		if self.context.version >= 20:
			self.triplet_offset = 0

	def read(self, stream):
		self.io_start = stream.tell()
		self.offset = stream.read_uint()
		self.unknown = stream.read_uint()
		self.mime_hash = stream.read_uint()
		self.mime_version = stream.read_uint()
		self.context.mime_version = self.mime_version
		self.file_index_offset = stream.read_uint()
		self.file_count = stream.read_uint()
		if self.context.version >= 20:
			self.triplet_count = stream.read_uint()
			self.triplet_offset = stream.read_uint()

		self.io_size = stream.tell() - self.io_start

	def write(self, stream):
		self.io_start = stream.tell()
		stream.write_uint(self.offset)
		stream.write_uint(self.unknown)
		stream.write_uint(self.mime_hash)
		stream.write_uint(self.mime_version)
		stream.write_uint(self.file_index_offset)
		stream.write_uint(self.file_count)
		if self.context.version >= 20:
			stream.write_uint(self.triplet_count)
			stream.write_uint(self.triplet_offset)

		self.io_size = stream.tell() - self.io_start

	def get_info_str(self):
		return f'MimeEntry [Size: {self.io_size}, Address: {self.io_start}] {self.name}'

	def get_fields_str(self):
		s = ''
		s += f'\n	* offset = {self.offset.__repr__()}'
		s += f'\n	* unknown = {self.unknown.__repr__()}'
		s += f'\n	* mime_hash = {self.mime_hash.__repr__()}'
		s += f'\n	* mime_version = {self.mime_version.__repr__()}'
		s += f'\n	* file_index_offset = {self.file_index_offset.__repr__()}'
		s += f'\n	* file_count = {self.file_count.__repr__()}'
		s += f'\n	* triplet_count = {self.triplet_count.__repr__()}'
		s += f'\n	* triplet_offset = {self.triplet_offset.__repr__()}'
		return s

	def __repr__(self):
		s = self.get_info_str()
		s += self.get_fields_str()
		s += '\n'
		return s

	def update_constants(self, ovl):
		"""Update the constants"""

		# update offset using the name buffer
		if is_jwe(ovl):
			constants = constants_jwe
		elif is_pz(ovl) or is_pz16(ovl):
			constants = constants_pz
		elif is_jwe2(ovl):
			constants = constants_jwe2
		else:
			raise ValueError(f"Unsupported game {get_game(ovl)}")
		self.name = constants.mimes_name[self.ext]
		self.mime_hash = constants.mimes_mime_hash[self.ext]
		self.mime_version = constants.mimes_mime_version[self.ext]

		# update triplets
		if is_pz16(ovl) or is_jwe2(ovl):
			triplet_grab = constants.mimes_triplets[self.ext]
			self.triplet_offset = len(ovl.triplets)
			self.triplet_count = len(triplet_grab)
			for triplet in triplet_grab:
				trip = Triplet(self.context)
				trip.a, trip.b, trip.c = triplet
				ovl.triplets.append(trip)

