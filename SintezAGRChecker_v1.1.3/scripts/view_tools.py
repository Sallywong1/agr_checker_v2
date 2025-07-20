import bpy

from . import check_highpoly_lowpoly

def show_glass_as_grid():
    im_name = "AGR_Glass_ColorGrid"
    image = bpy.data.images.get(im_name)
    if not image:
        bpy.ops.image.new(
            name=im_name,
            width=1024,
            height=1024,
            color=(0.0, 0.0, 0.0, 1.0),
            alpha=True,
            generated_type='COLOR_GRID', # BLANK, COLOR_GRID
            float=False,
            use_stereo_3d=False,
            tiled=False
        )
        image = bpy.data.images.get(im_name)

    for obj in bpy.data.objects:
        if obj.type == 'MESH' and "glass" in obj.name.lower():
            for mat in obj.data.materials:
                bsdf = check_highpoly_lowpoly.CheckUtils.get_bsdf(mat)
                if not bsdf:
                    continue

                texture_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                texture_node.image = image

                mat.node_tree.links.new(texture_node.outputs[0], bsdf.inputs[0])
                bsdf.inputs[4].default_value = 1

def show_glass_as_normal():
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and "glass" in obj.name.lower():
            for mat in obj.data.materials:
                bsdf = check_highpoly_lowpoly.CheckUtils.get_bsdf(mat)
                if not bsdf:
                    continue
                for node in mat.node_tree.nodes:
                    if node.bl_static_type == 'TEX_IMAGE':
                        mat.node_tree.nodes.remove(node)
                # tex_node = bsdf.inputs[0].links[0].from_node
                # mat.node_tree.nodes.remove(tex_node)

                bsdf.inputs[4].default_value = 0.4

def all_glass_gray():
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and "glass" in obj.name.lower():
            for mat in obj.data.materials:
                bsdf = check_highpoly_lowpoly.CheckUtils.get_bsdf(mat)
                if not bsdf:
                    continue
                bsdf.inputs[0].default_value = [1.0, 1.0, 1.0, 1.0]
                bsdf.inputs[1].default_value = 0.6
                bsdf.inputs[2].default_value = 0
                bsdf.inputs[4].default_value = 0.4