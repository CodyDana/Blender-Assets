import bpy, numpy as np
i = bpy.data.images.load('C:/Users/Cody/Desktop/Blender_Projects/References/BlackHat/blackhat_guide.png'); i.colorspace_settings.name='Non-Color'
x = np.array(i.pixels[:], dtype=np.float32).reshape(i.size[1], i.size[0], i.channels)[::-1]
b = x[:100, :, :3].reshape(-1, 3); print('BG top100 mean', b.mean(0)*255, 'std', b.std(0)*255, 'min', b.min(0)*255, 'max', b.max(0)*255)
b = x[560:, :300, :3].reshape(-1, 3); print('BG bottomleft mean', b.mean(0)*255, 'std', b.std(0)*255, 'min', b.min(0)*255, 'max', b.max(0)*255)
