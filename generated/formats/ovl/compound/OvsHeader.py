import numpy
import typing
from generated.array import Array
from generated.context import ContextReference
from generated.formats.ovl.compound.BufferEntry import BufferEntry
from generated.formats.ovl.compound.BufferGroup import BufferGroup
from generated.formats.ovl.compound.DataEntry import DataEntry
from generated.formats.ovl.compound.Fragment import Fragment
from generated.formats.ovl.compound.MemPool import MemPool
from generated.formats.ovl.compound.PoolGroup import PoolGroup
from generated.formats.ovl.compound.SetHeader import SetHeader
from generated.formats.ovl.compound.SizedStringEntry import SizedStringEntry


class OvsHeader:

	"""
	Description of one archive's content
	"""

	context = ContextReference()

	def __init__(self, context, arg=None, template=None):
		self.name = ''
		self._context = context
		self.arg = arg
		self.template = template
		self.io_size = 0
		self.io_start = 0
		self.pool_groups = Array(self.context)
		self.pools = Array(self.context)
		self.data_entries = Array(self.context)
		self.buffer_entries = Array(self.context)
		self.buffer_groups = Array(self.context)
		self.sized_str_entries = Array(self.context)
		self.fragments = Array(self.context)
		self.set_header = SetHeader(self.context, None, None)
		self.set_defaults()

	def set_defaults(self):
		self.pool_groups = Array(self.context)
		self.pools = Array(self.context)
		self.data_entries = Array(self.context)
		self.buffer_entries = Array(self.context)
		self.buffer_groups = Array(self.context)
		self.sized_str_entries = Array(self.context)
		self.fragments = Array(self.context)
		self.set_header = SetHeader(self.context, None, None)

	def read(self, stream):
		self.io_start = stream.tell()
		self.pool_groups.read(stream, PoolGroup, self.arg.num_pool_groups, None)
		self.pools.read(stream, MemPool, self.arg.num_pools, None)
		self.data_entries.read(stream, DataEntry, self.arg.num_datas, None)
		self.buffer_entries.read(stream, BufferEntry, self.arg.num_buffers, None)
		self.buffer_groups.read(stream, BufferGroup, self.arg.num_buffer_groups, None)
		self.sized_str_entries.read(stream, SizedStringEntry, self.arg.num_files, None)
		self.fragments.read(stream, Fragment, self.arg.num_fragments, None)
		self.set_header = stream.read_type(SetHeader, (self.context, None, None))

		self.io_size = stream.tell() - self.io_start

	def write(self, stream):
		self.io_start = stream.tell()
		self.pool_groups.write(stream, PoolGroup, self.arg.num_pool_groups, None)
		self.pools.write(stream, MemPool, self.arg.num_pools, None)
		self.data_entries.write(stream, DataEntry, self.arg.num_datas, None)
		self.buffer_entries.write(stream, BufferEntry, self.arg.num_buffers, None)
		self.buffer_groups.write(stream, BufferGroup, self.arg.num_buffer_groups, None)
		self.sized_str_entries.write(stream, SizedStringEntry, self.arg.num_files, None)
		self.fragments.write(stream, Fragment, self.arg.num_fragments, None)
		stream.write_type(self.set_header)

		self.io_size = stream.tell() - self.io_start

	def get_info_str(self):
		return f'OvsHeader [Size: {self.io_size}, Address: {self.io_start}] {self.name}'

	def get_fields_str(self):
		s = ''
		s += f'\n	* pool_groups = {self.pool_groups.__repr__()}'
		s += f'\n	* pools = {self.pools.__repr__()}'
		s += f'\n	* data_entries = {self.data_entries.__repr__()}'
		s += f'\n	* buffer_entries = {self.buffer_entries.__repr__()}'
		s += f'\n	* buffer_groups = {self.buffer_groups.__repr__()}'
		s += f'\n	* sized_str_entries = {self.sized_str_entries.__repr__()}'
		s += f'\n	* fragments = {self.fragments.__repr__()}'
		s += f'\n	* set_header = {self.set_header.__repr__()}'
		return s

	def __repr__(self):
		s = self.get_info_str()
		s += self.get_fields_str()
		s += '\n'
		return s
