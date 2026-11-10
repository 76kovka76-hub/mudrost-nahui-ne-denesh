import json
import os
import random
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

GROUP_ID = os.environ["VK_GROUP_ID"]
TOKEN = os.environ["VK_ACCESS_TOKEN"]
API_VERSION = "5.199"
HISTORY_FILE = Path("post_history.json")
MSK = timezone(timedelta(hours=3))

CRON_SLOTS = {
    "0 5 * * *": 0, "30 6 * * *": 1, "0 8 * * *": 2,
    "30 9 * * *": 3, "0 11 * * *": 4, "30 12 * * *": 5,
    "0 14 * * *": 6, "30 15 * * *": 7, "0 17 * * *": 8,
    "30 18 * * *": 9,
}
SLOT_TIMES = ["08:00", "09:30", "11:00", "12:30", "14:00",
              "15:30", "17:00", "18:30", "20:00", "21:30"]

# All fragments are infinitive phrases or complete clauses chosen to fit
# their sentence templates grammatically.
TEMPLATES = [
    "Иногда {a} — лучший способ {b}, и это, блядь, нормально.",
    "Не обязательно {a}: иногда достаточно {b}, чтобы {c}.",
    "Самое трудное — {a}, когда {b}, но именно так {c}.",
    "Если {a}, не надо {b}: {c}, и нахуй тебе лишняя драма.",
    "Запомни: {a} — это не слабость, а способ {b}, чёрт возьми.",
    "Порой полезнее {a}, чем {b}, потому что {c}, блядь.",
    "Не трать жизнь на то, чтобы {a}: лучше {b} и {c}.",
    "Когда хочется {a}, сначала попробуй {b} — иногда это и есть {c}.",
    "Взрослость — это {a}, даже если очень хочется {b}, потому что {c}.",
    "Можно сколько угодно {a}, но {b}; вот такая, нахуй, философия.",
]
A = [
    "уйти вовремя", "сказать честное «нет»", "перестать всем нравиться",
    "выбрать собственный покой", "признать свою ошибку", "отпустить прошлое",
    "не отвечать на провокации", "перестать спасать всех подряд",
    "попросить о помощи", "начать сначала", "сменить окружение",
    "держать слово перед собой", "не объяснять очевидное",
    "уважать собственные границы", "считать не только деньги, но и силы",
    "сделать паузу", "перестать ждать идеального момента",
    "не путать привычку с любовью", "выключить чувство вины",
    "посмотреть правде в глаза", "не принимать всё близко к сердцу",
    "выбирать поступки, а не красивые обещания", "перестать жить чужими ожиданиями",
    "не спорить ради последнего слова", "сохранить чувство юмора",
    "вовремя закрыть эту дверь", "перестать искать одобрение",
    "признать, что ты устал", "не предавать себя ради чужого комфорта",
    "отличать одиночество от свободы",
]
B = [
    "сохранить себя", "не потерять собственное достоинство",
    "вернуть себе спокойствие", "не тратить нервы на пустоту",
    "освободить место для нормальной жизни", "перестать наступать на те же грабли",
    "не превращать жизнь в бесконечный экзамен", "оставить прошлое в прошлом",
    "не делать чужую проблему своей", "жить без постоянных оправданий",
    "не позволять страху принимать решения", "не разменивать себя по мелочам",
    "сберечь время для действительно важных людей", "не кормить чужое эго",
    "не превращать обиду в образ жизни", "вернуть себе право на ошибку",
    "не ждать благодарности за каждый добрый поступок", "не терять себя в отношениях",
    "смотреть на факты, а не на фантазии", "не отдавать свой день чужому настроению",
    "перестать жить на автопилоте", "не путать терпение с обязанностью терпеть",
]
C = [
    "ты не обязан быть удобным для всех", "чужое мнение не оплачивает твои счета",
    "не каждый спор стоит твоего времени", "спокойствие дороже красивой победы",
    "люди верят поступкам, а не речам", "прошлое не обязано портить будущее",
    "уважение нельзя выбить просьбами", "твоя жизнь не черновик для чужих правок",
    "ошибка — это опыт, если сделать выводы", "границы нужны не для красоты",
    "никто не выдаст тебе запасную жизнь", "не всё потерянное стоило возвращать",
    "иногда точка честнее тысячи обещаний", "не всякая близость означает любовь",
    "время быстро показывает цену словам", "ты имеешь право передумать",
    "чужой хаос не должен становиться твоим домом", "самоуважение начинается с маленьких решений",
    "не нужно заслуживать нормальное отношение", "внутренний покой не обязан всем нравиться",
    "жизнь становится легче, когда перестаёшь играть чужую роль",
    "не всякая дверь заслуживает второго стука",
]
HASHTAGS = [
    "мысли", "мудрость", "жизнь", "философия", "правдажизни",
    "самоирония", "безиллюзий", "жизненныйопыт", "думай", "характер",
    "отношения", "люди", "выбор", "свободамысли", "силадуха",
    "сарказм", "безфильтров", "мудрыеслова", "мысливслух", "нервы",
    "личныеграницы", "самоуважение", "реальность", "ирония", "мотивация",
    "голосразума", "жесткаяправда", "умныемысли", "взрослаяпозиция",
    "по факту".replace(" ", ""), "безрозовыхочков", "жизненнаямудрость",
    "сильныйхарактер", "неудобнаяправда", "ценисебя", "смыслжизни",
]

def load_history():
    if not HISTORY_FILE.exists():
        return {"posts": [], "published_slots": []}
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        data.setdefault("posts", [])
        data.setdefault("published_slots", [])
        return data
    except (json.JSONDecodeError, OSError):
        print("История повреждена — остановка, чтобы не допустить повторов.")
        sys.exit(1)

def normalize(text):
    return re.sub(r"\\s+", " ", text.lower()).strip()

def make_post(day, slot, used):
    rng = random.Random(f"{day.isoformat()}-{slot}-wisdom-v2")
    for _ in range(1000):
        template = rng.choice(TEMPLATES)
        sentence = template.format(a=rng.choice(A), b=rng.choice(B), c=rng.choice(C))
        key = normalize(sentence)
        if key not in used:
            used.add(key)
            return sentence, rng.sample(HASHTAGS, 3)
    raise RuntimeError("Не удалось подобрать новую фразу без повтора.")

def get_slot():
    cron = os.getenv("SLOT_CRON", "")
    if cron in CRON_SLOTS:
        return CRON_SLOTS[cron]
    now = datetime.now(MSK)
    minutes = now.hour * 60 + now.minute
    schedule = [int(t[:2]) * 60 + int(t[3:]) for t in SLOT_TIMES]
    return min(range(10), key=lambda i: abs(schedule[i] - minutes))

def publish(message):
    response = requests.post(
        "https://api.vk.com/method/wall.post",
        data={
            "owner_id": f"-{GROUP_ID}",
            "from_group": 1,
            "message": message,
            "access_token": TOKEN,
            "v": API_VERSION,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        err = payload["error"]
        raise RuntimeError(f"VK API error {err.get('error_code')}: {err.get('error_msg')}")
    return payload["response"]["post_id"]

def main():
    day = datetime.now(MSK).date()
    slot = get_slot()
    slot_key = f"{day.isoformat()}:{slot}"
    history = load_history()
    if slot_key in history["published_slots"]:
        print(f"Слот {slot_key} уже опубликован — пропускаю.")
        return

    used = {normalize(item) for item in history["posts"]}
    sentence, tags = make_post(day, slot, used)
    message = sentence + "\\n\\n" + " ".join("#" + tag for tag in tags)
    post_id = publish(message)

    history["posts"].append(sentence)
    history["published_slots"].append(slot_key)
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2) + "\\n",
        encoding="utf-8",
    )
    print(f"Опубликовано: {day}, слот {SLOT_TIMES[slot]}, post_id={post_id}")
    print(message)

if __name__ == "__main__":
    main()
