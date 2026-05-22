from flask import Flask, request, jsonify, send_file
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
import os
import logging
import urllib3
import math
import random
import asyncio

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
main_key = "DRAGON-TEAM"

# الرابط السري لصور Free Fire
INFO_URL = "https://cdn.jsdelivr.net/gh/ShahGCreator/icon@main/PNG"

def fetch_player_info(uid):
    url = f'https://otman-info.vercel.app/player-info?uid={uid}'
    try:
        response = requests.get(url, timeout=15, verify=False)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Fetch error: {e}")
    return None

def fetch_image(image_url, size=None):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(image_url, timeout=15, verify=False, headers=headers)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content)).convert("RGBA")
            if size:
                img = img.resize(size, Image.Resampling.LANCZOS)
            return img
    except Exception as e:
        logger.error(f"Image fetch error: {e}")
    return None

def make_circle_with_border(image, size, border_color):
    """صورة دائرية مع إطار ملون"""
    if image is None:
        return None
    
    img = image.resize((size, size), Image.Resampling.LANCZOS)
    
    # قناع دائري
    mask = Image.new('L', (size, size), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, size, size), fill=255)
    
    # الصورة الدائرية
    circular = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    circular.paste(img, (0, 0), mask)
    
    # إضافة إطار ملون
    border = Image.new('RGBA', (size + 16, size + 16), (0, 0, 0, 0))
    draw_border = ImageDraw.Draw(border)
    
    # توهج خارجي
    for i in range(8, 0, -1):
        alpha = 50 - i * 5
        draw_border.ellipse((8 - i, 8 - i, size + 8 + i, size + 8 + i),
                           outline=(border_color[0], border_color[1], border_color[2], alpha), width=2)
    
    # الإطار الرئيسي
    draw_border.ellipse((8, 8, size + 8, size + 8), outline=border_color, width=4)
    draw_border.ellipse((12, 12, size + 4, size + 4), outline=(255, 255, 255, 150), width=1)
    
    border.paste(circular, (8, 8), circular)
    return border

def create_fancy_background():
    """خلفية فخمة متدرجة الألوان"""
    width, height = 1200, 1200
    img = Image.new('RGBA', (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    
    # تدرج لوني (بنفسجي إلى أزرق سماوي)
    for y in range(height):
        ratio = y / height
        r = int(40 + ratio * 60)
        g = int(10 + ratio * 80)
        b = int(70 + ratio * 150)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255), width=1)
    
    # دوائر زخرفية
    colors = [
        (255, 100, 100, 40), (100, 255, 100, 40), (100, 100, 255, 40),
        (255, 255, 100, 40), (255, 100, 255, 40), (100, 255, 255, 40)
    ]
    for i, color in enumerate(colors):
        r = 180 + i * 90
        draw.ellipse((width//2 - r, height//2 - r, width//2 + r, height//2 + r),
                    outline=color, width=3)
    
    # خطوط زخرفية
    for i in range(0, width, 60):
        draw.line([(i, 0), (i, height)], fill=(255, 255, 255, 15), width=1)
        draw.line([(0, i), (width, i)], fill=(255, 255, 255, 15), width=1)
    
    # نجوم
    for _ in range(150):
        x = random.randint(0, width)
        y = random.randint(0, height)
        intensity = random.randint(80, 255)
        draw.point((x, y), fill=(intensity, intensity, intensity, 255))
    
    return img

@app.route('/outfit-image', methods=['GET'])
def outfit_image():
    uid = request.args.get('uid')
    key = request.args.get('key')

    if not uid:
        return jsonify({'error': 'Missing uid'}), 400
    if key != main_key:
        return jsonify({'error': 'Invalid key'}), 403

    data = fetch_player_info(uid)
    if not data:
        return jsonify({'error': 'Failed to fetch player info'}), 500

    profile_info = data.get("profileInfo", {})
    clothes_ids = profile_info.get("clothes", [])
    equipped_skills = profile_info.get("equipedSkills", [])
    pet_id = data.get("petInfo", {}).get("id")
    weapon_id = data.get("basicInfo", {}).get("weaponSkinShows", [None])[0]
    player_name = data.get("basicInfo", {}).get("nickname", "WARRIOR")

    # ترتيب الملابس
    required_codes = ["211", "214", "203", "204", "205", "208"]
    fallback_ids = ["211000000", "214000000", "203000077", "204000345", "205000070", "208000000"]
    
    used_ids = set()
    outfit_images = []

    # جلب الصور (بدون threads متعددة لـ Vercel)
    for idx, code in enumerate(required_codes):
        matched = None
        for oid in clothes_ids:
            if str(oid).startswith(code) and oid not in used_ids:
                matched = oid
                used_ids.add(oid)
                break
        if matched is None:
            matched = fallback_ids[idx]
        url = f'{INFO_URL}/{matched}.png'
        img = fetch_image(url, size=(130, 130))
        outfit_images.append(img)

    # إنشاء الخلفية
    background = create_fancy_background()
    W, H = 1200, 1200
    draw = ImageDraw.Draw(background)

    # تحميل الخطوط
    try:
        title_font = ImageFont.truetype("arialbd.ttf", 55)
        big_font = ImageFont.truetype("arialbd.ttf", 38)
        name_font = ImageFont.truetype("arialbd.ttf", 32)
        small_font = ImageFont.truetype("arialbd.ttf", 20)
        watermark_font = ImageFont.truetype("arialbd.ttf", 28)
    except:
        title_font = ImageFont.load_default()
        big_font = ImageFont.load_default()
        name_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        watermark_font = ImageFont.load_default()

    # ===== واجهة المستخدم =====
    watermark = "⚡ DRAGONX1M@ ⚡"
    # ظل للخط
    for offset in range(4, 0, -1):
        draw.text((W//2 - 140 + offset, 25 + offset), watermark,
                 fill=(50, 50, 100, 120), font=watermark_font)
    draw.text((W//2 - 140, 25), watermark,
             fill=(255, 215, 0, 255), font=watermark_font)
    
    # خط زخرفي تحت الواجهة
    draw.line([(W//2 - 200, 65), (W//2 + 200, 65)], fill=(255, 215, 0, 200), width=2)

    # عنوان رئيسي
    title = "ELITE OUTFIT"
    for offset in range(3, 0, -1):
        draw.text((W//2 - 140 + offset, 85 + offset), title,
                 fill=(100, 100, 200, 100), font=title_font)
    draw.text((W//2 - 140, 85), title, fill=(0, 255, 255, 255), font=title_font)

    # إحداثيات الدوائر
    circles = [
        (250, 280, (0, 255, 255), "HELMET"),
        (250, 500, (255, 0, 255), "VISOR"),
        (250, 720, (255, 255, 0), "ARMOR"),
        (950, 280, (0, 255, 0), "LEG"),
        (950, 500, (255, 100, 0), "BOOTS"),
        (950, 720, (255, 0, 255), "PET"),
    ]

    # لصق الصور في الدوائر
    for idx, img in enumerate(outfit_images):
        if idx >= len(circles):
            break
        x, y, color, name = circles[idx]
        if img:
            circular = make_circle_with_border(img, 130, color)
            background.paste(circular, (x - 75, y - 75), circular)
        # اسم القطعة تحت الدائرة
        bbox = draw.textbbox((0, 0), name, font=small_font)
        text_w = bbox[2] - bbox[0]
        draw.text((x - text_w//2, y + 85), name, fill=color, font=small_font)

    # السلاح (دائرة في أسفل المنتصف)
    weapon_x, weapon_y = W//2, 950
    weapon_color = (255, 50, 100)
    if weapon_id:
        weapon_url = f'{INFO_URL}/weapon_{weapon_id}.png'
        weapon_img = fetch_image(weapon_url, size=(150, 90))
        if not weapon_img:
            weapon_url = f'{INFO_URL}/{weapon_id}.png'
            weapon_img = fetch_image(weapon_url, size=(150, 90))
        if weapon_img:
            weapon_border = Image.new('RGBA', (180, 120), (0, 0, 0, 0))
            wb_draw = ImageDraw.Draw(weapon_border)
            wb_draw.rectangle([(5, 5), (175, 115)], outline=weapon_color, width=4)
            wb_draw.rectangle([(10, 10), (170, 110)], outline=(255, 255, 255, 100), width=1)
            weapon_border.paste(weapon_img, (15, 15), weapon_img)
            background.paste(weapon_border, (weapon_x - 90, weapon_y - 60), weapon_border)
    
    draw.text((weapon_x - 30, weapon_y + 45), "WEAPON", fill=weapon_color, font=small_font)

    # الحيوان الأليف
    if pet_id:
        pet_url = f'{INFO_URL}/{pet_id}.png'
        pet_img = fetch_image(pet_url, size=(120, 120))
        if pet_img:
            pet_circle = make_circle_with_border(pet_img, 120, (255, 100, 200))
            background.paste(pet_circle, (950 - 68, 720 - 68), pet_circle)

    # صورة الـ Avatar الرئيسية
    avatar_id = "406"
    for skill in equipped_skills:
        if str(skill).endswith("06"):
            avatar_id = str(skill)
            break
    
    avatar_url = f'https://characteriroxmar.vercel.app/chars?id={avatar_id}'
    avatar_img = fetch_image(avatar_url, size=(340, 400))
    if avatar_img:
        ax = (W - avatar_img.width) // 2
        ay = 380
        background.paste(avatar_img, (ax, ay), avatar_img)
        draw.rectangle([ax - 10, ay - 10, ax + avatar_img.width + 10, ay + avatar_img.height + 10],
                      outline=(0, 255, 255, 200), width=4)
        for i in range(3):
            draw.rectangle([ax - 10 + i, ay - 10 + i, ax + avatar_img.width + 10 - i, ay + avatar_img.height + 10 - i],
                          outline=(255, 255, 255, 60), width=1)

    # اسم اللاعب
    name_text = f"🏆 {player_name.upper()} 🏆"
    for offset in range(3, 0, -1):
        draw.text((W//2 - len(name_text)*9 + offset, H - 85 + offset),
                 name_text, fill=(100, 100, 200, 120), font=name_font)
    draw.text((W//2 - len(name_text)*9, H - 85),
             name_text, fill=(255, 215, 0, 255), font=name_font)
    
    # خط زخرفي
    draw.line([(W//2 - 220, H - 50), (W//2 + 220, H - 50)], fill=(0, 255, 255, 200), width=3)
    draw.line([(W//2 - 210, H - 47), (W//2 + 210, H - 47)], fill=(255, 255, 255, 100), width=1)

    # تذييل صغير
    footer = "@DRAGONX1M"
    draw.text((W - 150, H - 30), footer, fill=(255, 255, 255, 150), font=small_font)

    # حفظ الصورة
    img_io = BytesIO()
    background.save(img_io, 'PNG')
    img_io.seek(0)
    
    logger.info("✅ Fancy Outfit Created!")
    return send_file(img_io, mimetype='image/png')

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': '✅ ELITE OUTFIT API',
        'creator': 'DRAGONX1M@',
        'endpoint': '/outfit-image?uid=ID&key=DRAGON-TEAM',
        'example': '/outfit-image?uid=2129828082&key=DRAGON-TEAM'
    })

# هذا مهم لـ Vercel - تصدير التطبيق
app = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)