"""Training mini-games: Tank, DPS, Potion."""
import asyncio
import random
import discord

from .storage import get_player, persist, get_locale
from .core import (
    knight_embed, t, go_lobby, exit_bot,
    apply_training_bonus, training_bonus_pct,
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


# ============== TRAIN MENU ==============
class TrainView(discord.ui.View):
    def __init__(self, user: discord.User, guild_id=None):
        super().__init__(timeout=300)
        self.user = user
        gid = guild_id

        tank_btn = discord.ui.Button(
            label=t(gid, user.id, "btn_train_tank"),
            style=discord.ButtonStyle.danger, row=0,
        )
        async def tank_cb(interaction):
            locale = get_locale(interaction.guild_id, self.user.id)
            if locale == "en":
                text = (
                    "🛡 Training begins. Your opponent: **☠️ Bone Duelist**. Prepare yourself!\n\n"
                    "Guide: Watch the **color of the incoming strike**. "
                    "Press the 🛡 button matching the color in the prompt to dodge.\n"
                    "One session lasts **5 rounds**, roughly **3 seconds** each."
                )
            else:
                text = (
                    "🛡 Bài luyện tập sắp đầu. Đối thủ của ngươi là **☠️ Đấu sĩ xương khô**. Hãy chuẩn bị sẵn sàng!\n\n"
                    "Hướng dẫn: Hãy chú ý **màu của chiêu thức** sắp được tung ra. "
                    "Bấm nút 🛡 trùng màu với màu trong lời thoại để né đòn.\n"
                    "Một lần luyện tập kéo dài **5 lượt**, mỗi lượt khoảng **3 giây**."
                )
            await interaction.response.edit_message(
                embed=knight_embed(text),
                view=TankReadyView(self.user, interaction.guild_id),
            )
        tank_btn.callback = tank_cb
        self.add_item(tank_btn)

        dps_btn = discord.ui.Button(
            label=t(gid, user.id, "btn_train_dps"),
            style=discord.ButtonStyle.primary, row=0,
        )
        async def dps_cb(interaction):
            locale = get_locale(interaction.guild_id, self.user.id)
            if locale == "en":
                text = (
                    "🗡 **🤺 The Dark Knight demonstrates the techniques himself. Pay close attention!**\n\n"
                    "🔥 Do not falter. One wrong beat… and you will die.\n\n"
                    "I will show you a sequence of 4 moves. You must press them **in exact order** within **10 seconds**.\n"
                    "One session lasts **5 rounds**."
                )
            else:
                text = (
                    "🗡 **🤺 Hiệp Sĩ Hắc Ám tự mình hướng dẫn chiêu thức cho ngươi. Hãy tập trung quan sát!**\n\n"
                    "🔥 Đừng dừng lại. Chỉ một nhịp sai… và ngươi sẽ mất mạng.\n\n"
                    "Ta sẽ ra một chuỗi 4 chiêu thức. Ngươi phải bấm **đúng thứ tự** trong **10 giây**.\n"
                    "Một lần luyện tập kéo dài **5 lượt**."
                )
            await interaction.response.edit_message(
                embed=knight_embed(text),
                view=DpsReadyView(self.user, interaction.guild_id),
            )
        dps_btn.callback = dps_cb
        self.add_item(dps_btn)

        potion_btn = discord.ui.Button(
            label=t(gid, user.id, "btn_train_potion"),
            style=discord.ButtonStyle.success, row=0,
        )
        async def potion_cb(interaction):
            locale = get_locale(interaction.guild_id, self.user.id)
            if locale == "en":
                text = (
                    "⚗️ 🤺 The phantom knight leads you into the **Alchemy Forge**:\n\n"
                    "You need exactly **three ingredients** to brew each batch of Potions. "
                    "**Each ingredient affects the success chance, "
                    "but the same ingredient may yield different quality each time — take note.**\n"
                    "The more Potions you carry, the higher your odds of survival on the battlefield.\n\n"
                    "**Choose your ingredients:**"
                )
            else:
                text = (
                    "⚗️ 🤺 Hiệp sĩ ma dẫn ngươi vào **Lò giả kim**:\n\n"
                    "Ngươi cần gom đúng **ba nguyên liệu** để pha chế mỗi mẻ Thần dược. "
                    "**Mỗi loại nguyên liệu sẽ ảnh hưởng đến xác suất thành công, "
                    "nhưng cùng một loại nguyên liệu cũng sẽ có chất lượng khác nhau – hãy lưu ý điều này.**\n"
                    "Kẻ nào sở hữu càng nhiều Thần dược, tỉ lệ sinh tồn của hắn trên chiến trường càng cao.\n\n"
                    "**Hãy chọn nguyên liệu:**"
                )
            await interaction.response.edit_message(
                embed=knight_embed(text),
                view=PotionView(self.user),
            )
        potion_btn.callback = potion_cb
        self.add_item(potion_btn)

        _add_lobby_exit(self, user, gid, row=1)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                t(interaction.guild_id, interaction.user.id, "msg_only_summoner"),
                ephemeral=True,
            )
            return False
        return True


# ============== TANK ==============
COLOR_RED = "🔴"
COLOR_GREEN = "🟢"
COLOR_BLUE = "🔵"
DIRECTIONS = {
    COLOR_RED:   ("btn_tank_left",  discord.ButtonStyle.danger),
    COLOR_GREEN: ("btn_tank_still", discord.ButtonStyle.success),
    COLOR_BLUE:  ("btn_tank_right", discord.ButtonStyle.primary),
}


class TankReadyView(discord.ui.View):
    def __init__(self, user, guild_id=None):
        super().__init__(timeout=120)
        self.user = user
        gid = guild_id

        ready = discord.ui.Button(
            label=t(gid, user.id, "tank_ready_btn"),
            style=discord.ButtonStyle.success, row=0,
        )
        async def go_cb(interaction):
            await interaction.response.defer()
            await run_tank_session(interaction, self.user)
        ready.callback = go_cb
        self.add_item(ready)

        _add_lobby_exit(self, user, gid, row=1)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


class TankRoundView(discord.ui.View):
    def __init__(self, user, hint_color, locale: str = "vi", guild_id=None):
        super().__init__(timeout=10)
        self.user = user
        self.hint_color = hint_color
        self.locale = locale
        self.choice = None
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()

        for color, (label_key, style) in DIRECTIONS.items():
            btn = discord.ui.Button(
                label=t(guild_id, user.id, label_key),
                style=style,
            )
            async def cb(interaction, c=color):
                if interaction.user.id != self.user.id:
                    await interaction.response.send_message(
                        t(interaction.guild_id, interaction.user.id, "msg_not_your_turn"),
                        ephemeral=True,
                    )
                    return
                self.choice = c
                await interaction.response.defer()
                if not self.future.done():
                    self.future.set_result(c)
                self.stop()
            btn.callback = cb
            self.add_item(btn)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    async def on_timeout(self):
        if not self.future.done():
            self.future.set_result(None)


async def run_tank_session(interaction, user):
    locale = get_locale(interaction.guild_id, user.id)
    successes = 0
    msg = None
    for turn in range(1, 6):
        hint_color = random.choice(list(DIRECTIONS.keys()))
        if locale == "en":
            text = (
                f"☠️ **Round {turn}/5** — The Bone Duelist is about to {hint_color} strike {hint_color} you. "
                f"Which way do you dodge?\n\nPress the matching color to evade."
            )
        else:
            text = (
                f"☠️ **Lượt {turn}/5** — Đấu sĩ xương khô sắp {hint_color} tấn công {hint_color} ngươi, "
                f"ngươi sẽ né phía nào?\n\nBấm nút trùng màu để né."
            )
        embed = knight_embed(text)
        view = TankRoundView(user, hint_color, locale, interaction.guild_id)
        if msg is None:
            await interaction.edit_original_response(embed=embed, view=view)
            msg = await interaction.original_response()
        else:
            await msg.edit(embed=embed, view=view)
        try:
            await asyncio.wait_for(view.future, timeout=4)
        except asyncio.TimeoutError:
            pass
        if view.choice == hint_color:
            successes += 1

    p = get_player(interaction.guild_id, user.id)
    if successes >= 4:
        base = 3 + (1 if successes == 5 else 0)
        gain = apply_training_bonus(base, p.get("rank", "I"))
        if locale == "en":
            msg_text = f"🌟 You dodged most strikes ({successes}/5). **+{gain} 🛡 Tank**"
        else:
            msg_text = f"🌟 Ngươi đã né hầu hết các đòn ({successes}/5). **+{gain} 🛡 Tank**"
    elif successes >= 2:
        gain = apply_training_bonus(2, p.get("rank", "I"))
        if locale == "en":
            msg_text = f"🛡 Decent, but you need more practice ({successes}/5). **+{gain} 🛡 Tank**"
        else:
            msg_text = f"🛡 Tạm được, vẫn cần rèn thêm ({successes}/5). **+{gain} 🛡 Tank**"
    else:
        gain = 0
        if locale == "en":
            msg_text = f"💀 You took too many hits ({successes}/5). **No points awarded.**"
        else:
            msg_text = f"💀 Ngươi đã trúng quá nhiều đòn ({successes}/5). **Không có điểm nào.**"
    p["tank"] += gain
    persist()
    bonus = training_bonus_pct(p.get("rank", "I"))
    if bonus > 0 and gain > 0:
        if locale == "en":
            msg_text += f"\n\n_(Rank **{p['rank']}** — training bonus applied: **+{bonus}%**.)_"
        else:
            msg_text += f"\n\n_(Hạng **{p['rank']}** — điểm thưởng luyện tập đã được nhân **+{bonus}%**.)_"
    title = "**🛡 Tank Training Result**" if locale == "en" else "**Kết quả luyện tập 🛡 Tank**"
    await msg.edit(
        embed=knight_embed(f"{title}\n\n{msg_text}"),
        view=AfterTrainView(user, interaction.guild_id),
    )


# ============== DPS ==============
DPS_EMOJIS = ["🗡", "⚔️", "💥", "🏹"]


class DpsReadyView(discord.ui.View):
    def __init__(self, user, guild_id=None):
        super().__init__(timeout=120)
        self.user = user
        gid = guild_id

        ready = discord.ui.Button(
            label=t(gid, user.id, "dps_ready_btn"),
            style=discord.ButtonStyle.success, row=0,
        )
        async def go_cb(interaction):
            await interaction.response.defer()
            await run_dps_session(interaction, self.user)
        ready.callback = go_cb
        self.add_item(ready)

        _add_lobby_exit(self, user, gid, row=1)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


class DpsRoundView(discord.ui.View):
    def __init__(self, user, sequence: list[str], locale: str = "vi"):
        super().__init__(timeout=10)
        self.user = user
        self.sequence = sequence
        self.locale = locale
        self.idx = 0
        self.failed = False
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()

        labels = list(sequence)
        random.shuffle(labels)
        for emoji_label in labels:
            btn = discord.ui.Button(label=emoji_label, style=discord.ButtonStyle.primary)
            async def cb(interaction, e=emoji_label):
                if interaction.user.id != self.user.id:
                    await interaction.response.send_message(
                        t(interaction.guild_id, interaction.user.id, "msg_not_your_turn"),
                        ephemeral=True,
                    )
                    return
                await interaction.response.defer()
                if self.future.done():
                    return
                expected = self.sequence[self.idx]
                if e != expected:
                    self.failed = True
                    if not self.future.done():
                        self.future.set_result(False)
                    self.stop()
                    return
                self.idx += 1
                if self.idx >= len(self.sequence):
                    if not self.future.done():
                        self.future.set_result(True)
                    self.stop()
            btn.callback = cb
            self.add_item(btn)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    async def on_timeout(self):
        if not self.future.done():
            self.future.set_result(False)


async def run_dps_session(interaction, user):
    locale = get_locale(interaction.guild_id, user.id)
    fails = 0
    msg = None
    for turn in range(1, 6):
        seq = random.sample(DPS_EMOJIS, 4)
        if locale == "en":
            text = (
                f"⚔️ **Round {turn}/5** — Press in exactly this order:\n\n"
                f"# {' → '.join(seq)}\n\nYou have 10 seconds."
            )
        else:
            text = (
                f"⚔️ **Lượt {turn}/5** — Hãy bấm theo đúng thứ tự sau đây:\n\n"
                f"# {' → '.join(seq)}\n\nNgươi có 10 giây."
            )
        view = DpsRoundView(user, seq, locale)
        if msg is None:
            await interaction.edit_original_response(embed=knight_embed(text), view=view)
            msg = await interaction.original_response()
        else:
            await msg.edit(embed=knight_embed(text), view=view)
        try:
            success = await asyncio.wait_for(view.future, timeout=11)
        except asyncio.TimeoutError:
            success = False
        if not success:
            fails += 1

    p = get_player(interaction.guild_id, user.id)
    if fails == 0:
        gain = apply_training_bonus(5, p.get("rank", "I"))
        text = f"🌟 🤺 {'Flawless technique.' if locale == 'en' else 'Chiêu thức hoàn mỹ.'}  **+{gain} 🗡 DPS**"
    elif fails <= 2:
        gain = apply_training_bonus(2, p.get("rank", "I"))
        text = f"🗡 {'Needs improvement, but acceptable.' if locale == 'en' else 'Cần cải thiện thêm, nhưng vẫn được.'}  **+{gain} 🗡 DPS**"
    else:
        gain = 0
        text = f"💀 {'Your technique crumbled. Defeated.' if locale == 'en' else 'Chiêu thức rối loạn. Ngươi đã thua.'}  **+0 🗡 DPS**"
    p["dps"] += gain
    persist()
    bonus = training_bonus_pct(p.get("rank", "I"))
    if bonus > 0 and gain > 0:
        if locale == "en":
            text += f"\n\n_(Rank **{p['rank']}** — training bonus applied: **+{bonus}%**.)_"
        else:
            text += f"\n\n_(Hạng **{p['rank']}** — điểm thưởng luyện tập đã được nhân **+{bonus}%**.)_"
    if locale == "en":
        title = f"**🗡 DPS Training Result** ({fails}/5 rounds failed)"
    else:
        title = f"**Kết quả luyện tập 🗡 DPS** (sai {fails}/5 lượt)"
    await msg.edit(
        embed=knight_embed(f"{title}\n\n{text}"),
        view=AfterTrainView(user, interaction.guild_id),
    )


# ============== POTION ==============
INGREDIENTS = [
    {"emoji": "🌿", "name": "Thảo dược",       "name_en": "Herb",           "lo": -10, "hi": 50},
    {"emoji": "🍄", "name": "Nấm",             "name_en": "Mushroom",       "lo": -30, "hi": 30},
    {"emoji": "💧", "name": "Nước tinh khiết", "name_en": "Pure Water",     "lo": -10, "hi": 20},
    {"emoji": "🔥", "name": "Tinh chất lửa",   "name_en": "Fire Essence",   "lo": -20, "hi": 50},
    {"emoji": "❄️", "name": "Hoa tuyết",       "name_en": "Snowblossom",    "lo": -10, "hi": 20},
]


def _ingredient_label(ing: dict, locale: str = "vi") -> str:
    name = ing["name_en"] if locale == "en" else ing["name"]
    return f"{ing['emoji']}{name} ({ing['lo']:+d}% ⇨ {ing['hi']:+d}%)"


class PotionView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user
        self.picked: list[dict] = []
        self._locale: str = "vi"
        self._guild_id = None
        self._build()

    def _build(self):
        self.clear_items()
        gid = self._guild_id
        for idx, ing in enumerate(INGREDIENTS):
            btn = discord.ui.Button(
                label=_ingredient_label(ing, self._locale),
                style=discord.ButtonStyle.secondary,
                row=0 if idx < 3 else 1,
            )
            async def cb(interaction, ing_=ing):
                if interaction.user.id != self.user.id:
                    return
                self._locale = get_locale(interaction.guild_id, self.user.id)
                self._guild_id = interaction.guild_id
                if len(self.picked) >= 3:
                    if self._locale == "en":
                        warn = (
                            "⚠️ **Warning:** You have already chosen **3 ingredients**. "
                            "A Potion batch only accepts exactly three — no more can be added. "
                            "Press **⚗️ Brew** or reset to start over."
                        )
                    else:
                        warn = (
                            "⚠️ **Cảnh báo:** Ngươi đã chọn đủ **3 nguyên liệu**. "
                            "Một mẻ Thần dược chỉ chấp nhận đúng ba nguyên liệu — không thể thêm nữa. "
                            "Hãy bấm **⚗️ Bào chế** hoặc làm lại từ đầu."
                        )
                    await interaction.response.send_message(warn, ephemeral=True)
                    return
                roll = random.choice([ing_["lo"], ing_["hi"]])
                self.picked.append({"name": ing_["name"], "name_en": ing_["name_en"], "emoji": ing_["emoji"], "value": roll})
                await self._refresh(interaction)
            btn.callback = cb
            self.add_item(btn)

        brew_label = "⚗️ Brew" if self._locale == "en" else "⚗️ Bào chế"
        brew = discord.ui.Button(
            label=brew_label,
            style=discord.ButtonStyle.success,
            row=2,
            disabled=len(self.picked) != 3,
        )
        async def brew_cb(interaction):
            if interaction.user.id != self.user.id:
                return
            self._locale = get_locale(interaction.guild_id, self.user.id)
            self._guild_id = interaction.guild_id
            await self._brew(interaction)
        brew.callback = brew_cb
        self.add_item(brew)

        reset_label = "↺ Reset" if self._locale == "en" else "↺ Làm lại"
        reset = discord.ui.Button(label=reset_label, style=discord.ButtonStyle.secondary, row=2)
        async def reset_cb(interaction):
            if interaction.user.id != self.user.id:
                return
            self._locale = get_locale(interaction.guild_id, self.user.id)
            self._guild_id = interaction.guild_id
            self.picked = []
            await self._refresh(interaction)
        reset.callback = reset_cb
        self.add_item(reset)

        lobby_label = t(gid, self.user.id, "btn_lobby")
        lobby = discord.ui.Button(label=lobby_label, style=discord.ButtonStyle.secondary, row=2)
        async def lobby_cb(interaction):
            await go_lobby(interaction, self.user)
        lobby.callback = lobby_cb
        self.add_item(lobby)

        exit_label = t(gid, self.user.id, "btn_exit")
        exitb = discord.ui.Button(label=exit_label, style=discord.ButtonStyle.danger, row=2)
        async def exit_cb(interaction):
            await exit_bot(interaction)
        exitb.callback = exit_cb
        self.add_item(exitb)

    def _picked_text(self):
        if not self.picked:
            return "(No ingredients selected yet)" if self._locale == "en" else "(Chưa chọn nguyên liệu nào)"
        lines = []
        for i, p in enumerate(self.picked):
            name = p.get("name_en", p["name"]) if self._locale == "en" else p["name"]
            lines.append(f"{i+1}. {p['emoji']} {name} → **{p['value']:+d}%**")
        return "\n".join(lines)

    async def _refresh(self, interaction):
        self._build()
        if self._locale == "en":
            note = (
                "**Each ingredient affects the success chance, "
                "but the same ingredient may yield different quality — take note.**"
            )
            selected_label = f"**Selected ({len(self.picked)}/3):**"
            title = "⚗️ **Alchemy Forge** — choose exactly **three ingredients** then press **Brew**."
        else:
            note = (
                "**Mỗi loại nguyên liệu sẽ ảnh hưởng đến xác suất thành công, "
                "nhưng cùng một loại nguyên liệu cũng sẽ có chất lượng khác nhau – hãy lưu ý điều này.**"
            )
            selected_label = f"**Đã chọn ({len(self.picked)}/3):**"
            title = "⚗️ **Lò giả kim** — chọn đúng **ba nguyên liệu** rồi bấm **Bào chế**."
        embed = knight_embed(
            f"{title}\n\n{note}\n\n{selected_label}\n{self._picked_text()}"
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def _brew(self, interaction):
        total = sum(p["value"] for p in self.picked)
        p = get_player(interaction.guild_id, self.user.id)
        rank = p.get("rank", "I")
        if total < 20:
            text = (
                f"💔 {'Total score:' if self._locale == 'en' else 'Tổng điểm:'} **{total}** — "
                + ("The brew yielded nothing." if self._locale == "en" else "Ngươi không chế được lọ thần dược nào.")
            )
            gain = 0
        elif total < 50:
            gain = apply_training_bonus(2, rank)
            text = (
                f"⚗️⚗️ {'Total score:' if self._locale == 'en' else 'Tổng điểm:'} **{total}** — "
                + (f"You brewed **2 potions**. **+{gain} 💊 Health**" if self._locale == "en"
                   else f"Ngươi chế được **2 lọ thần dược**. **+{gain} 💊 Health**")
            )
        elif total < 90:
            gain = apply_training_bonus(3, rank)
            text = (
                f"⚗️⚗️⚗️ {'Total score:' if self._locale == 'en' else 'Tổng điểm:'} **{total}** — "
                + (f"You brewed **3 potions**. **+{gain} 💊 Health**" if self._locale == "en"
                   else f"Ngươi chế được **3 lọ thần dược**. **+{gain} 💊 Health**")
            )
        else:
            gain = apply_training_bonus(5, rank)
            text = (
                f"⚗️⚗️⚗️⚗️⚗️ {'Total score:' if self._locale == 'en' else 'Tổng điểm:'} **{total}** — "
                + (f"You brewed **5 potions**! **+{gain} 💊 Health**" if self._locale == "en"
                   else f"Ngươi chế được **5 lọ thần dược**! **+{gain} 💊 Health**")
            )
        p["health"] += gain
        persist()
        bonus = training_bonus_pct(rank)
        if bonus > 0 and gain > 0:
            if self._locale == "en":
                text += f"\n\n_(Rank **{rank}** — training bonus applied: **+{bonus}%**.)_"
            else:
                text += f"\n\n_(Hạng **{rank}** — điểm thưởng luyện tập đã được nhân **+{bonus}%**.)_"
        title = "**Potion Brewing Result**" if self._locale == "en" else "**Kết quả pha chế thần dược**"
        await interaction.response.edit_message(
            embed=knight_embed(f"{title}\n\n{text}"),
            view=AfterTrainView(self.user, interaction.guild_id),
        )


# ============== AFTER TRAIN ==============
class AfterTrainView(discord.ui.View):
    def __init__(self, user, guild_id=None):
        super().__init__(timeout=300)
        self.user = user
        gid = guild_id

        again = discord.ui.Button(
            label=t(gid, user.id, "btn_train_again"),
            style=discord.ButtonStyle.primary, row=0,
        )
        async def again_cb(interaction):
            await interaction.response.edit_message(
                embed=knight_embed(t(interaction.guild_id, self.user.id, "msg_choose_train")),
                view=TrainView(self.user, interaction.guild_id),
            )
        again.callback = again_cb
        self.add_item(again)

        _add_lobby_exit(self, user, gid, row=0)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id
