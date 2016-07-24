#coding: utf8
import struct
import os
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

MESH_FILE_MARK = 0xbbc88034
GIM_FILE_MARK = 0x4d494752
MEX_FILE_MARK = 0x58454d4e
ANIMS_FILE_MARK = 0x53494752

GIM_FILE_TYPE_NONE = -1
GIM_FILE_TYPE_GENERAL = 0
GIM_FILE_TYPE_SKELETAL = 1

MODEL_TYPE_NONE = -1
MODEL_TYPE_GENERAL = 0
MODEL_TYPE_SKELETAL = 1
MODEL_TYPE_VERTEXANIM = 2

MESH_VERSION_PATCH_MASK = 0x00FFFFFF
MESH_VERSION_PATCH_SHIFT = 24
MESH_VERSION_PATCH_FLOAT16 = 0x01

GIM_FILE_VERSION = 0x50002

MESH_DATA_TYPE_COLLISION = 0
MESH_DATA_TYPE_OCCLUDEE = 1
MESH_DATA_TYPE_OCCLUDER = 2
MESH_DATA_TYPE_PICK = 3
MESH_DATA_TYPE_LOD = 4

class FileHeader(object):
	fmt = "II"
	def __init__(self, up):
		self.file_mark = up[0]
		self.version = up[1]

def LoadMeshData(gim_file):
	buff = open(gim_file, "r").read(4)
	mask = struct.unpack('I', buff)[0]

	def ReadMeshFile(mesh_file):
		version = 0
		mesh_type = -1
		with open(mesh_file, "rb") as f:
			buff = f.read()
			ptr = 0
			sz = struct.calcsize(FileHeader.fmt)
			header = FileHeader(struct.unpack(FileHeader.fmt, buff[:sz]))
			ptr += sz
			mesh_type = struct.unpack("H", buff[ptr:(ptr+2)])[0]
			version = header.version
		return version, mesh_type

	if mask == GIM_FILE_MARK:
		version, mesh_type = ReadMeshFile(gim_file)
	else:
		tree = ET.ElementTree(file=gim_file)
		root = tree.getroot()
		mesh_file = root.get('Mesh')
		if not mesh_file:
			mesh_file = gim_file.replace('.gim', '.mesh')
		version, mesh_type = ReadMeshFile(mesh_file)

	gim_type = GIM_FILE_TYPE_GENERAL
	if mesh_type in [MODEL_TYPE_GENERAL, MODEL_TYPE_VERTEXANIM]:
		gim_type = GIM_FILE_TYPE_GENERAL
	elif mesh_type == MODEL_TYPE_SKELETAL:
		gim_type = GIM_FILE_TYPE_SKELETAL
	elif mesh_type == MODEL_TYPE_NONE:
		gim_type = GIM_FILE_TYPE_NONE

	if gim_type == GIM_FILE_TYPE_GENERAL:
		mesh_data = MeshData()
	elif gim_type == GIM_FILE_TYPE_SKELETAL:
		mesh_data = MeshSkeletalData()
	else:
		raise RuntimeError("Unknown gim type")

	mesh_data.version = version
	mesh_data.filename = gim_file
	#mesh_data.name_str_id = StringID(gim_file)

	if not mesh_data.Load():
		raise RuntimeError("Load mesh failed.")

	return mesh_data

class SubMeshData(object):
	def __init__(self):
		self.sub_mesh_name = ""
		self.material_name = ""
		self.bounding_info = None
		self.uv_chnl_count = 0

		self.has_color = False
		self.has_tex_trans = False
		self.has_tex_anim = False

		self.unique_slot_id = None
		self.mtl_id = None


class SubMeshVData(object):
	def __init__(self):
		self.v_start = 0
		self.tri_start = 0
		self.v_count = 0
		self.tri_count = 0
		self.uv_chnl_count = 0
		self.has_color = False

class Point2F(object):
	def __init__(self):
		self.x = 0
		self.y = 0

class MeshVertexData(object):
	v_sz = 12    #sizeof(Vector3)
	tri_sz = 6	 #sizeof(Word)*3
	uv_sz = 8	#sizeof(Point2F)
	c_sz = 4	#sizeof(DWord)
	def __init__(self):
		self.sub_v_data = []
		self.sub_count = 0
		self.lod_new_v = 0
		self.all_v_count = 0
		self.v_count = 0
		self.tri_count = 0
		self.uv_chnl_count = 0
		self.has_color = False
		self.has_tangent = False

		self.vb = []
		self.nb = []
		self.ib = []

		self.tb = []
		self.cb = []
		self.tangent = []

		self.tcb_stride = 0
		self.sub_bone_count = []


	def ReadDataNew(self, fp, version, morph_key_count, patch_version):
		v_start = 0
		tri_start = 0
		for i in xrange(self.sub_count):
			svd = SubMeshVData()
			svd.v_start = v_start
			svd.tri_start = tri_start
			svd.v_count = struct.unpack('I', fp.read(4))[0]
			svd.tri_count = struct.unpack('I', fp.read(4))[0]
			svd.uv_chnl_count = struct.unpack('B', fp.read(1))[0]
			svd.has_color = struct.unpack('B', fp.read(1))[0]

			self.sub_v_data.append(svd)

			v_start += svd.v_count
			tri_start += svd.tri_count

		self.lod_new_v = struct.unpack('H', fp.read(2))[0]
		self.v_count = struct.unpack('I', fp.read(4))[0]
		self.tri_count = struct.unpack('I', fp.read(4))[0]

		has_color_data = False
		self.has_color = True
		self.uv_chnl_count = 0
		for i in xrange(self.sub_count):
			if self.sub_v_data[i].uv_chnl_count > self.uv_chnl_count:
				self.uv_chnl_count = self.sub_v_data[i].uv_chnl_count
			has_color_data = has_color_data or self.sub_v_data[i].has_color

		v_len = self.v_count * self.v_sz
		tri_len = self.tri_count * self.tri_sz

		key_count = 1
		if morph_key_count > 1:
			key_count = morph_key_count

		self.all_v_count = key_count * self.v_count
		self.vb = []
		self.nb = []
		self.ib = []
		for i in xrange(self.uv_chnl_count):
			self.tb.append(Point2F())

		if self.has_color:
			self.cb = []
			for i in xrange(self.v_count):
				self.cb.append(0xff)

		if not self.lod_new_v:
			return

		if patch_version == 0x01:
			for i in xrange(self.v_count*3):
				raise NotImplementedError("TODO")  #TODO
		else:
			self.vb = []
			for i in xrange(self.v_count):
				(x, y, z) = struct.unpack('fff', fp.read(12))
				self.vb.extend([x,y,z])

		self.nb = []
		for i in xrange(self.v_count):
			(x, y, z) = struct.unpack('fff', fp.read(12))
			self.nb.extend([x,y,z])

		has_tangent = False
		if version > 0x50001:
			has_tangent = (struct.unpack('H', fp.read(2))[0] != 0)

		if has_tangent:
			self.tangent = []
			for i in xrange(self.v_count):
				(x, y, z) = struct.unpack('fff', fp.read(12))
				self.tangent.extend([x,y,z])

		self.ib = []
		for i in xrange(self.tri_count*3):
			self.ib.append(struct.unpack('H', fp.read(2))[0])

		if patch_version == 0x01:
			raise NotImplementedError("TODO")  # TODO
		else:
			if self.uv_chnl_count > 0:
				for i in xrange(self.sub_count):
					if self.sub_v_data[i].uv_chnl_count > 0:
						v_start = self.sub_v_data[i].v_start
						v_count = self.sub_v_data[i].v_count
						for c in xrange(self.sub_v_data[i].uv_chnl_count):
							# TODO:
							fp.read(v_count*self.uv_sz)
		
		if has_color_data:
			for i in xrange(self.sub_count):
				if self.sub_v_data[i].has_color:
					v_start = self.sub_v_data[i].v_start
					v_count = self.sub_v_data[i].v_count
					fp.read(v_count*self.c_sz)  # TODO:

		self.tcb_stride = 0
		if self.has_color:
			self.tcb_stride += self.c_sz

		for c in xrange(self.uv_chnl_count):
			self.tcb_stride += self.uv_sz

		if morph_key_count <= 1:
			return

		v_len = self.v_count * self.v_sz
		for i in xrange(1, morph_key_count):
			fp.read(v_len)	  #TODO
			fp.read(v_len)    #TODO

		return


class MorphData(object):
	pass

class DataPair(object):
	fmt = "ih"
	def __init__(self, up):
		self.type = up[0]
		self.block_idx = up[1]

class DataShareTable(object):
	def __init__(self):
		self.data_pairs = []
		self.block_infos = []

	def ReadData(self, fp):
		block_count = struct.unpack('h', fp.read(2))[0]
		self.block_infos = []
		for i in xrange(block_count):
			self.block_infos.append(struct.unpack('I', fp.read(4))[0])

		pair_count = struct.unpack('h', fp.read(2))[0]
		self.data_pairs = []
		for i in xrange(pair_count):
			buf = fp.read(struct.calcsize(DataPair.fmt))
			self.data_pairs.append(DataPair(struct.unpack(DataPair.fmt, buf)))

MAX_BONE_REF_V = 4			# 顶点关联的最大骨骼节点数
class OriginalData(object):
	def __init__(self):
		pass

	def ReadDataNew(self, fp):
		self.vb_count = struct.unpack('I', fp.read(4))[0]
		if self.vb_count != 0:
			self.vb = []
			for i in xrange(self.vb_count):
				(x, y, z) = struct.unpack('fff', fp.read(12))
				self.vb.append((x,y,z))

		self.ib_count = struct.unpack('I', fp.read(4))[0]
		if self.ib_count != 0:
			self.ib = []
			for i in xrange(self.ib_count):
				self.ib.append(struct.unpack('H', fp.read(2))[0])

		self.cb_count = struct.unpack('I', fp.read(4))[0]
		if self.cb_count != 0:
			self.cb = []
			for i in xrange(self.cb_count):
				self.cb.append(struct.unpack('I', fp.read(4))[0])
				#self.cb[i] = ToDeviceColor(self.cb[i])

		self.has_skin = struct.unpack('b', fp.read(1))[0]
		if self.has_skin and self.vb_count != 0:
			length = self.vb_count * MAX_BONE_REF_V
			self.ref_bones = struct.unpack('B%d'%length, fp.read(length))
			length = self.vb_count * MAX_BONE_REF_V
			self.bone_weights = struct.unpack('f%d'%length, fp.read(4*length))

class MeshData(object):

	def __init__(self):
		self.filename = None
		self.patch_version = None
		self.version = None
		self.gim_doc = None

		self.vertex_data = None
		self.morph_data = None
		self.track_data = None

		self.data_table = DataShareTable()

	def LoadOld(self):
		pass

	def Load(self):
		self.patch_version = (self.version >> MESH_VERSION_PATCH_SHIFT) & 0xFF
		self.version = self.version & MESH_VERSION_PATCH_MASK
		if self.version > GIM_FILE_VERSION:
			raise RuntimeError("gim file version is too new")
		if self.version < 0x30018:
			raise RuntimeError("gim file version too old")

		if self.version == 0x30018:
			self.LoadOld()

		self.gim_doc = ET.ElementTree(file=self.filename).getroot()

		self.ReadGimFile(self.gim_doc)

		mesh_file = self.gim_doc.get('Mesh')
		if not mesh_file:
			mesh_file = self.filename.replace('.gim', '.mesh')

		self.ReadMeshFile(mesh_file, self.gim_doc)

		return True


	def ReadGimFile(self, gim_doc):
		if not self.ReadGimCommon(gim_doc):
			return False

		self.ReadLogicData(gim_doc)

		self.vertex_data = MeshVertexData()
		self.vertex_data.sub_count = self.sub_count
		self.vertex_data.sub_v_data = []

		self.ReadFileExtra(gim_doc)

	def ReadLogicData(self, gim_doc):
		pass

	def ReadFileExtra(self, gim_doc):
		pass

	def ReadMeshFile(self, mesh_file, gim_doc):
		table_offset = 0
		with open(mesh_file, 'rb') as f:
			self.ReadMeshHeader(f)
			self.ReadAnimDataNew(f)
			self.ReadBoundingData(f)
			table_offset = struct.unpack('I', f.read(4))[0]

		with open(mesh_file, 'rb') as f:
			self.ReadVertexData(f, table_offset)

	def ReadMeshHeader(self, fp):
		fp.seek(struct.calcsize(FileHeader.fmt), 1)	#seek from current position
		fp.seek(2, 1)  #seek by a Word

	def ReadAnimDataNew(self, fp):
		has_morph_data = struct.unpack('b', fp.read(1))[0]
		if has_morph_data:
			self.morph_data = MorphData()
			self.morph_data.ReadDataNew(fp)
			self.bi_key_count = self.morph_data.GetKeyCount()

		has_track_data = struct.unpack('b', fp.read(1))[0]
		if has_track_data:
			self.track_data = []
			#TODO: read track data
			raise NotImplementedError("TODO")

	def ReadBoundingData(self, fp):
		if not self.morph_data and not self.track_data:
			return
		if self.version >= 0x50002:
			return
		for i in xrange(self.bi_key_count):
			#TODO: skip BoundingInfo
			fp.seek(0, 1)
			fp.seek(0*self.sub_count, 1)

	def ReadVertexData(self, fp, table_offset):
		fp.seek(table_offset, 0)  #seek from start
		self.data_table.ReadData(fp)

		lod_count = 0
		for dp in self.data_table.data_pairs:
			if dp.type == MESH_DATA_TYPE_LOD:
				lod_count += 1

		block_count = len(self.data_table.block_infos)
		offset = self.data_table.block_infos[0]
		fp.seek(offset)  #seek from start
		self.ReadLodVertexData(fp)

		#od_count = block_count - lod_count
		self.orig_data_vec = [OriginalData(),]*(block_count-lod_count)
		for i in xrange(lod_count, block_count):
			offset = self.data_table.block_infos[i]
			fp.seek(offset, 0)
			od = self.orig_data_vec[i-lod_count]
			od.ReadDataNew(fp)

	def ReadLodVertexData(self, fp):
		morph_key_count = 0
		if self.morph_data:
			morph_key_count = self.morph_data.key_times.GetKeyCount()
			if self.morph_data.only_trans:
				morph_key_count = 1
		self.vertex_data.ReadDataNew(fp, self.version, morph_key_count, self.patch_version)

	def ReadGimCommon(self, gim_doc):
		self.no_compatible_mask = gim_doc.get('CompatibleMask')
		self.has_alpha_sub = False
		self.tri_sort_method = gim_doc.get('TriSortMethod')
		self.tangent_enable = gim_doc.get('TangentEnable')
		self.enable_anim_accum = gim_doc.get('AnimAccumEnable')
		self.hw_instancing_enable = gim_doc.get('HwInstancingEnable')
		self.pre_z_alpha_blend = gim_doc.get('PreZAlphaBlend')
		self.dynamic_merge_enable = gim_doc.get('DynamicMergeEnable')
		self.bounding_info = gim_doc.get('BoundingInfo')

		sub_meshes = gim_doc.find('SubMesh')
		self.sub_count = len(sub_meshes)

		if self.sub_count <= 0:
			return False

		for sm in sub_meshes:
			sub_data = SubMeshData()
			sub_data.sub_mesh_name = sm.get('Name')
			sub_data.mtl_id = sm.get('MtlSlotIdx')
			self.has_slot = True
			if not sub_data.mtl_id:
				sub_data.mtl_id = sm.get('MtlIdx')
				self.has_slot = False
			sub_data.unique_slot_id = sm.get('UniqueMtlValue')
			sub_data.bi_center = sm.get('BoundingCenter')
			sub_data.bi_half = sm.get('BoundingHalf')
			sub_data.bounding_info = sm.get('BoundingInfo')

		return True


class MeshSkeletalData(object):
	pass


if __name__ == "__main__":
	pass
