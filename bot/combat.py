"""Combat: PvE (monsters) and PvP (player vs player)."""
import asyncio
import random
import time

import discord

from .storage import get_player, persist, get_locale
from .core import (
    knight_embed, t, RANK_INFO, RANKS, Monster, monsters_by_level, can_fight_monster,
    attack_chance, block_chance, player_max_hp, heal_amount, damage_value,
    damage_pct, compute_power, hp_bar_widths, hp_pct_display,
    crit_check, miss_check, compute_rank, has_rank_role,
    go_lobby, exit_bot, announce_rank_up, maybe_grant_rank_role,
    unlock_achievements, announce_unlocks, announce_achievements_public,
    rank_name as rk_name, rank_speech as rk_speech,
)


def _add_lobby_exit(view: discord.ui.View, user, gid, row: int = 1):
    lobby = discord.ui.Button(
        label=t(gid, user.id, "btn_lobby"),
        style=discord.ButtonStyle.secondary, row=row,
    )
    async def lobby_cb(interaction):
        await go_lobby(interaction, user)
    lobby.callback = lobby_cb
    view.add_item(lobby)

    exitb = discord.ui.Button(
        label=t(gid, user.id, "btn_exit"),
        style=discord.ButtonStyle.danger, row=row,
    )
    async def exit_cb(interaction):
        await exit_bot(interaction)
    exitb.callback = exit_cb
    view.add_item(exitb)


# ============== CHALLENGE MENU ==============
class ChallengeMenuView(discord.ui.View):
    def __init__(self, user, guild_id=None):
        super().__init__(timeout=300)
        self.user = user
        gid = guild_id

        pvp_btn = discord.ui.Button(
            label=t(gid, user.id, "btn_pvp_challenge"),
            style=discord.ButtonStyle.primary, row=0,
        )
        async def pvp_cb(interaction):
            await show_pvp_target_picker(interaction, self.user)
        pvp_btn.callback = pvp_cb
        self.add_item(pvp_btn)

        pve_btn = discord.ui.Button(
            label=t(gid, user.id, "btn_pve_challenge"),
            style=discord.ButtonStyle.danger, row=0,
        )
        async def pve_cb(interaction):
            await interaction.response.edit_message(
                embed=knight_embed(t(interaction.guild_id, self.user.id, "pve_pick_level")),
                view=PveLevelView(self.user, interaction.guild_id),
            )
        pve_btn.callback = pve_cb
        self.add_item(pve_btn)

        _add_lobby_exit(self, user, gid, row=1)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


# ============== PvE LEVEL SELECT ==============
LEVEL_LABELS = {
    1: ("🪨 Cấp I — Khởi đầu", "🪨 Tier I — Beginnings"),
    2: ("🌲 Cấp II — Thích nghi", "🌲 Tier II — Adaptation"),
    3: ("🔥 Cấp III — Nguy hiểm", "🔥 Tier III — Dangerous"),
    4: ("🌑 Cấp IV — Ác mộng", "🌑 Tier IV — Nightmare"),
    5: ("👑 Cấp V — Endgame", "👑 Tier V — Endgame"),
}


def _level_label(lv: int, locale: str = "vi") -> str:
    vi, en = LEVEL_LABELS.get(lv, (str(lv), str(lv)))
    return en if locale == "en" else vi


class PveLevelView(discord.ui.View):
    def __init__(self, user, guild_id=None):
        super().__init__(timeout=300)
        self.user = user
        gid = guild_id
        locale = get_locale(gid, user.id) if gid else "vi"

        for lv in [1, 2, 3, 4, 5]:
            label = _level_label(lv, locale)
            btn = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary, row=(lv - 1) // 3)
            async def cb(interaction, lv_=lv):
                if interaction.user.id != self.user.id:
                    return
                await self._show_monsters(interaction, lv_)
            btn.callback = cb
            self.add_item(btn)

        _add_lobby_exit(self, user, gid, row=2)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    async def _show_monsters(self, interaction, level: int):
        p = get_player(interaction.guild_id, self.user.id)
        rank_lv = RANKS.index(p["rank"]) + 1
        allow_boss_challenge = (rank_lv == 4 and level == 5)
        if level > rank_lv and not allow_boss_challenge:
            await interaction.response.edit_message(
                embed=knight_embed(t(interaction.guild_id, self.user.id, "no_overrun",
                                     rank=rk_name(p['rank'], get_locale(interaction.guild_id, self.user.id)))),
                view=ChallengeMenuView(self.user, interaction.guild_id),
            )
            return
        member = interaction.guild.get_member(self.user.id) if interaction.guild else None
        if level == rank_lv and rank_lv > 1:
            from .storage import get_guild
            g = get_guild(interaction.guild_id)
            role_id = g["config"]["rank_roles"].get(p["rank"])
            if role_id and not has_rank_role(member, interaction.guild_id, p["rank"]):
                await interaction.response.edit_message(
                    embed=knight_embed(t(interaction.guild_id, self.user.id, "no_overrun",
                                         rank=rk_name(p['rank'], get_locale(interaction.guild_id, self.user.id)))),
                    view=ChallengeMenuView(self.user, interaction.guild_id),
                )
                return
        monsters = monsters_by_level(level)
        locale = get_locale(interaction.guild_id, self.user.id)
        label = _level_label(level, locale)
        choose_word = "Choose your foe:" if locale == "en" else "Hãy chọn đối thủ:"
        embed = knight_embed(f"**{label}** — {choose_word}")
        await interaction.response.edit_message(
            embed=embed,
            view=PveMonsterView(self.user, monsters, interaction.guild_id),
        )


async def show_pve_level_view(interaction, user):
    await interaction.response.edit_message(
        embed=knight_embed(t(interaction.guild_id, user.id, "pve_pick_level")),
        view=PveLevelView(user, interaction.guild_id),
    )


class PveMonsterView(discord.ui.View):
    def __init__(self, user, monsters, guild_id=None):
        super().__init__(timeout=300)
        self.user = user
        gid = guild_id
        for i, m in enumerate(monsters):
            btn = discord.ui.Button(
                label=f"{m.emoji} {m.name}  🛡{m.tank} 🗡{m.dps} 💊{m.hp}",
                style=discord.ButtonStyle.danger,
                row=i // 2,
            )
            async def cb(interaction, mon=m):
                if interaction.user.id != self.user.id:
                    return
                await show_pve_ready(interaction, self.user, mon)
            btn.callback = cb
            self.add_item(btn)

        back = discord.ui.Button(
            label=t(gid, user.id, "btn_back"),
            style=discord.ButtonStyle.secondary, row=4,
        )
        async def back_cb(interaction):
            await show_pve_level_view(interaction, self.user)
        back.callback = back_cb
        self.add_item(back)

        exitb = discord.ui.Button(
            label=t(gid, user.id, "btn_exit"),
            style=discord.ButtonStyle.danger, row=4,
        )
        async def exit_cb(interaction):
            await exit_bot(interaction)
        exitb.callback = exit_cb
        self.add_item(exitb)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


# ============== BATTLE CORE ==============
class BattleSide:
    def __init__(self, name, tank, dps, max_hp, is_monster=False, user_id=None):
        self.name = name
        self.tank = tank
        self.dps = dps
        self.max_hp = max_hp
        self.hp = max_hp
        self.is_monster = is_monster
        self.user_id = user_id


class PveActionView(discord.ui.View):
    def __init__(self, user_id, locale: str = "vi", guild_id=None):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.locale = locale
        self.choice: str | None = None
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()

        atk = discord.ui.Button(
            label=t(guild_id, user_id, "btn_attack"),
            style=discord.ButtonStyle.danger,
        )
        async def atk_cb(interaction):
            await self._set(interaction, "A")
        atk.callback = atk_cb
        self.add_item(atk)

        df = discord.ui.Button(
            label=t(guild_id, user_id, "btn_defend"),
            style=discord.ButtonStyle.primary,
        )
        async def df_cb(interaction):
            await self._set(interaction, "D")
        df.callback = df_cb
        self.add_item(df)

        flee = discord.ui.Button(
            label=t(guild_id, user_id, "btn_flee"),
            style=discord.ButtonStyle.secondary,
        )
        async def flee_cb(interaction):
            await self._set(interaction, "F")
        flee.callback = flee_cb
        self.add_item(flee)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user_id

    async def _set(self, interaction, c):
        self.choice = c
        await interaction.response.defer()
        if not self.future.done():
            self.future.set_result(c)
        self.stop()

    async def on_timeout(self):
        if not self.future.done():
            self.future.set_result("D")


def hp_bar(cur, mx, width=12):
    """Legacy helper — fills based on raw cur/mx (no percentage normalisation)."""
    filled = max(0, min(width, int(width * cur / mx)))
    return "█" * filled + "░" * (width - filled)


def _hp_bar_pct(pct: int, width: int) -> str:
    """Render a fixed-width bar from a normalised 0-100 percentage."""
    p = max(0, min(100, pct))
    filled = int(round(width * p / 100))
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def render_hp_line(side: "BattleSide", width: int) -> str:
    """Display HP as 'X/100' (normalised) with a power-scaled bar.
    The display can dip below 0 to expose how badly a fighter was beaten."""
    pct = hp_pct_display(side.hp, side.max_hp)
    return f"💊 `{_hp_bar_pct(pct, width)}` {pct}/100"


def attack_vs_defend(atk: BattleSide, defn: BattleSide, locale: str = "vi") -> list[str]:
    log = []
    block = block_chance(defn.tank, atk.dps)
    if miss_check():
        log.append(f"💀 🗡 {atk.name} {'missed!' if locale == 'en' else 'đánh trượt!'}")
        return log
    if random.random() < block:
        log.append(f"🌟 🛡 {defn.name} {'blocked the strike.' if locale == 'en' else 'chặn đứng đòn đánh.'}")
    else:
        dmg = damage_pct(atk.dps, defn.tank, defn.max_hp)
        if locale == "en":
            log.append(f"💀 🛡 {defn.name}'s defense crumbles! 🗡 {atk.name} deals **-{dmg} HP**.")
        else:
            log.append(f"💀 🛡 Phòng thủ của {defn.name} sụp đổ! 🗡 {atk.name} gây **-{dmg} HP**.")
        defn.hp -= dmg
    return log


def resolve_round(p: BattleSide, e: BattleSide, p_choice: str, e_choice: str, locale: str = "vi") -> list[str]:
    log = []
    if p_choice == "A" and e_choice == "A":
        for atk, defn in ((p, e), (e, p)):
            if miss_check():
                log.append(f"💀 🗡 {atk.name} {'missed!' if locale == 'en' else 'đánh trượt!'}")
                continue
            if random.random() < attack_chance(atk.dps, defn.dps):
                dmg = damage_pct(atk.dps, defn.tank, defn.max_hp)
                if crit_check():
                    dmg = int(dmg * 1.5)
                    log.append(f"🌟 🗡 {atk.name} **CRIT** {'on' if locale == 'en' else 'lên'} {defn.name}! **-{dmg} HP**")
                else:
                    log.append(f"🗡 {atk.name} {'overpowers' if locale == 'en' else 'áp đảo'} {defn.name}. **-{dmg} HP**")
                defn.hp -= dmg
            else:
                if locale == "en":
                    log.append(f"💀 {defn.name} parries {atk.name}'s blow.")
                else:
                    log.append(f"💀 Đòn của {atk.name} bị {defn.name} vượt qua.")
    elif p_choice == "A" and e_choice == "D":
        log += attack_vs_defend(p, e, locale)
    elif p_choice == "D" and e_choice == "A":
        log += attack_vs_defend(e, p, locale)
    else:
        # D + D — modest mutual recovery, capped so the fight still resolves in 10 rounds
        ph = max(1, int(round(p.max_hp * 0.04)))
        eh = max(1, int(round(e.max_hp * 0.04)))
        p.hp = min(p.max_hp, p.hp + ph)
        e.hp = min(e.max_hp, e.hp + eh)
        if locale == "en":
            log.append(f"💊 Both sides fall back… recovering. {p.name} **+{ph} HP**, {e.name} **+{eh} HP**.")
        else:
            log.append(f"💊 Cả hai lùi lại… củng cố sinh lực. {p.name} **+{ph} HP**, {e.name} **+{eh} HP**.")
    return log


def battle_status_embed(p: BattleSide, e: BattleSide, log_lines, turn, locale: str = "vi") -> discord.Embed:
    if locale == "en":
        turn_line = f"⚔️ **Round {turn}** — Make your choice."
        last_round = "__**Last round:**__"
    else:
        turn_line = f"⚔️ **Lượt {turn}** — Hãy ra quyết định."
        last_round = "__**Lượt vừa rồi:**__"
    pw_p = compute_power(p.tank, p.dps, p.max_hp)
    pw_e = compute_power(e.tank, e.dps, e.max_hp)
    wp, we = hp_bar_widths(pw_p, pw_e)
    return knight_embed(
        f"{turn_line}\n\n"
        f"**{p.name}**\n{render_hp_line(p, wp)}\n\n"
        f"**{e.name}**\n{render_hp_line(e, we)}\n\n"
        + ((f"{last_round}\n" + "\n".join(log_lines)) if log_lines else "")
    )


class PveReadyView(discord.ui.View):
    def __init__(self, user, monster: Monster, guild_id=None):
        super().__init__(timeout=120)
        self.user = user
        self.monster = monster
        gid = guild_id

        enter = discord.ui.Button(
            label=t(gid, user.id, "btn_enter_battle"),
            style=discord.ButtonStyle.danger, row=0,
        )
        async def enter_cb(interaction):
            await start_pve_battle(interaction, self.user, self.monster)
        enter.callback = enter_cb
        self.add_item(enter)

        back = discord.ui.Button(
            label=t(gid, user.id, "btn_back"),
            style=discord.ButtonStyle.secondary, row=0,
        )
        async def back_cb(interaction):
            await show_pve_level_view(interaction, self.user)
        back.callback = back_cb
        self.add_item(back)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


async def show_pve_ready(interaction: discord.Interaction, user: discord.User, monster: Monster):
    p_data = get_player(interaction.guild_id, user.id)
    p_hp = player_max_hp(p_data)
    locale = get_locale(interaction.guild_id, user.id)
    if locale == "en":
        text = (
            f"⚔️ **Battle Preparation**\n\n"
            f"**Opponent:** {monster.display} _(Level {monster.level})_\n"
            f"🛡 Tank `{monster.tank}` | 🗡 DPS `{monster.dps}` | 💊 HP `{monster.hp}`\n\n"
            f"**You:** {user.display_name}\n"
            f"🛡 Tank `{p_data['tank']}` | 🗡 DPS `{p_data['dps']}` | 💊 HP `{p_hp}`\n\n"
            f"_Take a deep breath… then press **💥 Enter Battle** when you are ready. Once you leave the lobby, there is no turning back._"
        )
    else:
        text = (
            f"⚔️ **Chuẩn bị trận chiến**\n\n"
            f"**Đối thủ:** {monster.display} _(Cấp {monster.level})_\n"
            f"🛡 Tank `{monster.tank}` | 🗡 DPS `{monster.dps}` | 💊 HP `{monster.hp}`\n\n"
            f"**Ngươi:** {user.display_name}\n"
            f"🛡 Tank `{p_data['tank']}` | 🗡 DPS `{p_data['dps']}` | 💊 HP `{p_hp}`\n\n"
            f"_Hít một hơi sâu… và bấm **💥 Vào trận** khi đã sẵn sàng. Một khi đã ra khỏi sảnh chờ, sẽ không có đường lui._"
        )
    await interaction.response.edit_message(
        embed=knight_embed(text),
        view=PveReadyView(user, monster, interaction.guild_id),
    )


async def start_pve_battle(interaction: discord.Interaction, user: discord.User, monster: Monster):
    locale = get_locale(interaction.guild_id, user.id)
    p_data = get_player(interaction.guild_id, user.id)
    p_side = BattleSide(user.display_name, p_data["tank"], p_data["dps"], player_max_hp(p_data), False, user.id)
    e_side = BattleSide(monster.display, monster.tank, monster.dps, monster.hp, True)

    # Defer the "Vào trận" interaction so we have time to drive the fight,
    # then drive UI updates through the interaction's original response — same
    # pattern Tank / DPS training use (mixing raw message.edit after defer was
    # unreliable on some hosts and caused the "Vào trận" interaction failed).
    try:
        await interaction.response.defer()
    except discord.InteractionResponded:
        pass

    log = []
    turn = 1
    fled = False
    msg = None
    while p_side.hp > 0 and e_side.hp > 0 and turn <= 30:
        view = PveActionView(user.id, locale, interaction.guild_id)
        embed = battle_status_embed(p_side, e_side, log, turn, locale)
        if msg is None:
            await interaction.edit_original_response(embed=embed, view=view)
            msg = await interaction.original_response()
        else:
            await msg.edit(embed=embed, view=view)
        try:
            p_choice = await asyncio.wait_for(view.future, timeout=31)
        except asyncio.TimeoutError:
            p_choice = "D"
        if p_choice == "F":
            fled = True
            break
        e_choice = "A" if random.random() < 0.7 else "D"
        log = resolve_round(p_side, e_side, p_choice, e_choice, locale)
        turn += 1

    if fled:
        if locale == "en":
            fled_text = (
                f"🏃 You fled from battle against **{monster.display}**. "
                f"A true knight never turns their back…"
            )
        else:
            fled_text = (
                f"🏃 Ngươi đã bỏ chạy khỏi trận đấu với **{monster.display}**. "
                f"Một hiệp sĩ thực sự không bao giờ quay lưng…"
            )
        await msg.edit(
            embed=knight_embed(fled_text),
            view=PostBattleView(user, interaction.guild_id),
        )
        return

    p_data = get_player(interaction.guild_id, user.id)
    if p_side.hp > 0 and e_side.hp <= 0:
        bonus = {1: 1, 2: 2, 3: 4, 4: 7, 5: 10}[monster.level]
        p_data["wins"] += 1
        p_data["wins_by_level"][str(monster.level)] = p_data["wins_by_level"].get(str(monster.level), 0) + 1
        old_rank = p_data["rank"]
        new_rank = compute_rank(p_data)
        rank_up = new_rank != old_rank
        p_data["rank"] = new_rank
        new_ach = unlock_achievements(p_data)
        persist()
        if locale == "en":
            text = (
                f"🌟 You are the last one standing.\n\n"
                f"⚔️ Defeated **{monster.display}** (Level {monster.level}) — **+{bonus} merit points**\n"
                f"💊 HP remaining: {p_side.hp}/{p_side.max_hp}"
            )
            if rank_up:
                rn = rk_name(new_rank, "en")
                rs = rk_speech(new_rank, "en")
                text += f"\n\n🏆 **RANK UP!** You are now **{rn}**\n{rs}"
                await maybe_grant_rank_role(interaction, user, new_rank)
        else:
            text = (
                f"🌟 Ngươi là kẻ sống sót cuối cùng.\n\n"
                f"⚔️ Hạ gục **{monster.display}** (Cấp {monster.level}) — **+{bonus} điểm chiến công**\n"
                f"💊 Máu còn lại: {p_side.hp}/{p_side.max_hp}"
            )
            if rank_up:
                rn = rk_name(new_rank, "vi")
                rs = rk_speech(new_rank, "vi")
                text += f"\n\n🏆 **THĂNG HẠNG!** Giờ đây ngươi là **{rn}**\n{rs}"
                await maybe_grant_rank_role(interaction, user, new_rank)
        text += announce_unlocks(new_ach, locale)
        await msg.edit(embed=knight_embed(text), view=PostBattleView(user, interaction.guild_id))
        if rank_up and interaction.channel:
            await announce_rank_up(interaction.channel, interaction.user, new_rank, interaction.guild_id)
        if new_ach and interaction.channel:
            await announce_achievements_public(interaction.channel, interaction.user, new_ach, locale)
    else:
        if locale == "en":
            lose_text = (
                f"💀 💊 Your life force… has been extinguished.\n\n"
                f"You have fallen at the hands of **{monster.display}**."
            )
        else:
            lose_text = (
                f"💀 💊 Sinh mệnh của ngươi… đã cạn.\n\n"
                f"Ngươi đã ngã xuống dưới tay **{monster.display}**."
            )
        await msg.edit(
            embed=knight_embed(lose_text),
            view=PostBattleView(user, interaction.guild_id),
        )


class PostBattleView(discord.ui.View):
    def __init__(self, user, guild_id=None, allowed_ids: set[int] | None = None, show_again: bool = True):
        super().__init__(timeout=300)
        self.user = user
        self.allowed_ids = allowed_ids if allowed_ids is not None else {user.id}
        gid = guild_id

        if show_again:
            again = discord.ui.Button(
                label=t(gid, user.id, "btn_fight_again"),
                style=discord.ButtonStyle.danger, row=0,
            )
            async def again_cb(interaction):
                await interaction.response.edit_message(
                    embed=knight_embed(t(interaction.guild_id, interaction.user.id, "msg_choose_next_foe")),
                    view=ChallengeMenuView(interaction.user, interaction.guild_id),
                )
            again.callback = again_cb
            self.add_item(again)

        lobby = discord.ui.Button(
            label=t(gid, user.id, "btn_lobby"),
            style=discord.ButtonStyle.secondary, row=0,
        )
        async def lobby_cb(interaction):
            await go_lobby(interaction, interaction.user)
        lobby.callback = lobby_cb
        self.add_item(lobby)

        exitb = discord.ui.Button(
            label=t(gid, user.id, "btn_exit"),
            style=discord.ButtonStyle.danger, row=0,
        )
        async def exit_cb(interaction):
            await exit_bot(interaction)
        exitb.callback = exit_cb
        self.add_item(exitb)

    async def interaction_check(self, interaction):
        return interaction.user.id in self.allowed_ids


# ============== PvP ==============
ONLINE_STATUSES = {discord.Status.online, discord.Status.idle, discord.Status.dnd}


def _list_online_targets(guild: discord.Guild, exclude_id: int) -> list[discord.Member]:
    """Return up to 25 non-bot members who appear online (idle/dnd counted)."""
    online = []
    offline = []
    for m in guild.members:
        if m.bot or m.id == exclude_id:
            continue
        if m.status in ONLINE_STATUSES:
            online.append(m)
        else:
            offline.append(m)
    online.sort(key=lambda m: m.display_name.lower())
    return online[:25]


class PvpTargetSelectView(discord.ui.View):
    def __init__(self, challenger, guild: discord.Guild, guild_id=None):
        super().__init__(timeout=180)
        self.challenger = challenger
        gid = guild_id
        locale = get_locale(gid, challenger.id) if gid else "vi"

        targets = _list_online_targets(guild, challenger.id)
        if targets:
            placeholder = "Choose an online opponent…" if locale == "en" else "Chọn đối thủ đang online…"
            options = []
            for m in targets:
                status_emoji = {
                    discord.Status.online: "🟢",
                    discord.Status.idle:   "🌙",
                    discord.Status.dnd:    "⛔",
                }.get(m.status, "⚪")
                options.append(discord.SelectOption(
                    label=m.display_name[:90],
                    value=str(m.id),
                    description=("Online" if locale == "en" else "Đang online") if m.status == discord.Status.online else (
                        "Idle" if locale == "en" else "Vắng mặt") if m.status == discord.Status.idle else (
                        "Do not disturb" if locale == "en" else "Đừng làm phiền"),
                    emoji=status_emoji,
                ))
            select = discord.ui.Select(placeholder=placeholder, options=options, min_values=1, max_values=1, row=0)

            async def pick_cb(interaction):
                target_id = int(select.values[0])
                target = guild.get_member(target_id)
                if not target:
                    try:
                        target = await guild.fetch_member(target_id)
                    except (discord.NotFound, discord.HTTPException):
                        target = None
                if not target:
                    cur = get_locale(interaction.guild_id, self.challenger.id)
                    msg = "💀 That person is no longer in this realm." if cur == "en" else "💀 Kẻ đó không còn ở trong vương quốc này."
                    await interaction.response.send_message(embed=knight_embed(msg), ephemeral=True)
                    return
                # Post-duel cooldown gate — challenger AND target must be free.
                cur_locale = get_locale(interaction.guild_id, self.challenger.id)
                ch_left = pvp_cooldown_remaining(interaction.guild_id, self.challenger.id)
                tg_left = pvp_cooldown_remaining(interaction.guild_id, target.id)
                if ch_left > 0:
                    await interaction.response.send_message(
                        embed=knight_embed(_cooldown_msg(self.challenger.display_name, ch_left, cur_locale)),
                        ephemeral=True,
                    )
                    return
                if tg_left > 0:
                    await interaction.response.send_message(
                        embed=knight_embed(_cooldown_msg(target.display_name, tg_left, cur_locale)),
                        ephemeral=True,
                    )
                    return
                await send_pvp_invite(interaction, self.challenger, target)

            select.callback = pick_cb
            self.add_item(select)
        else:
            empty_label = "🌑 No online opponents" if locale == "en" else "🌑 Không có đối thủ online"
            empty_btn = discord.ui.Button(label=empty_label, style=discord.ButtonStyle.secondary, disabled=True, row=0)
            self.add_item(empty_btn)

        _add_lobby_exit(self, challenger, gid, row=1)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.challenger.id


async def show_pvp_target_picker(interaction: discord.Interaction, challenger):
    locale = get_locale(interaction.guild_id, challenger.id)
    if locale == "en":
        text = (
            "⚔️ **Choose Your Opponent**\n\n"
            "Below is the list of warriors currently online in this realm. "
            "Pick one to send a 1v1 challenge."
        )
    else:
        text = (
            "⚔️ **Chọn đối thủ**\n\n"
            "Dưới đây là danh sách các đấu sĩ đang online trong vương quốc này. "
            "Hãy chọn một người để gửi lời thách đấu 1vs1."
        )
    await interaction.response.edit_message(
        embed=knight_embed(text),
        view=PvpTargetSelectView(challenger, interaction.guild, interaction.guild_id),
    )


async def send_pvp_invite(interaction: discord.Interaction, challenger, target):
    """Send invite as a private DM to the target; lock challenger's screen to 'waiting'."""
    locale_ch = get_locale(interaction.guild_id, challenger.id)
    locale_tg = get_locale(interaction.guild_id, target.id)
    channel = interaction.channel
    gid = interaction.guild_id
    guild_name = interaction.guild.name if interaction.guild else "?"
    channel_name = channel.name if channel and hasattr(channel, "name") else "?"

    if locale_tg == "en":
        invite_text = (
            f"⚔️✉️⚔️ **Challenge Invitation**\n\n"
            f"**{challenger.display_name}** has challenged you to a 1vs1 duel "
            f"in **#{channel_name}** of **{guild_name}**!\n\n"
            f"Do you dare accept? _(60 seconds to respond)_"
        )
    else:
        invite_text = (
            f"⚔️✉️⚔️ **Thư mời thách đấu**\n\n"
            f"**{challenger.display_name}** đã thách đấu ngươi 1vs1 "
            f"tại kênh **#{channel_name}** của **{guild_name}**!\n\n"
            f"Ngươi có dám chấp nhận? _(60 giây để trả lời)_"
        )

    if locale_ch == "en":
        wait_text = (
            f"📨 **Invitation sent to {target.display_name}.**\n\n"
            f"Awaiting their reply via private message (up to 60 seconds)…"
        )
    else:
        wait_text = (
            f"📨 **Đã gửi lời mời tới {target.display_name}.**\n\n"
            f"Đang chờ phản hồi qua tin nhắn riêng (tối đa 60 giây)…"
        )
    await interaction.response.edit_message(embed=knight_embed(wait_text), view=None)
    lobby_message = await interaction.original_response()

    try:
        dm_view = PvpInviteView(challenger, target, channel, lobby_message, gid)
        dm_msg = await target.send(embed=knight_embed(invite_text), view=dm_view)
        dm_view.bind_message(dm_msg)
    except (discord.Forbidden, discord.HTTPException):
        if locale_ch == "en":
            err = (
                f"💀 Could not deliver the invitation — **{target.display_name}** "
                f"has direct messages from server members closed."
            )
        else:
            err = (
                f"💀 Không thể gửi lời mời — **{target.display_name}** "
                f"đã tắt tin nhắn riêng từ thành viên server."
            )
        try:
            await lobby_message.edit(
                embed=knight_embed(err),
                view=ChallengeMenuView(challenger, gid),
            )
        except (discord.NotFound, discord.HTTPException):
            pass


class PvpInviteView(discord.ui.View):
    def __init__(self, challenger, target, channel, lobby_message, guild_id=None):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.target = target
        self.channel = channel
        self.lobby_message = lobby_message
        self.guild_id = guild_id
        self.responded = False
        self.dm_message: discord.Message | None = None

        accept = discord.ui.Button(
            label=t(guild_id, target.id, "pvp_accept_btn"),
            style=discord.ButtonStyle.success,
        )
        async def accept_cb(interaction):
            locale_tg = get_locale(self.guild_id, self.target.id)
            # Cooldown gate — neither fighter may start a new duel until both
            # are free (this matches the post-duel thread-cleanup window).
            ch_left = pvp_cooldown_remaining(self.guild_id, self.challenger.id)
            tg_left = pvp_cooldown_remaining(self.guild_id, self.target.id)
            if ch_left > 0 or tg_left > 0:
                blocked = self.challenger if ch_left >= tg_left else self.target
                secs = max(ch_left, tg_left)
                await interaction.response.edit_message(
                    embed=knight_embed(_cooldown_msg(blocked.display_name, secs, locale_tg)),
                    view=None,
                )
                self.responded = True
                self.stop()
                return
            self.responded = True
            if locale_tg == "en":
                ack = f"⚔️ Challenge accepted! Head to **#{self.channel.name}** to fight."
            else:
                ack = f"⚔️ Đã chấp nhận! Hãy vào kênh **#{self.channel.name}** để chiến đấu."
            await interaction.response.edit_message(embed=knight_embed(ack), view=None)
            self.stop()
            await start_pvp_battle(self.channel, self.lobby_message,
                                   self.challenger, self.target, self.guild_id)
        accept.callback = accept_cb
        self.add_item(accept)

        decline = discord.ui.Button(
            label=t(guild_id, target.id, "pvp_decline_btn"),
            style=discord.ButtonStyle.danger,
        )
        async def decline_cb(interaction):
            self.responded = True
            locale_tg = get_locale(self.guild_id, self.target.id)
            locale_ch = get_locale(self.guild_id, self.challenger.id)
            tmsg = ("🌑 You declined the challenge."
                    if locale_tg == "en"
                    else "🌑 Ngươi đã từ chối thách đấu.")
            cmsg = (f"🌑 **{self.target.display_name}** declined your challenge."
                    if locale_ch == "en"
                    else f"🌑 **{self.target.display_name}** đã từ chối thách đấu của ngươi.")
            await interaction.response.edit_message(embed=knight_embed(tmsg), view=None)
            try:
                await self.lobby_message.edit(
                    embed=knight_embed(cmsg),
                    view=ChallengeMenuView(self.challenger, self.guild_id),
                )
            except (discord.NotFound, discord.HTTPException):
                pass
            self.stop()
        decline.callback = decline_cb
        self.add_item(decline)

    def bind_message(self, message: discord.Message):
        self.dm_message = message

    async def interaction_check(self, interaction):
        if interaction.user.id != self.target.id:
            locale = get_locale(self.guild_id, interaction.user.id)
            msg = "Only the invited player may respond." if locale == "en" else "Chỉ người được mời mới có thể trả lời."
            await interaction.response.send_message(msg, ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.responded:
            return
        locale_tg = get_locale(self.guild_id, self.target.id) if self.guild_id else "vi"
        locale_ch = get_locale(self.guild_id, self.challenger.id) if self.guild_id else "vi"
        tmsg = ("⌛ The invitation has expired."
                if locale_tg == "en"
                else "⌛ Lời mời đã hết hạn.")
        cmsg = (f"⌛ **{self.target.display_name}** did not respond within 60 seconds. "
                f"The match has been cancelled."
                if locale_ch == "en"
                else f"⌛ **{self.target.display_name}** đã không trả lời trong 60 giây. "
                f"Trận đấu đã bị hủy.")
        if self.dm_message:
            try:
                await self.dm_message.edit(embed=knight_embed(tmsg), view=None)
            except (discord.NotFound, discord.HTTPException):
                pass
        try:
            await self.lobby_message.edit(
                embed=knight_embed(cmsg),
                view=ChallengeMenuView(self.challenger, self.guild_id),
            )
        except (discord.NotFound, discord.HTTPException):
            pass


# ============== PvP BATTLE ==============
def _build_pvp_embed(s1, s2, turn, max_turns, header_line, log_block, locale: str = "vi") -> discord.Embed:
    if locale == "en":
        title = f"⚔️ **Round {turn}/{max_turns}**"
    else:
        title = f"⚔️ **Lượt {turn}/{max_turns}**"
    pw1 = compute_power(s1.tank, s1.dps, s1.max_hp)
    pw2 = compute_power(s2.tank, s2.dps, s2.max_hp)
    w1, w2 = hp_bar_widths(pw1, pw2)
    body = (
        f"{title}\n\n"
        f"**{s1.name}** {render_hp_line(s1, w1)}\n"
        f"**{s2.name}** {render_hp_line(s2, w2)}\n\n"
        f"{header_line}"
    )
    if log_block:
        body += "\n\n" + log_block
    return knight_embed(body)


def _build_spectator_embed(s1, s2, turn, max_turns, header_line,
                           narration_lines: list[str], locale: str = "vi") -> discord.Embed:
    """Read-only spectator embed for the main channel — no buttons attached.

    `narration_lines` is the accumulated round-by-round commentary so the whole
    server can follow the duel by reading just this single message.
    """
    if locale == "en":
        title = f"👁 **Live — Round {max(0, turn)}/{max_turns}** (spectator view)"
        log_label = "📜 **Battle log:**"
    else:
        title = f"👁 **Trực tiếp — Lượt {max(0, turn)}/{max_turns}** (chế độ khán giả)"
        log_label = "📜 **Diễn biến trận đấu:**"
    pw1 = compute_power(s1.tank, s1.dps, s1.max_hp)
    pw2 = compute_power(s2.tank, s2.dps, s2.max_hp)
    w1, w2 = hp_bar_widths(pw1, pw2)
    body = (
        f"{title}\n\n"
        f"**{s1.name}** {render_hp_line(s1, w1)}\n"
        f"**{s2.name}** {render_hp_line(s2, w2)}\n\n"
        f"{header_line}"
    )
    # Accumulated narration (keep the embed under Discord's 4096-char limit by
    # showing the most recent rounds first, oldest dropped if needed).
    if narration_lines:
        joined = "\n".join(narration_lines)
        if len(joined) > 3500:
            # keep the tail
            joined = "…\n" + joined[-3400:]
        body += f"\n\n{log_label}\n{joined}"
    return knight_embed(body)


async def _safe_edit(message, **kwargs):
    """Edit a message and swallow Discord exceptions to avoid breaking the battle loop."""
    if message is None:
        return
    try:
        await message.edit(**kwargs)
    except (discord.NotFound, discord.HTTPException, discord.Forbidden):
        pass


class PvpTurnView(discord.ui.View):
    """Sequential-turn PvP view. Only `current_uid` may pick attack/defend.
    Either combatant may surrender at any time."""

    def __init__(self, current_uid: int, other_uid: int, locale: str = "vi", guild_id=None):
        super().__init__(timeout=60)
        self.current_uid = current_uid
        self.other_uid = other_uid
        self.locale = locale
        self.choice: str | None = None
        self.surrender_uid: int | None = None
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()

        atk = discord.ui.Button(
            label=t(guild_id, current_uid, "btn_attack"),
            style=discord.ButtonStyle.danger, row=0,
        )
        async def atk_cb(interaction):
            if interaction.user.id != self.current_uid:
                msg = "It is not your turn." if self.locale == "en" else "Chưa tới lượt ngươi."
                await interaction.response.send_message(msg, ephemeral=True)
                return
            await self._set(interaction, "A")
        atk.callback = atk_cb
        self.add_item(atk)

        df = discord.ui.Button(
            label=t(guild_id, current_uid, "btn_defend"),
            style=discord.ButtonStyle.primary, row=0,
        )
        async def df_cb(interaction):
            if interaction.user.id != self.current_uid:
                msg = "It is not your turn." if self.locale == "en" else "Chưa tới lượt ngươi."
                await interaction.response.send_message(msg, ephemeral=True)
                return
            await self._set(interaction, "D")
        df.callback = df_cb
        self.add_item(df)

        sur_label = "🏳️ Surrender" if locale == "en" else "🏳️ Đầu hàng"
        sur = discord.ui.Button(label=sur_label, style=discord.ButtonStyle.secondary, row=0)
        async def sur_cb(interaction):
            if interaction.user.id not in (self.current_uid, self.other_uid):
                msg = "You are not in this battle." if self.locale == "en" else "Ngươi không tham chiến."
                try:
                    await interaction.response.send_message(msg, ephemeral=True)
                except (discord.NotFound, discord.HTTPException, discord.InteractionResponded):
                    pass
                return
            self.surrender_uid = interaction.user.id
            try:
                await interaction.response.defer()
            except (discord.NotFound, discord.HTTPException, discord.InteractionResponded):
                pass
            if not self.future.done():
                self.future.set_result(True)
            self.stop()
        sur.callback = sur_cb
        self.add_item(sur)

    async def _set(self, interaction, c: str):
        # Defensive: if the future was already settled (timeout or surrender raced
        # us), still acknowledge the click so Discord doesn't show "interaction
        # failed" on the user's screen.
        if self.future.done():
            try:
                await interaction.response.defer()
            except (discord.NotFound, discord.HTTPException, discord.InteractionResponded):
                pass
            return
        self.choice = c
        try:
            await interaction.response.defer()
        except (discord.NotFound, discord.HTTPException, discord.InteractionResponded):
            pass
        if not self.future.done():
            self.future.set_result(True)
        self.stop()

    async def on_timeout(self):
        if not self.future.done():
            if self.choice is None:
                self.choice = "D"
            self.future.set_result(True)


def _choice_label(c: str, locale: str = "vi") -> str:
    if c == "A":
        return "🗡 attack" if locale == "en" else "🗡 tấn công"
    return "🛡 defend" if locale == "en" else "🛡 phòng thủ"


# ---------------------------------------------------------------------------
# Active-PvP registry — lets admins force-end ongoing duels via /end_pvp.
# Keyed by (guild_id, channel_id). Each entry holds a cancel asyncio.Event,
# the thread (if any), and the two combatants for messaging.
# ---------------------------------------------------------------------------
_ACTIVE_PVP: dict[tuple[int, int], dict] = {}


# ---------------------------------------------------------------------------
# Post-duel cooldown — fighters cannot start / accept a new PvP for this many
# seconds after a duel ends (matches the duel-thread cleanup window).
# ---------------------------------------------------------------------------
PVP_COOLDOWN_SECS = 15
_PVP_COOLDOWN: dict[tuple[int, int], float] = {}  # (gid, uid) -> ts when free


def _set_pvp_cooldown(gid: int, uid: int, secs: int = PVP_COOLDOWN_SECS) -> None:
    if gid is None or uid is None:
        return
    _PVP_COOLDOWN[(gid, uid)] = time.time() + secs


def pvp_cooldown_remaining(gid: int, uid: int) -> int:
    """Seconds remaining on the user's post-duel PvP cooldown (0 if free)."""
    ts = _PVP_COOLDOWN.get((gid, uid))
    if not ts:
        return 0
    rem = ts - time.time()
    if rem <= 0:
        _PVP_COOLDOWN.pop((gid, uid), None)
        return 0
    return int(rem) + 1


def _cooldown_msg(name: str, secs: int, locale: str) -> str:
    if locale == "en":
        return (f"⏳ **{name}** is still recovering from the previous duel — "
                f"please wait **{secs}s** before starting another PvP match.")
    return (f"⏳ **{name}** vẫn đang hồi sức sau trận đấu vừa rồi — "
            f"hãy chờ **{secs} giây** rồi mới có thể tham gia trận PvP kế tiếp.")


def get_active_pvp(guild_id: int, channel_id: int):
    return _ACTIVE_PVP.get((guild_id, channel_id))


async def end_pvp_in_channel(guild_id: int, channel_id: int) -> bool:
    """Signal an ongoing PvP duel in the given channel to stop ASAP.

    Returns True if a duel was found and signalled, False otherwise.
    """
    state = _ACTIVE_PVP.get((guild_id, channel_id))
    if not state:
        return False
    state["cancel"].set()
    # Also wake any pending turn future so the loop unblocks immediately.
    for fut_attr in ("view1_future", "view2_future"):
        fut = state.get(fut_attr)
        if fut is not None and not fut.done():
            try:
                fut.set_result(None)
            except Exception:
                pass
    return True


async def _wait_for_choice_or_cancel(view_future, cancel_event, timeout: float):
    """Wait for a turn choice OR a cancel signal, whichever comes first."""
    cancel_task = asyncio.create_task(cancel_event.wait())
    choice_task = asyncio.ensure_future(view_future)
    try:
        await asyncio.wait(
            {cancel_task, choice_task},
            timeout=timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )
    finally:
        if not cancel_task.done():
            cancel_task.cancel()


async def start_pvp_battle(channel, lobby_message, u1, u2, gid):
    """Run a 1vs1 sequential PvP battle.

    New flow (4 messages):
      1) Public @everyone announcement in `channel` (top-of-channel banner).
      2) Public spectator embed in `channel` — updates each round, NO buttons.
      3) Private thread under `channel` with both fighters added — holds the
         interactive UI (buttons). Only the two combatants can see this.
      4) Public final-result announcement in `channel` (with @everyone) once
         the duel concludes.
    """
    locale = get_locale(gid, u1.id) if gid else "vi"
    p1d = get_player(gid, u1.id)
    p2d = get_player(gid, u2.id)
    s1 = BattleSide(u1.display_name, p1d["tank"], p1d["dps"], player_max_hp(p1d), False, u1.id)
    s2 = BattleSide(u2.display_name, p2d["tank"], p2d["dps"], player_max_hp(p2d), False, u2.id)
    sides_by_id = {u1.id: s1, u2.id: s2}
    users_by_id = {u1.id: u1, u2.id: u2}

    # ---- 1) Public @everyone announcement
    try:
        ann = t(gid, u1.id, "pvp_announce", c_mention=u1.mention, t_mention=u2.mention)
        await channel.send(
            content=ann,
            allowed_mentions=discord.AllowedMentions(everyone=True, users=True),
        )
    except (discord.Forbidden, discord.HTTPException):
        pass

    # ---- 2) Public spectator embed (read-only, lives in main channel)
    # `spectator_narration` accumulates round-by-round commentary; outsiders
    # only need to read this single embed to follow the entire duel.
    spectator_narration: list[str] = []
    waiting_line = t(gid, u1.id, "pvp_spectator_waiting")
    spectator_msg = None
    try:
        spectator_msg = await channel.send(
            embed=_build_spectator_embed(s1, s2, 0, 10, waiting_line,
                                         spectator_narration, locale),
        )
    except (discord.Forbidden, discord.HTTPException):
        spectator_msg = None

    # ---- 3) Private thread with both fighters; interactive UI lives here
    interactive_msg = None
    thread = None
    try:
        thread_name = (f"⚔️ {u1.display_name} vs {u2.display_name}")[:100]
        thread = await channel.create_thread(
            name=thread_name,
            type=discord.ChannelType.private_thread,
            invitable=False,
            auto_archive_duration=60,
        )
        try:
            await thread.add_user(u1)
        except (discord.Forbidden, discord.HTTPException):
            pass
        try:
            await thread.add_user(u2)
        except (discord.Forbidden, discord.HTTPException):
            pass
        intro_line = t(gid, u1.id, "pvp_thread_intro",
                       c_mention=u1.mention, t_mention=u2.mention)
        interactive_msg = await thread.send(embed=knight_embed(intro_line))
    except (discord.Forbidden, discord.HTTPException, AttributeError):
        thread = None
        # Fallback: post the interactive message directly in the channel
        try:
            interactive_msg = await channel.send(
                content=f"{u1.mention} {u2.mention}",
                embed=knight_embed(t(gid, u1.id, "pvp_thread_intro",
                                     c_mention=u1.mention, t_mention=u2.mention)),
                allowed_mentions=discord.AllowedMentions(users=True),
            )
        except (discord.Forbidden, discord.HTTPException):
            interactive_msg = None

    # Acknowledge on the challenger's old ephemeral lobby panel
    if lobby_message is not None:
        if locale == "en":
            where = (f"private duel room <#{thread.id}>" if thread is not None
                     else f"<#{channel.id}>")
            notice = (
                f"⚔️ **The duel has begun!**\n\n"
                f"Head to {where} to play. Spectators can watch the live status in "
                f"<#{channel.id}>."
            )
        else:
            where = (f"phòng đấu riêng <#{thread.id}>" if thread is not None
                     else f"<#{channel.id}>")
            notice = (
                f"⚔️ **Trận đấu đã bắt đầu!**\n\n"
                f"Hãy vào {where} để thi đấu. Khán giả theo dõi trực tiếp tại "
                f"<#{channel.id}>."
            )
        await _safe_edit(lobby_message, embed=knight_embed(notice), view=None)

    # If we have nowhere to host the interactive UI, abort gracefully.
    if interactive_msg is None:
        return

    # Register this duel so /end_pvp can cancel it.
    cancel_event = asyncio.Event()
    registry_key = (gid, channel.id) if gid else None
    if registry_key is not None:
        _ACTIVE_PVP[registry_key] = {
            "cancel": cancel_event,
            "thread": thread,
            "u1": u1,
            "u2": u2,
            "view1_future": None,
            "view2_future": None,
        }

    await asyncio.sleep(2.0)

    MAX_TURNS = 10
    surrender_uid: int | None = None
    cancelled_by_admin = False
    persistent_log = ""

    for turn in range(1, MAX_TURNS + 1):
        if cancel_event.is_set():
            cancelled_by_admin = True
            break
        # Random first mover each round
        first = random.choice([u1, u2])
        second = u2 if first.id == u1.id else u1

        # ---- First chooser's turn
        first_header = (
            f"🎯 It is **{first.display_name}**'s turn — make your choice."
            if locale == "en"
            else f"🎯 Đến lượt **{first.display_name}** ra chiêu."
        )
        view1 = PvpTurnView(first.id, second.id, locale, gid)
        await _safe_edit(
            interactive_msg,
            embed=_build_pvp_embed(s1, s2, turn, MAX_TURNS, first_header, persistent_log, locale),
            view=view1,
        )
        spec_header = t(gid, u1.id, "pvp_spectator_round", turn=turn, max_turns=MAX_TURNS)
        await _safe_edit(
            spectator_msg,
            embed=_build_spectator_embed(s1, s2, turn, MAX_TURNS, spec_header,
                                         spectator_narration, locale),
        )
        if registry_key is not None:
            _ACTIVE_PVP[registry_key]["view1_future"] = view1.future
        await _wait_for_choice_or_cancel(view1.future, cancel_event, timeout=61)
        if registry_key is not None:
            _ACTIVE_PVP[registry_key]["view1_future"] = None
        if cancel_event.is_set():
            cancelled_by_admin = True
            break
        if view1.surrender_uid is not None:
            surrender_uid = view1.surrender_uid
            break
        c1 = view1.choice or "D"

        # ---- Second chooser's turn (first's pick is hidden)
        between_header = (
            f"✅ **{first.display_name}** has chosen.\n"
            f"🎯 Now **{second.display_name}**, make your choice."
            if locale == "en"
            else f"✅ **{first.display_name}** đã chọn chiêu thức.\n"
                 f"🎯 Đến lượt **{second.display_name}** chọn."
        )
        view2 = PvpTurnView(second.id, first.id, locale, gid)
        await _safe_edit(
            interactive_msg,
            embed=_build_pvp_embed(s1, s2, turn, MAX_TURNS, between_header, persistent_log, locale),
            view=view2,
        )
        if registry_key is not None:
            _ACTIVE_PVP[registry_key]["view2_future"] = view2.future
        await _wait_for_choice_or_cancel(view2.future, cancel_event, timeout=61)
        if registry_key is not None:
            _ACTIVE_PVP[registry_key]["view2_future"] = None
        if cancel_event.is_set():
            cancelled_by_admin = True
            break
        if view2.surrender_uid is not None:
            surrender_uid = view2.surrender_uid
            break
        c2 = view2.choice or "D"

        # ---- Resolve
        s_first = sides_by_id[first.id]
        s_second = sides_by_id[second.id]
        round_log = resolve_round(s_first, s_second, c1, c2, locale)
        c1_label = _choice_label(c1, locale)
        c2_label = _choice_label(c2, locale)
        if locale == "en":
            choices_line = (
                f"**{first.display_name}** chose {c1_label} — "
                f"**{second.display_name}** chose {c2_label}."
            )
            result_header = "⚔️ Round result:"
        else:
            choices_line = (
                f"**{first.display_name}** chọn {c1_label} — "
                f"**{second.display_name}** chọn {c2_label}."
            )
            result_header = "⚔️ Kết quả lượt đấu:"
        persistent_log = choices_line + "\n" + "\n".join(round_log)

        # Append this round's commentary to the running spectator narration.
        round_label = (f"__**Round {turn}**__" if locale == "en"
                       else f"__**Lượt {turn}**__")
        spectator_narration.append(f"{round_label}\n{persistent_log}")

        await _safe_edit(
            interactive_msg,
            embed=_build_pvp_embed(s1, s2, turn, MAX_TURNS, result_header, persistent_log, locale),
            view=None,
        )
        await _safe_edit(
            spectator_msg,
            embed=_build_spectator_embed(s1, s2, turn, MAX_TURNS, result_header,
                                         spectator_narration, locale),
        )

        if s1.hp <= 0 or s2.hp <= 0:
            break
        await asyncio.sleep(2.5)

    # ---- Resolve match outcome
    p1d = get_player(gid, u1.id)
    p2d = get_player(gid, u2.id)

    if cancelled_by_admin:
        if locale == "en":
            result = (
                "🛑 **Duel cancelled by an administrator.**\n\n"
                "The match has been called off — no winner is recorded and "
                "neither fighter's stats are affected."
            )
        else:
            result = (
                "🛑 **Trận đấu đã bị quản trị viên hủy bỏ.**\n\n"
                "Trận đấu kết thúc giữa chừng — không ghi nhận người thắng/thua "
                "và chỉ số của cả hai đấu sĩ không thay đổi."
            )
    elif surrender_uid is not None:
        loser_id = surrender_uid
        winner_id = u2.id if loser_id == u1.id else u1.id
        if locale == "en":
            result = (
                f"🏳️ **The duel has been halted.**\n\n"
                f"**{users_by_id[loser_id].display_name}** surrendered and is recorded as the loser.\n"
                f"🏆 **{users_by_id[winner_id].display_name}** wins by default."
            )
        else:
            result = (
                f"🏳️ **Trận đấu bị tạm ngừng.**\n\n"
                f"**{users_by_id[loser_id].display_name}** đã đầu hàng và mặc định bị tính thua.\n"
                f"🏆 **{users_by_id[winner_id].display_name}** thắng cuộc."
            )
        wd = p1d if winner_id == u1.id else p2d
        ld = p1d if loser_id == u1.id else p2d
        wd["pvp_wins"] = wd.get("pvp_wins", 0) + 1
        wd["pvp_streak"] = wd.get("pvp_streak", 0) + 1
        ld["pvp_streak"] = 0
    elif s1.hp <= 0 and s2.hp <= 0:
        result = ("💀 Both warriors have fallen — a true draw."
                  if locale == "en"
                  else "💀 Cả hai đều ngã xuống — hòa.")
        p1d["pvp_streak"] = 0
        p2d["pvp_streak"] = 0
    elif s1.hp <= 0:
        if locale == "en":
            result = f"🏆 **{s2.name}** is victorious! 💀 {s1.name} has been extinguished."
        else:
            result = f"🏆 **{s2.name}** chiến thắng! 💀 {s1.name} đã bị hạ gục."
        p2d["pvp_wins"] = p2d.get("pvp_wins", 0) + 1
        p2d["pvp_streak"] = p2d.get("pvp_streak", 0) + 1
        p1d["pvp_streak"] = 0
    elif s2.hp <= 0:
        if locale == "en":
            result = f"🏆 **{s1.name}** is victorious! 💀 {s2.name} has been extinguished."
        else:
            result = f"🏆 **{s1.name}** chiến thắng! 💀 {s2.name} đã bị hạ gục."
        p1d["pvp_wins"] = p1d.get("pvp_wins", 0) + 1
        p1d["pvp_streak"] = p1d.get("pvp_streak", 0) + 1
        p2d["pvp_streak"] = 0
    else:
        # Reached MAX_TURNS — compare HP
        if s1.hp == s2.hp:
            if locale == "en":
                result = (f"⚖️ After {MAX_TURNS} rounds, both warriors stand with equal life force "
                          f"({s1.hp} HP each) — a draw.")
            else:
                result = (f"⚖️ Sau {MAX_TURNS} lượt, cả hai đấu sĩ còn lại sinh lực ngang nhau "
                          f"({s1.hp} HP) — hòa.")
            p1d["pvp_streak"] = 0
            p2d["pvp_streak"] = 0
        elif s1.hp > s2.hp:
            if locale == "en":
                result = (f"🏆 After {MAX_TURNS} rounds, **{s1.name}** stands taller "
                          f"({s1.hp} HP vs {s2.hp} HP) — victory!")
            else:
                result = (f"🏆 Sau {MAX_TURNS} lượt, **{s1.name}** đứng vững hơn "
                          f"({s1.hp} HP vs {s2.hp} HP) — chiến thắng!")
            p1d["pvp_wins"] = p1d.get("pvp_wins", 0) + 1
            p1d["pvp_streak"] = p1d.get("pvp_streak", 0) + 1
            p2d["pvp_streak"] = 0
        else:
            if locale == "en":
                result = (f"🏆 After {MAX_TURNS} rounds, **{s2.name}** stands taller "
                          f"({s2.hp} HP vs {s1.hp} HP) — victory!")
            else:
                result = (f"🏆 Sau {MAX_TURNS} lượt, **{s2.name}** đứng vững hơn "
                          f"({s2.hp} HP vs {s1.hp} HP) — chiến thắng!")
            p2d["pvp_wins"] = p2d.get("pvp_wins", 0) + 1
            p2d["pvp_streak"] = p2d.get("pvp_streak", 0) + 1
            p1d["pvp_streak"] = 0

    if cancelled_by_admin:
        # No achievements / no persistence — preserve original state.
        pass
    else:
        new1 = unlock_achievements(p1d)
        new2 = unlock_achievements(p2d)
        persist()
        if new1:
            result += f"\n\n<@{u1.id}>" + announce_unlocks(new1, locale)
        if new2:
            result += f"\n\n<@{u2.id}>" + announce_unlocks(new2, locale)

    # Final round summary line for the spectator embed
    if cancelled_by_admin:
        if locale == "en":
            final_spec_header = "🛑 **Duel cancelled by an administrator.**"
        else:
            final_spec_header = "🛑 **Trận đấu đã bị quản trị viên hủy bỏ.**"
    elif locale == "en":
        final_spec_header = "🏁 **Match concluded** — see the final announcement below."
    else:
        final_spec_header = "🏁 **Trận đấu kết thúc** — xem thông báo kết quả phía dưới."
    await _safe_edit(
        spectator_msg,
        embed=_build_spectator_embed(s1, s2, MAX_TURNS, MAX_TURNS, final_spec_header,
                                     spectator_narration, locale),
    )

    # Wrap up the private interactive panel — drop the buttons, show result.
    await _safe_edit(
        interactive_msg,
        embed=knight_embed(result),
        view=PostBattleView(u1, gid, allowed_ids={u1.id, u2.id}, show_again=False),
    )

    # ---- 4) Public final announcement (separate @everyone message)
    try:
        if cancelled_by_admin:
            if locale == "en":
                final_ann = "🛑 **PvP duel cancelled by an administrator.**"
            else:
                final_ann = "🛑 **Trận đấu PvP đã bị quản trị viên hủy bỏ.**"
        else:
            final_ann = t(gid, u1.id, "pvp_final_announce",
                          c_mention=u1.mention, t_mention=u2.mention)
        await channel.send(
            content=final_ann,
            embed=knight_embed(result),
            allowed_mentions=discord.AllowedMentions(everyone=True, users=True),
        )
    except (discord.Forbidden, discord.HTTPException):
        pass

    # Apply post-duel cooldown — for the next 15s neither fighter may start
    # or accept a new PvP match (matches the thread-cleanup window).
    if gid is not None:
        _set_pvp_cooldown(gid, u1.id, PVP_COOLDOWN_SECS)
        _set_pvp_cooldown(gid, u2.id, PVP_COOLDOWN_SECS)

    # Delete the private duel room. Default grace period is 15 seconds so the
    # two fighters can review the final panel; if an admin cancelled the duel
    # we tear it down right away.
    if thread is not None:
        delay = 0 if cancelled_by_admin else PVP_COOLDOWN_SECS
        # Tell both fighters their private duel room is about to disappear.
        if not cancelled_by_admin and delay > 0:
            try:
                notice = (
                    f"{u1.mention} {u2.mention}\n"
                    + t(gid, u1.id, "pvp_thread_delete_notice", secs=delay)
                )
                await thread.send(
                    content=notice,
                    allowed_mentions=discord.AllowedMentions(users=[u1, u2]),
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
        try:
            await asyncio.sleep(delay)
        except Exception:
            pass
        try:
            await thread.delete()
        except (discord.Forbidden, discord.HTTPException, discord.NotFound):
            # Fall back to archive+lock if we lack Manage Threads permission.
            try:
                await thread.edit(archived=True, locked=True)
            except (discord.Forbidden, discord.HTTPException):
                pass

    # Unregister the duel so /end_pvp can't act on a stale entry.
    if registry_key is not None:
        _ACTIVE_PVP.pop(registry_key, None)
