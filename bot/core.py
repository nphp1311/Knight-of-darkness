"""Core: i18n, embeds, game data, formulas, navigation helpers."""
import random
from dataclasses import dataclass

import discord

from .storage import get_locale, get_guild


# ============== EMBEDS ==============
DARK_COLOR = 0x1a0000
GOLD_COLOR = 0xc9a227
SHADOW_COLOR = 0x2f3136
KNIGHT_NAME = "🤺 Hiệp Sĩ Hắc Ám"


def knight_embed(text: str, *, title: str | None = None, color: int = DARK_COLOR) -> discord.Embed:
    """Embed lời thoại của Hiệp Sĩ Hắc Ám (KHÔNG dùng chữ in nghiêng)."""
    return discord.Embed(title=title or KNIGHT_NAME, description=text, color=color)


# ============== I18N ==============
# Each entry: (vi, en). Used for UI labels and bot dialogue.
TR = {
    # Lobby / nav
    "lobby_intro": ("Hỡi chiến binh dũng cảm, ta có thể giúp gì cho ngươi?",
                    "Brave warrior, how may I aid you?"),
    "exit_msg": ("🌕 Hẹn gặp lại ngươi trên chiến trường.",
                 "🌕 Farewell — until we meet again on the battlefield."),
    "btn_train": ("🛠 Luyện tập", "🛠 Train"),
    "btn_challenge": ("⚔️ Thách đấu", "⚔️ Challenge"),
    "btn_stats": ("📊 Xem thông tin cá nhân", "📊 My Stats"),
    "btn_board": ("🏆 Bảng xếp hạng", "🏆 Leaderboard"),
    "btn_chat": ("💬 Trò chuyện", "💬 Chat"),
    "btn_admin": ("🛡️ Quản lý (dành cho admin)", "🛡️ Admin Panel (admin only)"),
    "btn_exit": ("🚪 Thoát", "🚪 Exit"),
    "btn_lobby": ("🗿 Quay lại sảnh chờ", "🗿 Back to lobby"),
    "btn_back": ("◀ Quay lại", "◀ Back"),
    "btn_lang": ("🌐 EN / VI", "🌐 EN / VI"),
    # Stats
    "stats_rank": ("Hạng", "Rank"),
    "stats_wins": ("Số quái đã thắng", "Monsters defeated"),
    "stats_pvp_wins": ("Số trận PvP thắng", "PvP wins"),
    # Leaderboard
    "lb_pick": ("🏆 Ngươi muốn xem bảng xếp hạng nào?", "🏆 Which leaderboard do you wish to see?"),
    "lb_pve_btn": ("🐉 Bảng xếp hạng Diệt Quái", "🐉 Monster Slayer Leaderboard"),
    "lb_pvp_btn": ("⚔️ Bảng xếp hạng Đấu Sĩ", "⚔️ Duelist Leaderboard"),
    "lb_pve_title": ("🐉 **Bảng xếp hạng Diệt Quái — Top 10**",
                     "🐉 **Monster Slayer Leaderboard — Top 10**"),
    "lb_pvp_title": ("⚔️ **Bảng xếp hạng Đấu Sĩ — Top 10**",
                     "⚔️ **Duelist Leaderboard — Top 10**"),
    "lb_empty": ("(Chưa có dữ liệu)", "(No data yet)"),
    # Challenge
    "challenge_intro": ("⚔️ Khát máu đã trỗi dậy trong ngươi. Hãy chọn đối thủ — đồng loại hay quái vật?",
                        "⚔️ Bloodlust stirs within you. Choose your foe — mortal or monster?"),
    "btn_pvp": ("⚔️ Thách đấu người chơi", "⚔️ Challenge a player"),
    "btn_pve": ("🐉 Thách đấu quái vật", "🐉 Challenge a monster"),
    "pve_pick_level": ("💀 Hãy chọn cấp bậc quái vật mà ngươi dám đối mặt. Càng cao… cái chết càng đến gần.",
                       "💀 Choose the level of monster you dare face. The higher you climb, the closer death draws."),
    "no_overrun": ("💀 Ngươi chưa đạt cấp tương ứng (chưa có role hạng) nên không thể thách đấu vượt cấp với quái. Hạng hiện tại của ngươi: **{rank}**.",
                   "💀 You have not yet earned the matching rank role, so you cannot challenge monsters above your rank. Your current rank: **{rank}**."),
    "no_rank_role_setup": ("💀 Server chưa thiết lập role thưởng cho hạng này. Hãy nhờ admin gắn role trước.",
                           "💀 The server has not configured a rank role yet. Ask an admin to set it up first."),
    # Chat
    "chat_intro": ("Ngươi muốn nói về điều gì?", "Of what do you wish to speak?"),
    "btn_chat_arena": ("🏛 Về đấu trường này", "🏛 About this arena"),
    "btn_chat_self": ("🌑 Về bản thân ngài", "🌑 About yourself"),
    "btn_chat_guide": ("📜 Hướng dẫn sử dụng đấu trường", "📜 Arena guide"),
    "btn_chat_again": ("💬 Hỏi điều khác", "💬 Ask something else"),
    # Rank up
    "rankup_title": ("🏆 THĂNG HẠNG!", "🏆 RANK UP!"),
    "rankup_text": ("🎉 {mention} vừa đạt hạng **{rank_name}**!\n\n_{speech}_\n\n🎁 **Phần thưởng:** Từ giờ mỗi lần luyện tập (Tank / DPS / Thần dược) sẽ nhận được điểm cộng nhiều hơn **+{bonus}%**.",
                    "🎉 {mention} has reached **{rank_name}**!\n\n_{speech}_\n\n🎁 **Reward:** From now on, each training session (Tank / DPS / Potion) grants **+{bonus}%** more points."),
    "rankup_top_text": ("✨🏆 @everyone — Hãy chiêm ngưỡng! {mention} đã đăng cơ ngôi vị **{rank_name}**! 🏆✨\n\n_{speech}_\n\n🎁 **Phần thưởng tối thượng:** Từ giờ mỗi lần luyện tập sẽ nhận được điểm cộng nhiều hơn **+{bonus}%**.",
                        "✨🏆 @everyone — Behold! {mention} has ascended to **{rank_name}**! 🏆✨\n\n_{speech}_\n\n🎁 **Supreme reward:** From now on, each training session grants **+{bonus}%** more points."),
}


def t(guild_id, user_id, key: str, **fmt) -> str:
    locale = get_locale(guild_id, user_id) if guild_id else "vi"
    vi, en = TR.get(key, (key, key))
    s = en if locale == "en" else vi
    if fmt:
        try:
            s = s.format(**fmt)
        except Exception:
            pass
    return s


# ============== MONSTERS ==============
@dataclass
class Monster:
    name: str
    emoji: str
    level: int
    tank: int
    dps: int
    hp: int

    @property
    def display(self) -> str:
        return f"{self.emoji} {self.name}"


def _dict_to_monster(d: dict) -> Monster:
    return Monster(
        name=str(d.get("name", "?")),
        emoji=str(d.get("emoji", "❓")),
        level=int(d.get("level", 1)),
        tank=int(d.get("tank", 0)),
        dps=int(d.get("dps", 0)),
        hp=int(d.get("hp", 1)),
    )


def monsters_by_level(level: int) -> list[Monster]:
    from .storage import get_monsters_by_level
    return [_dict_to_monster(d) for d in get_monsters_by_level(level)]


# ============== RANKS ==============
RANKS = ["I", "II", "III", "IV", "V"]
RANK_INFO = {
    "I": {
        "name": "🕯 Kẻ Tập Sự",
        "speech": "🕯 Ngươi đã đặt chân lên một con đường đẫm máu. Nguyện cầu cho linh hồn của những kẻ bại trận dưới tay ngươi sẽ được siêu thoát.",
    },
    "II": {
        "name": "⚔️ Chiến Binh Tập Luyện",
        "speech": "⚔️ Máu làm ngươi say, và âm thanh hò reo vang lên từ khán đài làm ngươi mê muội.",
    },
    "III": {
        "name": "🩸 Kẻ Săn Linh Hồn",
        "speech": "🩸 Ngươi đã trở thành một đối thủ đáng gờm. Tất cả mọi sinh vật trong đấu trường bắt đầu nhìn ngươi bằng ánh mắt e sợ.",
    },
    "IV": {
        "name": "👁 Kỵ Sĩ Hắc Ấn",
        "speech": "👁 Hãy dẫm lên xác của kẻ thua cuộc và tiến về phía trước. Vong hồn của bọn ta dõi theo người.",
    },
    "V": {
        "name": "👑 Chúa Tể Hắc Ám",
        "speech": "🏆✨ Tại đấu trường này, giờ đây ngươi là Kẻ thống trị. ✨🏆",
    },
}


TRAINING_BONUS_PCT = {"I": 0, "II": 10, "III": 20, "IV": 35, "V": 60}


def training_bonus_pct(rank: str) -> int:
    return TRAINING_BONUS_PCT.get(rank, 0)


def apply_training_bonus(gain: int, rank: str) -> int:
    """Nhân điểm luyện tập với hệ số thưởng theo rank. gain=0 thì giữ nguyên."""
    if gain <= 0:
        return gain
    pct = training_bonus_pct(rank)
    return int(round(gain * (1 + pct / 100)))


def compute_rank(player) -> str:
    wins = player.get("wins", 0)
    wbl = player.get("wins_by_level", {})

    def w(lv: int) -> int:
        return int(wbl.get(str(lv), 0))

    # Chỉ tính số trận thắng ở cấp ngang hàng với hạng hiện tại.
    if w(5) >= 1:
        return "V"
    if w(3) >= 50:   # 50 trận thắng cấp III → lên IV
        return "IV"
    if w(2) >= 30:   # 30 trận thắng cấp II → lên III
        return "III"
    if w(1) >= 20:   # 20 trận thắng cấp I → lên II
        return "II"
    return "I"


def rank_progress_text(player, guild_id=None, user_id=None) -> str:
    wbl = player.get("wins_by_level", {})
    label = t(guild_id, user_id, "stats_wins") if guild_id else "Số trận thắng"
    return (
        f"{label}: **{player.get('wins', 0)}**\n"
        f"🪨 Cấp I: {wbl.get('1', 0)} | 🌲 Cấp II: {wbl.get('2', 0)} | "
        f"🔥 Cấp III: {wbl.get('3', 0)} | 🌑 Cấp IV: {wbl.get('4', 0)} | 👑 Cấp V: {wbl.get('5', 0)}"
    )


def can_fight_monster(player, monster: "Monster", has_rank_role: bool = False) -> bool:
    """
    Người chơi chỉ được đấu quái có cấp <= rank hiện tại của họ.
    Ngoại lệ: rank IV được phép thách đấu boss cấp V (Rồng Hắc Ám) — đây là bài thi cuối cùng.
    """
    rank = player.get("rank", "I")
    rank_lv = RANKS.index(rank) + 1
    if monster.level <= rank_lv:
        return True
    # Cho phép IV thách boss V
    if rank_lv == 4 and monster.level == 5:
        return True
    return False


# ============== BATTLE FORMULAS ==============
def attack_chance(dps_p: int, dps_e: int) -> float:
    c = 0.5 + (dps_p - dps_e) * 0.02
    return max(0.2, min(0.8, c))


def block_chance(tank_p: int, dps_e: int) -> float:
    c = 0.3 + (tank_p - dps_e) * 0.02
    return max(0.1, min(0.7, c))


def player_max_hp(player) -> int:
    return 50 + int(player.get("health", 5)) * 12


def heal_amount(player) -> int:
    h = player.get("health", 5)
    return max(2, int(h * random.uniform(1.0, 2.0)))


def damage_value(dps: int) -> int:
    return max(1, int(dps * random.uniform(0.8, 1.2)))


def crit_check() -> bool:
    return random.random() < 0.2


def miss_check() -> bool:
    return random.random() < 0.15


# ============== LORE ==============
DEFAULT_LORE = {
    "intro": "Hỡi chiến binh dũng cảm, ta có thể giúp gì cho ngươi?",
    "outro": "🌕 Hẹn gặp lại ngươi trên chiến trường.",
    "arena": (
        "💀 Ngươi có từng nghe về việc vùng đất này từng thuộc về thế lực Thiên Đường "
        "trước khi bị ác quỷ chiếm đóng? Những cột đá trắng muốt và nền gạch sạch bong "
        "trông rất đẹp đẽ, nhưng ta thích phiên bản của đấu trường ở thời điểm hiện tại hơn — "
        "khi nó ngày ngày bị bao phủ bởi mùi máu và tiếng thét gào."
    ),
    "self": (
        "🌑 Trước khi sa ngã thành ma quỷ, ta từng là một tướng lĩnh của các thiên thần. "
        "Cánh của ta đã bị bẻ gãy bởi chính những người mà ta từng tin tưởng, "
        "nhưng tinh thần hiệp sĩ của ta thì tuyệt đối sẽ không lung lay. "
        "Ta không quỳ gối trước bất kì thần linh hay vua chúa. "
        "Tín ngưỡng duy nhất của ta chính là thanh gươm đẫm máu mà ta nắm trong tay."
    ),
}


def get_lore_text(guild_id, topic: str) -> str:
    """Random pool: luôn có câu mặc định + tất cả câu admin nhập."""
    g = get_guild(guild_id)
    msgs = list(g["lore"].get(topic, {}).get("messages", []))
    pool = [DEFAULT_LORE[topic]] + msgs
    return random.choice(pool)


ARENA_GUIDE = (
    "📜 **Hướng dẫn sử dụng đấu trường**\n\n"
    "🛠 **Luyện tập** — 3 bài tập giúp ngươi tăng chỉ số:\n"
    "• 🛡 **Tank** — né đòn theo màu (5 lượt).\n"
    "• 🗡 **DPS** — bấm chuỗi nút theo đúng thứ tự (5 lượt).\n"
    "• 💊 **Pha chế thần dược** — chọn 3 nguyên liệu trong Lò giả kim.\n\n"
    "⚔️ **Thách đấu** — chọn 1 trong 2:\n"
    "• 🐉 **PvE** — đấu quái vật (5 cấp). Mỗi quái hạ gục cho điểm chiến công.\n"
    "• ⚔️ **PvP** — gửi thư mời 1vs1 đến người chơi khác.\n"
    "• Cơ chế: Tấn công / Phòng thủ với HP, đòn chí mạng, chặn, đánh trượt.\n\n"
    "📊 **Xem thông tin cá nhân** — kiểm tra chỉ số 🛡 🗡 💊, hạng, số trận thắng.\n"
    "🏆 **Bảng xếp hạng** — top 10 chiến binh trong server.\n\n"
    "👑 **Hệ thống hạng** — I → II → III → IV → V (Kẻ Tập Sự → Chúa Tể Hắc Ám).\n"
    "Khi đạt hạng mới, ta sẽ chúc mừng ngươi trước toàn thể chiến binh."
)
ARENA_GUIDE_EN = (
    "📜 **Arena Guide**\n\n"
    "🛠 **Train** — 3 mini-games to raise your stats:\n"
    "• 🛡 **Tank** — dodge by matching colors (5 rounds).\n"
    "• 🗡 **DPS** — press the buttons in the correct order (5 rounds).\n"
    "• 💊 **Brew potions** — pick 3 ingredients in the alchemy chamber.\n\n"
    "⚔️ **Challenge** — pick one:\n"
    "• 🐉 **PvE** — fight monsters (5 tiers). Each kill grants merit points.\n"
    "• ⚔️ **PvP** — send a 1v1 invitation to another player.\n"
    "• System: Attack / Defend with HP, crits, blocks, and misses.\n\n"
    "📊 **My stats** — check 🛡 🗡 💊, rank, and total wins.\n"
    "🏆 **Leaderboard** — top 10 warriors of the server.\n\n"
    "👑 **Rank system** — I → II → III → IV → V (Apprentice → Dark Lord).\n"
    "When you reach a new rank, I will honor you before all warriors."
)


def arena_guide(guild_id, user_id) -> str:
    return ARENA_GUIDE_EN if get_locale(guild_id, user_id) == "en" else ARENA_GUIDE


# ============== ACHIEVEMENTS ==============
ACHIEVEMENTS = {
    "pve_10":   {"icon": "🗡",  "name": "Diệt Quái x10",   "desc": "Hạ gục 10 quái vật."},
    "pve_100":  {"icon": "⚔️", "name": "Diệt Quái x100",  "desc": "Hạ gục 100 quái vật."},
    "pve_200":  {"icon": "🩸", "name": "Diệt Quái x200",  "desc": "Hạ gục 200 quái vật."},
    "pve_300":  {"icon": "💀", "name": "Diệt Quái x300",  "desc": "Hạ gục 300 quái vật."},
    "pve_400":  {"icon": "🔥", "name": "Diệt Quái x400",  "desc": "Hạ gục 400 quái vật."},
    "pve_500":  {"icon": "👹", "name": "Diệt Quái x500",  "desc": "Hạ gục 500 quái vật."},
    "boss_slayer":  {"icon": "🐉", "name": "Đồ Tể Của Boss", "desc": "Hạ gục được boss cấp V (Rồng Hắc Ám)."},
    "pvp_unbeaten": {"icon": "🏅", "name": "Bất Bại",         "desc": "Thắng 10 trận PvP liên tiếp."},
    "rank_II":  {"icon": "⚔️", "name": "Đăng cơ Hạng II",  "desc": "Trở thành ⚔️ Chiến Binh Tập Luyện và nhận role thưởng."},
    "rank_III": {"icon": "🩸", "name": "Đăng cơ Hạng III", "desc": "Trở thành 🩸 Kẻ Săn Linh Hồn và nhận role thưởng."},
    "rank_IV":  {"icon": "👁",  "name": "Đăng cơ Hạng IV",  "desc": "Trở thành 👁 Kỵ Sĩ Hắc Ấn và nhận role thưởng."},
    "rank_V":   {"icon": "👑", "name": "Đăng cơ Hạng V",   "desc": "Đăng cơ 👑 Chúa Tể Hắc Ám và nhận role thưởng."},
}
ACHIEVEMENT_ORDER = list(ACHIEVEMENTS.keys())


def _qualifies(aid: str, p) -> bool:
    wins = int(p.get("wins", 0))
    rank = p.get("rank", "I")
    streak = int(p.get("pvp_streak", 0))
    boss_kills = int(p.get("wins_by_level", {}).get("5", 0))
    if aid == "pve_10":  return wins >= 10
    if aid == "pve_100": return wins >= 100
    if aid == "pve_200": return wins >= 200
    if aid == "pve_300": return wins >= 300
    if aid == "pve_400": return wins >= 400
    if aid == "pve_500": return wins >= 500
    if aid == "boss_slayer":  return boss_kills >= 1
    if aid == "pvp_unbeaten": return streak >= 10
    if aid.startswith("rank_"):
        target = aid.split("_", 1)[1]
        if target not in RANKS or rank not in RANKS:
            return False
        return RANKS.index(rank) >= RANKS.index(target)
    return False


def unlock_achievements(player) -> list[str]:
    """Quét lại điều kiện, thêm các thành tựu mới vào player['achievements']
    và trả về danh sách ID vừa mở khoá (để công bố)."""
    have = set(player.get("achievements", []))
    newly = []
    for aid in ACHIEVEMENT_ORDER:
        if aid not in have and _qualifies(aid, player):
            newly.append(aid)
    if newly:
        player.setdefault("achievements", [])
        player["achievements"].extend(newly)
    return newly


def format_achievements(player) -> str:
    have = set(player.get("achievements", []))
    if not have:
        return "🏅 **Thành tựu:** _(chưa có thành tựu nào — hãy ra trận!)_"
    lines = ["🏅 **Thành tựu đã đạt:**"]
    for aid in ACHIEVEMENT_ORDER:
        if aid in have:
            a = ACHIEVEMENTS[aid]
            lines.append(f"{a['icon']} **{a['name']}** — {a['desc']}")
    return "\n".join(lines)


def announce_unlocks(new_ids: list[str]) -> str:
    if not new_ids:
        return ""
    lines = ["", "🎖 **Thành tựu mới mở khoá!**"]
    for aid in new_ids:
        a = ACHIEVEMENTS[aid]
        lines.append(f"• {a['icon']} **{a['name']}** — {a['desc']}")
    return "\n".join(lines)


# ============== NAVIGATION ==============
async def go_lobby(interaction: discord.Interaction, user: discord.User):
    from .menu import MainView
    await interaction.response.edit_message(
        embed=knight_embed(get_lore_text(interaction.guild_id, "intro")),
        view=MainView(user, interaction.guild),
    )


async def exit_bot(interaction: discord.Interaction):
    await interaction.response.edit_message(
        embed=knight_embed(get_lore_text(interaction.guild_id, "outro")),
        view=None,
    )


# ============== RANK UP ANNOUNCE ==============
async def announce_rank_up(channel: discord.abc.Messageable, member: discord.abc.User, new_rank: str, guild_id):
    """Khi user đạt 1 rank mới: chúc mừng. Rank V (cao nhất): tag @everyone — đây là sự kiện đặc biệt, không phải trận đấu thông thường."""
    rinfo = RANK_INFO[new_rank]
    is_top = new_rank == "V"
    bonus = training_bonus_pct(new_rank)
    if is_top:
        text = t(guild_id, member.id, "rankup_top_text",
                 mention=member.mention, rank_name=rinfo["name"], speech=rinfo["speech"], bonus=bonus)
        embed = discord.Embed(
            title="✨👑🏆 ĐĂNG CƠ — CHÚA TỂ ĐẤU TRƯỜNG 🏆👑✨",
            description=text,
            color=GOLD_COLOR,
        )
        embed.set_footer(text="🌑 Một huyền thoại đã được khắc tên vào sổ đẫm máu.")
    else:
        text = t(guild_id, member.id, "rankup_text",
                 mention=member.mention, rank_name=rinfo["name"], speech=rinfo["speech"], bonus=bonus)
        embed = discord.Embed(
            title=f"🎉🏆 {t(guild_id, member.id, 'rankup_title')} 🏆🎉",
            description=text,
            color=GOLD_COLOR,
        )
    try:
        await channel.send(
            content=("@everyone" if is_top else None),
            embed=embed,
            allowed_mentions=discord.AllowedMentions(everyone=is_top, users=True),
        )
    except (discord.Forbidden, discord.HTTPException):
        pass


async def maybe_grant_rank_role(interaction, user, new_rank):
    """Cấp role thưởng nếu admin đã thiết lập."""
    try:
        g = get_guild(interaction.guild_id)
        role_id = g["config"]["rank_roles"].get(new_rank)
        if not role_id:
            return False
        guild = interaction.guild
        member = guild.get_member(user.id) or await guild.fetch_member(user.id)
        role = guild.get_role(int(role_id))
        if member and role:
            await member.add_roles(role, reason=f"Lên hạng {new_rank}")
            return True
    except Exception:
        pass
    return False


def has_rank_role(member: discord.Member | None, guild_id, rank: str) -> bool:
    if not member:
        return False
    g = get_guild(guild_id)
    role_id = g["config"]["rank_roles"].get(rank)
    if not role_id:
        return False
    return any(str(r.id) == str(role_id) for r in member.roles)
