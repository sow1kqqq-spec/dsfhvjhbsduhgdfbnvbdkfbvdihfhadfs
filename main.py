import asyncio
import logging
import json
import os
import aiohttp
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
import re
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN", "8292483950:AAEpeXQm6EYmVc9pP29W9Q1NJgFS2YZDmNk")
CHANNEL_ID = "@Zendeks_rblx"
ADMIN_IDS = [6668784806, 8972052372]

DATA_FILE = "bot_data.json"
CHECK_CACHE_TIME = 60
API_BASE = "https://api.growagarden2stock.com"
POLL_INTERVAL = 30
RESTOCK_INTERVAL = 270

BOT_LINK = "https://t.me/growagarden2stock_tetrisbot"
BOT_NAME = "ЛУЧШИЙ БОТ ПО СТОКАМ"
PREDICT_URL = "https://www.game.guide/grow-a-garden-2-stock-predictor"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class SupportStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_reply = State()

class SponsorStates(StatesGroup):
    waiting_for_channel = State()
    waiting_for_link = State()

LANGUAGES = {
    'ru': {'name': 'Русский', 'flag': '🇷🇺'},
    'en': {'name': 'English', 'flag': '🇬🇧'},
    'fr': {'name': 'Français', 'flag': '🇫🇷'},
    'it': {'name': 'Italiano', 'flag': '🇮🇹'},
    'de': {'name': 'Deutsch', 'flag': '🇩🇪'},
    'es': {'name': 'Español', 'flag': '🇪🇸'},
    'pt': {'name': 'Português', 'flag': '🇵🇹'},
    'tr': {'name': 'Türkçe', 'flag': '🇹🇷'},
    'ar': {'name': 'العربية', 'flag': '🇸🇦'},
    'zh': {'name': '中文', 'flag': '🇨🇳'},
    'ja': {'name': '日本語', 'flag': '🇯🇵'},
    'ko': {'name': '한국어', 'flag': '🇰🇷'},
}

stock_cache: Dict[str, Dict] = {
    "seeds": {"items": [], "last_update": None},
    "gear": {"items": [], "last_update": None},
    "crates": {"items": [], "last_update": None},
}
item_database: Dict = {}
previous_stock: Dict[str, List[str]] = {}
last_restock_time: Optional[datetime] = None
next_restock_time: Optional[datetime] = None
restock_notified: bool = False

support_messages: Dict[int, Dict] = {}

weather_cache: Dict = {}
previous_weather: Optional[str] = None

predict_cache: Dict = {
    "seeds": [],
    "gear": [],
    "crates": [],
    "next_restock": None,
    "last_update": None
}
active_stock_displays: Dict[int, int] = {}

def get_stock_countdown_str() -> str:
    if not last_restock_time:
        return "таймер запускается..."
    
    now = datetime.now(timezone.utc)
    target = last_restock_time + timedelta(seconds=RESTOCK_INTERVAL)
    rem = int((target - now).total_seconds())
    
    if rem <= 0:
        return "обновление стока..."
        
    m = rem // 60
    s = rem % 60
    return f"{m}м {s}с"

def generate_stock_text() -> str:
    text = "📊 Актуальные стоки\n"
    text += "─" * 20 + "\n\n"
    
    seeds = get_items_for_display("seeds")
    text += create_category_header("Seeds", "🌱", len(seeds))
    if not seeds:
        text += "   ❌ Нет предметов\n"
    else:
        for item in seeds:
            text += create_item_line(item)
    text += create_category_footer()
    
    gear = get_items_for_display("gear")
    text += create_category_header("Gears", "🛠️", len(gear))
    if not gear:
        text += "   ❌ Нет предметов\n"
    else:
        for item in gear:
            text += create_item_line(item)
    text += create_category_footer()
    
    crates = get_items_for_display("crates")
    text += create_category_header("Crates", "📦", len(crates))
    if not crates:
        text += "   ❌ Нет предметов\n"
    else:
        for item in crates:
            text += create_item_line(item)
    text += create_category_footer()
    
    if next_restock_time:
        countdown = get_stock_countdown_str()
        text += f"\n⏱️ Сток: {format_restock_time(next_restock_time)} (МСК)\n⏳ До обновления: <b>{countdown}</b>"
    
    return text

def clear_active_stock(user_id: int):
    active_stock_displays.pop(user_id, None)

FALLBACK_PRICES = {
    # Seeds
    "carrot": "1",
    "strawberry": "10",
    "blueberry": "25",
    "tulip": "40",
    "tomato": "200",
    "apple": "400",
    "bamboo": "700",
    "corn": "2500",
    "cactus": "5000",
    "pineapple": "30000",
    "mushroom": "15000",
    "green_bean": "20000",
    "banana": "30000",
    "grape": "50000",
    "coconut": "140000",
    "mango": "300000",
    "dragon_fruit": "120000",
    "acorn": "700000",
    "cherry": "1200000",
    "sunflower": "5000000",
    "venus_fly_trap": "7000000",
    "pomegranate": "12000000",
    "poison_apple": "25000000",
    "moon_bloom": "65000000",
    "dragons_breath": "90000000",
    
    # Crates
    "ladder_crate": "30000",
    "bench_crate": "60000",
    "light_crate": "90000",
    "sign_crate": "150000",
    "arch_crate": "200000",
    "roleplay_crate": "300000",
    "bridge_crate": "700000",
    "conveyor_crate": "700000",
    "spring_crate": "900000",
    "seesaw_crate": "1500000",
    "owner_door_crate": "1500000",
    "bear_trap_crate": "TBA",
    "fence_crate": "7000000",
    "teleporter_pad_crate": "20000000",
    
    # Gears
    "common_sprinkler": "3000",
    "common_watering_can": "2000",
    "sign": "4000",
    "uncommon_sprinkler": "10000",
    "rare_sprinkler": "80000",
    "trowel": "1000",
    "jump_mushroom": "1800",
    "speed_mushroom": "1500",
    "lantern": "12000",
    "megaphone": "4000",
    "shrink_mushroom": "10000",
    "supersize_mushroom": "4500",
    "gnome": "100000",
    "flashbang": "20000",
    "basic_pot": "300000",
    "legendary_sprinkler": "1200000",
    "teleporter": "60000",
    "invisibility_mushroom": "30000",
    "wheelbarrow": "500000",
    "player_magnet": "7000000",
    "strawberry_sniper": "13000000",
    "super_watering_can": "1000000",
    "super_sprinkler": "3000000",
    "grappling_hook": "10000000"
}

FALLBACK_RARITIES = {
    # Seeds
    "carrot": "common",
    "strawberry": "common",
    "blueberry": "common",
    "tulip": "uncommon",
    "tomato": "uncommon",
    "apple": "uncommon",
    "bamboo": "rare",
    "corn": "rare",
    "cactus": "rare",
    "pineapple": "rare",
    "mushroom": "epic",
    "green_bean": "epic",
    "banana": "epic",
    "grape": "epic",
    "coconut": "epic",
    "mango": "epic",
    "dragon_fruit": "legendary",
    "acorn": "legendary",
    "cherry": "legendary",
    "sunflower": "legendary",
    "venus_fly_trap": "mythic",
    "pomegranate": "mythic",
    "poison_apple": "mythic",
    "moon_bloom": "super",
    "dragons_breath": "super",
    "dragon_s_breath": "super",
    "baby_cactus": "rare",
    "beanstalk": "secret",
    "briar_rose": "mythic",
    "ghost_pepper": "mythic",
    "glow_mushroom": "epic",
    "horned_melon": "rare",
    "hypno_bloom": "super",
    "poison_ivy": "legendary",
    "romanesco": "mythic",
    "venom_spitter": "mythic",
    
    # Gears
    "common_watering_can": "common",
    "common_sprinkler": "common",
    "trowel": "common",
    "speed_mushroom": "common",
    "sign": "uncommon",
    "uncommon_sprinkler": "uncommon",
    "rare_sprinkler": "rare",
    "lantern": "rare",
    "jump_mushroom": "rare",
    "shrink_mushroom": "rare",
    "supersize_mushroom": "rare",
    "flashbang": "epic",
    "basic_pot": "epic",
    "megaphone": "epic",
    "invisibility_mushroom": "epic",
    "teleporter": "epic",
    "wheelbarrow": "epic",
    "gnome": "legendary",
    "legendary_sprinkler": "legendary",
    "super_watering_can": "legendary",
    "player_magnet": "legendary",
    "grappling_hook": "mythic",
    "super_sprinkler": "mythic",
    "strawberry_sniper": "mythic",

    # Crates
    "ladder_crate": "common",
    "bench_crate": "uncommon",
    "light_crate": "uncommon",
    "sign_crate": "uncommon",
    "arch_crate": "rare",
    "roleplay_crate": "rare",
    "bridge_crate": "epic",
    "conveyor_crate": "epic",
    "spring_crate": "epic",
    "seesaw_crate": "epic",
    "owner_door_crate": "legendary",
    "bear_trap_crate": "legendary",
    "fence_crate": "legendary",
    "teleporter_pad_crate": "mythic",
    "common_guild_crate": "common",
    "uncommon_guild_crate": "uncommon",
    "rare_guild_crate": "rare",
    "epic_guild_crate": "epic",
    "legendary_guild_crate": "legendary",
    "mythic_guild_crate": "mythic",
    "super_guild_crate": "super",
}

RARITY_ORDER = [
    'super', 'mythic', 'legendary', 'epic', 
    'rare', 'uncommon', 'common'
]

RARITY_EMOJIS = {
    'super': '⭐️',
    'mythic': '🟡',
    'legendary': '🔴',
    'epic': '🟣',
    'rare': '🔵',
    'uncommon': '🟢',
    'common': '⚪️'
}

RARITY_NAMES = {
    'super': 'Супер',
    'mythic': 'Мифический',
    'legendary': 'Легендарный',
    'epic': 'Эпический',
    'rare': 'Редкий',
    'uncommon': 'Необычный',
    'common': 'Обычный'
}

RARITY_EMOJIS_FULL = {
    'super': '🌟',
    'mythic': '💎',
    'legendary': '🔴',
    'epic': '🟣',
    'rare': '🔵',
    'uncommon': '🟢',
    'common': '⚪️'
}

WEATHER_EMOJIS = {
    'rain': '🌧️',
    'lightning': '⚡',
    'thunder': '⛈️',
    'rainbow': '🌈',
    'snowfall': '❄️',
    'starfall': '🌠',
    'blood moon': '🌕',
    'bloodmoon': '🌕',
    'gold moon': '🟡',
    'midas': '🟡',
    'rainbow moon': '🌈',
    'rainbowmoon': '🌈',
    'clear': '☀️',
    'none': '☀️'
}

CATEGORY_EMOJIS = {'seeds': '🌱', 'gear': '🛠️', 'crates': '📦'}
CATEGORY_NAMES = {'seeds': 'Seeds', 'gear': 'Gears', 'crates': 'Crates'}

SEED_EMOJIS = {
    'carrot': '🥕',
    'strawberry': '🍓',
    'blueberry': '🫐',
    'tulip': '🌷',
    'tomato': '🍅',
    'apple': '🍎',
    'bamboo': '🎋',
    'corn': '🌽',
    'cactus': '🌵',
    'pineapple': '🍍',
    'mushroom': '🍄',
    'green bean': '🫘',
    'banana': '🍌',
    'grape': '🍇',
    'coconut': '🥥',
    'mango': '🥭',
    'dragon fruit': '🐉',
    'acorn': '🌰',
    'cherry': '🍒',
    'sunflower': '🌻',
    'venus fly trap': '🪴',
    'pomegranate': '🍎',
    'poison apple': '☠️',
    'venom spitter': '💀',
    'moon bloom': '🌙',
    "dragon's breath": '🔥',
    'pumpkin': '🎃',
    'lotus': '🪷',
    'beanstalk': '🌱',
    'glow mushroom': '🍄',
    'thorn rose': '🌹',
    'poison ivy': '☘️',
    'ghost pepper': '🌶️',
    'baby cactus': '🌵',
    'romanesco': '🥦',
    'horned melon': '🍈',
    'pinetree': '🌲',
}

GEAR_EMOJIS = {
    'trowel': '🔧',
    'shovel': '⛏️',
    'rake': '🧹',
    'watering can': '💧',
    'common sprinkler': '💦',
    'uncommon sprinkler': '💦',
    'rare sprinkler': '💦',
    'legendary sprinkler': '💦',
    'super sprinkler': '💦',
    'common watering can': '💧',
    'super watering can': '💧',
    'gnome': '🧝',
    'lantern': '🏮',
    'sign': '📋',
    'teleporter': '🌀',
    'wheelbarrow': '🛒',
    'rainbow': '🌈',
    'freeze ray': '❄️',
    'flashbang': '💥',
    'door crowbar': '🔓',
    'speed mushroom': '⚡',
    'jump mushroom': '⬆️',
    'shrink mushroom': '⬇️',
    'supersize mushroom': '⬆️',
    'megaphone': '📢',
    'basic pot': '🪴',
    'player magnet': '🧲',
    'strawberry sniper': '🎯',
    'invisibility mushroom': '👻',
}

CRATE_EMOJIS = {
    'fence': '🪵',
    'bridge': '🌉',
    'ladder': '🪜',
    'light': '💡',
    'spring': '🔄',
    'seesaw': '⚖️',
    'conveyor': '⚙️',
    'bear trap': '🐻',
    'owner door': '🚪',
    'roleplay': '🎭',
    'teleporter pad': '🌀',
}

def create_category_header(name: str, emoji: str, count: int) -> str:
    line = "─" * 8
    return f"\n{emoji} {line} {name} {line} {emoji}\n"

def create_category_footer() -> str:
    return "─" * 20 + "\n"

def create_item_line(item: Dict) -> str:
    name = item["name"]
    rarity = item["rarity"]
    price = item["price"]
    quantity = item["quantity"]
    emoji = item["emoji"]
    
    rarity_emoji = get_rarity_emoji(rarity)
    rarity_name = get_rarity_name(rarity)
    
    if not emoji:
        emoji = "🟫"
    
    extra_info = ""
    if item.get("seed_price") and item.get("crop_price"):
        extra_info += f"      └ 🌱 {format_cost(item['seed_price'])} | 🍎 {format_cost(item['crop_price'])}\n"
    if item.get("stock_range"):
        extra_info += f"      └ 📦 {item['stock_range']}\n"
    
    return (
        f"   {rarity_emoji} {emoji} <b>{name}</b>\n"
        f"      └ 💰 {format_cost(price)} ×{quantity}\n"
        f"      └ {rarity_name}\n"
        f"{extra_info}"
    )

def format_cost(cost) -> str:
    if cost is None or cost == 'None' or cost == 'TBA':
        return "TBA"
    try:
        if isinstance(cost, str):
            cost = cost.replace(',', '').replace('K', '000').replace('M', '000000')
        c = int(str(cost).replace(',', ''))
        if c >= 1000000:
            return f"{c/1000000:.1f}M"
        elif c >= 1000:
            return f"{c/1000:.1f}K"
        else:
            return str(c)
    except:
        return str(cost)

def get_rarity_emoji(rarity: str) -> str:
    rarity_lower = rarity.lower()
    return RARITY_EMOJIS.get(rarity_lower, '⚪️')

def get_rarity_emoji_full(rarity: str) -> str:
    rarity_lower = rarity.lower()
    return RARITY_EMOJIS_FULL.get(rarity_lower, '⚪️')

def get_rarity_name(rarity: str, lang: str = 'ru') -> str:
    rarity_lower = rarity.lower()
    if lang == 'ru':
        return RARITY_NAMES.get(rarity_lower, rarity)
    return rarity.capitalize()

def get_rarity_index(rarity: str) -> int:
    rarity_lower = rarity.lower()
    try:
        return RARITY_ORDER.index(rarity_lower)
    except ValueError:
        return len(RARITY_ORDER)

def normalize_name(name: str) -> str:
    return name.lower().replace("'", "").replace(" ", "_")

def get_emoji_for_item(name: str, category: str) -> str:
    name_lower = name.lower()
    
    if category == "seeds":
        for key, emoji in SEED_EMOJIS.items():
            if key in name_lower or name_lower in key:
                return emoji
        return "🌱"
    
    elif category == "gear":
        for key, emoji in GEAR_EMOJIS.items():
            if key in name_lower or name_lower in key:
                return emoji
        return "🛠️"
    
    elif category == "crates":
        for key, emoji in CRATE_EMOJIS.items():
            if key in name_lower or name_lower in key:
                return emoji
        return "📦"
    
    return "🟫"

def get_weather_emoji(weather_name: str) -> str:
    name_lower = weather_name.lower()
    for key, emoji in WEATHER_EMOJIS.items():
        if key in name_lower or name_lower in key:
            return emoji
    return "🌤️"

def get_moscow_time() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=3)

def format_restock_time(dt: datetime) -> str:
    moscow_time = dt + timedelta(hours=3)
    return moscow_time.strftime("%d.%m в %H:%M")

def format_weather_time(dt: datetime) -> str:
    moscow_time = dt + timedelta(hours=3)
    return moscow_time.strftime("%H:%M")

def get_time_of_day() -> str:
    now = get_moscow_time()
    hour = now.hour
    
    if 6 <= hour < 12:
        return "🌅 Утро"
    elif 12 <= hour < 18:
        return "☀️ День"
    elif 18 <= hour < 22:
        return "🌅 Вечер"
    else:
        return "🌙 Ночь"

def get_time_of_day_emoji() -> str:
    now = get_moscow_time()
    hour = now.hour
    
    if 6 <= hour < 12:
        return "🌅"
    elif 12 <= hour < 18:
        return "☀️"
    elif 18 <= hour < 22:
        return "🌅"
    else:
        return "🌙"

def get_current_moscow_time() -> str:
    now = get_moscow_time()
    return now.strftime("%H:%M:%S")

async def fetch_from_api(endpoint: str) -> Optional[Dict]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}/{endpoint}", timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success", True):
                        return data
                return None
    except Exception as e:
        logger.error(f"Ошибка API {endpoint}: {e}")
        return None

async def fetch_items_database() -> bool:
    global item_database
    data = await fetch_from_api("api/items")
    if data:
        item_database = data
        logger.info(f"Загружено {len(item_database)} предметов")
        return True
    return False

async def fetch_stock(category: str) -> Optional[Dict]:
    return await fetch_from_api(f"stock?category={category}")

async def fetch_weather() -> Optional[Dict]:
    return await fetch_from_api("weather")

async def fetch_predict() -> Optional[Dict]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.growagarden2stock.com/api/predictions", timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Convert updatedAt in milliseconds to seconds
                    updated_at_ms = data.get("updatedAt", 0)
                    updated_at_sec = int(updated_at_ms / 1000) if updated_at_ms > 1000000000000 else int(datetime.now(timezone.utc).timestamp())
                    
                    # Use current local timestamp as now_sec
                    now_sec = int(datetime.now(timezone.utc).timestamp())
                    
                    # Group seeds by timestamp
                    seeds_by_time = {}
                    for item in data.get("seeds", []):
                        ts = item.get("timestamp")
                        if not ts:
                            continue
                        name = item.get("name")
                        key = normalize_name(name)
                        db_item = item_database.get(key, {})
                        rarity = db_item.get("rarity", "Common").lower()
                        
                        seeds_by_time.setdefault(ts, []).append({
                            "name": name,
                            "rarity": rarity,
                            "qty": "?"
                        })
                    
                    upcoming_seeds = []
                    for ts, items in sorted(seeds_by_time.items()):
                        upcoming_seeds.append({
                            "time": ts,
                            "items": items
                        })
                        
                    # Group gears by timestamp (only gears, no props!)
                    gears_by_time = {}
                    for item in data.get("gears", []):
                        ts = item.get("timestamp")
                        if not ts:
                            continue
                        name = item.get("name")
                        key = normalize_name(name)
                        db_item = item_database.get(key, {})
                        rarity = db_item.get("rarity", "Common").lower()
                        
                        gears_by_time.setdefault(ts, []).append({
                            "name": name,
                            "rarity": rarity,
                            "qty": "?"
                        })
                        
                    upcoming_gears = []
                    for ts, items in sorted(gears_by_time.items()):
                        upcoming_gears.append({
                            "time": ts,
                            "items": items
                        })

                    # Group props (crates) by timestamp
                    crates_by_time = {}
                    for item in data.get("props", []):
                        ts = item.get("timestamp")
                        if not ts:
                            continue
                        name = item.get("name")
                        key = normalize_name(name)
                        db_item = item_database.get(key, {})
                        rarity = db_item.get("rarity", "Common").lower()
                        
                        crates_by_time.setdefault(ts, []).append({
                            "name": name,
                            "rarity": rarity,
                            "qty": "?"
                        })
                        
                    upcoming_crates = []
                    for ts, items in sorted(crates_by_time.items()):
                        upcoming_crates.append({
                            "time": ts,
                            "items": items
                        })
                        
                    next_restock_ts = ((now_sec // 300) + 1) * 300
                    remaining = next_restock_ts - now_sec
                    
                    if remaining > 0:
                        m = remaining // 60
                        s = remaining % 60
                        next_restock_str = f"{m}м {s}с"
                    else:
                        next_restock_str = "0м 0с"
                    
                    seeds_entry = None
                    for entry in upcoming_seeds:
                        if entry.get("time") == next_restock_ts:
                            seeds_entry = entry
                            break
                    if not seeds_entry and upcoming_seeds:
                        for entry in upcoming_seeds:
                            if entry.get("time") >= now_sec:
                                seeds_entry = entry
                                next_restock_ts = entry.get("time")
                                remaining = next_restock_ts - now_sec
                                m = remaining // 60
                                s = remaining % 60
                                next_restock_str = f"{m}м {s}с"
                                break
                        if not seeds_entry:
                            seeds_entry = upcoming_seeds[-1]
                    
                    gears_entry = None
                    for entry in upcoming_gears:
                        if entry.get("time") == next_restock_ts:
                            gears_entry = entry
                            break
                    if not gears_entry and upcoming_gears:
                        for entry in upcoming_gears:
                            if entry.get("time") >= now_sec:
                                gears_entry = entry
                                break
                        if not gears_entry:
                            gears_entry = upcoming_gears[-1]

                    crates_entry = None
                    for entry in upcoming_crates:
                        if entry.get("time") == next_restock_ts:
                            crates_entry = entry
                            break
                    if not crates_entry and upcoming_crates:
                        for entry in upcoming_crates:
                            if entry.get("time") >= now_sec:
                                crates_entry = entry
                                break
                        if not crates_entry:
                            crates_entry = upcoming_crates[-1]
                    
                    seeds_list = []
                    if seeds_entry:
                        for item in seeds_entry.get("items", []):
                            name = item.get("name", "")
                            qty = item.get("qty", "?")
                            rarity = item.get("rarity", "Common").lower()
                            
                            key = normalize_name(name)
                            db_item = item_database.get(key, {})
                            
                            fallback_price = "TBA"
                            if key in FALLBACK_PRICES:
                                fallback_price = FALLBACK_PRICES[key]
                            
                            price = db_item.get("shecklePrice") or fallback_price
                            
                            seeds_list.append({
                                "name": name,
                                "price": format_cost(price),
                                "quantity": str(qty),
                                "rarity": rarity,
                                "emoji": get_emoji_for_item(name, "seeds")
                            })
                    
                    gear_list = []
                    if gears_entry:
                        for item in gears_entry.get("items", []):
                            name = item.get("name", "")
                            qty = item.get("qty", "?")
                            rarity = item.get("rarity", "Common").lower()
                            
                            key = normalize_name(name)
                            db_item = item_database.get(key, {})
                            
                            fallback_price = "TBA"
                            if key in FALLBACK_PRICES:
                                fallback_price = FALLBACK_PRICES[key]
                                
                            price = db_item.get("shecklePrice") or fallback_price
                            
                            gear_list.append({
                                "name": name,
                                "price": format_cost(price),
                                "quantity": str(qty),
                                "rarity": rarity,
                                "emoji": get_emoji_for_item(name, "gear")
                            })

                    crates_list = []
                    if crates_entry:
                        for item in crates_entry.get("items", []):
                            name = item.get("name", "")
                            qty = item.get("qty", "?")
                            rarity = item.get("rarity", "Common").lower()
                            
                            key = normalize_name(name)
                            db_item = item_database.get(key, {})
                            
                            fallback_price = "TBA"
                            if key in FALLBACK_PRICES:
                                fallback_price = FALLBACK_PRICES[key]
                                
                            price = db_item.get("shecklePrice") or fallback_price
                            
                            crates_list.append({
                                "name": name,
                                "price": format_cost(price),
                                "quantity": str(qty),
                                "rarity": rarity,
                                "emoji": get_emoji_for_item(name, "crates")
                            })
                    
                    seeds_list.sort(key=lambda x: get_rarity_index(x["rarity"]))
                    gear_list.sort(key=lambda x: get_rarity_index(x["rarity"]))
                    crates_list.sort(key=lambda x: get_rarity_index(x["rarity"]))
                    
                    logger.info(f"✅ Предикт обновлен: {len(seeds_list)} семян, {len(gear_list)} орудий, {len(crates_list)} ящиков")
                    
                    return {
                        "seeds": seeds_list,
                        "gear": gear_list,
                        "crates": crates_list,
                        "next_restock": next_restock_str,
                        "last_update": datetime.now(timezone.utc),
                        "raw_weather": data.get("weathers", []),
                        "raw_now": now_sec,
                        "upcoming_seeds": upcoming_seeds,
                        "upcoming_gears": upcoming_gears,
                        "upcoming_crates": upcoming_crates
                    }
    except Exception as e:
        logger.error(f"Ошибка fetch_predict: {e}")
    return None

async def update_stock_data():
    global stock_cache, previous_stock, last_restock_time, next_restock_time, restock_notified
    
    logger.info("🔄 Обновление стоков...")
    
    if not item_database:
        await fetch_items_database()
    
    new_legendary_items = []
    new_stock_items = []
    current_all_items = {}
    
    for category in ["seeds", "gear", "crates"]:
        data = await fetch_stock(category)
        if data:
            items = data.get("items", [])
            in_stock_items = [
                item for item in items 
                if item.get("in_stock") == 1 or item.get("in_stock") == True
            ]
            
            current_all_items[category] = [item.get("item_name", "").lower() for item in in_stock_items]
            
            for item in in_stock_items:
                name = item.get("item_name", "")
                key = normalize_name(name)
                db_item = item_database.get(key, {})
                
                # Resolve rarity using database, item payload, and FALLBACK_RARITIES
                rarity = db_item.get("rarity") or item.get("rarity")
                if rarity is None or rarity == "" or rarity.lower() == "common":
                    if key in FALLBACK_RARITIES:
                        rarity = FALLBACK_RARITIES[key]
                    else:
                        rarity = rarity or "common"
                rarity = rarity.lower()
                
                # Resolve price using database, item payload, and FALLBACK_PRICES
                price_val = db_item.get("shecklePrice") or item.get("price")
                if price_val is None or str(price_val).strip().lower() in ['none', 'tba', '']:
                    if key in FALLBACK_PRICES:
                        price_val = FALLBACK_PRICES[key]
                    else:
                        price_val = "TBA"
                
                prev_items = previous_stock.get(category, [])
                if name.lower() not in prev_items:
                    item_info = {
                        "name": name,
                        "category": category,
                        "rarity": rarity,
                        "price": price_val,
                        "quantity": item.get("quantity", "?"),
                        "emoji": get_emoji_for_item(name, category),
                        "seed_price": db_item.get("seed_price"),
                        "crop_price": db_item.get("crop_price"),
                        "stock_range": db_item.get("stock")
                    }
                    new_stock_items.append(item_info)
                    allowed_keys = ['moon_bloom', 'dragons_breath', 'dragon_s_breath', 'super_sprinkler', 'super_watering_can']
                    if key in allowed_keys and category != 'crates':
                        new_legendary_items.append(item_info)
            
            stock_cache[category]["items"] = in_stock_items
            stock_cache[category]["last_update"] = datetime.now(timezone.utc)
            logger.info(f"✅ {category}: {len(in_stock_items)}/{len(items)} в наличии")
    
    previous_stock = current_all_items
    
    now = datetime.now(timezone.utc)
    if last_restock_time is None or (now - last_restock_time).total_seconds() > RESTOCK_INTERVAL:
        last_restock_time = now
        next_restock_time = now
        restock_notified = False
        logger.info(f"🔄 Новый ресток в {format_restock_time(next_restock_time)} (МСК)")
    
    if new_legendary_items:
        await notify_legendary_items(new_legendary_items)
        
    if new_stock_items:
        await send_personal_notifications(new_stock_items)
    
    logger.info("✅ Стоки обновлены")

async def update_predict():
    global predict_cache
    data = await fetch_predict()
    if data:
        predict_cache = data
        logger.info(f"✅ Предикт обновлен: {len(data.get('seeds', []))} предметов")

async def update_weather():
    global weather_cache, previous_weather
    
    data = await fetch_weather()
    if not data:
        return
    
    current = data.get("current", {})
    if not current:
        return
    
    weather_name = current.get("weather_name", "Clear")
    
    if weather_name not in ["Clear", "None"] and weather_name != previous_weather:
        previous_weather = weather_name
        weather_cache = current
        
        await notify_weather_change(current)
    
    weather_cache = current

async def notify_weather_change(weather: Dict):
    weather_name = weather.get("weather_name", "")
    weather_emoji = get_weather_emoji(weather_name)
    started_at = weather.get("started_at")
    time_of_day = get_time_of_day()
    
    next_update = "скоро"
    if started_at:
        try:
            dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            next_update = format_weather_time(dt + timedelta(minutes=2))
        except:
            pass
    
    message = (
        f"🌦 ПОГОДА СМЕНИЛАСЬ!\n\n"
        f"{weather_emoji} {weather_name}\n"
        f"🕐 {time_of_day}\n"
        f"⏱️ Обновление: {next_update} (МСК)\n\n"
        f"👀 Включи уведомления в канале!\n\n"
        f"🌾 <a href='{BOT_LINK}'>{BOT_NAME}</a>"
    )
    
    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        logger.info(f"📤 Отправлена погода: {weather_name}")
    except Exception as e:
        logger.error(f"Ошибка отправки погоды: {e}")

async def send_personal_notifications(new_items: List[Dict]):
    if not new_items:
        return
        
    data = load_data()
    users = data.get("users", {})
    
    for user_id, info in users.items():
        tracked_items = info.get("tracked_items", [])
        if not tracked_items:
            continue
            
        tracked_lower = [x.lower() for x in tracked_items]
        
        user_items = []
        for item in new_items:
            item_name = item["name"].lower()
            if item_name in tracked_lower:
                user_items.append(item)
                
        if user_items:
            text = "🔄 <b>Новое обновление стока!</b>\n\nПоявились следующие интересующие вас предметы:\n\n"
            for item in user_items:
                rarity_emoji = get_rarity_emoji(item["rarity"])
                
                price_val = item.get("price")
                key = normalize_name(item["name"])
                if price_val is None or str(price_val).strip().lower() in ['none', 'tba', '']:
                    if key in FALLBACK_PRICES:
                        price_val = FALLBACK_PRICES[key]
                    else:
                        price_val = "TBA"
                        
                price = format_cost(price_val)
                text += f"   {rarity_emoji} {item['emoji']} <b>{item['name']}</b> (💰 {price} ×{item['quantity']})\n"
                
            text += f"\n📊 Откройте бота, чтобы посмотреть все стоки!"
            
            try:
                await bot.send_message(chat_id=int(user_id), text=text, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Не удалось отправить личное уведомление пользователю {user_id}: {e}")

async def send_to_all_channels(text: str):
    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Ошибка отправки в основной канал {CHANNEL_ID}: {e}")

async def send_to_connected_channels(text: str):
    data = load_data()
    channels = data.get("channels", [])
    if not channels:
        return
        
    channel_names = data.get("channel_names", {})
    active_channels = list(channels)
    changed = False
    
    for channel_id in channels:
        name_str = channel_names.get(channel_id, channel_id)
        try:
            await bot.send_message(
                chat_id=int(channel_id),
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except TelegramForbiddenError as e:
            logger.warning(f"Бот заблокирован/удален из чата {name_str} ({channel_id}), удаляем: {e}")
            if channel_id in active_channels:
                active_channels.remove(channel_id)
                changed = True
        except TelegramBadRequest as e:
            err_msg = str(e).lower()
            if "chat not found" in err_msg or "not member" in err_msg or "not enough rights" in err_msg:
                logger.warning(f"Удаляем чат {name_str} ({channel_id}) из-за ошибки прав/существования: {e}")
                if channel_id in active_channels:
                    active_channels.remove(channel_id)
                    changed = True
            else:
                logger.error(f"Ошибка запроса при отправке в чат {name_str} ({channel_id}): {e}")
        except Exception as e:
            logger.error(f"Временная ошибка отправки в чат {name_str} ({channel_id}): {e}")
            
    if changed:
        data["channels"] = active_channels
        save_data(data)

async def notify_legendary_items(items: List[Dict]):
    for item in items:
        rarity = item["rarity"]
        name = item["name"]
        emoji = item["emoji"]
        quantity = item["quantity"]
        price = format_cost(item["price"])
        
        rarity_lower = rarity.lower()
        if rarity_lower == 'legendary':
            rarity_name_feminine = 'Легендарная'
        elif rarity_lower == 'mythic':
            rarity_name_feminine = 'Мифическая'
        elif rarity_lower == 'super':
            rarity_name_feminine = 'Супер'
        else:
            rarity_name_feminine = rarity.capitalize()
            
        message = (
            f"📣 | Новая {rarity_name_feminine} в стоке!\n"
            f"{emoji} <b>{name}</b> - 💰 {price} - {quantity} шт.\n\n"
            f"<blockquote>успел забрать ⁉️</blockquote>\n"
            f"⚠️ <a href='{BOT_LINK}'>лучший бот по стокам</a>"
        )
        
        await send_to_all_channels(message)
        await send_to_connected_channels(message)

def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {"sponsors": [], "users": {}, "user_languages": {}, "channels": []}
        save_data(default_data)
        return default_data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user_language(user_id: int) -> str:
    data = load_data()
    return data.get("user_languages", {}).get(str(user_id), "")

def set_user_language(user_id: int, lang: str):
    data = load_data()
    if "user_languages" not in data:
        data["user_languages"] = {}
    data["user_languages"][str(user_id)] = lang
    save_data(data)

async def check_user_subscription(user_id: int, channel: str) -> bool:
    if user_id in ADMIN_IDS:
        return True
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator', 'restricted']
    except Exception as e:
        err_msg = str(e).lower()
        if "user not found" in err_msg or "member not found" in err_msg:
            return False
        logger.warning(f"Проверка подписки в {channel} пропущена из-за ошибки: {e}")
        return True

async def is_user_subscribed(user_id: int, force_check: bool = False) -> bool:
    if user_id in ADMIN_IDS:
        return True
        
    data = load_data()
    current_time = datetime.now(timezone.utc).timestamp()
    
    if "users" not in data:
        data["users"] = {}
        
    user_cache = data["users"].get(str(user_id), {})
    if not force_check and user_cache:
        last_check = user_cache.get("last_check", 0)
        if current_time - last_check < CHECK_CACHE_TIME:
            return user_cache.get("subscribed", False)
            
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {
            "first_seen": datetime.now(timezone.utc).isoformat()
        }
    
    if not await check_user_subscription(user_id, CHANNEL_ID):
        data["users"][str(user_id)]["subscribed"] = False
        data["users"][str(user_id)]["last_check"] = current_time
        save_data(data)
        return False
    
    for sponsor in data.get("sponsors", []):
        channel = sponsor.get("channel")
        if channel and not await check_user_subscription(user_id, channel):
            data["users"][str(user_id)]["subscribed"] = False
            data["users"][str(user_id)]["last_check"] = current_time
            save_data(data)
            return False
            
    data["users"][str(user_id)]["subscribed"] = True
    data["users"][str(user_id)]["last_check"] = current_time
    save_data(data)
    return True

def get_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Сток", callback_data="view_stock"),
        InlineKeyboardButton(text="🔮 Предикт", callback_data="view_predict"),
        InlineKeyboardButton(text="🌤 Погода", callback_data="view_weather")
    )
    builder.row(
        InlineKeyboardButton(text="⏱ Автостоки", callback_data="auto_stock"),
        InlineKeyboardButton(text="📢 Подключить канал", callback_data="auto_stock_channel")
    )
    builder.row(
        InlineKeyboardButton(text="🆘 Поддержка", callback_data="support")
    )
    if user_id in ADMIN_IDS:
        builder.row(
            InlineKeyboardButton(text="⚙️ Админ", callback_data="admin_panel")
        )
    return builder.as_markup()

def get_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить спонсора", callback_data="admin_add_sponsor"),
        InlineKeyboardButton(text="📋 Список", callback_data="admin_list_sponsors")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить", callback_data="admin_remove_sponsor"),
        InlineKeyboardButton(text="📊 Пользователи", callback_data="admin_list_users")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_refresh_stock"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    return builder.as_markup()

def get_subscribe_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    channel_url = f"https://t.me/{CHANNEL_ID.replace('@', '')}"
    builder.row(
        InlineKeyboardButton(text="📢 Подписаться на канал", url=channel_url)
    )
    builder.row(
        InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subscription")
    )
    return builder.as_markup()

def get_language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    langs = list(LANGUAGES.items())
    for i in range(0, len(langs), 3):
        row = []
        for lang_code, lang_info in langs[i:i+3]:
            row.append(InlineKeyboardButton(
                text=f"{lang_info['flag']} {lang_info['name']}",
                callback_data=f"set_lang_{lang_code}"
            ))
        builder.row(*row)
    return builder.as_markup()

def get_auto_stock_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔔 Вкл", callback_data="auto_stock_on"),
        InlineKeyboardButton(text="🔕 Выкл", callback_data="auto_stock_off")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    return builder.as_markup()

def get_support_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✍️ Написать", callback_data="support_write")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    return builder.as_markup()

def get_admin_reply_keyboard(user_id: int, msg_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💬 Ответить", callback_data=f"admin_reply_{user_id}_{msg_id}"),
        InlineKeyboardButton(text="❌ Отменить", callback_data=f"admin_cancel_{user_id}_{msg_id}")
    )
    return builder.as_markup()

def get_items_for_display(category: str) -> List[Dict]:
    items = stock_cache.get(category, {}).get("items", [])
    
    enriched = []
    for item in items:
        name = item.get("item_name", "")
        key = normalize_name(name)
        db_item = item_database.get(key, {})
        
        # Resolve rarity using database, item payload, and FALLBACK_RARITIES
        rarity = db_item.get("rarity") or item.get("rarity")
        if rarity is None or rarity == "" or rarity.lower() == "common":
            if key in FALLBACK_RARITIES:
                rarity = FALLBACK_RARITIES[key]
            else:
                rarity = rarity or "common"
        rarity = rarity.lower()

        price = db_item.get("shecklePrice") or item.get("price")
        if price is None or str(price).strip().lower() in ['none', 'tba', '']:
            if key in FALLBACK_PRICES:
                price = FALLBACK_PRICES[key]
            else:
                price = "TBA"
        
        emoji = get_emoji_for_item(name, category)
        
        enriched.append({
            "name": name,
            "rarity": rarity,
            "price": str(price),
            "quantity": item.get("quantity", "?"),
            "emoji": emoji,
            "seed_price": db_item.get("seed_price"),
            "crop_price": db_item.get("crop_price"),
            "stock_range": db_item.get("stock")
        })
    
    enriched.sort(key=lambda x: get_rarity_index(x["rarity"]))
    return enriched

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    clear_active_stock(user_id)
    
    data = load_data()
    
    if "users" not in data:
        data["users"] = {}
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }
        save_data(data)
    
    lang = get_user_language(user_id)
    if not lang:
        await message.answer(
            "🌍 <b>Выберите ваш язык / Choose your language:</b>",
            reply_markup=get_language_keyboard(),
            parse_mode="HTML"
        )
        return
        
    if not await is_user_subscribed(user_id):
        text = f"🌱 <b>Grow a Garden 2 Stock Bot</b>\n\n"
        text += f"📢 Для доступа подпишись на канал:\n{CHANNEL_ID}\n\n"
        
        sponsors = data.get("sponsors", [])
        if sponsors:
            text += "📢 <b>А также на спонсоров:</b>\n"
            for sponsor in sponsors:
                channel = sponsor.get("channel", "")
                link = sponsor.get("link", "")
                text += f"• {channel}: {link}\n"
        
        text += "\n⬇️ После подписки нажми кнопку ниже."
        
        await message.answer(text, reply_markup=get_subscribe_keyboard(), parse_mode="HTML")
        return
    
    if not stock_cache["seeds"]["items"]:
        await update_stock_data()
    
    await message.answer(
        "🌱 <b>Grow a Garden 2 Биржа</b>\n\n"
        "📊 Выберите действие:",
        reply_markup=get_main_keyboard(user_id),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("set_lang_"))
async def set_language(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_active_stock(user_id)
    lang_code = callback.data.replace("set_lang_", "")
    
    if lang_code in LANGUAGES:
        set_user_language(user_id, lang_code)
        await callback.answer(f"✅ Язык установлен: {LANGUAGES[lang_code]['name']}")
        
        await callback.message.delete()
        
        if not await is_user_subscribed(user_id):
            data = load_data()
            text = f"🌱 <b>Grow a Garden 2 Stock Bot</b>\n\n"
            text += f"📢 Для доступа подпишись на канал:\n{CHANNEL_ID}\n\n"
            
            sponsors = data.get("sponsors", [])
            if sponsors:
                text += "📢 <b>А также на спонсоров:</b>\n"
                for sponsor in sponsors:
                    channel = sponsor.get("channel", "")
                    link = sponsor.get("link", "")
                    text += f"• {channel}: {link}\n"
            
            text += "\n⬇️ После подписки нажми кнопку ниже."
            await callback.message.answer(text, reply_markup=get_subscribe_keyboard(), parse_mode="HTML")
        else:
            await callback.message.answer(
                "🌱 <b>Grow a Garden 2 Биржа</b>\n\n"
                "📊 Выберите действие:",
                reply_markup=get_main_keyboard(user_id),
                parse_mode="HTML"
            )

@dp.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_active_stock(user_id)
    
    if await is_user_subscribed(user_id, force_check=True):
        await callback.message.delete()
        
        await callback.message.answer(
            "✅ <b>Подписка подтверждена!</b>\n\n"
            "🌱 Добро пожаловать!",
            reply_markup=get_main_keyboard(user_id),
            parse_mode="HTML"
        )
        await callback.answer("✅ Подписка подтверждена!")
    else:
        data = load_data()
        sponsors = data.get("sponsors", [])
        
        text = "❌ <b>Вы не подписаны на все каналы!</b>\n\n"
        text += f"📢 Основной канал: {CHANNEL_ID}\n"
        
        if sponsors:
            text += "\n📢 <b>Спонсоры:</b>\n"
            for sponsor in sponsors:
                channel = sponsor.get("channel", "")
                link = sponsor.get("link", "")
                text += f"• {channel}: {link}\n"
        
        text += "\n⬇️ После подписки нажмите кнопку ниже."
        
        await callback.message.edit_text(
            text,
            reply_markup=get_subscribe_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer("❌ Вы не подписаны!", show_alert=True)

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_active_stock(user_id)
    
    if not await is_user_subscribed(user_id):
        await callback.answer("❌ Подписка не подтверждена!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🌱 <b>Grow a Garden 2 Биржа</b>\n\n"
        "📊 Выберите действие:",
        reply_markup=get_main_keyboard(user_id),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "view_stock")
async def view_stock(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_user_subscribed(user_id):
        await callback.answer("❌ Подписка не подтверждена!", show_alert=True)
        return
    
    if not stock_cache["seeds"]["items"]:
        await update_stock_data()
    
    text = generate_stock_text()
    
    await callback.message.edit_text(
        text,
        reply_markup=get_main_keyboard(user_id),
        parse_mode="HTML"
    )
    
    active_stock_displays[user_id] = callback.message.message_id

def get_predict_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌱 Семена", callback_data="predict_seeds"),
        InlineKeyboardButton(text="🛠️ Инструменты", callback_data="predict_gears"),
        InlineKeyboardButton(text="📦 Ящики", callback_data="predict_crates")
    )
    builder.row(
        InlineKeyboardButton(text="🚪 Выйти", callback_data="back_to_main")
    )
    return builder.as_markup()

def get_predict_back_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="view_predict")
    )
    return builder.as_markup()

@dp.callback_query(F.data == "view_predict")
async def view_predict(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_active_stock(user_id)
    
    if not await is_user_subscribed(user_id):
        await callback.answer("❌ Подписка не подтверждена!", show_alert=True)
        return
        
    text = "🔮 <b>Предикт стоков</b>\n"
    text += "─" * 15 + "\n\n"
    text += "Выберите категорию прогнозов:"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_predict_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "predict_seeds")
async def predict_seeds(callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_user_subscribed(user_id):
        await callback.answer("❌ Подписка не подтверждена!", show_alert=True)
        return
        
    if not predict_cache.get("seeds"):
        await update_predict()
        
    now_sec = predict_cache.get("raw_now")
    if not now_sec:
        now_sec = int(datetime.now(timezone.utc).timestamp())
        
    upcoming_seeds = predict_cache.get("upcoming_seeds", [])
    
    def build_section(upcoming_list, category, title, emoji):
        items_list = []
        for entry in upcoming_list:
            ts = entry.get("time")
            if ts < now_sec:
                continue
            dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=3)))
            
            for item in entry.get("items", []):
                name = item.get("name")
                rarity = item.get("rarity", "Common").lower()
                if rarity in ['super', 'mythic', 'secret'] or name.lower() in ['super watering can', 'super sprinkler']:
                    items_list.append({
                        "name": name,
                        "dt": dt,
                        "emoji": get_emoji_for_item(name, category),
                        "rarity": rarity
                    })
                    
        if not items_list:
            return "   <i>Нет данных о редких предметах</i>\n\n"
            
        months_lc = {
            1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
            5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
            9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
        }
        
        by_date = {}
        for x in items_list:
            dt = x["dt"]
            date_str = f"{dt.day} {months_lc.get(dt.month, '')}"
            by_date.setdefault(date_str, []).append(x)
            
        sorted_dates = sorted(by_date.keys(), key=lambda d: by_date[d][0]["dt"])
        
        sec_text = ""
        is_first = True
        for date_str in sorted_dates:
            if is_first:
                sec_text += f"<blockquote>{emoji} <b>{title}</b>\n{date_str}</blockquote>\n"
                is_first = False
            else:
                sec_text += f"<blockquote>{date_str}</blockquote>\n"
                
            items = sorted(by_date[date_str], key=lambda x: x["dt"])
            for x in items:
                time_str = f"{x['dt'].hour}:{x['dt'].minute:02d}"
                item_rarity = x.get("rarity", "").lower()
                if item_rarity in ['super', 'mythic', 'secret']:
                    item_text = f"<b><u>{x['emoji']} {x['name']}</u></b>"
                else:
                    item_text = f"{x['emoji']} {x['name']}"
                sec_text += f"<code>{time_str}</code> · {item_text}\n"
            sec_text += "\n"
        return sec_text

    text = build_section(upcoming_seeds, "seeds", "СЕМЕНА", "🌱")
    
    await callback.message.edit_text(
        text,
        reply_markup=get_predict_back_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "predict_gears")
async def predict_gears(callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_user_subscribed(user_id):
        await callback.answer("❌ Подписка не подтверждена!", show_alert=True)
        return
        
    if not predict_cache.get("gear"):
        await update_predict()
        
    now_sec = predict_cache.get("raw_now")
    if not now_sec:
        now_sec = int(datetime.now(timezone.utc).timestamp())
        
    upcoming_gears = predict_cache.get("upcoming_gears", [])
    
    def build_section(upcoming_list, category, title, emoji):
        items_list = []
        for entry in upcoming_list:
            ts = entry.get("time")
            if ts < now_sec:
                continue
            dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=3)))
            
            for item in entry.get("items", []):
                name = item.get("name")
                rarity = item.get("rarity", "Common").lower()
                if rarity in ['super', 'mythic', 'secret'] or name.lower() in ['super watering can', 'super sprinkler']:
                    items_list.append({
                        "name": name,
                        "dt": dt,
                        "emoji": get_emoji_for_item(name, category),
                        "rarity": rarity
                    })
                    
        if not items_list:
            return "   <i>Нет данных о редких предметах</i>\n\n"
            
        months_lc = {
            1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
            5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
            9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
        }
        
        by_date = {}
        for x in items_list:
            dt = x["dt"]
            date_str = f"{dt.day} {months_lc.get(dt.month, '')}"
            by_date.setdefault(date_str, []).append(x)
            
        sorted_dates = sorted(by_date.keys(), key=lambda d: by_date[d][0]["dt"])
        
        sec_text = ""
        is_first = True
        for date_str in sorted_dates:
            if is_first:
                sec_text += f"<blockquote>{emoji} <b>{title}</b>\n{date_str}</blockquote>\n"
                is_first = False
            else:
                sec_text += f"<blockquote>{date_str}</blockquote>\n"
                
            items = sorted(by_date[date_str], key=lambda x: x["dt"])
            for x in items:
                time_str = f"{x['dt'].hour}:{x['dt'].minute:02d}"
                item_rarity = x.get("rarity", "").lower()
                if item_rarity in ['super', 'mythic', 'secret']:
                    item_text = f"<b><u>{x['emoji']} {x['name']}</u></b>"
                else:
                    item_text = f"{x['emoji']} {x['name']}"
                sec_text += f"<code>{time_str}</code> · {item_text}\n"
            sec_text += "\n"
        return sec_text

    text = build_section(upcoming_gears, "gear", "ИНСТРУМЕНТЫ", "⚙️")
    
    await callback.message.edit_text(
        text,
        reply_markup=get_predict_back_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "predict_crates")
async def predict_crates(callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_user_subscribed(user_id):
        await callback.answer("❌ Подписка не подтверждена!", show_alert=True)
        return
        
    if not predict_cache.get("crates"):
        await update_predict()
        
    now_sec = predict_cache.get("raw_now")
    if not now_sec:
        now_sec = int(datetime.now(timezone.utc).timestamp())
        
    upcoming_crates = predict_cache.get("upcoming_crates", [])
    
    def build_section(upcoming_list, category, title, emoji):
        items_list = []
        for entry in upcoming_list:
            ts = entry.get("time")
            if ts < now_sec:
                continue
            dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=3)))
            
            for item in entry.get("items", []):
                name = item.get("name")
                rarity = item.get("rarity", "Common").lower()
                if rarity in ['super', 'mythic', 'secret'] or name.lower() in ['super watering can', 'super sprinkler']:
                    items_list.append({
                        "name": name,
                        "dt": dt,
                        "emoji": get_emoji_for_item(name, category),
                        "rarity": rarity
                    })
                    
        if not items_list:
            return "   <i>Нет данных о редких предметах</i>\n\n"
            
        months_lc = {
            1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
            5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
            9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
        }
        
        by_date = {}
        for x in items_list:
            dt = x["dt"]
            date_str = f"{dt.day} {months_lc.get(dt.month, '')}"
            by_date.setdefault(date_str, []).append(x)
            
        sorted_dates = sorted(by_date.keys(), key=lambda d: by_date[d][0]["dt"])
        
        sec_text = ""
        is_first = True
        for date_str in sorted_dates:
            if is_first:
                sec_text += f"<blockquote>{emoji} <b>{title}</b>\n{date_str}</blockquote>\n"
                is_first = False
            else:
                sec_text += f"<blockquote>{date_str}</blockquote>\n"
                
            items = sorted(by_date[date_str], key=lambda x: x["dt"])
            for x in items:
                time_str = f"{x['dt'].hour}:{x['dt'].minute:02d}"
                item_rarity = x.get("rarity", "").lower()
                if item_rarity in ['super', 'mythic', 'secret']:
                    item_text = f"<b><u>{x['emoji']} {x['name']}</u></b>"
                else:
                    item_text = f"{x['emoji']} {x['name']}"
                sec_text += f"<code>{time_str}</code> · {item_text}\n"
            sec_text += "\n"
        return sec_text

    text = build_section(upcoming_crates, "crates", "ЯЩИКИ", "📦")
    
    await callback.message.edit_text(
        text,
        reply_markup=get_predict_back_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "view_weather")
async def view_weather(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_active_stock(user_id)
    
    if not await is_user_subscribed(user_id):
        await callback.answer("❌ Подписка не подтверждена!", show_alert=True)
        return
    
    if not predict_cache.get("raw_weather"):
        await update_predict()
        
    if not weather_cache:
        await update_weather()
    
    text = "🌤 <b>Погода и Время</b>\n"
    text += "─" * 20 + "\n\n"
    
    time_of_day = get_time_of_day()
    text += f"🕐 <b>Время суток:</b> {time_of_day}\n"
    
    if weather_cache:
        weather_name = weather_cache.get("weather_name", "Clear")
        weather_emoji = get_weather_emoji(weather_name)
        started_at = weather_cache.get("started_at")
        
        if weather_name not in ["Clear", "None"]:
            text += f"🌦 <b>Эффект погоды:</b> {weather_emoji} {weather_name}\n"
            if started_at:
                try:
                    dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    text += f"⏱️ Начало: {format_weather_time(dt)} (МСК)\n"
                except:
                    pass
        else:
            text += "☀️ <b>Эффект погоды:</b> Ясно\n"
    else:
        text += "🌦 <b>Эффект погоды:</b> Нет данных\n"
        
    text += "─" * 20 + "\n\n"
    
    raw_weather = predict_cache.get("raw_weather", [])
    raw_now = predict_cache.get("raw_now")
    
    if raw_weather and isinstance(raw_weather, list) and raw_now:
        text += "📅 <b>Расписание лунных событий:</b>\n"
        
        upcoming_count = 0
        for event in raw_weather:
            name = event.get("name", "Clear")
            ts = event.get("timestamp", 0)
            if ts < raw_now:
                continue
                
            dt_msk = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=3)))
            time_str = dt_msk.strftime('%H:%M:%S')
            
            rel_sec = ts - raw_now
            if rel_sec > 0:
                rel_str = f"через {rel_sec // 60}м"
            else:
                rel_str = "активна сейчас"
                
            moon_emoji = get_weather_emoji(name)
            
            text += f"  • {time_str} ({rel_str}) — {moon_emoji} <b>{name}</b>\n"
            upcoming_count += 1
            if upcoming_count >= 5:
                break
    else:
        text += "🌙 <b>Лунный цикл:</b> Нет данных прогноза\n"
        
    await callback.message.edit_text(
        text,
        reply_markup=get_main_keyboard(user_id),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "support")
async def support_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_active_stock(user_id)
    
    if not await is_user_subscribed(user_id):
        await callback.answer("❌ Подписка не подтверждена!", show_alert=True)
        return
    
    text = "🆘 Поддержка\n"
    text += "─" * 15 + "\n\n"
    text += "📌 Задайте вопрос администратору.\n"
    text += "Напишите сообщение, мы ответим.\n\n"
    text += "💬 Нажмите кнопку ниже."
    
    await callback.message.edit_text(
        text,
        reply_markup=get_support_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "support_write")
async def support_write(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if not await is_user_subscribed(user_id):
        await callback.answer("❌ Подписка не подтверждена!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "✍️ Напишите сообщение\n\n"
        "Опишите проблему или задайте вопрос.\n"
        "<i>Для отмены /cancel</i>",
        parse_mode="HTML"
    )
    await state.set_state(SupportStates.waiting_for_message)
    await callback.answer()

@dp.message(SupportStates.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    
    if text == "/cancel":
        await message.answer(
            "❌ Отменено",
            reply_markup=get_main_keyboard(user_id)
        )
        await state.clear()
        return
    
    sent = False
    for admin_id in ADMIN_IDS:
        try:
            support_messages[admin_id] = {
                "user_id": user_id,
                "message_id": message.message_id,
                "text": text,
                "date": datetime.now(timezone.utc)
            }
            
            admin_text = (
                f"📩 Новое сообщение!\n\n"
                f"👤 <a href='tg://user?id={user_id}'>Пользователь</a>\n"
                f"🆔 {user_id}\n"
                f"📝 {text}\n\n"
                f"⏱️ {datetime.now(timezone.utc).strftime('%H:%M:%S')}"
            )
            
            await bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode="HTML",
                reply_markup=get_admin_reply_keyboard(user_id, message.message_id)
            )
            sent = True
            logger.info(f"📤 Сообщение от {user_id} админу {admin_id}")
        except Exception as e:
            logger.error(f"Ошибка админу {admin_id}: {e}")
    
    if sent:
        await message.answer(
            "✅ Отправлено!\n\nАдминистратор ответит.",
            reply_markup=get_main_keyboard(user_id),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ Ошибка!\n\nПопробуйте позже.",
            reply_markup=get_main_keyboard(user_id),
            parse_mode="HTML"
        )
    
    await state.clear()

@dp.callback_query(F.data.startswith("admin_reply_"))
async def admin_reply_start(callback: CallbackQuery, state: FSMContext):
    admin_id = callback.from_user.id
    
    if admin_id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return
    
    data = callback.data.split("_")
    user_id = int(data[2])
    msg_id = int(data[3])
    
    await state.update_data(reply_to_user=user_id, reply_to_msg=msg_id)
    
    await callback.message.answer(
        f"✍️ Ответ пользователю\n\nНапишите текст.\n<i>/cancel - отмена</i>",
        parse_mode="HTML"
    )
    await state.set_state(SupportStates.waiting_for_reply)
    await callback.answer()

@dp.message(SupportStates.waiting_for_reply)
async def process_admin_reply(message: Message, state: FSMContext):
    admin_id = message.from_user.id
    
    if admin_id not in ADMIN_IDS:
        await message.answer("⛔ Нет прав!")
        await state.clear()
        return
    
    if message.text == "/cancel":
        await message.answer("❌ Отменено")
        await state.clear()
        return
    
    data = await state.get_data()
    user_id = data.get("reply_to_user")
    
    if not user_id:
        await message.answer("❌ Ошибка")
        await state.clear()
        return
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"📩 Ответ:\n\n{message.text}",
            parse_mode="HTML"
        )
        
        await message.answer(
            f"✅ Отправлено!",
            parse_mode="HTML"
        )
        
        try:
            await message.delete()
        except:
            pass
            
        logger.info(f"📤 Админ {admin_id} ответил {user_id}")
        
    except Exception as e:
        await message.answer(
            f"❌ Ошибка: {e}",
            parse_mode="HTML"
        )
    
    await state.clear()

@dp.callback_query(F.data.startswith("admin_cancel_"))
async def admin_cancel(callback: CallbackQuery):
    admin_id = callback.from_user.id
    
    if admin_id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return
    
    data = callback.data.split("_")
    user_id = int(data[2])
    
    await callback.message.edit_text(
        f"❌ Отменено\nПользователь: {user_id}"
    )
    await callback.answer("✅ Отменено")

@dp.callback_query(F.data == "auto_stock")
async def auto_stock_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_active_stock(user_id)
    
    if not await is_user_subscribed(user_id):
        await callback.answer("❌ Подписка не подтверждена!", show_alert=True)
        return
        
    text = (
        "⏱ <b>Личные уведомления о стоках</b>\n\n"
        "Бот будет отправлять вам личные сообщения, когда выбранные вами семена или инструменты появятся в наличии (in stock)!\n\n"
        "Выберите категорию для настройки:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌱 Семена", callback_data="auto_stock_list_seeds"),
        InlineKeyboardButton(text="🛠️ Инструменты", callback_data="auto_stock_list_gears")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@dp.my_chat_member()
async def on_bot_chat_member_update(update: ChatMemberUpdated):
    chat_id = update.chat.id
    chat_type = update.chat.type
    new_status = update.new_chat_member.status
    
    # In channels, bot must be admin/creator. In groups/supergroups, bot can be admin/creator/member
    has_access = False
    if chat_type == 'channel' and new_status in ['administrator', 'creator']:
        has_access = True
    elif chat_type in ['group', 'supergroup'] and new_status in ['administrator', 'creator', 'member']:
        has_access = True
        
    data = load_data()
    if "channels" not in data:
        data["channels"] = []
        
    channel_id = str(chat_id)
    
    if has_access:
        if "channel_names" not in data:
            data["channel_names"] = {}
            
        chat_title = update.chat.title or "Без названия"
        chat_username = update.chat.username
        chat_desc = f"'{chat_title}'"
        if chat_username:
            chat_desc += f" (@{chat_username})"
            
        data["channel_names"][channel_id] = chat_desc

        if channel_id not in data["channels"]:
            data["channels"].append(channel_id)
            save_data(data)
            logger.info(f"✅ Бот подключен к {chat_type} {chat_desc} ({channel_id}) (статус: {new_status})")
            
            try:
                message = (
                    "✅ <b>Бот успешно подключен!</b>\n\n"
                    "📢 Теперь я буду отправлять уведомления о легендарных и редких предметах сюда.\n\n"
                    f"🌾 <a href='{BOT_LINK}'>Grow a Garden 2 Stock Bot</a>"
                )
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Не удалось отправить приветствие в {chat_type} {chat_id}: {e}")
    else:
        if "channel_names" in data and channel_id in data["channel_names"]:
            name_str = data["channel_names"].pop(channel_id, channel_id)
        else:
            name_str = channel_id
            
        if channel_id in data["channels"]:
            data["channels"].remove(channel_id)
            save_data(data)
            logger.info(f"❌ Бот отключен от {chat_type} {name_str} ({channel_id}) (статус: {new_status})")

def get_auto_stock_items_keyboard(user_id: int, category: str, page: int = 0) -> InlineKeyboardMarkup:
    data = load_data()
    user_cache = data.get("users", {}).get(str(user_id), {})
    tracked_items = user_cache.get("tracked_items", [])
    tracked_lower = [x.lower() for x in tracked_items]
    
    if category == "seeds":
        items_dict = SEED_EMOJIS
        title_emoji = "🌱"
    else:
        items_dict = GEAR_EMOJIS
        title_emoji = "🛠️"
        
    builder = InlineKeyboardBuilder()
    sorted_names = sorted(items_dict.keys())
    
    page_size = 12
    total_pages = (len(sorted_names) + page_size - 1) // page_size
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(sorted_names))
    page_items = sorted_names[start_idx:end_idx]
    
    for name in page_items:
        emoji = items_dict[name]
        is_tracked = name.lower() in tracked_lower
        status_symbol = "✅" if is_tracked else "❌"
        display_name = name.title()
        btn_text = f"{emoji} {display_name} {status_symbol}"
        builder.add(InlineKeyboardButton(text=btn_text, callback_data=f"track_toggle:{name}:{category}:{page}"))
        
    builder.adjust(2)
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Пред.", callback_data=f"auto_stock_page:{category}:{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="След. ➡️", callback_data=f"auto_stock_page:{category}:{page+1}"))
        
    builder.row(*nav_row)
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="auto_stock"))
    
    return builder.as_markup()

@dp.callback_query(F.data == "auto_stock_list_seeds")
async def auto_stock_list_seeds(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text(
        "🌱 <b>Настройка уведомлений: Seeds</b>\n\nВыделите семена, о появлении которых хотите получать уведомления:",
        reply_markup=get_auto_stock_items_keyboard(user_id, "seeds", 0),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "auto_stock_list_gears")
async def auto_stock_list_gears(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text(
        "🛠️ <b>Настройка уведомлений: Gears</b>\n\nВыделите инструменты, о появлении которых хотите получать уведомления:",
        reply_markup=get_auto_stock_items_keyboard(user_id, "gear", 0),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("auto_stock_page:"))
async def auto_stock_page_change(callback: CallbackQuery):
    user_id = callback.from_user.id
    parts = callback.data.split(":")
    category = parts[1]
    page = int(parts[2])
    
    cat_title = "Seeds" if category == "seeds" else "Gears"
    cat_emoji = "🌱" if category == "seeds" else "🛠️"
    
    await callback.message.edit_text(
        f"{cat_emoji} <b>Настройка уведомлений: {cat_title}</b>\n\nВыделите предметы, о появлении которых хотите получать уведомления:",
        reply_markup=get_auto_stock_items_keyboard(user_id, category, page),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("track_toggle:"))
async def track_toggle_item(callback: CallbackQuery):
    user_id = callback.from_user.id
    parts = callback.data.split(":")
    item_name = parts[1]
    category = parts[2]
    page = int(parts[3])
    
    data = load_data()
    if "users" not in data:
        data["users"] = {}
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {}
        
    user_cache = data["users"][str(user_id)]
    tracked_items = user_cache.get("tracked_items", [])
    
    tracked_lower = [x.lower() for x in tracked_items]
    item_lower = item_name.lower()
    
    if item_lower in tracked_lower:
        tracked_items = [x for x in tracked_items if x.lower() != item_lower]
        status_str = "Выключено"
    else:
        tracked_items.append(item_name)
        status_str = "Включено"
        
    data["users"][str(user_id)]["tracked_items"] = tracked_items
    save_data(data)
    
    await callback.answer(f"🔔 {item_name.title()}: {status_str}")
    
    await callback.message.edit_reply_markup(
        reply_markup=get_auto_stock_items_keyboard(user_id, category, page)
    )

@dp.callback_query(F.data == "auto_stock_channel")
async def auto_stock_channel_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_active_stock(user_id)
    
    if not await is_user_subscribed(user_id):
        await callback.answer("❌ Подписка не подтверждена!", show_alert=True)
        return
        
    text = (
        "🤖 <b>Подключи бота к своему каналу</b>\n\n"
        "🔹 1. Нажми на кнопку ниже\n"
        "🔹 2. Выбери свой канал\n"
        "🔹 3. Дай права администратора (обязательно)\n\n"
        "🔗 Бот будет отправлять уведомления о легендарных предметах в твой канал!"
    )
    
    builder = InlineKeyboardBuilder()
    add_channel_url = f"{BOT_LINK}?startchannel=true"
    builder.row(
        InlineKeyboardButton(text="🤖 Добавить в канал", url=add_channel_url)
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "admin_list_users")
async def admin_list_users(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return
    
    data = load_data()
    users = data.get("users", {})
    
    if not users:
        text = "📊 Список пользователей пуст."
    else:
        total = len(users)
        text = f"📊 Пользователи бота\n"
        text += "─" * 20 + "\n\n"
        text += f"👥 Всего: {total}\n\n"
        
        user_list = list(users.items())
        user_list.sort(key=lambda x: x[1].get("first_seen", ""), reverse=True)
        
        for i, (user_id, info) in enumerate(user_list[:50], 1):
            username = info.get("username", "")
            first_name = info.get("first_name", "")
            last_name = info.get("last_name", "")
            
            name = first_name
            if last_name:
                name += f" {last_name}"
            if username:
                name += f" (@{username})"
            
            text += f"{i}. {name}\n"
            text += f"   🆔 {user_id}\n"
            text += f"   📅 {info.get('first_seen', '')[:10]}\n\n"
        
        if total > 50:
            text += f"... и ещё {total - 50} пользователей"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⚙️ Админ панель\n\nВыберите:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "admin_refresh_stock")
async def admin_refresh_stock(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return
    
    await callback.answer("🔄 Обновление...")
    await update_stock_data()
    await update_weather()
    await update_predict()
    
    text = "✅ Обновлено!\n"
    text += "─" * 12 + "\n\n"
    
    for category in ["seeds", "gear", "crates"]:
        count = len(stock_cache.get(category, {}).get("items", []))
        text += f"{CATEGORY_EMOJIS.get(category, '📦')} {CATEGORY_NAMES.get(category, category)}: {count}\n"
    
    if predict_cache.get("seeds"):
        text += f"\n🔮 Предикт: {len(predict_cache.get('seeds', []))} предметов"
    
    if next_restock_time:
        text += f"\n⏱️ Ресток: {format_restock_time(next_restock_time)} (МСК)"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "admin_add_sponsor")
async def add_sponsor_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📢 Добавление спонсора\n\nВведите username канала:\n<i>@sponsor</i>",
        parse_mode="HTML"
    )
    await state.set_state(SponsorStates.waiting_for_channel)
    await callback.answer()

@dp.message(SponsorStates.waiting_for_channel)
async def process_sponsor_channel(message: Message, state: FSMContext):
    await state.update_data(channel=message.text.strip())
    await message.answer(
        "📢 Введите ссылку (/skip - пропустить):",
        parse_mode="HTML"
    )
    await state.set_state(SponsorStates.waiting_for_link)

@dp.message(SponsorStates.waiting_for_link)
async def process_sponsor_link(message: Message, state: FSMContext):
    data = load_data()
    user_data = await state.get_data()
    channel = user_data.get("channel")
    link = message.text.strip()
    
    if link == "/skip":
        link = channel
    
    data["sponsors"].append({"channel": channel, "link": link})
    save_data(data)
    
    await message.answer(
        f"✅ Добавлен!\n\n📢 {channel}\n🔗 {link}",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    await state.clear()

@dp.callback_query(F.data == "admin_list_sponsors")
async def list_sponsors(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return
    
    data = load_data()
    sponsors = data.get("sponsors", [])
    
    if not sponsors:
        text = "📋 Список пуст."
    else:
        text = "📋 Список спонсоров:\n\n"
        for i, sponsor in enumerate(sponsors, 1):
            text += f"{i}. {sponsor.get('channel')}\n   🔗 {sponsor.get('link')}\n\n"
    
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "admin_remove_sponsor")
async def remove_sponsor_start(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return
    
    data = load_data()
    sponsors = data.get("sponsors", [])
    
    if not sponsors:
        await callback.message.edit_text("📋 Список пуст.", reply_markup=get_admin_keyboard())
        return
    
    builder = InlineKeyboardBuilder()
    for i, sponsor in enumerate(sponsors):
        channel = sponsor.get("channel", f"Спонсор {i+1}")
        builder.row(InlineKeyboardButton(
            text=f"❌ {channel}",
            callback_data=f"remove_sponsor_{i}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    
    await callback.message.edit_text(
        "🗑 Выберите спонсора:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("remove_sponsor_"))
async def remove_sponsor_confirm(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return
    
    index = int(callback.data.split("_")[2])
    data = load_data()
    sponsors = data.get("sponsors", [])
    
    if 0 <= index < len(sponsors):
        removed = sponsors.pop(index)
        data["sponsors"] = sponsors
        save_data(data)
        
        await callback.answer("✅ Удален!", show_alert=True)
        await callback.message.edit_text(
            f"✅ Удален!\n\n📢 {removed.get('channel')}",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )

async def stock_countdown_updater():
    while True:
        try:
            if active_stock_displays:
                text = generate_stock_text()
                
                for user_id, msg_id in list(active_stock_displays.items()):
                    try:
                        await bot.edit_message_text(
                            chat_id=user_id,
                            message_id=msg_id,
                            text=text,
                            reply_markup=get_main_keyboard(user_id),
                            parse_mode="HTML"
                        )
                    except TelegramBadRequest as e:
                        err_msg = str(e).lower()
                        if "not modified" in err_msg:
                            pass
                        else:
                            logger.info(f"Убираем {user_id} из обновлений стока: {e}")
                            active_stock_displays.pop(user_id, None)
                    except TelegramForbiddenError:
                        logger.info(f"Бот заблокирован пользователем {user_id}, убираем из обновлений")
                        active_stock_displays.pop(user_id, None)
                    except Exception as e:
                        logger.error(f"Ошибка обновления экрана стоков для {user_id}: {e}")
        except Exception as e:
            logger.error(f"Ошибка в stock_countdown_updater: {e}")
            
        await asyncio.sleep(5)

async def background_updater():
    while True:
        try:
            await update_stock_data()
            await update_weather()
            await update_predict()
        except Exception as e:
            logger.error(f"Ошибка: {e}")
        await asyncio.sleep(POLL_INTERVAL)

async def main():
    logger.info("🚀 Запуск...")
    
    try:
        await bot.get_chat(CHANNEL_ID)
        logger.info(f"✅ Канал {CHANNEL_ID} найден")
    except Exception as e:
        logger.error(f"❌ Канал {CHANNEL_ID} не найден! Ошибка: {e}")
    
    logger.info("📥 Загрузка...")
    await fetch_items_database()
    await update_stock_data()
    await update_weather()
    await update_predict()
    logger.info("✅ Готово")
    
    asyncio.create_task(background_updater())
    asyncio.create_task(stock_countdown_updater())
    logger.info(f"🔄 Фон (интервал: {POLL_INTERVAL}с)")
    
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
