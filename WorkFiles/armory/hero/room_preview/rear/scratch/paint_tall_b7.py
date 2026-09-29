"""b7: regenerate T_AK_HPaintingTall for the new paper (hero_backwall PAPER_W / PAPER_Z1 / IMG_Z0) into the test copy's
Textures (reads the live T_AK_HPainting_BC; writes ONLY into rear/Textures)."""
import sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\armory\hero")
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\armory")
import tex_backwall as TB

out = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\hero\room_preview\rear\Textures")
bc, orm, nrm = TB.painting_tall()
TB.TEX = out
TB.save("PaintingTall", bc, orm, nrm)
