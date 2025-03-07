import numpy
import typing
from generated.array import Array
from generated.context import ContextReference


class PCJointThing:

	"""
	8 bytes
	"""

	context = ContextReference()

	def __init__(self, context, arg=None, template=None):
		self.name = ''
		self._context = context
		self.arg = arg
		self.template = template
		self.io_size = 0
		self.io_start = 0

		# -1
		self.shorts = numpy.zeros((4), dtype='short')
		self.set_defaults()

	def set_defaults(self):
		self.shorts = numpy.zeros((4), dtype='short')

	def read(self, stream):
		self.io_start = stream.tell()
		self.shorts = stream.read_shorts((4))

		self.io_size = stream.tell() - self.io_start

	def write(self, stream):
		self.io_start = stream.tell()
		stream.write_shorts(self.shorts)

		self.io_size = stream.tell() - self.io_start

	def get_info_str(self):
		return f'PCJointThing [Size: {self.io_size}, Address: {self.io_start}] {self.name}'

	def get_fields_str(self):
		s = ''
		s += f'\n	* shorts = {self.shorts.__repr__()}'
		return s

	def __repr__(self):
		s = self.get_info_str()
		s += self.get_fields_str()
		s += '\n'
		return s
