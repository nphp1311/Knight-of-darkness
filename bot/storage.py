"""JSON storage for guild + player + lore + i18n locale + monsters."""
import json
import os
from threading import Lock

DATA_FILE = "data/data.json"
_lock = Lock()


DEFAULT_MONSTERS: list[dict] = [
    {"name": "Đấu Sĩ Xương Khô", "emoji": "☠️", "level": 1, "tank": 26, "dps": 30, "hp": 45},
    {"name": "Chuột Dịch Hạch", "emoji": "🐀", "level": 1, "tank": 23, "dps": 41, "hp": 34},
    {"name": "Sói Bóng Đêm", "emoji": "🐺", "level": 2, "tank": 60, "dps": 83, "hp": 90},
    {"name": "Nhện Độc", "emoji": "🕷", "level": 2, "tank": 53, "dps": 71, "hp": 120},
    {"name": "Medusa", "emoji": "🐍", "level": 2, "tank": 53, "dps": 71, "hp": 120},
    {"name": "Kỵ Sĩ Bị Nguyền", "emoji": "🧟", "level": 3, "tank": 135, "dps": 150, "hp": 195},
    {"name": "Hỏa Linh Canh Giữ", "emoji": "🔥", "level": 3, "tank": 113, "dps": 225, "hp": 165},
    {"name": "Ma Tướng Huyết Ảnh", "emoji": "🩸", "level": 4, "tank": 300, "dps": 375, "hp": 488},
    {"name": "Người Gác Vực Thẳm", "emoji": "🗿", "level": 4, "tank": 675, "dps": 188, "hp": 825},
    {"name": "Rồng Hắc Ám", "emoji": "🐉", "level": 5, "tank": 675, "dps": 1050, "hp": 1500},
]


def _ensure_file():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def _load():
    _ensure_file()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


data = _load()


def persist():
    with _lock:
        _ensure_file()
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def get_guild(guild_id):
    gid = str(guild_id)
    if gid not in data:
        data[gid] = {"config": {"rank_roles": {}}, "players": {}, "lore": {}, "locales": {}}
    g = data[gid]
    g.setdefault("config", {"rank_roles": {}})
    g["config"].setdefault("rank_roles", {})
    g.setdefault("players", {})
    g.setdefault("lore", {})
    g.setdefault("locales", {})
    for key in ("intro", "outro", "arena", "self"):
        g["lore"].setdefault(key, {"messages": []})
        g["lore"][key].setdefault("messages", [])
    return g


def get_player(guild_id, user_id):
    g = get_guild(guild_id)
    uid = str(user_id)
    if uid not in g["players"]:
        g["players"][uid] = {
            "tank": 5, "dps": 5, "health": 5, "wins": 0, "pvp_wins": 0,
            "wins_by_level": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
            "rank": "I",
            "pvp_streak": 0,
            "achievements": [],
            "potion_last_zero": False,
            "potion_since_last_max": 0,
        }
        persist()
    p = g["players"][uid]
    p.setdefault("tank", 5)
    p.setdefault("dps", 5)
    p.setdefault("health", 5)
    p.setdefault("wins", 0)
    p.setdefault("pvp_wins", 0)
    p.setdefault("wins_by_level", {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0})
    p.setdefault("rank", "I")
    p.setdefault("pvp_streak", 0)
    p.setdefault("achievements", [])
    p.setdefault("potion_last_zero", False)
    p.setdefault("potion_since_last_max", 0)
    for k in ("1", "2", "3", "4", "5"):
        p["wins_by_level"].setdefault(k, 0)
    return p


def get_locale(guild_id, user_id) -> str:
    g = get_guild(guild_id)
    return g["locales"].get(str(user_id), "vi")


def set_locale(guild_id, user_id, locale: str):
    g = get_guild(guild_id)
    g["locales"][str(user_id)] = locale
    persist()


# ============== MONSTERS (global) ==============
def get_monsters() -> list[dict]:
    if "monsters" not in data or not isinstance(data.get("monsters"), list):
        data["monsters"] = [dict(m) for m in DEFAULT_MONSTERS]
        persist()
    return data["monsters"]


def get_monsters_by_level(level: int) -> list[dict]:
    return [m for m in get_monsters() if int(m.get("level", 0)) == int(level)]


def add_monster(m: dict):
    monsters = get_monsters()
    monsters.append(m)
    persist()


def update_monster(idx: int, m: dict):
    monsters = get_monsters()
    if 0 <= idx < len(monsters):
        monsters[idx] = m
        persist()


def delete_monster(idx: int):
    monsters = get_monsters()
    if 0 <= idx < len(monsters):
        monsters.pop(idx)
        persist()


def find_monster_index(name: str, level: int) -> int:
    for i, m in enumerate(get_monsters()):
        if m.get("name") == name and int(m.get("level", 0)) == int(level):
            return i
    return -1
