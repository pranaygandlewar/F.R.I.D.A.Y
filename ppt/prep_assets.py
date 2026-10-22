import os
import shutil
from PIL import Image

BASE_DIR = r"d:\Mark-LV-main\ppt"
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

USER_UPLOADED_DIR = r"C:\Users\m\.gemini\antigravity-ide\brain\2c756c9f-f923-48f1-94d3-05c7b30c7335\.user_uploaded"

src_hud_ring = os.path.join(USER_UPLOADED_DIR, "media_1791751746382.png")
src_hud_face = os.path.join(USER_UPLOADED_DIR, "media_1791751769665.png")
src_ide_banner = os.path.join(USER_UPLOADED_DIR, "media_1791751802240.png")
src_ide_edith = os.path.join(USER_UPLOADED_DIR, "media_1791751833868.png")

# 1. Copy raw screenshots
shutil.copy2(src_hud_ring, os.path.join(ASSETS_DIR, "hud_ring_full.png"))
shutil.copy2(src_hud_face, os.path.join(ASSETS_DIR, "hud_face_full.png"))
shutil.copy2(src_ide_banner, os.path.join(ASSETS_DIR, "ide_banner_full.png"))
shutil.copy2(src_ide_edith, os.path.join(ASSETS_DIR, "ide_edith_full.png"))

print("Copied full screenshots.")

# 2. Crop Clean Header Banner from ide_banner_full (1024, 640)
im_banner = Image.open(src_ide_banner)
# In screenshot 3, the header banner card is in the editor pane.
# Let's inspect bounding box or crop the central banner.
# The editor starts around x=140 to 980, y=130 to 390
# Let's crop exactly the card:
crop_banner = im_banner.crop((150, 135, 985, 385))
crop_banner.save(os.path.join(ASSETS_DIR, "header_banner_clean.png"))

# 3. Crop Clean EDITH graphic from ide_edith_full (1024, 640)
im_edith = Image.open(src_ide_edith)
# The EDITH diagram is inside the editor pane:
crop_edith = im_edith.crop((145, 110, 988, 435))
crop_edith.save(os.path.join(ASSETS_DIR, "edith_security_clean.png"))

# 4. Crop 3D Avatar face from hud_face_full (1024, 761)
im_face = Image.open(src_hud_face)
# Central face is around x=200 to 650, y=110 to 520
crop_face = im_face.crop((230, 120, 620, 520))
crop_face.save(os.path.join(ASSETS_DIR, "avatar_3d_face_crop.png"))

# 5. Crop Arc Reactor circle from hud_ring_full (1024, 761)
im_ring = Image.open(src_hud_ring)
crop_ring = im_ring.crop((150, 110, 650, 580))
crop_ring.save(os.path.join(ASSETS_DIR, "arc_reactor_crop.png"))

# 6. Crop Activity Log / Conversation
crop_log = im_face.crop((655, 115, 995, 360))
crop_log.save(os.path.join(ASSETS_DIR, "hud_activity_log_crop.png"))

# 7. Crop News Widget
crop_news = im_face.crop((150, 660, 645, 750))
crop_news.save(os.path.join(ASSETS_DIR, "hud_news_crop.png"))

print("Cropped assets generated successfully.")
