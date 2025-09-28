#!/usr/bin/env python3
"""
Телеграм-бот: ролевка в стиле Сейлор Мун
Требования: python-telegram-bot v20+ (async)
Простейшая persistent storage — SQLite (файл sailor.db в папке запуска)
"""

from dotenv import load_dotenv
load_dotenv()  # Это загрузит переменные окружения из файла .env
import os
import shutil
import sqlite3
import asyncio
import random
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import requests

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    ChatPermissions,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

# ------------ Конфигурация и данные игры ------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Пожалуйста, укажи BOT_TOKEN через переменную окружения.")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))

DB_PATH = "/tmp/sailor.db"  # временный путь на контейнере
GITHUB_DB_URL = "https://raw.githubusercontent.com/nkbss-nkbss/SailorMoonGameBot/main/sailor.db"

if not os.path.exists(DB_PATH):
    # вариант 1: скачиваем напрямую из GitHub
    r = requests.get(GITHUB_DB_URL)
    with open(DB_PATH, "wb") as f:
        f.write(r.content)

r = requests.get(GITHUB_DB_URL)

STYLES = {
    "luna": {"name": "Сейлор Мун 🌙", "hp_base": 30, "atk_base": 3, "img": "https://i.pinimg.com/1200x/6a/02/19/6a0219632e0cf643b21a15f134ba79c4.jpg" },
    "fire": {"name": "Сейлор Марс 🔥", "hp_base": 26, "atk_base": 5, "img": "https://i.pinimg.com/736x/38/ee/d2/38eed255dd4c9895304dfe7aa03fda0e.jpg"},
    "jupiter": {"name": "Сейлор Юпитер ⚡", "hp_base": 34, "atk_base": 4, "img": "https://i.pinimg.com/736x/b8/f7/ba/b8f7ba5311e3d8acea0834aedbf5dda6.jpg"},
    "water": {"name": "Сейлор Меркурий 💧", "hp_base": 32, "atk_base": 3, "img": "https://i.pinimg.com/736x/b1/61/1a/b1611addcf1190d311218c22614e1e36.jpg"},
    "love": {"name": "Сейлор Венера 💖", "hp_base": 28, "atk_base": 4, "img": "https://i.pinimg.com/736x/91/c1/f6/91c1f699cc6764e6dd2af9b660d709ba.jpg"},
}

ITEMS = {
    "luna_brooch": {"title": "Лунная брошь", "desc": "Небольшой бонус к атаке", "price": 50, "atk": 2},
    "healing_herb": {"title": "Лунный эликсир", "desc": "Восстанавливает энергию/HP", "price": 30, "heal": 10},
    "moon_crystal": {"title": "Лунный кристалл", "desc": "Редкий ресурс для трансформаций", "price": 0, "rare": True},
}

MONSTERS = [
    {"id": "m1", "name": "Слабый демон", "lvl": 1, "hp": 8, "atk": 2, "reward_xp": 10, "reward_gold": 10},
    {"id": "m2", "name": "Средний демон", "lvl": 2, "hp": 14, "atk": 3, "reward_xp": 18, "reward_gold": 18},
    {"id": "m3", "name": "Сильный демон", "lvl": 3, "hp": 22, "atk": 5, "reward_xp": 35, "reward_gold": 40},
    {"id": "m4", "name": "Сильный демон", "lvl": 4, "hp": 30, "atk": 7, "reward_xp": 45, "reward_gold": 50},

    {"id": "boss1", "name": "👾 БОСС: Джедайт", "lvl": 5, "hp": 50, "atk": 8, "reward_xp": 120, "reward_gold": 120},
    {"id": "boss2", "name": "👾 БОСС: Нефрит", "lvl": 10, "hp": 60, "atk": 9, "reward_xp": 120, "reward_gold": 120},
    {"id": "boss3", "name": "👾 БОСС: Зойсайт", "lvl": 15, "hp": 70, "atk": 10, "reward_xp": 120, "reward_gold": 120},
    {"id": "boss4", "name": "👾 БОСС: Кунсайт", "lvl": 20, "hp": 80, "atk": 20, "reward_xp": 120, "reward_gold": 120},

    {"id": "boss5", "name": "👾 БОСС: Петсайт", "lvl": 5, "hp": 50, "atk": 8, "reward_xp": 120, "reward_gold": 120},
    {"id": "boss6", "name": "👾 БОСС: Калаверайт", "lvl": 10, "hp": 60, "atk": 9, "reward_xp": 120, "reward_gold": 120},
    {"id": "boss7", "name": "👾 БОСС: Бертерайт", "lvl": 15, "hp": 70, "atk": 10, "reward_xp": 120, "reward_gold": 120},
    {"id": "boss8", "name": "👾 БОСС: Кермисайт", "lvl": 20, "hp": 80, "atk": 20, "reward_xp": 120, "reward_gold": 120},

    {"id": "superboss1", "name": "👹💥 СУПЕРБОСС: Королева Погибель", "lvl": 50, "hp": 90, "atk": 20, "reward_xp": 200, "reward_gold": 200},
    {"id": "superboss2", "name": "👹💥 СУПЕРБОСС: Рубеус", "lvl": 50, "hp": 90, "atk": 20, "reward_xp": 200, "reward_gold": 200},
    {"id": "superboss3", "name": "👹💥 СУПЕРБОСС: Изумруд", "lvl": 50, "hp": 90, "atk": 20, "reward_xp": 200, "reward_gold": 200},
    {"id": "superboss4", "name": "👹💥 СУПЕРБОСС: Мудрец", "lvl": 50, "hp": 90, "atk": 20, "reward_xp": 200, "reward_gold": 200},



]

LEVELS = [
    (0, "Сейлор-новичок"),
    (50, "Сейлор-защитник"),
    (150, "Сейлор-воительница"),
    (350, "Лунная принцесса"),
    (700, "Лунная королева"),
]

DAILY_EXP_BONUS = 5

# ------------ Вспомогательные структуры ------------
@dataclass
class Player:
    user_id: int
    username: str
    name: str
    style: str
    lvl: int
    xp: int
    gold: int
    hp: int
    max_hp: int
    atk: int
    energy: int
    last_daily: str  # date iso
    inventory: str  # comma-separated item keys

# ------------ База данных ------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            style TEXT,
            lvl INTEGER,
            xp INTEGER,
            gold INTEGER,
            hp INTEGER,
            max_hp INTEGER,
            atk INTEGER,
            energy INTEGER,
            last_daily TEXT,
            inventory TEXT,
            last_energy_tick TEXT DEFAULT '' 
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER PRIMARY KEY AUTOINCREMENT,
            leader_id INTEGER,
            member_ids TEXT, -- comma-separated
            active INTEGER DEFAULT 1
        )
        """
    )
    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect(DB_PATH)

# ------------ Игровая логика ------------
def create_player_obj(user_id: int, username: str, name: str, style: str) -> Player:
    s = STYLES.get(style, STYLES["luna"])
    max_hp = s["hp_base"]
    atk = s["atk_base"]
    return Player(
        user_id=user_id,
        username=username or "",
        name=name or "Таинственная Воительница",
        style=style,
        lvl=1,
        xp=0,
        gold=50,
        hp=max_hp,
        max_hp=max_hp,
        atk=atk,
        energy=5,
        last_daily="",
        inventory="",
    )

def save_player(p: Player):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO players (
            user_id, username, name, style, lvl, xp, gold, hp, max_hp, atk, energy, last_daily, inventory
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            p.user_id,
            p.username,
            p.name,
            p.style,
            p.lvl,
            p.xp,
            p.gold,
            p.hp,
            p.max_hp,
            p.atk,
            p.energy,
            p.last_daily,
            p.inventory,
        ),
    )
    conn.commit()
    conn.close()

def load_player(user_id: int) -> Player | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    r = cur.fetchone()
    conn.close()
    if not r:
        return None
    return Player(
        user_id=r[0],
        username=r[1],
        name=r[2],
        style=r[3],
        lvl=r[4],
        xp=r[5],
        gold=r[6],
        hp=r[7],
        max_hp=r[8],
        atk=r[9],
        energy=r[10],
        last_daily=r[11] or "",
        inventory=r[12] or "",
    )

def level_name_for_xp(xp: int):
    name = LEVELS[0][1]
    lvl = 1
    for req, title in LEVELS:
        if xp >= req:
            name = title
    # derive numeric level as index of LEVELS that xp >= req
    for i, (req, _) in enumerate(LEVELS):
        if xp >= req:
            lvl = i+1
    return lvl, name

def add_xp_and_check_level(p: Player, add_xp: int):
    p.xp += add_xp
    old_lvl = p.lvl
    new_lvl, _ = level_name_for_xp(p.xp)
    p.lvl = new_lvl
    # if leveled up, give small bonus
    leveled = False
    if new_lvl > old_lvl:
        leveled = True
        p.max_hp += 5 * (new_lvl - old_lvl)
        p.atk += 1 * (new_lvl - old_lvl)
        p.hp = p.max_hp
    return leveled

def add_item_to_player(p: Player, item_key: str):
    inv = p.inventory.split(",") if p.inventory else []
    inv.append(item_key)
    p.inventory = ",".join([i for i in inv if i])

def consume_item_from_player(p: Player, item_key: str) -> bool:
    inv = p.inventory.split(",") if p.inventory else []
    if item_key in inv:
        inv.remove(item_key)
        p.inventory = ",".join([i for i in inv if i])
        return True
    return False

def get_inventory_list(p: Player):
    if not p.inventory:
        return []
    return [i for i in p.inventory.split(",") if i]

def make_user_buttons(user_id: int):
    """
    Создает inline-кнопки для основного меню игрока.
    """
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Профиль", callback_data=f"profile:{user_id}")],
        [InlineKeyboardButton("📦 Инвентарь", callback_data=f"inventory:{user_id}")],
        [InlineKeyboardButton("⚔️ Бой", callback_data=f"fight:{user_id}")],
        [InlineKeyboardButton("👯 Команда", callback_data=f"team:{user_id}")],
        [InlineKeyboardButton("🤝 Пригласить в команду", callback_data=f"teamup:{user_id}")],
        [InlineKeyboardButton("🌟 Рейтинг", callback_data=f"leaderboard:{user_id}")],
        [InlineKeyboardButton("🚶 Исследовать", callback_data=f"explore:{user_id}")],
        [InlineKeyboardButton("🛡 Командный бой", callback_data=f"teamfight:{user_id}")]
    ])
    return kb

def check_and_restore_energy(player):
    now = datetime.now(timezone.utc)

    if not player.last_energy_tick:
        last_tick = now - timedelta(hours=1)
    else:
        last_tick = datetime.fromisoformat(player.last_energy_tick)

    hours_passed = int((now - last_tick).total_seconds() // 3600)
    
    if hours_passed > 0:
        player.energy = min(5, player.energy + hours_passed)
        player.last_energy_tick = (last_tick + timedelta(hours=hours_passed)).isoformat()
        save_player(player)
    
    next_tick = last_tick + timedelta(hours=hours_passed + 1)
    seconds_left = (next_tick - now).total_seconds()
    minutes = int(seconds_left // 60)
    seconds = int(seconds_left % 60)
    
    return minutes, seconds

    
# ------------ Команды бота ------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    p = load_player(user.id)
    if p:
        await update.effective_message.reply_text(
            f"С возвращением, {p.name} — {STYLES[p.style]['name']}! "
            f"Профиль: /profile"
        )
        return

    # ask to choose style via inline keyboard
    kb = []
    for key, val in STYLES.items():
        kb.append([InlineKeyboardButton(val["name"], callback_data=f"choose_style:{key}")])
    await update.effective_message.reply_text(
        "Добро пожаловать, новобранка! 🌙\nВыбери Стихию Силы, чтобы стать Сейлор-воительницей:",
        reply_markup=InlineKeyboardMarkup(kb),
    )

async def cb_choose_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    style_key = query.data.split(":")[1]
    user = query.from_user

    # Создаём объект Player через create_player_obj, который автоматически присваивает начальные значения
    p = create_player_obj(user.id, user.username or "", user.first_name, style_key)
    
    # Сохраняем игрока в базе данных
    save_player(p)

    style = STYLES[style_key]

    await query.message.reply_photo(
        photo=style["img"],
        caption=f"✨ Ты выбрал(а) путь {style['name']}!\nТеперь ты настоящий защитник во имя Луны 🌙"
    )

async def cmd_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = load_player(user.id)
    if not player:
        await update.effective_message.reply_text("Сначала /start.")
        return
    
    minutes, seconds = check_and_restore_energy(player)
    await update.effective_message.reply_text(
        f"⚡ Твоя энергия: {player.energy}/{5}\n"
        f"До следующей единицы: {minutes} мин {seconds} сек"
    )



async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    p = load_player(user.id)
    if not p:
        await update.message.reply_text("Ты ещё не зарегистрирован(а). Напиши /start 🌙")
        return

    style = STYLES.get(p.style, {"name": "Неизвестно", "img": None})
    inv = get_inventory_list(p)
    inv_text = ", ".join([ITEMS[i]["title"] for i in inv if i in ITEMS]) if inv else "пусто"

    await update.message.reply_photo(
        photo=style["img"],
        caption=f"🌙 Профиль {p.name}\n"
                f"Воин: {style['name']}\n"
                f"Уровень: {p.lvl}\n"
                f"XP: {p.xp}\n"
                f"Gold: {p.gold}\n"
                f"HP: {p.hp}/{p.max_hp}\n"
                f"Атака: {p.atk}\n"
                f"Энергия: {p.energy}\n"
                f"Инвентарь: {inv_text}"
    )
    


async def cmd_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    p = load_player(user.id)
    if not p:
        await update.effective_message.reply_text("Сначала /start.")
        return
    inv = get_inventory_list(p)
    if not inv:
        await update.effective_message.reply_text("Инвентарь пуст.")
        return
    lines = []
    for i in inv:
        if i in ITEMS:
            it = ITEMS[i]
            lines.append(f"{it['title']} — {it['desc']}")
        else:
            lines.append(f"{i} — (неизвестно)")
    await update.effective_message.reply_text("📦 Твой инвентарь:\n" + "\n".join(lines))

async def cmd_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # show shop as inline buttons
    kb = []
    for key, it in ITEMS.items():
        if it.get("price", 0) > 0:
            kb.append([InlineKeyboardButton(f"{it['title']} — {it['price']}💠", callback_data=f"buy:{key}")])
    await update.effective_message.reply_text("Магазин Сейлор — выбери предмет:", reply_markup=InlineKeyboardMarkup(kb))

async def shop_buy_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    if not data.startswith("buy:"):
        return
    item_key = data.split(":", 1)[1]
    user = q.from_user
    p = load_player(user.id)
    if not p:
        await q.edit_message_text("Сначала зарегистрируйся: /start")
        return
    item = ITEMS.get(item_key)
    if not item:
        await q.edit_message_text("Предмет не найден.")
        return
    price = item.get("price", 0)
    if p.gold < price:
        await q.edit_message_text("Недостаточно золота.")
        return
    p.gold -= price
    add_item_to_player(p, item_key)
    save_player(p)
    await q.edit_message_text(f"Ты купила {item['title']}! Он в инвентаре.")

async def cmd_fight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    p = load_player(user.id)
    if not p:
        await update.effective_message.reply_text("Сначала /start.")
        return
    if p.energy <= 0:
        await update.effective_message.reply_text("Энергия закончилась. Попробуй позже или используй предметы для восстановления.")
        return
    # choose monster roughly by player level
    pool = [m for m in MONSTERS if m["lvl"] <= max(1, p.lvl+1)]
    monster = random.choice(pool)
    # simple fight simulation: player roll + atk vs monster hp/atk
    p.energy -= 1
    player_roll = random.randint(1, 10) + p.atk
    monster_roll = random.randint(1, 10) + monster["atk"]
    # determine outcome
    result_text = []
    result_text.append(f"⚔️ Ты встретила: *{monster['name']}* (ур. {monster['lvl']})")
    result_text.append(f"Твой бросок (atk+рандом): {player_roll}   |   Монстр: {monster_roll}")
    if player_roll >= monster_roll:
        # victory
        xp = monster["reward_xp"]
        gold = monster["reward_gold"]
        add_xp_and_check_level(p, xp)
        p.gold += gold
        # small chance to drop moon_crystal
        if random.random() < 0.08:
            add_item_to_player(p, "moon_crystal")
            drop_text = "\n✨ Тебе выпал Лунный кристалл!"
        else:
            drop_text = ""
        save_player(p)
        result_text.append(f"🌟 Победа! +{xp} XP, +{gold}💠.{drop_text}")
    else:
        # defeat
        dmg = max(1, monster["atk"] + random.randint(0, 3))
        p.hp -= dmg
        if p.hp <= 0:
            # faint, reset hp to half max
            p.hp = max(1, p.max_hp // 2)
            result_text.append(f"💥 Поражение. Ты была сбита с ног и теряешь {dmg} HP. Восстановлена до {p.hp} HP.")
        else:
            result_text.append(f"💥 Поражение. Ты теряешь {dmg} HP. Текущее HP: {p.hp}/{p.max_hp}")
        save_player(p)
    result = "\n".join(result_text)
    await update.effective_message.reply_markdown(result)

async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    p = load_player(user.id)
    if not p:
        await update.effective_message.reply_text("Сначала /start.")
        return
    today = datetime.utcnow().date().isoformat()
    if p.last_daily == today:
        await update.effective_message.reply_text("Дневная награда уже получена сегодня.")
        return
    p.last_daily = today
    p.gold += 20
    p.energy = min(5, p.energy + 2)
    add_xp_and_check_level(p, DAILY_EXP_BONUS)
    save_player(p)
    await update.effective_message.reply_text("🌞 Ежедневная награда: +20💠, +2 Энергии, +5 XP. Удачи, Сейлор!")

async def cmd_use(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # use item by name: /use luna_brooch
    user = update.effective_user
    p = load_player(user.id)
    if not p:
        await update.effective_message.reply_text("Сначала /start.")
        return
    args = context.args
    if not args:
        await update.effective_message.reply_text("Укажи ключ предмета:\nЛунная брошь - luna_brooch\nЛунный эликсир - healing_herb\nЛунный кристалл - moon_crystal")
        return
    key = args[0]
    if key not in ITEMS:
        await update.effective_message.reply_text("Нет такого предмета.")
        return
    if not consume_item_from_player(p, key):
        await update.effective_message.reply_text("У тебя нет этого предмета в инвентаре.")
        return
    item = ITEMS[key]
    # apply effects
    if item.get("heal"):
        heal = item["heal"]
        p.hp = min(p.max_hp, p.hp + heal)
        await update.effective_message.reply_text(f"✨ Ты использовала {item['title']}. Восстановлено {heal} HP. Текущее HP: {p.hp}/{p.max_hp}")
    elif item.get("atk"):
        p.atk += item["atk"]
        await update.effective_message.reply_text(f"🔰 {item['title']} добавил +{item['atk']} к Атаке навсегда.")
    else:
        await update.effective_message.reply_text(f"Ты использовала {item['title']}.")
    save_player(p)

async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name, lvl, xp FROM players ORDER BY lvl DESC, xp DESC LIMIT 10")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Рейтинг пока пуст 🌙")
        return

    text = "🌟 ТОП-10 защитников Луны 🌟\n\n"
    for i, (name, lvl, xp) in enumerate(rows, start=1):
        text += f"{i}. {name} — {lvl} lvl ({xp} XP)\n"

    await update.message.reply_text(text)

def random_event(p: Player) -> str:
    events = [
        ("✨ Ты нашёл волшебный кристалл! +20 XP", lambda: setattr(p, "xp", p.xp + 20)),
        ("💰 Ты нашёл кошелёк с золотом! +30 gold", lambda: setattr(p, "gold", p.gold + 30)),
        ("💔 Тёмная энергия поразила тебя! -10 HP", lambda: setattr(p, "hp", max(0, p.hp - 10))),
        ("👹 Ты встретил монстра! Начинается бой...", lambda: None)
    ]
    event = random.choice(events)
    event[1]()  # применяем эффект
    save_player(p)
    return event[0]

async def cmd_explore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    p = load_player(user.id)
    if not p:
        await update.message.reply_text("Сначала /start 🌙")
        return

    event_text = random_event(p)
    await update.message.reply_text(f"🚶‍♀️ {p.name} отправился исследовать мир...\n\n{event_text}")


# ------------ Командные механики ------------
async def cmd_teamup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    p = load_player(user.id)
    if not p:
        await update.effective_message.reply_text("Сначала /start.")
        return
    if not context.args:
        await update.effective_message.reply_text("Укажи ник для приглашения: /teamup @username")
        return

    target = context.args[0].lstrip("@")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM players WHERE username = ?", (target,))
    row = cur.fetchone()
    conn.close()

    if not row:
        await update.effective_message.reply_text("Игрок с таким username не найден или он не регистрировался.")
        return

    target_id = row[0]

    # создаём inline-кнопки
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"team_accept:{user.id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"team_decline:{user.id}")
        ]
    ])

    await context.bot.send_message(
        chat_id=target_id,
        text=f"👯 @{p.username or p.name} приглашает тебя в команду!",
        reply_markup=kb
    )

    await update.effective_message.reply_text(f"Приглашение отправлено @{target}. Ждём ответа.")

async def team_invite_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data
    user = q.from_user
    p = load_player(user.id)
    if not p:
        await q.edit_message_text("Сначала /start.")
        return

    if data.startswith("team_accept:"):
        leader_id = int(data.split(":")[1])

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO teams (leader_id, member_ids, active) VALUES (?,?,1)",
                    (leader_id, f"{leader_id},{user.id}"))
        conn.commit()
        conn.close()

        await q.edit_message_text("✅ Ты принял(а) приглашение. Команда создана!")
        await context.bot.send_message(chat_id=leader_id, text=f"🎉 @{user.username or user.first_name} принял(а) приглашение!")

    elif data.startswith("team_decline:"):
        leader_id = int(data.split(":")[1])
        await q.edit_message_text("❌ Ты отклонил(а) приглашение.")
        await context.bot.send_message(chat_id=leader_id, text=f"😢 @{user.username or user.first_name} отклонил(а) приглашение.")


async def cmd_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # показывает команды, в которых состоит пользователь
    user = update.effective_user
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT team_id, leader_id, member_ids, active FROM teams WHERE active=1")
    rows = cur.fetchall()
    conn.close()
    res = []
    for r in rows:
        team_id, leader_id, member_ids, active = r
        members = member_ids.split(",") if member_ids else []
        if str(user.id) in members:
            # show
            names = []
            for uid in members:
                pl = load_player(int(uid))
                if pl:
                    names.append(pl.username or pl.name)
                else:
                    names.append(str(uid))
            res.append(f"Team {team_id}: leader {leader_id}, members: {', '.join(names)}")
    if not res:
        await update.effective_message.reply_text("Ты не в активных командах.")
    else:
        await update.effective_message.reply_text("\n".join(res))

async def cmd_teamfight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT team_id, leader_id, member_ids FROM teams WHERE active=1")
    rows = cur.fetchall()
    conn.close()

    # Найти команду пользователя
    found = None
    for r in rows:
        team_id, leader_id, member_ids = r
        if str(user.id) in (member_ids or "").split(","):
            found = (team_id, leader_id, member_ids)
            break
    if not found:
        await update.effective_message.reply_text("Ты не в активной команде.")
        return

    team_id, leader_id, member_ids = found
    members = [int(x) for x in member_ids.split(",") if x]

    # Проверка энергии и расход
    insufficient_energy = []
    for uid in members:
        pl = load_player(uid)
        if pl:
            if pl.energy <= 0:
                insufficient_energy.append(pl.name)
            else:
                pl.energy -= 1
                save_player(pl)

    if insufficient_energy:
        await update.effective_message.reply_text(
            "💤 Следующие игроки слишком устали для командного боя: " + ", ".join(insufficient_energy)
        )
        return


    # --- Подсчёт силы команды ---
    total_atk = 0
    total_hp = 0
    for uid in members:
        pl = load_player(uid)
        if pl:
            total_atk += pl.atk
            total_hp += pl.hp

    # --- Выбор босса ---
    bosses = [m for m in MONSTERS if m["id"].startswith("boss")]
    super_bosses = [m for m in MONSTERS if m["id"].startswith("superboss")]

    # 10% шанс на супербосса
    if random.random() < 0.10 and super_bosses:
        boss = random.choice(super_bosses)
        boss_type = "СУПЕРБОСС"
    else:
        boss = random.choice(bosses)
        boss_type = "БОСС"

    # --- Броски ---
    team_roll = random.randint(1, 10) + total_atk // max(1, len(members))
    boss_roll = random.randint(1, 10) + boss["atk"]

    res = [f"👯 Командная битва против {boss['name']}"]
    res.append(f"Командный бросок: {team_roll}   |   Босс: {boss_roll}")

    if team_roll >= boss_roll:
        # Победа, распределяем награды
        xp = boss["reward_xp"] // len(members)
        gold = boss["reward_gold"] // len(members)
        drop_text = ""
        for uid in members:
            pl = load_player(uid)
            if pl:
                add_xp_and_check_level(pl, xp)
                pl.gold += gold
                # Шанс на редкий предмет (например, лунный кристалл)
                if random.random() < 0.08:
                    add_item_to_player(pl, "moon_crystal")
                    drop_text += f"\n✨ {pl.name} получил Лунный кристалл!"
                save_player(pl)
        res.append(f"🌟 Команда победила! Каждому +{xp} XP, +{gold}💠{drop_text}")
    else:
        res.append("💥 Босс оказался сильнее. Попробуйте снова после восстановления энергии.")

    await update.effective_message.reply_text("\n".join(res))


# ------------ Удобства и обработчики ошибок ------------
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("Неизвестная команда. Доступные: /start /profile /fight /shop /inventory /daily /use /teamup /team /teamfight")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Ошибка: {context.error}")
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text("Произошла ошибка — попробуй снова.")
    except Exception:
        pass



# ------------ Main ------------
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).concurrent_updates(True).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(cb_choose_style, pattern=r"^choose_style:"))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("inventory", cmd_inventory))
    app.add_handler(CommandHandler("shop", cmd_shop))
    app.add_handler(CallbackQueryHandler(shop_buy_cb, pattern=r"^buy:"))
    app.add_handler(CommandHandler("fight", cmd_fight))
    app.add_handler(CommandHandler("daily", cmd_daily))
    app.add_handler(CommandHandler("use", cmd_use))
    app.add_handler(CommandHandler("teamup", cmd_teamup))
    app.add_handler(CommandHandler("team", cmd_team))
    app.add_handler(CommandHandler("teamfight", cmd_teamfight))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_handler(CommandHandler("explore", cmd_explore))
    app.add_handler(CommandHandler("energy", cmd_energy))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))
    app.add_error_handler(error_handler)
    app.add_handler(CallbackQueryHandler(cb_choose_style, pattern="^choose:"))
    app.add_handler(CallbackQueryHandler(team_invite_cb, pattern=r"^team_(accept|decline):"))

    app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=BOT_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()







