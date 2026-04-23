"""Combat: PvE (monsters) and PvP (player vs player)."""
import asyncio
import random
import discord

from .storage import get_player, persist
from .core import (
    knight_embed, t, RANK_INFO, RANKS, Monster, monsters_by_level, can_fight_monster,
    attack_chance, block_chance, player_max_hp, heal_amount, damage_value,
    crit_check, miss_check, compute_rank, has_rank_role,
    go_lobby, exit_bot, announce_rank_up, maybe_grant_rank_role,
    unlock_achievements, announce_unlocks,
)


# ============== CHALLENGE MENU ==============
class ChallengeMenuView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="⚔️ Thách đấu người chơi", style=discord.ButtonStyle.primary, row=0)
    async def pvp(self, interaction, button):
        await interaction.response.send_modal(PvpInviteModal(self.user))

    @discord.ui.button(label="🐉 Thách đấu quái vật", style=discord.ButtonStyle.danger, row=0)
    async def pve(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed(t(interaction.guild_id, self.user.id, "pve_pick_level")),
            view=PveLevelView(self.user),
        )

    @discord.ui.button(label="🗿 Quay lại sảnh chờ", style=discord.ButtonStyle.secondary, row=1)
    async def lobby(self, interaction, button):
        await go_lobby(interaction, self.user)

    @discord.ui.button(label="🚪 Thoát", style=discord.ButtonStyle.danger, row=1)
    async def exit(self, interaction, button):
        await exit_bot(interaction)


# ============== PvE LEVEL SELECT ==============
LEVEL_LABELS = {
    1: "🪨 Cấp I — Khởi đầu",
    2: "🌲 Cấp II — Thích nghi",
    3: "🔥 Cấp III — Nguy hiểm",
    4: "🌑 Cấp IV — Ác mộng",
    5: "👑 Cấp V — Endgame",
}


class PveLevelView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user
        for lv in [1, 2, 3, 4, 5]:
            btn = discord.ui.Button(label=LEVEL_LABELS[lv], style=discord.ButtonStyle.secondary, row=(lv - 1) // 3)

            async def cb(interaction, lv_=lv):
                if interaction.user.id != self.user.id:
                    return
                await self._show_monsters(interaction, lv_)

            btn.callback = cb
            self.add_item(btn)

        lobby = discord.ui.Button(label="🗿 Quay lại sảnh chờ", style=discord.ButtonStyle.secondary, row=2)
        async def lobby_cb(interaction):
            await go_lobby(interaction, self.user)
        lobby.callback = lobby_cb
        self.add_item(lobby)

        exitb = discord.ui.Button(label="🚪 Thoát", style=discord.ButtonStyle.danger, row=2)
        async def exit_cb(interaction):
            await exit_bot(interaction)
        exitb.callback = exit_cb
        self.add_item(exitb)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    async def _show_monsters(self, interaction, level: int):
        p = get_player(interaction.guild_id, self.user.id)
        # Member chưa đạt cấp tương ứng (chưa có role) thì không thể thách đấu vượt cấp với quái.
        rank_lv = RANKS.index(p["rank"]) + 1
        # Ngoại lệ: rank IV (4) được phép thách boss cấp V — bài thi cuối.
        allow_boss_challenge = (rank_lv == 4 and level == 5)
        if level > rank_lv and not allow_boss_challenge:
            await interaction.response.edit_message(
                embed=knight_embed(t(interaction.guild_id, self.user.id, "no_overrun",
                                     rank=RANK_INFO[p['rank']]['name'])),
                view=ChallengeMenuView(self.user),
            )
            return
        # Ngoài ra, để mở khoá đấu cấp = rank, cũng yêu cầu user đã thực sự nhận được role hạng (nếu admin có thiết lập).
        member = interaction.guild.get_member(self.user.id) if interaction.guild else None
        if level == rank_lv and rank_lv > 1:
            from .storage import get_guild
            g = get_guild(interaction.guild_id)
            role_id = g["config"]["rank_roles"].get(p["rank"])
            if role_id and not has_rank_role(member, interaction.guild_id, p["rank"]):
                await interaction.response.edit_message(
                    embed=knight_embed(t(interaction.guild_id, self.user.id, "no_overrun",
                                         rank=RANK_INFO[p['rank']]['name'])),
                    view=ChallengeMenuView(self.user),
                )
                return
        monsters = monsters_by_level(level)
        embed = knight_embed(f"**{LEVEL_LABELS[level]}** — Hãy chọn đối thủ:")
        await interaction.response.edit_message(embed=embed, view=PveMonsterView(self.user, monsters))


class PveMonsterView(discord.ui.View):
    def __init__(self, user, monsters):
        super().__init__(timeout=300)
        self.user = user
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

        back = discord.ui.Button(label="◀ Quay lại", style=discord.ButtonStyle.secondary, row=4)
        async def back_cb(interaction):
            await interaction.response.edit_message(
                embed=knight_embed(t(interaction.guild_id, self.user.id, "pve_pick_level")),
                view=PveLevelView(self.user),
            )
        back.callback = back_cb
        self.add_item(back)

        exitb = discord.ui.Button(label="🚪 Thoát", style=discord.ButtonStyle.danger, row=4)
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
    def __init__(self, user_id):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.choice: str | None = None
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user_id

    async def _set(self, interaction, c):
        self.choice = c
        await interaction.response.defer()
        if not self.future.done():
            self.future.set_result(c)
        self.stop()

    @discord.ui.button(label="🗡 Tấn công", style=discord.ButtonStyle.danger)
    async def atk(self, interaction, button):
        await self._set(interaction, "A")

    @discord.ui.button(label="🛡 Phòng thủ", style=discord.ButtonStyle.primary)
    async def df(self, interaction, button):
        await self._set(interaction, "D")

    @discord.ui.button(label="🚪 Bỏ trận", style=discord.ButtonStyle.secondary)
    async def flee(self, interaction, button):
        await self._set(interaction, "F")

    async def on_timeout(self):
        if not self.future.done():
            self.future.set_result("D")


def hp_bar(cur, mx, width=12):
    filled = max(0, min(width, int(width * cur / mx)))
    return "█" * filled + "░" * (width - filled)


def attack_vs_defend(atk: BattleSide, defn: BattleSide) -> list[str]:
    log = []
    block = block_chance(defn.tank, atk.dps)
    if miss_check():
        log.append(f"💀 🗡 {atk.name} đánh trượt!")
        return log
    if random.random() < block:
        log.append(f"🌟 🛡 {defn.name} chặn đứng đòn đánh.")
    else:
        dmg = damage_value(atk.dps)
        log.append(f"💀 🛡 Phòng thủ của {defn.name} sụp đổ! 🗡 {atk.name} gây **-{dmg} HP**.")
        defn.hp -= dmg
    return log


def resolve_round(p: BattleSide, e: BattleSide, p_choice: str, e_choice: str) -> list[str]:
    log = []
    if p_choice == "A" and e_choice == "A":
        for atk, defn, atk_label in (
            (p, e, f"🗡 {p.name}"),
            (e, p, f"🗡 {e.name}"),
        ):
            if miss_check():
                log.append(f"💀 {atk_label} đánh trượt!")
                continue
            if random.random() < attack_chance(atk.dps, defn.dps):
                dmg = damage_value(atk.dps)
                if crit_check():
                    dmg = int(dmg * 1.5)
                    log.append(f"🌟 {atk_label} **CRIT** lên {defn.name}! **-{dmg} HP**")
                else:
                    log.append(f"🗡 {atk_label} áp đảo {defn.name}. **-{dmg} HP**")
                defn.hp -= dmg
            else:
                log.append(f"💀 Đòn của {atk_label} bị {defn.name} vượt qua.")
    elif p_choice == "A" and e_choice == "D":
        log += attack_vs_defend(p, e)
    elif p_choice == "D" and e_choice == "A":
        log += attack_vs_defend(e, p)
    else:
        ph = heal_amount(p)
        eh = heal_amount(e)
        p.hp = min(p.max_hp, p.hp + ph)
        e.hp = min(e.max_hp, e.hp + eh)
        log.append(f"💊 Cả hai lùi lại… củng cố sinh lực. {p.name} **+{ph} HP**, {e.name} **+{eh} HP**.")
    return log


def battle_status_embed(p: BattleSide, e: BattleSide, log_lines, turn) -> discord.Embed:
    return knight_embed(
        f"⚔️ **Lượt {turn}** — Hãy ra quyết định.\n\n"
        f"**{p.name}**\n💊 `{hp_bar(p.hp, p.max_hp)}` {max(0, p.hp)}/{p.max_hp}\n\n"
        f"**{e.name}**\n💊 `{hp_bar(e.hp, e.max_hp)}` {max(0, e.hp)}/{e.max_hp}\n\n"
        + (("__**Lượt vừa rồi:**__\n" + "\n".join(log_lines)) if log_lines else "")
    )


class PveReadyView(discord.ui.View):
    """Màn hình chuẩn bị trước khi vào trận PvE — buộc user xác nhận bằng nút 💥 Vào trận."""
    def __init__(self, user, monster: Monster):
        super().__init__(timeout=120)
        self.user = user
        self.monster = monster

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="💥 Vào trận", style=discord.ButtonStyle.danger, row=0)
    async def enter(self, interaction, button):
        await start_pve_battle(interaction, self.user, self.monster)

    @discord.ui.button(label="◀ Quay lại", style=discord.ButtonStyle.secondary, row=0)
    async def back(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed(t(interaction.guild_id, self.user.id, "pve_pick_level")),
            view=PveLevelView(self.user),
        )


async def show_pve_ready(interaction: discord.Interaction, user: discord.User, monster: Monster):
    """Hiển thị màn hình chuẩn bị trước khi đánh quái. Người chơi phải bấm 💥 Vào trận để bắt đầu."""
    p_data = get_player(interaction.guild_id, user.id)
    p_hp = player_max_hp(p_data)
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
        view=PveReadyView(user, monster),
    )


async def start_pve_battle(interaction: discord.Interaction, user: discord.User, monster: Monster):
    p_data = get_player(interaction.guild_id, user.id)
    p_side = BattleSide(user.display_name, p_data["tank"], p_data["dps"], player_max_hp(p_data), False, user.id)
    e_side = BattleSide(monster.display, monster.tank, monster.dps, monster.hp, True)

    await interaction.response.defer()
    msg = interaction.message

    log = []
    turn = 1
    fled = False
    while p_side.hp > 0 and e_side.hp > 0 and turn <= 30:
        view = PveActionView(user.id)
        await msg.edit(embed=battle_status_embed(p_side, e_side, log, turn), view=view)
        try:
            p_choice = await asyncio.wait_for(view.future, timeout=31)
        except asyncio.TimeoutError:
            p_choice = "D"
        if p_choice == "F":
            fled = True
            break
        e_choice = "A" if random.random() < 0.7 else "D"
        log = resolve_round(p_side, e_side, p_choice, e_choice)
        turn += 1

    if fled:
        await msg.edit(
            embed=knight_embed(
                f"🏃 Ngươi đã bỏ chạy khỏi trận đấu với **{monster.display}**. "
                f"Một hiệp sĩ thực sự không bao giờ quay lưng…"
            ),
            view=PostBattleView(user),
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
        text = (
            f"🌟 Ngươi là kẻ sống sót cuối cùng.\n\n"
            f"⚔️ Hạ gục **{monster.display}** (Cấp {monster.level}) — **+{bonus} điểm chiến công**\n"
            f"💊 Máu còn lại: {p_side.hp}/{p_side.max_hp}"
        )
        if rank_up:
            text += f"\n\n🏆 **THĂNG HẠNG!** Giờ đây ngươi là **{RANK_INFO[new_rank]['name']}**\n{RANK_INFO[new_rank]['speech']}"
            await maybe_grant_rank_role(interaction, user, new_rank)
        text += announce_unlocks(new_ach)
        await msg.edit(embed=knight_embed(text), view=PostBattleView(user))
        if rank_up and interaction.channel:
            await announce_rank_up(interaction.channel, interaction.user, new_rank, interaction.guild_id)
    else:
        await msg.edit(
            embed=knight_embed(
                f"💀 💊 Sinh mệnh của ngươi… đã cạn.\n\n"
                f"Ngươi đã ngã xuống dưới tay **{monster.display}**."
            ),
            view=PostBattleView(user),
        )


class PostBattleView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="⚔️ Đấu tiếp", style=discord.ButtonStyle.danger, row=0)
    async def again(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed("Hãy chọn đối thủ tiếp theo của ngươi:"),
            view=ChallengeMenuView(self.user),
        )

    @discord.ui.button(label="🗿 Quay lại sảnh chờ", style=discord.ButtonStyle.secondary, row=0)
    async def lobby(self, interaction, button):
        await go_lobby(interaction, self.user)

    @discord.ui.button(label="🚪 Thoát", style=discord.ButtonStyle.danger, row=0)
    async def exit(self, interaction, button):
        await exit_bot(interaction)


# ============== PvP ==============
class PvpInviteModal(discord.ui.Modal, title="⚔️ Thư mời thách đấu"):
    def __init__(self, challenger: discord.User):
        super().__init__()
        self.challenger = challenger
        self.target_input = discord.ui.TextInput(
            label="ID hoặc @mention của đối thủ",
            placeholder="Nhập user ID hoặc dán mention <@123...>",
            required=True,
        )
        self.add_item(self.target_input)

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.target_input.value.strip()
        target_id = None
        if raw.startswith("<@") and raw.endswith(">"):
            inner = raw[2:-1].lstrip("!&")
            try:
                target_id = int(inner)
            except ValueError:
                pass
        else:
            try:
                target_id = int(raw)
            except ValueError:
                pass

        if not target_id:
            await interaction.response.send_message(
                embed=knight_embed("💀 Không tìm được đối thủ. Hãy thử lại với @mention hoặc ID."),
                ephemeral=True,
            )
            return

        if target_id == self.challenger.id:
            await interaction.response.send_message(
                embed=knight_embed("💀 Ngươi không thể thách đấu chính mình."), ephemeral=True,
            )
            return

        target = interaction.guild.get_member(target_id)
        if not target:
            try:
                target = await interaction.guild.fetch_member(target_id)
            except (discord.NotFound, discord.HTTPException):
                target = None
        if not target:
            await interaction.response.send_message(
                embed=knight_embed("💀 Kẻ đó không có mặt trong vương quốc này."), ephemeral=True,
            )
            return

        if target.bot:
            await interaction.response.send_message(
                embed=knight_embed("💀 Ngươi không thể thách đấu một bot."), ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=knight_embed(
                f"⚔️✉️⚔️ **Thư mời thách đấu**\n\n"
                f"{target.mention}, **{self.challenger.display_name}** thách đấu ngươi 1v1!\n"
                f"{target.display_name}, ngươi có dám chấp nhận?"
            ),
            view=PvpInviteView(self.challenger, target),
        )


class PvpInviteView(discord.ui.View):
    def __init__(self, challenger, target):
        super().__init__(timeout=120)
        self.challenger = challenger
        self.target = target

    async def interaction_check(self, interaction):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("Chỉ người được mời mới có thể trả lời.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Đồng ý", style=discord.ButtonStyle.success)
    async def accept(self, interaction, button):
        await show_pvp_ready(interaction, self.challenger, self.target)

    @discord.ui.button(label="🚪 Từ chối", style=discord.ButtonStyle.danger)
    async def decline(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed(
                f"🌑 {self.target.display_name} đã từ chối thách đấu của {self.challenger.display_name}."
            ),
            view=None,
        )


class PvpReadyView(discord.ui.View):
    """Cả hai người chơi phải bấm 💥 Vào trận trước khi đấu trường thực sự rung chuyển."""
    def __init__(self, challenger, target):
        super().__init__(timeout=120)
        self.challenger = challenger
        self.target = target
        self.ready: set[int] = set()
        self.started = False

    async def interaction_check(self, interaction):
        if interaction.user.id not in (self.challenger.id, self.target.id):
            await interaction.response.send_message("Ngươi không phải là một trong hai đấu sĩ.", ephemeral=True)
            return False
        return True

    def _status_text(self) -> str:
        c_mark = "✅" if self.challenger.id in self.ready else "⏳"
        t_mark = "✅" if self.target.id in self.ready else "⏳"
        return (
            f"⚔️ **Cả hai đấu sĩ đã đối mặt nhau giữa đấu trường…**\n\n"
            f"{c_mark} **{self.challenger.display_name}**\n"
            f"{t_mark} **{self.target.display_name}**\n\n"
            f"_Cả hai phải bấm **💥 Vào trận** thì trận tử chiến mới bắt đầu._"
        )

    @discord.ui.button(label="💥 Vào trận", style=discord.ButtonStyle.danger, row=0)
    async def enter(self, interaction, button):
        if interaction.user.id in self.ready:
            await interaction.response.send_message("Ngươi đã sẵn sàng rồi — chờ đối thủ.", ephemeral=True)
            return
        self.ready.add(interaction.user.id)

        if {self.challenger.id, self.target.id}.issubset(self.ready) and not self.started:
            self.started = True
            await interaction.response.defer()
            try:
                await interaction.channel.send(
                    content=(
                        f"@everyone ⚔️ **Đấu trường rung chuyển!** "
                        f"{self.challenger.mention} vs {self.target.mention} — "
                        f"hãy tới chứng kiến trận tử chiến 1vs1!"
                    ),
                    allowed_mentions=discord.AllowedMentions(everyone=True, users=True),
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
            msg = interaction.message
            await run_pvp_battle(interaction, msg, self.challenger, self.target)
            self.stop()
        else:
            await interaction.response.edit_message(
                embed=knight_embed(self._status_text()),
                view=self,
            )

    @discord.ui.button(label="🚪 Rút lui", style=discord.ButtonStyle.secondary, row=0)
    async def withdraw(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed(
                f"🌑 **{interaction.user.display_name}** đã rút lui khỏi đấu trường. "
                f"Trận tử chiến không xảy ra."
            ),
            view=None,
        )
        self.stop()


async def show_pvp_ready(interaction: discord.Interaction, challenger, target):
    view = PvpReadyView(challenger, target)
    await interaction.response.edit_message(
        embed=knight_embed(view._status_text()),
        view=view,
    )


class PvpRoundView(discord.ui.View):
    def __init__(self, p1_id, p2_id):
        super().__init__(timeout=30)
        self.choices: dict[int, str] = {}
        self.p1_id = p1_id
        self.p2_id = p2_id
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()

    async def _record(self, interaction, c: str):
        if interaction.user.id not in (self.p1_id, self.p2_id):
            await interaction.response.send_message("Ngươi không tham chiến.", ephemeral=True)
            return
        if interaction.user.id in self.choices:
            await interaction.response.send_message("Ngươi đã chọn rồi.", ephemeral=True)
            return
        self.choices[interaction.user.id] = c
        await interaction.response.send_message(
            f"Đã ghi nhận: {('🗡 Tấn công' if c=='A' else '🛡 Phòng thủ')}", ephemeral=True,
        )
        if len(self.choices) == 2 and not self.future.done():
            self.future.set_result(True)
            self.stop()

    @discord.ui.button(label="🗡 Tấn công", style=discord.ButtonStyle.danger)
    async def atk(self, interaction, button):
        await self._record(interaction, "A")

    @discord.ui.button(label="🛡 Phòng thủ", style=discord.ButtonStyle.primary)
    async def df(self, interaction, button):
        await self._record(interaction, "D")

    async def on_timeout(self):
        for uid in (self.p1_id, self.p2_id):
            self.choices.setdefault(uid, "D")
        if not self.future.done():
            self.future.set_result(True)


async def run_pvp_battle(interaction, msg, u1, u2):
    p1d = get_player(interaction.guild_id, u1.id)
    p2d = get_player(interaction.guild_id, u2.id)
    s1 = BattleSide(u1.display_name, p1d["tank"], p1d["dps"], player_max_hp(p1d), False, u1.id)
    s2 = BattleSide(u2.display_name, p2d["tank"], p2d["dps"], player_max_hp(p2d), False, u2.id)

    log = []
    turn = 1
    while s1.hp > 0 and s2.hp > 0 and turn <= 30:
        view = PvpRoundView(u1.id, u2.id)
        embed = knight_embed(
            f"⚔️ **Lượt {turn}** — Cả hai hãy chọn (30 giây).\n\n"
            f"**{s1.name}** 💊 `{hp_bar(s1.hp, s1.max_hp)}` {max(0, s1.hp)}/{s1.max_hp}\n"
            f"**{s2.name}** 💊 `{hp_bar(s2.hp, s2.max_hp)}` {max(0, s2.hp)}/{s2.max_hp}\n\n"
            + (("__**Lượt vừa rồi:**__\n" + "\n".join(log)) if log else "")
        )
        await msg.edit(embed=embed, view=view)
        try:
            await asyncio.wait_for(view.future, timeout=31)
        except asyncio.TimeoutError:
            pass
        c1 = view.choices.get(u1.id, "D")
        c2 = view.choices.get(u2.id, "D")
        log = ["⚔️ Cả hai đã ra quyết định…"]
        log += resolve_round(s1, s2, c1, c2)
        turn += 1

    if s1.hp <= 0 and s2.hp <= 0:
        result = "💀 Cả hai đều ngã xuống."
        p1d["pvp_streak"] = 0
        p2d["pvp_streak"] = 0
    elif s1.hp <= 0:
        result = f"🏆 **{s2.name}** chiến thắng! 💀 {s1.name}, sinh mệnh của ngươi… đã cạn."
        p2d["pvp_wins"] = p2d.get("pvp_wins", 0) + 1
        p2d["pvp_streak"] = p2d.get("pvp_streak", 0) + 1
        p1d["pvp_streak"] = 0
    elif s2.hp <= 0:
        result = f"🏆 **{s1.name}** chiến thắng! 💀 {s2.name}, sinh mệnh của ngươi… đã cạn."
        p1d["pvp_wins"] = p1d.get("pvp_wins", 0) + 1
        p1d["pvp_streak"] = p1d.get("pvp_streak", 0) + 1
        p2d["pvp_streak"] = 0
    else:
        result = "Trận đấu kết thúc trong bế tắc."
        p1d["pvp_streak"] = 0
        p2d["pvp_streak"] = 0

    new1 = unlock_achievements(p1d)
    new2 = unlock_achievements(p2d)
    persist()
    if new1:
        result += f"\n\n<@{u1.id}>" + announce_unlocks(new1)
    if new2:
        result += f"\n\n<@{u2.id}>" + announce_unlocks(new2)

    await msg.edit(embed=knight_embed(result), view=None)
