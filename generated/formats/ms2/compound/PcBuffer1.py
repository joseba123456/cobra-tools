import numpy
import typing
from generated.array import Array
from generated.context import ContextReference
from generated.formats.ms2.compound.ModelInfo import ModelInfo
from generated.formats.ms2.compound.Ms2BufferInfoPC import Ms2BufferInfoPC
from generated.formats.ms2.compound.Ms2BufferInfoZT import Ms2BufferInfoZT


class PcBuffer1:

	context = ContextReference()

	def __init__(self, context, arg=None, template=None):
		self.name = ''
		self._context = context
		self.arg = arg
		self.template = template
		self.io_size = 0
		self.io_start = 0
		self.buffer_info_pc = Ms2BufferInfoZT(self.context, self.arg, None)
		self.buffer_info_pc = Ms2BufferInfoPC(self.context, None, None)
		self.model_infos = Array(self.context)
		self.set_defaults()

	def set_defaults(self):
		if self.context.version == 13:
			self.buffer_info_pc = Ms2BufferInfoZT(self.context, self.arg, None)
		if self.context.version == 32:
			self.buffer_info_pc = Ms2BufferInfoPC(self.context, None, None)
		self.model_infos = Array(self.context)

	def read(self, stream):
		self.io_start = stream.tell()
		if self.context.version == 13:
			self.buffer_info_pc = stream.read_type(Ms2BufferInfoZT, (self.context, self.arg, None))
		if self.context.version == 32:
			self.buffer_info_pc = stream.read_type(Ms2BufferInfoPC, (self.context, None, None))
		self.model_infos.read(stream, ModelInfo, self.arg.general_info.mdl_2_count, None)

		self.io_size = stream.tell() - self.io_start

	def write(self, stream):
		self.io_start = stream.tell()
		if self.context.version == 13:
			stream.write_type(self.buffer_info_pc)
		if self.context.version == 32:
			stream.write_type(self.buffer_info_pc)
		self.model_infos.write(stream, ModelInfo, self.arg.general_info.mdl_2_count, None)

		self.io_size = stream.tell() - self.io_start

	def get_info_str(self):
		return f'PcBuffer1 [Size: {self.io_size}, Address: {self.io_start}] {self.name}'

	def get_fields_str(self):
		s = ''
		s += f'\n	* buffer_info_pc = {self.buffer_info_pc.__repr__()}'
		s += f'\n	* model_infos = {self.model_infos.__repr__()}'
		return s

	def __repr__(self):
		s = self.get_info_str()
		s += self.get_fields_str()
		s += '\n'
		return s
