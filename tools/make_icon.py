from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
p=Path(r"D:\code\phongthan_proxy_manager\assets"); p.mkdir(exist_ok=True)
img=Image.new("RGBA",(256,256),(24,32,52,255))
d=ImageDraw.Draw(img)
d.rounded_rectangle((18,18,238,238),radius=42,fill=(45,96,160,255),outline=(220,235,255,255),width=8)
try:
    font=ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf",92)
except:
    font=ImageFont.load_default()
text="PT"
box=d.textbbox((0,0),text,font=font)
x=(256-(box[2]-box[0]))//2
y=(256-(box[3]-box[1]))//2-8
d.text((x,y),text,font=font,fill=(255,255,255,255))
img.save(p/"app.ico",sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
print(p/"app.ico")
