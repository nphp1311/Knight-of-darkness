"""Admin panel (chỉ admin server mới thấy/dùng)."""
import discord

from .storage import (
    get_guild, get_player, persist,
    get_monsters, get_monsters_by_level, add_monster, update_monster, delete_monster,
)
from .core import knight_embed, RANKS, RANK_INFO, compute_rank, DEFAULT_LORE, go_lobby, exit_bot


def is_admin(member: discord.Member) -> bool:
    return bool(member.guild_permissions.administrator)


def parse_user_id(raw: str) -> int | None:
    raw = raw.strip()
    if raw.startswith("<@") and raw.endswith(">"):
        inner = raw[2:-1].lstrip("!&")
        try:
            return int(inner)
        except ValueError:
            return None
    try:
        return int(raw)
    except ValueError:
        return None


# ============== ADMIN MAIN ==============
class AdminView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="🏷 Thiết lập role thưởng theo hạng", style=discord.ButtonStyle.primary, row=0)
    async def roles(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed("Hãy chọn hạng cần gắn role thưởng:"),
            view=RankRoleSelectView(self.user),
        )

    @discord.ui.button(label="🧿 Quản lý Lore trò chuyện", style=discord.ButtonStyle.primary, row=0)
    async def lore(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed(
                "🧿 **Quản lý Lore trò chuyện**\n\n"
                "Câu mặc định luôn nằm trong pool hiển thị ngẫu nhiên cùng các câu do admin nhập.\n\n"
                "Hãy chọn chủ đề lời thoại của Hiệp Sĩ Hắc Ám mà ngươi muốn quản lý:"
            ),
            view=LoreTopicView(self.user),
        )

    @discord.ui.button(label="🐉 Quản lý quái vật", style=discord.ButtonStyle.primary, row=1)
    async def monsters(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed(
                "🐉 **Quản lý quái vật**\n\n"
                "Hãy chọn cấp độ quái cần xem / chỉnh sửa / thêm mới:"
            ),
            view=MonsterLevelView(self.user),
        )

    # ─── Hàng nguy hiểm: 3 nút màu đỏ ───
    @discord.ui.button(label="✏️ Chỉnh sửa data người chơi", style=discord.ButtonStyle.danger, row=2)
    async def edit(self, interaction, button):
        await interaction.response.send_modal(EditPlayerModal(self.user))

    @discord.ui.button(label="🗑 Reset chỉ số người chơi về 0", style=discord.ButtonStyle.danger, row=2)
    async def delete(self, interaction, button):
        await interaction.response.send_modal(DeletePlayerModal(self.user))

    @discord.ui.button(label="☢️ Reset toàn server", style=discord.ButtonStyle.danger, row=2)
    async def reset(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed(
                "☢️ **CẢNH BÁO** — Hành động này sẽ xoá toàn bộ chỉ số của mọi người chơi trong server.\n"
                "Ngươi có chắc chắn?"
            ),
            view=ResetConfirmView(self.user),
        )

    @discord.ui.button(label="🗿 Quay lại sảnh chờ", style=discord.ButtonStyle.secondary, row=3)
    async def lobby(self, interaction, button):
        await go_lobby(interaction, self.user)

    @discord.ui.button(label="🚪 Thoát", style=discord.ButtonStyle.danger, row=3)
    async def exit(self, interaction, button):
        await exit_bot(interaction)


# ============== RANK ROLE SETUP ==============
class RankRoleSelectView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user
        for rk in RANKS:
            btn = discord.ui.Button(label=f"Hạng {rk}", style=discord.ButtonStyle.secondary)

            async def cb(interaction, r=rk):
                await interaction.response.edit_message(
                    embed=knight_embed(
                        f"Hãy chọn role để gắn cho hạng **{r}** ({RANK_INFO[r]['name']}):"
                    ),
                    view=RolePickerView(self.user, r),
                )

            btn.callback = cb
            self.add_item(btn)

        back = discord.ui.Button(label="◀ Quay lại", style=discord.ButtonStyle.secondary, row=4)
        async def back_cb(interaction):
            await interaction.response.edit_message(
                embed=knight_embed("**Bảng quản trị**"),
                view=AdminView(self.user),
            )
        back.callback = back_cb
        self.add_item(back)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


class RolePickerView(discord.ui.View):
    def __init__(self, user, rank):
        super().__init__(timeout=300)
        self.user = user
        self.rank = rank
        self.add_item(RoleSelect(rank))
        clear = discord.ui.Button(label="❌ Xoá role hiện tại", style=discord.ButtonStyle.danger, row=1)

        async def clear_cb(interaction):
            g = get_guild(interaction.guild_id)
            g["config"]["rank_roles"].pop(rank, None)
            persist()
            await interaction.response.edit_message(
                embed=knight_embed(f"Đã xoá role thưởng cho hạng **{rank}**."),
                view=AdminView(self.user),
            )
        clear.callback = clear_cb
        self.add_item(clear)

        back = discord.ui.Button(label="◀ Quay lại", style=discord.ButtonStyle.secondary, row=1)
        async def back_cb(interaction):
            await interaction.response.edit_message(
                embed=knight_embed("Hãy chọn hạng cần gắn role thưởng:"),
                view=RankRoleSelectView(self.user),
            )
        back.callback = back_cb
        self.add_item(back)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


class RoleSelect(discord.ui.RoleSelect):
    def __init__(self, rank):
        super().__init__(placeholder="Chọn role...", min_values=1, max_values=1, row=0)
        self.rank = rank

    async def callback(self, interaction):
        role = self.values[0]
        g = get_guild(interaction.guild_id)
        g["config"]["rank_roles"][self.rank] = str(role.id)
        persist()
        await interaction.response.edit_message(
            embed=knight_embed(
                f"✅ Đã gắn role {role.mention} làm phần thưởng khi người chơi đạt hạng **{self.rank}**."
            ),
            view=AdminView(interaction.user),
        )


# ============== EDIT / RESET PLAYER ==============
class EditPlayerModal(discord.ui.Modal, title="✏️ Chỉnh sửa chỉ số người chơi"):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.uid = discord.ui.TextInput(label="User ID hoặc @mention", required=True)
        self.tank = discord.ui.TextInput(label="🛡 Tank", required=True)
        self.dps = discord.ui.TextInput(label="🗡 DPS", required=True)
        self.health = discord.ui.TextInput(label="💊 Health", required=True)
        self.wins = discord.ui.TextInput(label="⚔️ Số trận thắng", required=True)
        for i in (self.uid, self.tank, self.dps, self.health, self.wins):
            self.add_item(i)

    async def on_submit(self, interaction):
        target_id = parse_user_id(self.uid.value)
        if not target_id:
            await interaction.response.send_message(embed=knight_embed("💀 Không hiểu user."), ephemeral=True)
            return
        try:
            t_, d_, h_, w_ = int(self.tank.value), int(self.dps.value), int(self.health.value), int(self.wins.value)
        except ValueError:
            await interaction.response.send_message(embed=knight_embed("💀 Chỉ số phải là số."), ephemeral=True)
            return
        p = get_player(interaction.guild_id, target_id)
        p["tank"], p["dps"], p["health"], p["wins"] = t_, d_, h_, w_
        p["rank"] = compute_rank(p)
        persist()
        await interaction.response.send_message(
            embed=knight_embed(f"✅ Đã cập nhật <@{target_id}>: 🛡{t_} 🗡{d_} 💊{h_} ⚔️{w_} | Hạng **{p['rank']}**"),
            ephemeral=True,
        )


class DeletePlayerModal(discord.ui.Modal, title="🗑 Reset người chơi"):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.uid = discord.ui.TextInput(label="User ID hoặc @mention", required=True)
        self.add_item(self.uid)

    async def on_submit(self, interaction):
        target_id = parse_user_id(self.uid.value)
        if not target_id:
            await interaction.response.send_message(embed=knight_embed("💀 Không hiểu user."), ephemeral=True)
            return
        g = get_guild(interaction.guild_id)
        if str(target_id) in g["players"]:
            del g["players"][str(target_id)]
            persist()
            await interaction.response.send_message(
                embed=knight_embed(f"🗑 Đã reset dữ liệu của <@{target_id}>."), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=knight_embed("Không tìm thấy người chơi này."), ephemeral=True
            )


class ResetConfirmView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.user = user

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="☢️ Xác nhận reset toàn bộ", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        g = get_guild(interaction.guild_id)
        g["players"] = {}
        persist()
        await interaction.response.edit_message(
            embed=knight_embed("☢️ Toàn bộ chỉ số người chơi trong server đã bị xoá."),
            view=AdminView(self.user),
        )

    @discord.ui.button(label="❌ Huỷ", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed("**Bảng quản trị**"),
            view=AdminView(self.user),
        )


# ============== LORE MANAGEMENT ==============
LORE_TOPICS = {
    "intro": "🌅 Lời chào mở đầu",
    "outro": "🌒 Lời chào kết thúc",
    "arena": "🏛 Về đấu trường này",
    "self": "🌑 Về bản thân ngài",
}


def _format_lore_list(g, topic: str) -> str:
    msgs = g["lore"][topic]["messages"]
    default = DEFAULT_LORE[topic]
    lines = [f"🔒 **(Mặc định, không thể sửa/xoá)** — {default[:120]}{'…' if len(default) > 120 else ''}"]
    if not msgs:
        lines.append("\n_Chưa có câu nào do admin nhập. Pool hiện tại chỉ gồm câu mặc định._")
    else:
        for i, m in enumerate(msgs):
            preview = m if len(m) <= 120 else m[:117] + "…"
            lines.append(f"▫️ **#{i+1}** — {preview}")
    return "\n\n".join(lines)


class LoreTopicView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user
        for topic, label in LORE_TOPICS.items():
            btn = discord.ui.Button(label=label, style=discord.ButtonStyle.primary, row=0)

            async def cb(interaction, t_=topic):
                await show_lore_list(interaction, self.user, t_)

            btn.callback = cb
            self.add_item(btn)

        back = discord.ui.Button(label="◀ Quay lại", style=discord.ButtonStyle.secondary, row=1)

        async def back_cb(interaction):
            await interaction.response.edit_message(
                embed=knight_embed("🛡️ **Bảng quản trị**"),
                view=AdminView(self.user),
            )

        back.callback = back_cb
        self.add_item(back)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


class LoreSelect(discord.ui.Select):
    def __init__(self, topic: str, guild_data):
        self.topic = topic
        msgs = guild_data["lore"][topic]["messages"]
        options = []
        for i, m in enumerate(msgs):
            preview = m if len(m) <= 90 else m[:87] + "…"
            options.append(discord.SelectOption(label=f"#{i+1}: {preview}", value=str(i)))
        if not options:
            options = [discord.SelectOption(label="(Chưa có câu admin nào)", value="-1")]
        super().__init__(
            placeholder="Chọn câu admin để sửa / xoá...",
            min_values=1, max_values=1, row=0, options=options,
        )
        if options[0].value == "-1":
            self.disabled = True

    async def callback(self, interaction):
        idx = int(self.values[0])
        if idx < 0:
            await interaction.response.defer()
            return
        g = get_guild(interaction.guild_id)
        msgs = g["lore"][self.topic]["messages"]
        text = msgs[idx] if 0 <= idx < len(msgs) else "(không tồn tại)"
        embed = knight_embed(
            f"🧿 **Lore — {LORE_TOPICS[self.topic]} — câu admin #{idx+1}**\n\n{text}"
        )
        await interaction.response.edit_message(
            embed=embed,
            view=LoreItemActionView(interaction.user, self.topic, idx),
        )


class LoreManageView(discord.ui.View):
    def __init__(self, user, topic, guild_data):
        super().__init__(timeout=300)
        self.user = user
        self.topic = topic
        self.add_item(LoreSelect(topic, guild_data))

        add_btn = discord.ui.Button(label="➕ Thêm câu mới", style=discord.ButtonStyle.success, row=1)
        async def add_cb(interaction):
            await interaction.response.send_modal(LoreAddModal(self.user, self.topic))
        add_btn.callback = add_cb
        self.add_item(add_btn)

        back = discord.ui.Button(label="◀ Quay lại", style=discord.ButtonStyle.secondary, row=2)
        async def back_cb(interaction):
            await interaction.response.edit_message(
                embed=knight_embed("🧿 Hãy chọn chủ đề lời thoại:"),
                view=LoreTopicView(self.user),
            )
        back.callback = back_cb
        self.add_item(back)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


async def show_lore_list(interaction, user, topic: str):
    g = get_guild(interaction.guild_id)
    embed = knight_embed(
        f"🧿 **Lore — {LORE_TOPICS[topic]}**\n\n"
        f"{_format_lore_list(g, topic)}\n\n"
        "_Bot sẽ chọn ngẫu nhiên một câu trong pool (gồm câu mặc định + tất cả câu admin nhập) "
        "khi user hỏi chủ đề này._"
    )
    await interaction.response.edit_message(embed=embed, view=LoreManageView(user, topic, g))


class LoreItemActionView(discord.ui.View):
    def __init__(self, user, topic, idx):
        super().__init__(timeout=300)
        self.user = user
        self.topic = topic
        self.idx = idx

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="✏️ Sửa", style=discord.ButtonStyle.primary, row=0)
    async def edit(self, interaction, button):
        g = get_guild(interaction.guild_id)
        msgs = g["lore"][self.topic]["messages"]
        current = msgs[self.idx] if 0 <= self.idx < len(msgs) else ""
        await interaction.response.send_modal(LoreEditModal(self.user, self.topic, self.idx, current))

    @discord.ui.button(label="🗑 Xoá", style=discord.ButtonStyle.danger, row=0)
    async def delete(self, interaction, button):
        g = get_guild(interaction.guild_id)
        msgs = g["lore"][self.topic]["messages"]
        if 0 <= self.idx < len(msgs):
            msgs.pop(self.idx)
            persist()
        await show_lore_list(interaction, self.user, self.topic)

    @discord.ui.button(label="◀ Quay lại danh sách", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction, button):
        await show_lore_list(interaction, self.user, self.topic)


class LoreAddModal(discord.ui.Modal, title="➕ Thêm câu lore mới"):
    def __init__(self, user, topic):
        super().__init__()
        self.user = user
        self.topic = topic
        self.text = discord.ui.TextInput(
            label="Nội dung lời thoại (tối đa 2000 ký tự)",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000,
        )
        self.add_item(self.text)

    async def on_submit(self, interaction):
        g = get_guild(interaction.guild_id)
        g["lore"][self.topic]["messages"].append(self.text.value.strip())
        persist()
        await show_lore_list(interaction, self.user, self.topic)


class LoreEditModal(discord.ui.Modal, title="✏️ Sửa câu lore"):
    def __init__(self, user, topic, idx, current_text: str):
        super().__init__()
        self.user = user
        self.topic = topic
        self.idx = idx
        self.text = discord.ui.TextInput(
            label="Nội dung lời thoại (tối đa 2000 ký tự)",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000,
            default=current_text[:2000],
        )
        self.add_item(self.text)

    async def on_submit(self, interaction):
        g = get_guild(interaction.guild_id)
        msgs = g["lore"][self.topic]["messages"]
        if 0 <= self.idx < len(msgs):
            msgs[self.idx] = self.text.value.strip()
            persist()
        await show_lore_list(interaction, self.user, self.topic)


# ============== MONSTER MANAGEMENT ==============
LEVEL_LABELS_ADMIN = {
    1: "🪨 Cấp I", 2: "🌲 Cấp II", 3: "🔥 Cấp III", 4: "🌑 Cấp IV", 5: "👑 Cấp V",
}


def _format_monster_list(level: int) -> str:
    monsters = get_monsters_by_level(level)
    if not monsters:
        return "_(Chưa có quái nào ở cấp này.)_"
    lines = []
    for m in monsters:
        lines.append(
            f"▫️ {m.get('emoji','❓')} **{m.get('name','?')}** — "
            f"🛡 {m.get('tank',0)} | 🗡 {m.get('dps',0)} | 💊 {m.get('hp',0)}"
        )
    return "\n".join(lines)


class MonsterLevelView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user
        for lv in [1, 2, 3, 4, 5]:
            btn = discord.ui.Button(
                label=LEVEL_LABELS_ADMIN[lv],
                style=discord.ButtonStyle.secondary,
                row=(lv - 1) // 3,
            )

            async def cb(interaction, lv_=lv):
                await show_monster_list(interaction, self.user, lv_)

            btn.callback = cb
            self.add_item(btn)

        back = discord.ui.Button(label="◀ Quay lại", style=discord.ButtonStyle.secondary, row=2)
        async def back_cb(interaction):
            await interaction.response.edit_message(
                embed=knight_embed("**Bảng quản trị**"),
                view=AdminView(self.user),
            )
        back.callback = back_cb
        self.add_item(back)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


async def show_monster_list(interaction, user, level: int):
    embed = knight_embed(
        f"🐉 **Quái cấp {level}** — {LEVEL_LABELS_ADMIN[level]}\n\n"
        f"{_format_monster_list(level)}\n\n"
        "_Chọn một quái trong menu để sửa / xoá, hoặc bấm **➕ Thêm quái mới**._"
    )
    await interaction.response.edit_message(
        embed=embed, view=MonsterManageView(user, level),
    )


class MonsterSelect(discord.ui.Select):
    def __init__(self, level: int):
        self.level = level
        # Build options for monsters at this level. Use absolute index in global list as value.
        options = []
        for i, m in enumerate(get_monsters()):
            if int(m.get("level", 0)) != level:
                continue
            label = f"{m.get('emoji','❓')} {m.get('name','?')}"[:100]
            desc = f"🛡{m.get('tank',0)} 🗡{m.get('dps',0)} 💊{m.get('hp',0)}"[:100]
            options.append(discord.SelectOption(label=label, value=str(i), description=desc))
        if not options:
            options = [discord.SelectOption(label="(Chưa có quái nào)", value="-1")]
        super().__init__(
            placeholder="Chọn quái để sửa / xoá...",
            min_values=1, max_values=1, row=0, options=options,
        )
        if options[0].value == "-1":
            self.disabled = True

    async def callback(self, interaction):
        idx = int(self.values[0])
        if idx < 0:
            await interaction.response.defer()
            return
        monsters = get_monsters()
        if not (0 <= idx < len(monsters)):
            await interaction.response.defer()
            return
        m = monsters[idx]
        embed = knight_embed(
            f"🐉 **{m.get('emoji','❓')} {m.get('name','?')}** _(Cấp {m.get('level','?')})_\n\n"
            f"🛡 Tank: **{m.get('tank',0)}**\n"
            f"🗡 DPS: **{m.get('dps',0)}**\n"
            f"💊 HP: **{m.get('hp',0)}**"
        )
        await interaction.response.edit_message(
            embed=embed,
            view=MonsterItemView(interaction.user, idx, self.level),
        )


class MonsterManageView(discord.ui.View):
    def __init__(self, user, level: int):
        super().__init__(timeout=300)
        self.user = user
        self.level = level
        self.add_item(MonsterSelect(level))

        add_btn = discord.ui.Button(
            label="➕ Thêm quái mới",
            style=discord.ButtonStyle.success, row=1,
        )
        async def add_cb(interaction):
            await interaction.response.send_modal(MonsterAddModal(self.user, self.level))
        add_btn.callback = add_cb
        self.add_item(add_btn)

        back = discord.ui.Button(label="◀ Quay lại chọn cấp", style=discord.ButtonStyle.secondary, row=2)
        async def back_cb(interaction):
            await interaction.response.edit_message(
                embed=knight_embed(
                    "🐉 **Quản lý quái vật**\n\n"
                    "Hãy chọn cấp độ quái cần xem / chỉnh sửa / thêm mới:"
                ),
                view=MonsterLevelView(self.user),
            )
        back.callback = back_cb
        self.add_item(back)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


class MonsterItemView(discord.ui.View):
    def __init__(self, user, idx: int, level: int):
        super().__init__(timeout=300)
        self.user = user
        self.idx = idx
        self.level = level

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="✏️ Sửa", style=discord.ButtonStyle.primary, row=0)
    async def edit(self, interaction, button):
        monsters = get_monsters()
        if not (0 <= self.idx < len(monsters)):
            await show_monster_list(interaction, self.user, self.level)
            return
        await interaction.response.send_modal(MonsterEditModal(self.user, self.idx, self.level, monsters[self.idx]))

    @discord.ui.button(label="🗑 Xoá", style=discord.ButtonStyle.danger, row=0)
    async def delete(self, interaction, button):
        delete_monster(self.idx)
        await show_monster_list(interaction, self.user, self.level)

    @discord.ui.button(label="◀ Quay lại danh sách", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction, button):
        await show_monster_list(interaction, self.user, self.level)


def _parse_int(s: str, default: int = 0) -> int:
    try:
        return int(str(s).strip())
    except (ValueError, TypeError):
        return default


def _parse_level(s: str) -> int | None:
    raw = str(s).strip().upper()
    roman = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
    if raw in roman:
        return roman[raw]
    try:
        n = int(raw)
        if 1 <= n <= 5:
            return n
    except ValueError:
        pass
    return None


class MonsterAddModal(discord.ui.Modal, title="➕ Thêm quái mới"):
    def __init__(self, user, default_level: int):
        super().__init__()
        self.user = user
        self.default_level = default_level
        self.f_name = discord.ui.TextInput(label="Tên quái + emoji (vd: 🐉 Rồng Lửa)", required=True, max_length=80)
        self.f_level = discord.ui.TextInput(label="Cấp (1-5 hoặc I-V)", required=True, max_length=4, default=str(default_level))
        self.f_tank = discord.ui.TextInput(label="🛡 Tank (số nguyên)", required=True, max_length=8)
        self.f_dps = discord.ui.TextInput(label="🗡 DPS (số nguyên)", required=True, max_length=8)
        self.f_hp = discord.ui.TextInput(label="💊 HP (số nguyên)", required=True, max_length=8)
        for i in (self.f_name, self.f_level, self.f_tank, self.f_dps, self.f_hp):
            self.add_item(i)

    async def on_submit(self, interaction):
        lv = _parse_level(self.f_level.value)
        if lv is None:
            await interaction.response.send_message(
                embed=knight_embed("💀 Cấp phải là 1-5 hoặc I-V."), ephemeral=True,
            )
            return
        # Tách emoji ở đầu nếu có (ký tự đầu nếu nó không phải chữ cái/số ASCII).
        raw = self.f_name.value.strip()
        emoji, name = _split_emoji_name(raw)
        m = {
            "name": name or raw,
            "emoji": emoji or "❓",
            "level": lv,
            "tank": max(0, _parse_int(self.f_tank.value)),
            "dps": max(0, _parse_int(self.f_dps.value)),
            "hp": max(1, _parse_int(self.f_hp.value, 1)),
        }
        add_monster(m)
        await show_monster_list(interaction, self.user, lv)


class MonsterEditModal(discord.ui.Modal, title="✏️ Sửa quái"):
    def __init__(self, user, idx: int, level: int, current: dict):
        super().__init__()
        self.user = user
        self.idx = idx
        self.level = level
        cur_full = f"{current.get('emoji','')} {current.get('name','')}".strip()
        self.f_name = discord.ui.TextInput(label="Tên quái + emoji", required=True, max_length=80, default=cur_full[:80])
        self.f_level = discord.ui.TextInput(label="Cấp (1-5 hoặc I-V)", required=True, max_length=4, default=str(current.get("level", level)))
        self.f_tank = discord.ui.TextInput(label="🛡 Tank", required=True, max_length=8, default=str(current.get("tank", 0)))
        self.f_dps = discord.ui.TextInput(label="🗡 DPS", required=True, max_length=8, default=str(current.get("dps", 0)))
        self.f_hp = discord.ui.TextInput(label="💊 HP", required=True, max_length=8, default=str(current.get("hp", 1)))
        for i in (self.f_name, self.f_level, self.f_tank, self.f_dps, self.f_hp):
            self.add_item(i)

    async def on_submit(self, interaction):
        lv = _parse_level(self.f_level.value)
        if lv is None:
            await interaction.response.send_message(
                embed=knight_embed("💀 Cấp phải là 1-5 hoặc I-V."), ephemeral=True,
            )
            return
        raw = self.f_name.value.strip()
        emoji, name = _split_emoji_name(raw)
        m = {
            "name": name or raw,
            "emoji": emoji or "❓",
            "level": lv,
            "tank": max(0, _parse_int(self.f_tank.value)),
            "dps": max(0, _parse_int(self.f_dps.value)),
            "hp": max(1, _parse_int(self.f_hp.value, 1)),
        }
        update_monster(self.idx, m)
        await show_monster_list(interaction, self.user, lv)


def _split_emoji_name(raw: str) -> tuple[str, str]:
    """Tách emoji đầu chuỗi (1-2 ký tự đầu cho tới khoảng trắng) và phần còn lại là tên."""
    raw = raw.strip()
    if not raw:
        return ("", "")
    # Cách dễ nhất: lấy mọi thứ trước khoảng trắng đầu tiên làm emoji,
    # phần sau là tên. Nếu không có khoảng trắng, coi toàn bộ là tên, emoji rỗng.
    parts = raw.split(None, 1)
    if len(parts) == 1:
        # Không có khoảng trắng: chỉ có tên hoặc chỉ có emoji.
        # Heuristic: nếu chuỗi rất ngắn (<=4 ký tự) coi như emoji.
        if len(parts[0]) <= 4 and not parts[0][0].isascii():
            return (parts[0], "")
        return ("", parts[0])
    head, tail = parts[0], parts[1]
    # head có vẻ là emoji nếu không bắt đầu bằng chữ ASCII bình thường
    if head and not head[0].isalnum():
        return (head, tail)
    # Nếu head là chữ ASCII, coi cả raw là tên, emoji rỗng
    return ("", raw)
