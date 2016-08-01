#coding:utf8

import nxloader
import collada as cld
import numpy


def Convert(gim_file):
	mesh_data = nxloader.LoadMeshData(gim_file)

	mesh = cld.Collada()
	effect = cld.material.Effect("effect0", [], "phong", diffuse=(1,0,0), specular=(0,1,0))
	mat = cld.material.Material("material0", "mymaterial", effect)
	mesh.effects.append(effect)
	mesh.materials.append(mat)

	vert_src = cld.source.FloatSource("cubeverts", numpy.array(mesh_data.vertex_data.vb), ('X', 'Y', 'Z'))
	normal_src = cld.source.FloatSource("cubenormals", numpy.array(mesh_data.vertex_data.nb), ('X', 'Y', 'Z'))
	geom = cld.geometry.Geometry(mesh, "geometry0", "mycube", [vert_src, normal_src])
	input_list = cld.source.InputList()
	input_list.addInput(0, 'VERTEX', "#cubeverts")
	input_list.addInput(1, 'NORMAL', "#cubenormals")

	vertex_normal_indices = []
	for i in mesh_data.vertex_data.ib:
		vertex_normal_indices.append(i)
		vertex_normal_indices.append(i)

	# vcounts = numpy.array([3]*12)
	indices = numpy.array(vertex_normal_indices)
	# triset = geom.createPolylist(indices, vcounts, input_list, "materialref")
	triset = geom.createTriangleSet(indices, input_list, "materialref")
	geom.primitives.append(triset)
	mesh.geometries.append(geom)
	matnode = cld.scene.MaterialNode("materialref", mat, inputs=[])
	geomnode = cld.scene.GeometryNode(geom, [matnode])
	node = cld.scene.Node("node0", children=[geomnode])
	myscene = cld.scene.Scene("myscene", [node])
	mesh.scenes.append(myscene)
	mesh.scene = myscene
	mesh.write('tree.dae')


def TestCollada():
	mesh = cld.Collada()

	effect = cld.material.Effect("effect0", [], "phong", diffuse=(1,0,0), specular=(0,1,0))
	mat = cld.material.Material("material0", "mymaterial", effect)
	mesh.effects.append(effect)
	mesh.materials.append(mat)

	import numpy
	vert_floats = [-50,50,50,50,50,50,-50,-50,50,50, -50,50,-50,50,-50,50,50,-50,-50,-50,-50,50,-50,-50]
	normal_floats = [0,0,1,0,0,1,0,0,1,0,0,1,0,1,0,
		0,1,0,0,1,0,0,1,0,0,-1,0,0,-1,0,0,-1,0,0,-1,0,-1,0,0,
		-1,0,0,-1,0,0,-1,0,0,1,0,0,1,0,0,1,0,0,1,0,0,0,0,-1,
		0,0,-1,0,0,-1,0,0,-1]
	vert_src = cld.source.FloatSource("cubeverts", numpy.array(vert_floats), ('X', 'Y', 'Z'))
	normal_src = cld.source.FloatSource("cubenormals", numpy.array(normal_floats), ('X', 'Y', 'Z'))

	geom = cld.geometry.Geometry(mesh, "geometry0", "mycube", [vert_src, normal_src])
	input_list = cld.source.InputList()
	input_list.addInput(0, 'VERTEX', "#cubeverts")
	input_list.addInput(1, 'NORMAL', "#cubenormals")
	indices = numpy.array([0,0,2,1,3,2,0,0,3,2,1,3,0,4,1,5,5,6,0,
		4,5,6,4,7,6,8,7,9,3,10,6,8,3,10,2,11,0,12,
		4,13,6,14,0,12,6,14,2,15,3,16,7,17,5,18,3,
		16,5,18,1,19,5,20,7,21,6,22,5,20,6,22,4,23])
	triset = geom.createTriangleSet(indices, input_list, "materialref")
	geom.primitives.append(triset)
	mesh.geometries.append(geom)
	matnode = cld.scene.MaterialNode("materialref", mat, inputs=[])
	geomnode = cld.scene.GeometryNode(geom, [matnode])
	node = cld.scene.Node("node0", children=[geomnode])
	myscene = cld.scene.Scene("myscene", [node])
	mesh.scenes.append(myscene)
	mesh.scene = myscene
	mesh.write('test.dae')

	
if __name__ == '__main__':
	Convert(r'E:\H35\trunk\client\res\model\fb\heiwhdch\zw\fb_haidc_tree001_1221.gim')
	# Convert(r'E:\H35\trunk\client\res\model\col_model\redbox.gim')
	# TestCollada()