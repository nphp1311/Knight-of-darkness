"""Training mini-games: Tank, DPS, Potion."""
import asyncio
import random
import discord

from .storage import get_player, persist
from .core import knight_embed, go_lobby, exit_bot, apply_training_bonus, training_bonus_pct


# ============== TRAIN MENU ==============
class TrainView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=300)
        self.user = user

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Chỉ người triệu hồi ta mới có thể chọn.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Nâng chỉ số 🛡 Tank", style=discord.ButtonStyle.danger, row=0)
    async def tank(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed(
                "🛡 Bài luyện tập sắp đầu. Đối thủ của ngươi là **☠️ Đấu sĩ xương khô**. Hãy chuẩn bị sẵn sàng!\n\n"
                "Hướng dẫn: Hãy chú ý **màu của chiêu thức** sắp được tung ra. "
                "Bấm nút 🛡 trùng màu với màu trong lời thoại để né đòn.\n"
                "Một lần luyện tập kéo dài **5 lượt**, mỗi lượt khoảng **3 giây**."
            ),
            view=TankReadyView(self.user),
        )

    @discord.ui.button(label="Nâng chỉ số 🗡 DPS", style=discord.ButtonStyle.primary, row=0)
    async def dps(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed(
                "🗡 **🤺 Hiệp Sĩ Hắc Ám tự mình hướng dẫn chiêu thức cho ngươi. Hãy tập trung quan sát!**\n\n"
                "🔥 Đừng dừng lại. Chỉ một nhịp sai… và ngươi sẽ mất mạng.\n\n"
                "Ta sẽ ra một chuỗi 4 chiêu thức. Ngươi phải bấm **đúng thứ tự** trong **10 giây**.\n"
                "Một lần luyện tập kéo dài **5 lượt**."
            ),
            view=DpsReadyView(self.user),
        )

    @discord.ui.button(label="Pha chế 💊 Thần dược", style=discord.ButtonStyle.success, row=0)
    async def potion(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed(
                "⚗️ 🤺 Hiệp sĩ ma dẫn ngươi vào **Lò giả kim**:\n\n"
                "Ngươi cần gom đúng **ba nguyên liệu** để pha chế mỗi mẻ Thần dược. "
                "**Mỗi loại nguyên liệu sẽ ảnh hưởng đến xác suất thành công, "
                "nhưng cùng một loại nguyên liệu cũng sẽ có chất lượng khác nhau – hãy lưu ý điều này.**\n"
                "Kẻ nào sở hữu càng nhiều Thần dược, tỉ lệ sinh tồn của hắn trên chiến trường càng cao.\n\n"
                "**Hãy chọn nguyên liệu:**"
            ),
            view=PotionView(self.user),
        )

    @discord.ui.button(label="🗿 Quay lại sảnh chờ", style=discord.ButtonStyle.secondary, row=1)
    async def lobby(self, interaction, button):
        await go_lobby(interaction, self.user)

    @discord.ui.button(label="🚪 Thoát", style=discord.ButtonStyle.danger, row=1)
    async def exit(self, interaction, button):
        await exit_bot(interaction)


# ============== TANK ==============
# ============== TANK ==============
COLOR_RED = "🔴"
COLOR_GREEN = "🟢"
COLOR_BLUE = "🔵"

COLOR_LABELS = {
    COLOR_RED: "🔴",
    COLOR_GREEN: "🟢",
    COLOR_BLUE: "🔵",
}

DIRECTIONS = {
    COLOR_RED:    ("◀️ Né trái",   discord.ButtonStyle.danger),
    COLOR_GREEN:  ("⏸️ Đứng yên",  discord.ButtonStyle.success),
    COLOR_BLUE:   ("▶️ Né phải",   discord.ButtonStyle.primary),
}


class TankReadyView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.user = user

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="💥 Đã rõ", style=discord.ButtonStyle.success, row=0)
    async def go(self, interaction, button):
        await interaction.response.defer()
        await run_tank_session(interaction, self.user)

    @discord.ui.button(label="🗿 Quay lại sảnh chờ", style=discord.ButtonStyle.secondary, row=1)
    async def lobby(self, interaction, button):
        await go_lobby(interaction, self.user)

    @discord.ui.button(label="🚪 Thoát", style=discord.ButtonStyle.danger, row=1)
    async def exit(self, interaction, button):
        await exit_bot(interaction)


class TankRoundView(discord.ui.View):
    def __init__(self, user, hint_color):
        super().__init__(timeout=10)
        self.user = user
        self.hint_color = hint_color
        self.choice = None
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()

        for color, (label, style) in DIRECTIONS.items():
            btn = discord.ui.Button(label=label, style=style)

            async def cb(interaction, c=color):
                if interaction.user.id != self.user.id:
                    await interaction.response.send_message("Đây không phải lượt của ngươi.", ephemeral=True)
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
    successes = 0
    msg = None
    for turn in range(1, 6):
        hint_color = random.choice(list(COLOR_LABELS.keys()))
        emoji = hint_color
        embed = knight_embed(
            f"☠️ **Lượt {turn}/5** — Đấu sĩ xương khô sắp {emoji} **tấn công** {emoji} ngươi, "
            f"ngươi sẽ né phía nào?\n\nBấm nút trùng màu để né."
        )       
        view = TankRoundView(user, hint_color)
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
        msg_text = f"🌟 Ngươi đã né hầu hết các đòn ({successes}/5). **+{gain} 🛡 Tank**"
    elif successes >= 2:
        gain = apply_training_bonus(2, p.get("rank", "I"))
        msg_text = f"🛡 Tạm được, vẫn cần rèn thêm ({successes}/5). **+{gain} 🛡 Tank**"
    else:
        gain = 0
        msg_text = f"💀 Ngươi đã trúng quá nhiều đòn ({successes}/5). **Không có điểm nào.**"
    p["tank"] += gain
    persist()
    bonus = training_bonus_pct(p.get("rank", "I"))
    if bonus > 0 and gain > 0:
        msg_text += f"\n\n_(Hạng **{p['rank']}** — điểm thưởng luyện tập đã được nhân **+{bonus}%**.)_"
    await msg.edit(
        embed=knight_embed(f"**Kết quả luyện tập 🛡 Tank**\n\n{msg_text}"),
        view=AfterTrainView(user),
    )


# ============== DPS ==============
DPS_EMOJIS = ["🗡", "⚔️", "💥", "🏹"]


class DpsReadyView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.user = user

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="💥 Đã rõ", style=discord.ButtonStyle.success, row=0)
    async def go(self, interaction, button):
        await interaction.response.defer()
        await run_dps_session(interaction, self.user)

    @discord.ui.button(label="🗿 Quay lại sảnh chờ", style=discord.ButtonStyle.secondary, row=1)
    async def lobby(self, interaction, button):
        await go_lobby(interaction, self.user)

    @discord.ui.button(label="🚪 Thoát", style=discord.ButtonStyle.danger, row=1)
    async def exit(self, interaction, button):
        await exit_bot(interaction)


class DpsRoundView(discord.ui.View):
    def __init__(self, user, sequence: list[str]):
        super().__init__(timeout=10)
        self.user = user
        self.sequence = sequence
        self.idx = 0
        self.failed = False
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()

        labels = list(sequence)
        random.shuffle(labels)
        for emoji_label in labels:
            btn = discord.ui.Button(label=emoji_label, style=discord.ButtonStyle.primary)

            async def cb(interaction, e=emoji_label):
                if interaction.user.id != self.user.id:
                    await interaction.response.send_message("Đây không phải lượt của ngươi.", ephemeral=True)
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
    fails = 0
    msg = None
    for turn in range(1, 6):
        seq = random.sample(DPS_EMOJIS, 4)
        embed = knight_embed(
            f"⚔️ **Lượt {turn}/5** — Hãy bấm theo đúng thứ tự sau đây:\n\n"
            f"# {' → '.join(seq)}\n\nNgươi có 10 giây."
        )
        view = DpsRoundView(user, seq)
        if msg is None:
            await interaction.edit_original_response(embed=embed, view=view)
            msg = await interaction.original_response()
        else:
            await msg.edit(embed=embed, view=view)
        try:
            success = await asyncio.wait_for(view.future, timeout=11)
        except asyncio.TimeoutError:
            success = False
        if not success:
            fails += 1

    p = get_player(interaction.guild_id, user.id)
    if fails == 0:
        gain = apply_training_bonus(5, p.get("rank", "I"))
        text = f"🌟 🤺 Chiêu thức hoàn mỹ.  **+{gain} 🗡 DPS**"
    elif fails <= 2:
        gain = apply_training_bonus(2, p.get("rank", "I"))
        text = f"🗡 Cần cải thiện thêm, nhưng vẫn được.  **+{gain} 🗡 DPS**"
    else:
        gain = 0
        text = "💀 Chiêu thức rối loạn. Ngươi đã thua.  **+0 🗡 DPS**"
    p["dps"] += gain
    persist()
    bonus = training_bonus_pct(p.get("rank", "I"))
    if bonus > 0 and gain > 0:
        text += f"\n\n_(Hạng **{p['rank']}** — điểm thưởng luyện tập đã được nhân **+{bonus}%**.)_"
    await msg.edit(
        embed=knight_embed(f"**Kết quả luyện tập 🗡 DPS** (sai {fails}/5 lượt)\n\n{text}"),
        view=AfterTrainView(user),
    )


# ============== POTION ==============
INGREDIENTS = [
    {"emoji": "🌿", "name": "Thảo dược",       "lo": -10, "hi": 50},
    {"emoji": "🍄", "name": "Nấm",             "lo": -30, "hi": 30},
    {"emoji": "💧", "name": "Nước tinh khiết", "lo": -10, "hi": 20},
    {"emoji": "🔥", "name": "Tinh chất lửa",   "lo": -20, "hi": 50},
    {"emoji": "❄️", "name": "Hoa tuyết",       "lo": -10, "hi": 20},
]


def _ingredient_label(ing: dict) -> str:
    """Format đồng bộ: '🌿Thảo dược (-10% ⇨ +50%)'."""
    return f"{ing['emoji']}{ing['name']} ({ing['lo']:+d}% ⇨ {ing['hi']:+d}%)"


class PotionView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user
        self.picked: list[dict] = []
        self._build()

    def _build(self):
        self.clear_items()
        for idx, ing in enumerate(INGREDIENTS):
            btn = discord.ui.Button(
                label=_ingredient_label(ing),
                style=discord.ButtonStyle.secondary,
                row=0 if idx < 3 else 1,
            )

            async def cb(interaction, ing_=ing):
                if interaction.user.id != self.user.id:
                    return
                if len(self.picked) >= 3:
                    # Cảnh báo khi chọn quá ba nguyên liệu
                    await interaction.response.send_message(
                        "⚠️ **Cảnh báo:** Ngươi đã chọn đủ **3 nguyên liệu**. "
                        "Một mẻ Thần dược chỉ chấp nhận đúng ba nguyên liệu — không thể thêm nữa. "
                        "Hãy bấm **⚗️ Bào chế** hoặc làm lại từ đầu.",
                        ephemeral=True,
                    )
                    return
                roll = random.choice([ing_["lo"], ing_["hi"]])
                self.picked.append({"name": ing_["name"], "emoji": ing_["emoji"], "value": roll})
                await self._refresh(interaction)

            btn.callback = cb
            self.add_item(btn)

        brew = discord.ui.Button(
            label="⚗️ Bào chế",
            style=discord.ButtonStyle.success,
            row=2,
            disabled=len(self.picked) != 3,
        )

        async def brew_cb(interaction):
            if interaction.user.id != self.user.id:
                return
            await self._brew(interaction)

        brew.callback = brew_cb
        self.add_item(brew)

        reset = discord.ui.Button(label="↺ Làm lại", style=discord.ButtonStyle.secondary, row=2)

        async def reset_cb(interaction):
            if interaction.user.id != self.user.id:
                return
            self.picked = []
            await self._refresh(interaction)

        reset.callback = reset_cb
        self.add_item(reset)

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

    def _picked_text(self):
        if not self.picked:
            return "(Chưa chọn nguyên liệu nào)"
        lines = [f"{i+1}. {p['emoji']} {p['name']} → **{p['value']:+d}%**" for i, p in enumerate(self.picked)]
        return "\n".join(lines)

    async def _refresh(self, interaction):
        self._build()
        embed = knight_embed(
            "⚗️ **Lò giả kim** — chọn đúng **ba nguyên liệu** rồi bấm **Bào chế**.\n\n"
            "**Mỗi loại nguyên liệu sẽ ảnh hưởng đến xác suất thành công, "
            "nhưng cùng một loại nguyên liệu cũng sẽ có chất lượng khác nhau – hãy lưu ý điều này.**\n\n"
            f"**Đã chọn ({len(self.picked)}/3):**\n{self._picked_text()}"
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def _brew(self, interaction):
        total = sum(p["value"] for p in self.picked)
        p = get_player(interaction.guild_id, self.user.id)
        rank = p.get("rank", "I")
        if total < 20:
            text = f"💔 Tổng điểm: **{total}** — Ngươi không chế được lọ thần dược nào."
            gain = 0
        elif total < 50:
            gain = apply_training_bonus(2, rank)
            text = f"⚗️⚗️ Tổng điểm: **{total}** — Ngươi chế được **2 lọ thần dược**. **+{gain} 💊 Health**"
        elif total < 90:
            gain = apply_training_bonus(3, rank)
            text = f"⚗️⚗️⚗️ Tổng điểm: **{total}** — Ngươi chế được **3 lọ thần dược**. **+{gain} 💊 Health**"
        else:
            gain = apply_training_bonus(5, rank)
            text = f"⚗️⚗️⚗️⚗️⚗️ Tổng điểm: **{total}** — Ngươi chế được **5 lọ thần dược**! **+{gain} 💊 Health**"
        p["health"] += gain
        persist()
        bonus = training_bonus_pct(rank)
        if bonus > 0 and gain > 0:
            text += f"\n\n_(Hạng **{rank}** — điểm thưởng luyện tập đã được nhân **+{bonus}%**.)_"
        await interaction.response.edit_message(
            embed=knight_embed(f"**Kết quả pha chế thần dược**\n\n{text}"),
            view=AfterTrainView(self.user),
        )


# ============== AFTER TRAIN ==============
class AfterTrainView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="🛠 Luyện tập tiếp", style=discord.ButtonStyle.primary, row=0)
    async def again(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed("Hãy chọn bài tập phù hợp:"),
            view=TrainView(self.user),
        )

    @discord.ui.button(label="🗿 Quay lại sảnh chờ", style=discord.ButtonStyle.secondary, row=0)
    async def lobby(self, interaction, button):
        await go_lobby(interaction, self.user)

    @discord.ui.button(label="🚪 Thoát", style=discord.ButtonStyle.danger, row=0)
    async def exit(self, interaction, button):
        await exit_bot(interaction)
