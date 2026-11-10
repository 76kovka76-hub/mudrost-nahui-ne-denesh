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

# GitHub Actions passes the exact cron expression, so delayed runners still use
# the intended slot rather than guessing from the actual start minute.
CRON_SLOTS = {
    "0 5 * * *": 0,
    "30 6 * * *": 1,
    "0 8 * * *": 2,
    "30 9 * * *": 3,
    "0 11 * * *": 4,
    "30 12 * * *": 5,
    "0 14 * * *": 6,
    "30 15 * * *": 7,
    "0 17 * * *": 8,
    "30 18 * * *": 9,
}
SLOT_TIMES = ["08:00", "09:30", "11:00", "12:30", "14:00",
              "15:30", "17:00", "18:30", "20:00", "21:30"]

# Short, original aphorisms assembled from curated language pools.
TEMPLATES = [
    "Иногда {a} — это просто {b}, которому наконец-то {c}.",
    "Самая дорогая привычка — {a}, потому что она {b} и {c}.",
    "Взрослая жизнь начинается там, где {a}, а {b} уже не {c}.",
    "Не путай {a} с {b}: первое {c}, а второе — нет.",
    "Порой лучший план на жизнь — {a}, пока {b} не перестанет {c}.",
    "Если {a}, это ещё не значит, что {b} обязано {c}.",
    "Мудрость — это когда {a}, даже если {b} очень хочется {c}.",
    "Главный жизненный навык — {a}, не превращая {b} в {c}.",
    "Человек взрослеет, когда {a} и перестаёт {b}, чтобы {c}.",
    "Запомни: {a} не делает тебя {b}, зато помогает {c}.",
]
A = [
    "молчать вовремя", "выбирать себя", "держать дистанцию", "говорить прямо",
    "отпускать прошлое", "не спорить с идиотами", "беречь нервы",
    "признавать ошибки", "не ждать спасателей", "считать свои деньги",
    "задавать неудобные вопросы", "уметь сказать «нет»", "менять маршрут",
    "не объяснять очевидное", "сохранять чувство юмора", "уходить без спектакля",
    "думать своей головой", "не раздавать обещания", "уважать чужие границы",
    "не путать гордость с достоинством",
]
B = [
    "чужое мнение", "красивую иллюзию", "бесплатный цирк", "старую обиду",
    "чужую ответственность", "пустые обещания", "вечную спешку",
    "синдром спасателя", "страх перемен", "показное спокойствие",
    "токсичную привычку", "чужой успех", "громкие слова", "удобную ложь",
    "собственное эго", "бесконечное ожидание", "эмоциональный мусор",
]
C = [
    "перестать управлять твоей жизнью", "не жрать твои силы",
    "не решать за тебя", "не стоить твоего сна", "не портить тебе день",
    "остаться в прошлом", "не требовать оправданий", "не диктовать правила",
    "не превращаться в драму", "не мешать жить спокойно",
    "не стоить ни одной нервной клетки", "наконец отъебаться",
]
HASHTAGS = [
    "мысли", "мудрость", "жизнь", "философия", "правдажизни",
    "самоирония", "безиллюзий", "жизненныйопыт", "думай", "характер",
    "отношения", "люди", "выбор", "свободамысли", "силадуха",
    "взрослая жизнь".replace(" ", ""), "сарказм", "безфильтров",
    "мудрыеслова", "мысливслух", "нервы", "личныеграницы",
    "самоуважение", "реальность", "ирония", "мотивация",
    "некисни", "по факту".replace(" ", ""), "голосразума",
    "жесткаяправда", "умныемысли", "жизньбезрозовыхочков",
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
    return re.sub(r"\s+", " ", text.lower()).strip()

def make_post(day, slot, used):
    rng = random.Random(f"{day.isoformat()}-{slot}-wisdom-v1")
    for attempt in range(500):
        template = rng.choice(TEMPLATES)
        sentence = template.format(a=rng.choice(A), b=rng.choice(B), c=rng.choice(C))
        key = normalize(sentence)
        if key not in used:
            used.add(key)
            tags = rng.sample(HASHTAGS, 3)
            return sentence, tags
        rng.random()
    raise RuntimeError("Не удалось подобрать новую фразу без повтора.")

def get_slot():
    cron = os.getenv("SLOT_CRON", "")
    if cron in CRON_SLOTS:
        return CRON_SLOTS[cron]
    # Manual run: use the nearest scheduled time, with deterministic fallback.
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
        raise RuntimeError(f"VK API error {payload['error'].get('error_code')}: "
                           f"{payload['error'].get('error_msg')}")
    return payload["response"]["post_id"]

def main():
    now = datetime.now(MSK)
    day = now.date()
    slot = get_slot()
    slot_key = f"{day.isoformat()}:{slot}"
    history = load_history()

    if slot_key in history["published_slots"]:
        print(f"Слот {slot_key} уже опубликован — пропускаю.")
        return

    used = {normalize(item) for item in history["posts"]}
    sentence, tags = make_post(day, slot, used)
    message = sentence + "\n\n" + " ".join("#" + tag for tag in tags)
    post_id = publish(message)

    history["posts"].append(sentence)
    history["published_slots"].append(slot_key)
    # Keep the complete phrase history to prevent repeats across the lifetime
    # of the community. GitHub Actions commits this file after each run.
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Опубликовано: {day}, слот {SLOT_TIMES[slot]}, post_id={post_id}")
    print(message)

if __name__ == "__main__":
    main()
