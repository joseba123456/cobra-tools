import numpy
import typing
from generated.array import Array
from generated.context import ContextReference


class Type2:

	"""
	Sound SFX/Sound Voice
	02 -- identifier for Sound SFX section
	"""

	context = ContextReference()

	def set_defaults(self):
		self.length = 0
		self.sfx_id = 0
		self.const_a = 0
		self.const_b = 0
		self.didx_id = 0
		self.wem_length = 0
		self.extra = numpy.zeros((self.length - 17), dtype='byte')

	def read(self, stream):
		self.io_start = stream.tell()
		self.length = stream.read_uint()
		self.sfx_id = stream.read_uint()
		self.const_a = stream.read_uint()
		self.const_b = stream.read_byte()
		self.didx_id = stream.read_uint()
		self.wem_length = stream.read_uint()
		self.extra = stream.read_bytes((self.length - 17))

		self.io_size = stream.tell() - self.io_start

	def write(self, stream):
		self.io_start = stream.tell()
		stream.write_uint(self.length)
		stream.write_uint(self.sfx_id)
		stream.write_uint(self.const_a)
		stream.write_byte(self.const_b)
		stream.write_uint(self.didx_id)
		stream.write_uint(self.wem_length)
		stream.write_bytes(self.extra)

		self.io_size = stream.tell() - self.io_start

	def get_info_str(self):
		return f'Type2 [Size: {self.io_size}, Address: {self.io_start}] {self.name}'

	def get_fields_str(self):
		s = ''
		s += f'\n	* length = {self.length.__repr__()}'
		s += f'\n	* sfx_id = {self.sfx_id.__repr__()}'
		s += f'\n	* const_a = {self.const_a.__repr__()}'
		s += f'\n	* const_b = {self.const_b.__repr__()}'
		s += f'\n	* didx_id = {self.didx_id.__repr__()}'
		s += f'\n	* wem_length = {self.wem_length.__repr__()}'
		s += f'\n	* extra = {self.extra.__repr__()}'
		return s

	def __repr__(self):
		s = self.get_info_str()
		s += self.get_fields_str()
		s += '\n'
		return s

	def __init__(self, context, arg=None, template=None):
		self._context = context
		self.name = ''
		self.arg = arg
		self.template = template
		self.io_size = 0
		self.io_start = 0

		# length of this section
		self.length = 0

		# id of this Sound SFX object
		self.sfx_id = 0

		# ?
		self.const_a = 0

		# ?
		self.const_b = 0

		# ?
		self.didx_id = 0

		# ?
		self.wem_length = 0

		# include this here so that numpy doesn't choke
		# self.extra = numpy.zeros((self.length - 17), dtype='byte')

