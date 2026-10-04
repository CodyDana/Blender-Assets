from PIL import Image
import numpy as np
S='C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects--claude-worktrees-cardshop-build-integration-5227b4/24ade915-2f01-4a92-a0c7-405f2d922327/scratchpad/ref.png'
im=np.asarray(Image.open(S).convert('RGB')).astype(int)
for y in range(100,340,3):
    print(y, im[y,505:520].mean(0).astype(int), im[y,465:475].mean(0).astype(int))
