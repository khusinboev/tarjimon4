import asyncio, datetime, os
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


async def save_timetable():
    group_name = "MMF 2/56-24 MexM (o'z)"
    base_name = "56-24"
    save_dir = "./timetables"
    os.makedirs(save_dir, exist_ok=True)
    svg_path = f"{save_dir}/{base_name}.svg"
    # --- 2. Yangi SVG yuklab olish ---
    if os.path.exists(svg_path):
        return svg_path
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(device_scale_factor=3)
        await page.goto("https://tdtu.edupage.org/timetable/", timeout=90000)

        await page.click("span[title='Классы']")
        await page.wait_for_selector("li a")

        elements = await page.query_selector_all("li a")
        for el in elements:
            if (await el.inner_text()).strip() == group_name:
                await el.click()
                break

        await page.wait_for_selector("svg")
        await page.wait_for_timeout(2000)

        svg_element = await page.query_selector("svg")
        svg_content = await svg_element.evaluate("(el) => el.outerHTML")

        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        await browser.close()
    print(f"[OK] Yangi SVG saqlandi: {svg_path}")
    return svg_path


def get_daily_timetable(svg_path):
    """
    Hozirgi kunlik dars jadvalini matn shaklida qaytaradi.
    Bir vaqt oralig'ida ikkita dars bo'lsa, ikkalasini ham ko'rsatadi.
    """
    if not os.path.exists(svg_path):
        return "❌ Jadval fayli topilmadi. Avval jadvalni yuklab oling."

    with open(svg_path, 'r', encoding='utf-8') as f:
        svg_content = f.read()

    soup = BeautifulSoup(svg_content, 'xml')

    # Kunlar
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5))).weekday()
    days_uz = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba"]

    if today >= len(days_uz):
        return "🕒 Bugun dam olish kuni 😊"

    current_day = days_uz[today]

    # Kunlar va ularning y koordinatalari
    day_coordinates = {
        "Dushanba": (420, 675),
        "Seshanba": (675, 930),
        "Chorshanba": (930, 1185),
        "Payshanba": (1185, 1440),
        "Juma": (1440, 1695),
        "Shanba": (1695, 1950)
    }

    # Dars vaqtlari
    lesson_times = {
        0: "8:00 - 8:25",
        1: "8:30 - 9:50",
        2: "10:00 - 11:20",
        3: "11:30 - 12:50",
        4: "13:20 - 14:40",
        5: "14:50 - 16:10",
        6: "16:20 - 17:40",
        7: "17:50 - 19:10",
        8: "19:20 - 20:40"
    }

    # Ustun koordinatalari (x)
    column_coordinates = [
        (237.5975876048103, 534.5311889820537),  # 0-ustun
        (534.5311889820537, 831.464790359297),  # 1-ustun
        (831.464790359297, 1128.3983917365404),  # 2-ustun
        (1128.3983917365404, 1425.3319931137837),  # 3-ustun
        (1425.3319931137837, 1722.265594491027),  # 4-ustun
        (1722.265594491027, 2019.1991958682704),  # 5-ustun
        (2019.1991958682704, 2316.1327972455133),  # 6-ustun
        (2316.1327972455133, 2613.066398622757),  # 7-ustun
        (2613.066398622757, 2910.0000000000005)  # 8-ustun
    ]

    day_y_start, day_y_end = day_coordinates[current_day]

    # Bugungi darslarni to'plash
    todays_lessons = []

    # Barcha dars kataklarini olish
    for rect in soup.find_all('rect'):
        if rect.get('stroke') == 'none' and rect.get('style') and 'fill: rgb(255, 255, 255)' in rect.get('style', ''):
            try:
                x = float(rect.get('x', 0))
                y = float(rect.get('y', 0))
                height = float(rect.get('height', 0))

                if day_y_start <= y < day_y_end:
                    # Qaysi vaqt oralig'iga tegishli
                    lesson_time = None
                    for col_num, (col_start, col_end) in enumerate(column_coordinates):
                        if col_start <= x < col_end:
                            lesson_time = lesson_times.get(col_num)
                            break

                    if lesson_time:
                        title_elem = rect.find_next('title')
                        if title_elem:
                            lesson_info = title_elem.text.strip()
                            lines = lesson_info.split('\n')

                            if len(lines) >= 3:
                                lesson_name = lines[0].strip()
                                teacher = lines[1].strip()
                                classroom = lines[2].strip()

                                # Katak balandligi va joylashuviga qarab hafta navbatini aniqlash
                                week_type = detect_week_type(y, height, day_y_start)

                                todays_lessons.append({
                                    'time': lesson_time,
                                    'name': lesson_name,
                                    'teacher': teacher,
                                    'classroom': classroom,
                                    'y': y,
                                    'height': height,
                                    'week_type': week_type
                                })
            except (ValueError, AttributeError):
                continue

    # Darslarni tartiblash (vaqt bo'yicha, keyin joylashuv bo'yicha)
    todays_lessons.sort(key=lambda x: (x['time'], x['y']))

    return format_timetable(current_day, todays_lessons)


def detect_week_type(y, height, day_start):
    """
    Darsning hafta navbatini aniqlaydi:
    - 0: har doim
    - 1: birinchi dars (yuqori qism)
    - 2: ikkinchi dars (quyi qism)
    """
    # Agar katak balandligi kichik bo'lsa (~127.5), bu ikkita darsdan biri
    if height < 150:
        # Katakning nisbiy joylashuvi
        relative_y = y - day_start
        if relative_y < 127.5:
            return 1  # Birinchi dars (yuqori)
        else:
            return 2  # Ikkinchi dars (quyi)
    return 0  # Har doim

def parse_time(t):
    """Masalan '8:30 - 9:50' -> 8*60+30 = 510 (boshlanish daqiqasi)"""
    start = t.split('-')[0].strip()
    h, m = map(int, start.split(':'))
    return h * 60 + m

def format_timetable(day, lessons):
    """
    Dars jadvalini chiroyli formatda tayyorlash
    """
    if not lessons:
        return f"📅 {day} kuni darslar mavjud emas 🎉"

    result = f"<b>📚 {day} kuni dars jadvali</b>\n\n"

    # Darslarni vaqt bo'yicha guruhlash
    lessons_by_time = {}
    for lesson in lessons:
        time = lesson['time']
        if time not in lessons_by_time:
            lessons_by_time[time] = []
        lessons_by_time[time].append(lesson)

    # Har bir vaqt oralig'i uchun darslarni chiqarish
    for time, time_lessons in sorted(lessons_by_time.items(), key=lambda x: parse_time(x[0])):
        result += f"<b>🕒 {time}</b>\n"

        # Agar bir vaqtda bir nechta dars bo'lsa
        if len(time_lessons) > 1:
            # Darslarni hafta turi bo'yicha tartiblash
            time_lessons.sort(key=lambda x: x.get('week_type', 0))

            for i, lesson in enumerate(time_lessons, 1):
                week_info = get_week_info(lesson.get('week_type', 0), i, len(time_lessons))

                result += f"   {week_info}\n"
                result += f"   📖 {lesson['name']}\n"
                result += f"   👨‍🏫 {lesson['teacher']}\n"
                result += f"   🏫 {lesson['classroom']}\n"

                if i < len(time_lessons):
                    result += "   ───────────────────\n"
        else:
            # Faqat bitta dars bo'lsa
            lesson = time_lessons[0]
            result += f"   📖 {lesson['name']}\n"
            result += f"   👨‍🏫 {lesson['teacher']}\n"
            result += f"   🏫 {lesson['classroom']}\n"

        result += "\n"

    # Agar navbatdosh darslar bo'lsa, izoh qo'shish
    if any(len(lessons_by_time[time]) > 1 for time in lessons_by_time):
        result += "<i>Eslatma: Bir vaqt oralig'ida ikkita fan ko'rsatilgan bo'lsa, bu hafta turiga qarab aniqlanadi</i>"

    return result


def get_week_info(week_type, current_index, total_count):
    """
    Hafta ma'lumotlarini formatlash
    """
    if total_count == 1:
        return "📚"
    elif week_type == 1:
        return "🅰️ 1-fan"
    elif week_type == 2:
        return "🅱️ 2-fan"
    else:
        return f"📚 {current_index}-dars"

# Test code - commented out to prevent execution on import
# if __name__ == "__main__":
#     print(get_daily_timetable(asyncio.run(save_timetable())))