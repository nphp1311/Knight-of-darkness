"""Combat: PvE (monsters) and PvP (player vs player)."""
import asyncio
import random
import discord

from .storage import get_player, persist, get_locale
from .core import (
    knight_embed, t, RANK_INFO, RANKS, Monster, monsters_by_level, can_fight_monster,
    attack_chance, block_chance, player_max_hp, heal_amount, damage_value,
    crit_check, miss_check, compute_rank, has_rank_role,
    go_lobby, exit_bot, announce_rank_up, maybe_grant_rank_role,
    unlock_achievements, announce_unlocks,
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
    filled = max(0, min(width, int(width * cur / mx)))
    return "█" * filled + "░" * (width - filled)


def attack_vs_defend(atk: BattleSide, defn: BattleSide, locale: str = "vi") -> list[str]:
    log = []
    block = block_chance(defn.tank, atk.dps)
    if miss_check():
        log.append(f"💀 🗡 {atk.name} {'missed!' if locale == 'en' else 'đánh trượt!'}")
        return log
    if random.random() < block:
        log.append(f"🌟 🛡 {defn.name} {'blocked the strike.' if locale == 'en' else 'chặn đứng đòn đánh.'}")
    else:
        dmg = damage_value(atk.dps)
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
                dmg = damage_value(atk.dps)
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
        ph = heal_amount(p)
        eh = heal_amount(e)
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
    return knight_embed(
        f"{turn_line}\n\n"
        f"**{p.name}**\n💊 `{hp_bar(p.hp, p.max_hp)}` {max(0, p.hp)}/{p.max_hp}\n\n"
        f"**{e.name}**\n💊 `{hp_bar(e.hp, e.max_hp)}` {max(0, e.hp)}/{e.max_hp}\n\n"
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

    await interaction.response.defer()
    msg = interaction.message

    log = []
    turn = 1
    fled = False
    while p_side.hp > 0 and e_side.hp > 0 and turn <= 30:
        view = PveActionView(user.id, locale, interaction.guild_id)
        await msg.edit(embed=battle_status_embed(p_side, e_side, log, turn, locale), view=view)
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
    def __init__(self, user, guild_id=None, allowed_ids: set[int] | None = None):
        super().__init__(timeout=300)
        self.user = user
        self.allowed_ids = allowed_ids if allowed_ids is not None else {user.id}
        gid = guild_id

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
    locale = get_locale(interaction.guild_id, challenger.id)
    if locale == "en":
        invite_text = (
            f"⚔️✉️⚔️ **Challenge Invitation**\n\n"
            f"{target.mention}, **{challenger.display_name}** challenges you to a 1v1 duel!\n"
            f"{target.display_name}, do you dare accept? _(60 seconds to respond)_"
        )
    else:
        invite_text = (
            f"⚔️✉️⚔️ **Thư mời thách đấu**\n\n"
            f"{target.mention}, **{challenger.display_name}** thách đấu ngươi 1v1!\n"
            f"{target.display_name}, ngươi có dám chấp nhận? _(60 giây để trả lời)_"
        )
    view = PvpInviteView(challenger, target, interaction.guild_id)
    await interaction.response.edit_message(embed=knight_embed(invite_text), view=view)
    msg = await interaction.original_response()
    view.bind_message(msg)


class PvpInviteView(discord.ui.View):
    def __init__(self, challenger, target, guild_id=None):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.target = target
        self.responded = False
        self.message: discord.Message | None = None
        gid = guild_id

        accept = discord.ui.Button(
            label=t(gid, target.id, "pvp_accept_btn"),
            style=discord.ButtonStyle.success,
        )
        async def accept_cb(interaction):
            self.responded = True
            await show_pvp_ready(interaction, self.challenger, self.target)
        accept.callback = accept_cb
        self.add_item(accept)

        decline = discord.ui.Button(
            label=t(gid, target.id, "pvp_decline_btn"),
            style=discord.ButtonStyle.danger,
        )
        async def decline_cb(interaction):
            self.responded = True
            locale = get_locale(interaction.guild_id, self.target.id)
            if locale == "en":
                msg = f"🌑 {self.target.display_name} has declined {self.challenger.display_name}'s challenge."
            else:
                msg = f"🌑 {self.target.display_name} đã từ chối thách đấu của {self.challenger.display_name}."
            await interaction.response.edit_message(embed=knight_embed(msg), view=None)
        decline.callback = decline_cb
        self.add_item(decline)

    def bind_message(self, message: discord.Message):
        self.message = message

    async def interaction_check(self, interaction):
        if interaction.user.id != self.target.id:
            msg = "Only the invited player may respond." if get_locale(interaction.guild_id, interaction.user.id) == "en" else "Chỉ người được mời mới có thể trả lời."
            await interaction.response.send_message(msg, ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.responded or not self.message:
            return
        # Use challenger's locale (we don't have an interaction here)
        from .storage import get_locale as _gl
        gid = self.message.guild.id if self.message.guild else None
        locale = _gl(gid, self.challenger.id) if gid else "vi"
        if locale == "en":
            msg = (
                f"⌛ **{self.target.display_name}** did not respond within 60 seconds. "
                f"The challenge from **{self.challenger.display_name}** has been cancelled."
            )
        else:
            msg = (
                f"⌛ **{self.target.display_name}** đã không trả lời trong 60 giây. "
                f"Lời thách đấu của **{self.challenger.display_name}** đã bị hủy."
            )
        try:
            await self.message.edit(embed=knight_embed(msg), view=None)
        except (discord.NotFound, discord.HTTPException):
            pass


class PvpReadyView(discord.ui.View):
    def __init__(self, challenger, target, guild_id=None):
        super().__init__(timeout=120)
        self.challenger = challenger
        self.target = target
        self.ready: set[int] = set()
        self.started = False
        gid = guild_id

        enter = discord.ui.Button(
            label=t(gid, challenger.id, "btn_enter_battle"),
            style=discord.ButtonStyle.danger, row=0,
        )
        enter.callback = self._enter_cb
        self.add_item(enter)

        withdraw = discord.ui.Button(
            label=t(gid, challenger.id, "pvp_withdraw_btn"),
            style=discord.ButtonStyle.secondary, row=0,
        )
        withdraw.callback = self._withdraw_cb
        self.add_item(withdraw)

    async def interaction_check(self, interaction):
        if interaction.user.id not in (self.challenger.id, self.target.id):
            locale = get_locale(interaction.guild_id, interaction.user.id)
            msg = "You are not one of the two combatants." if locale == "en" else "Ngươi không phải là một trong hai đấu sĩ."
            await interaction.response.send_message(msg, ephemeral=True)
            return False
        return True

    def _status_text(self, locale: str = "vi") -> str:
        c_mark = "✅" if self.challenger.id in self.ready else "⏳"
        t_mark = "✅" if self.target.id in self.ready else "⏳"
        if locale == "en":
            return (
                f"⚔️ **Both warriors face each other in the arena…**\n\n"
                f"{c_mark} **{self.challenger.display_name}**\n"
                f"{t_mark} **{self.target.display_name}**\n\n"
                f"_Both must press **💥 Enter Battle** for the deathmatch to begin._"
            )
        return (
            f"⚔️ **Cả hai đấu sĩ đã đối mặt nhau giữa đấu trường…**\n\n"
            f"{c_mark} **{self.challenger.display_name}**\n"
            f"{t_mark} **{self.target.display_name}**\n\n"
            f"_Cả hai phải bấm **💥 Vào trận** thì trận tử chiến mới bắt đầu._"
        )

    async def _enter_cb(self, interaction):
        locale = get_locale(interaction.guild_id, interaction.user.id)
        if interaction.user.id in self.ready:
            msg = "You are already ready — waiting for your opponent." if locale == "en" else "Ngươi đã sẵn sàng rồi — chờ đối thủ."
            await interaction.response.send_message(msg, ephemeral=True)
            return
        self.ready.add(interaction.user.id)

        if {self.challenger.id, self.target.id}.issubset(self.ready) and not self.started:
            self.started = True
            await interaction.response.defer()
            try:
                announce_text = (
                    f"@everyone ⚔️ **The arena trembles!** "
                    f"{self.challenger.mention} vs {self.target.mention} — witness the 1v1 deathmatch!"
                ) if locale == "en" else (
                    f"@everyone ⚔️ **Đấu trường rung chuyển!** "
                    f"{self.challenger.mention} vs {self.target.mention} — "
                    f"hãy tới chứng kiến trận tử chiến 1vs1!"
                )
                await interaction.channel.send(
                    content=announce_text,
                    allowed_mentions=discord.AllowedMentions(everyone=True, users=True),
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
            msg = interaction.message
            await run_pvp_battle(interaction, msg, self.challenger, self.target)
            self.stop()
        else:
            await interaction.response.edit_message(
                embed=knight_embed(self._status_text(locale)),
                view=self,
            )

    async def _withdraw_cb(self, interaction):
        locale = get_locale(interaction.guild_id, interaction.user.id)
        if locale == "en":
            msg = f"🌑 **{interaction.user.display_name}** has withdrawn from the arena. The deathmatch did not take place."
        else:
            msg = f"🌑 **{interaction.user.display_name}** đã rút lui khỏi đấu trường. Trận tử chiến không xảy ra."
        await interaction.response.edit_message(embed=knight_embed(msg), view=None)
        self.stop()


async def show_pvp_ready(interaction: discord.Interaction, challenger, target):
    view = PvpReadyView(challenger, target, interaction.guild_id)
    locale = get_locale(interaction.guild_id, challenger.id)
    await interaction.response.edit_message(
        embed=knight_embed(view._status_text(locale)),
        view=view,
    )


class PvpRoundView(discord.ui.View):
    def __init__(self, p1_id, p2_id, locale: str = "vi", guild_id=None):
        super().__init__(timeout=30)
        self.choices: dict[int, str] = {}
        self.p1_id = p1_id
        self.p2_id = p2_id
        self.locale = locale
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()

        atk = discord.ui.Button(
            label=t(guild_id, p1_id, "btn_attack"),
            style=discord.ButtonStyle.danger,
        )
        async def atk_cb(interaction):
            await self._record(interaction, "A")
        atk.callback = atk_cb
        self.add_item(atk)

        df = discord.ui.Button(
            label=t(guild_id, p1_id, "btn_defend"),
            style=discord.ButtonStyle.primary,
        )
        async def df_cb(interaction):
            await self._record(interaction, "D")
        df.callback = df_cb
        self.add_item(df)

    async def _record(self, interaction, c: str):
        if interaction.user.id not in (self.p1_id, self.p2_id):
            msg = "You are not participating in this battle." if self.locale == "en" else "Ngươi không tham chiến."
            await interaction.response.send_message(msg, ephemeral=True)
            return
        if interaction.user.id in self.choices:
            msg = "You have already made your choice." if self.locale == "en" else "Ngươi đã chọn rồi."
            await interaction.response.send_message(msg, ephemeral=True)
            return
        self.choices[interaction.user.id] = c
        # Confirm in the user's own locale (not just challenger's)
        user_locale = get_locale(interaction.guild_id, interaction.user.id)
        if c == "A":
            confirm = "Recorded: 🗡 Attack" if user_locale == "en" else "Đã ghi nhận: 🗡 Tấn công"
        else:
            confirm = "Recorded: 🛡 Defend" if user_locale == "en" else "Đã ghi nhận: 🛡 Phòng thủ"
        await interaction.response.send_message(confirm, ephemeral=True)
        if len(self.choices) == 2 and not self.future.done():
            self.future.set_result(True)
            self.stop()

    async def on_timeout(self):
        for uid in (self.p1_id, self.p2_id):
            self.choices.setdefault(uid, "D")
        if not self.future.done():
            self.future.set_result(True)


async def run_pvp_battle(interaction, msg, u1, u2):
    locale = get_locale(interaction.guild_id, u1.id)
    p1d = get_player(interaction.guild_id, u1.id)
    p2d = get_player(interaction.guild_id, u2.id)
    s1 = BattleSide(u1.display_name, p1d["tank"], p1d["dps"], player_max_hp(p1d), False, u1.id)
    s2 = BattleSide(u2.display_name, p2d["tank"], p2d["dps"], player_max_hp(p2d), False, u2.id)

    log = []
    turn = 1
    while s1.hp > 0 and s2.hp > 0 and turn <= 30:
        view = PvpRoundView(u1.id, u2.id, locale, interaction.guild_id)
        if locale == "en":
            round_header = (
                f"⚔️ **Round {turn}** — Both choose (30 seconds).\n\n"
                f"**{s1.name}** 💊 `{hp_bar(s1.hp, s1.max_hp)}` {max(0, s1.hp)}/{s1.max_hp}\n"
                f"**{s2.name}** 💊 `{hp_bar(s2.hp, s2.max_hp)}` {max(0, s2.hp)}/{s2.max_hp}"
            )
            last_label = "__**Last round:**__"
        else:
            round_header = (
                f"⚔️ **Lượt {turn}** — Cả hai hãy chọn (30 giây).\n\n"
                f"**{s1.name}** 💊 `{hp_bar(s1.hp, s1.max_hp)}` {max(0, s1.hp)}/{s1.max_hp}\n"
                f"**{s2.name}** 💊 `{hp_bar(s2.hp, s2.max_hp)}` {max(0, s2.hp)}/{s2.max_hp}"
            )
            last_label = "__**Lượt vừa rồi:**__"
        embed = knight_embed(
            round_header + ("\n\n" + last_label + "\n" + "\n".join(log) if log else "")
        )
        await msg.edit(embed=embed, view=view)
        try:
            await asyncio.wait_for(view.future, timeout=31)
        except asyncio.TimeoutError:
            pass
        c1 = view.choices.get(u1.id, "D")
        c2 = view.choices.get(u2.id, "D")
        decided = "⚔️ Both have made their decisions…" if locale == "en" else "⚔️ Cả hai đã ra quyết định…"
        log = [decided]
        log += resolve_round(s1, s2, c1, c2, locale)
        turn += 1

    if s1.hp <= 0 and s2.hp <= 0:
        result = "💀 Both warriors have fallen." if locale == "en" else "💀 Cả hai đều ngã xuống."
        p1d["pvp_streak"] = 0
        p2d["pvp_streak"] = 0
    elif s1.hp <= 0:
        if locale == "en":
            result = f"🏆 **{s2.name}** is victorious! 💀 {s1.name}, your life force… has been extinguished."
        else:
            result = f"🏆 **{s2.name}** chiến thắng! 💀 {s1.name}, sinh mệnh của ngươi… đã cạn."
        p2d["pvp_wins"] = p2d.get("pvp_wins", 0) + 1
        p2d["pvp_streak"] = p2d.get("pvp_streak", 0) + 1
        p1d["pvp_streak"] = 0
    elif s2.hp <= 0:
        if locale == "en":
            result = f"🏆 **{s1.name}** is victorious! 💀 {s2.name}, your life force… has been extinguished."
        else:
            result = f"🏆 **{s1.name}** chiến thắng! 💀 {s2.name}, sinh mệnh của ngươi… đã cạn."
        p1d["pvp_wins"] = p1d.get("pvp_wins", 0) + 1
        p1d["pvp_streak"] = p1d.get("pvp_streak", 0) + 1
        p2d["pvp_streak"] = 0
    else:
        result = "The battle ends in a stalemate." if locale == "en" else "Trận đấu kết thúc trong bế tắc."
        p1d["pvp_streak"] = 0
        p2d["pvp_streak"] = 0

    new1 = unlock_achievements(p1d)
    new2 = unlock_achievements(p2d)
    persist()
    if new1:
        result += f"\n\n<@{u1.id}>" + announce_unlocks(new1, locale)
    if new2:
        result += f"\n\n<@{u2.id}>" + announce_unlocks(new2, locale)

    await msg.edit(
        embed=knight_embed(result),
        view=PostBattleView(u1, interaction.guild_id, allowed_ids={u1.id, u2.id}),
    )
