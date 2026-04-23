"""Admin panel (chỉ admin server mới thấy/dùng)."""
import discord

from .storage import (
    get_guild, get_player, persist, get_locale,
    get_monsters, get_monsters_by_level, add_monster, update_monster, delete_monster,
)
from .core import knight_embed, t, RANKS, RANK_INFO, compute_rank, DEFAULT_LORE, go_lobby, exit_bot


# ============== ADMIN I18N ==============
TR_ADMIN = {
    # Main panel
    "admin_title": (
        "🛡️ **Bảng quản trị**",
        "🛡️ **Admin Panel**"
    ),
    "btn_roles": (
        "🏷 Thiết lập role thưởng theo hạng",
        "🏷 Set Rank Reward Roles"
    ),
    "btn_lore": (
        "🧿 Quản lý Lore trò chuyện",
        "🧿 Manage Chat Lore"
    ),
    "btn_monsters": (
        "🐉 Quản lý quái vật",
        "🐉 Manage Monsters"
    ),
    "btn_edit_player": (
        "✏️ Chỉnh sửa data người chơi",
        "✏️ Edit Player Data"
    ),
    "btn_reset_player": (
        "🗑 Reset người chơi về mặc định (5-5-5)",
        "🗑 Reset Player to Default (5-5-5)"
    ),
    "btn_reset_server": (
        "☢️ Reset toàn server",
        "☢️ Reset Entire Server"
    ),
    # Rank roles
    "roles_pick": (
        "Hãy chọn hạng cần gắn role thưởng:",
        "Choose the rank to assign a reward role:"
    ),
    "rank_btn_label": ("Hạng {rk}", "Rank {rk}"),
    "roles_pick_role": (
        "Hãy chọn role để gắn cho hạng **{rk}** ({rank_name}):",
        "Choose the role to assign for Rank **{rk}** ({rank_name}):"
    ),
    "role_cleared": (
        "Đã xoá role thưởng cho hạng **{rk}**.",
        "Reward role for Rank **{rk}** has been removed."
    ),
    "btn_clear_role": (
        "❌ Xoá role hiện tại",
        "❌ Remove current role"
    ),
    "role_select_placeholder": ("Chọn role...", "Select a role..."),
    "role_assigned": (
        "✅ Đã gắn role {role_mention} làm phần thưởng khi người chơi đạt hạng **{rk}**.",
        "✅ Role {role_mention} has been assigned as the reward for reaching Rank **{rk}**."
    ),
    # Lore
    "lore_title": (
        "🧿 **Quản lý Lore trò chuyện**\n\n"
        "Câu mặc định luôn nằm trong pool hiển thị ngẫu nhiên cùng các câu do admin nhập.\n\n"
        "Hãy chọn chủ đề lời thoại của Hiệp Sĩ Hắc Ám mà ngươi muốn quản lý:",
        "🧿 **Manage Chat Lore**\n\n"
        "The default line is always in the random pool alongside admin-entered lines.\n\n"
        "Choose the dialogue topic you wish to manage:"
    ),
    "lore_default_label": (
        "🔒 **(Mặc định, không thể sửa/xoá)** — {preview}",
        "🔒 **(Default — cannot be edited or deleted)** — {preview}"
    ),
    "lore_no_admin": (
        "\n_Chưa có câu nào do admin nhập. Pool hiện tại chỉ gồm câu mặc định._",
        "\n_No admin-entered lines yet. The current pool contains only the default._"
    ),
    "lore_bot_note": (
        "_Bot sẽ chọn ngẫu nhiên một câu trong pool (gồm câu mặc định + tất cả câu admin nhập) "
        "khi user hỏi chủ đề này._",
        "_The bot will randomly pick from the pool (default + all admin lines) "
        "when a user asks about this topic._"
    ),
    "lore_item_header": (
        "🧿 **Lore — {topic_label} — câu admin #{idx}**",
        "🧿 **Lore — {topic_label} — admin line #{idx}**"
    ),
    "lore_not_found": ("(không tồn tại)", "(does not exist)"),
    "lore_pick_topic": (
        "🧿 Hãy chọn chủ đề lời thoại:",
        "🧿 Choose a dialogue topic:"
    ),
    "btn_add_lore": ("➕ Thêm câu mới", "➕ Add new line"),
    "btn_edit_lore": ("✏️ Sửa", "✏️ Edit"),
    "btn_delete_lore": ("🗑 Xoá", "🗑 Delete"),
    "btn_back_list": ("◀ Quay lại danh sách", "◀ Back to list"),
    "lore_select_placeholder": ("Chọn câu admin để sửa / xoá...", "Select an admin line to edit / delete..."),
    "lore_select_none": ("(Chưa có câu admin nào)", "(No admin lines yet)"),
    # Monsters
    "monsters_title": (
        "🐉 **Quản lý quái vật**\n\n"
        "Hãy chọn cấp độ quái cần xem / chỉnh sửa / thêm mới:",
        "🐉 **Manage Monsters**\n\n"
        "Choose the monster tier to view / edit / add:"
    ),
    "monster_list_title": (
        "🐉 **Quái cấp {level}** — {label}\n\n{body}\n\n"
        "_Chọn một quái trong menu để sửa / xoá, hoặc bấm **➕ Thêm quái mới**._",
        "🐉 **Tier {level} Monsters** — {label}\n\n{body}\n\n"
        "_Select a monster from the menu to edit / delete, or press **➕ Add new monster**._"
    ),
    "monster_none": ("_(Chưa có quái nào ở cấp này.)_", "_(No monsters at this tier.)_"),
    "monster_select_placeholder": ("Chọn quái để sửa / xoá...", "Select a monster to edit / delete..."),
    "monster_select_none": ("(Chưa có quái nào)", "(No monsters yet)"),
    "btn_add_monster": ("➕ Thêm quái mới", "➕ Add new monster"),
    "btn_back_tier": ("◀ Quay lại chọn cấp", "◀ Back to tier selection"),
    "btn_edit_monster": ("✏️ Sửa", "✏️ Edit"),
    "btn_delete_monster": ("🗑 Xoá", "🗑 Delete"),
    "monster_detail": (
        "🐉 **{emoji} {name}** _(Cấp {level})_\n\n"
        "🛡 Tank: **{tank}**\n🗡 DPS: **{dps}**\n💊 HP: **{hp}**",
        "🐉 **{emoji} {name}** _(Level {level})_\n\n"
        "🛡 Tank: **{tank}**\n🗡 DPS: **{dps}**\n💊 HP: **{hp}**"
    ),
    "monster_invalid_level": (
        "💀 Cấp phải là 1-5 hoặc I-V.",
        "💀 Level must be 1-5 or I-V."
    ),
    # Edit / Reset player
    "edit_player_title": (
        "✏️ Chỉnh sửa chỉ số người chơi",
        "✏️ Edit Player Stats"
    ),
    "edit_uid_label": ("User ID hoặc @mention", "User ID or @mention"),
    "edit_tank_label": ("🛡 Tank", "🛡 Tank"),
    "edit_dps_label": ("🗡 DPS", "🗡 DPS"),
    "edit_health_label": ("💊 Health", "💊 Health"),
    "edit_wins_label": ("⚔️ Số trận thắng", "⚔️ Win count"),
    "edit_bad_user": ("💀 Không hiểu user.", "💀 Cannot parse that user."),
    "edit_bad_stats": ("💀 Chỉ số phải là số.", "💀 Stats must be numbers."),
    "edit_success": (
        "✅ Đã cập nhật <@{uid}>: 🛡{tank} 🗡{dps} 💊{health} ⚔️{wins} | Hạng **{rank}**",
        "✅ Updated <@{uid}>: 🛡{tank} 🗡{dps} 💊{health} ⚔️{wins} | Rank **{rank}**"
    ),
    "reset_player_title": ("🗑 Reset người chơi", "🗑 Reset Player"),
    "reset_uid_label": ("User ID hoặc @mention", "User ID or @mention"),
    "reset_bad_user": ("💀 Không hiểu user.", "💀 Cannot parse that user."),
    "reset_success": ("🗑 Đã reset dữ liệu của <@{uid}>.", "🗑 Data for <@{uid}> has been reset."),
    "reset_not_found": ("Không tìm thấy người chơi này.", "Player not found."),
    # Reset server
    "reset_server_warn": (
        "☢️ **CẢNH BÁO** — Hành động này sẽ xoá toàn bộ chỉ số của mọi người chơi trong server.\n"
        "Ngươi có chắc chắn?",
        "☢️ **WARNING** — This action will erase all player data in this server.\n"
        "Are you absolutely sure?"
    ),
    "btn_confirm_reset": ("☢️ Xác nhận reset toàn bộ", "☢️ Confirm full reset"),
    "btn_cancel": ("❌ Huỷ", "❌ Cancel"),
    "reset_server_done": (
        "☢️ Toàn bộ chỉ số người chơi trong server đã bị xoá.",
        "☢️ All player data in this server has been erased."
    ),
}


def ta(guild_id: int | None, user_id: int | None, key: str, **fmt) -> str:
    """Admin i18n helper — same pattern as t() in core."""
    locale = get_locale(guild_id, user_id) if guild_id else "vi"
    vi, en = TR_ADMIN.get(key, (key, key))
    s = en if locale == "en" else vi
    if fmt:
        try:
            s = s.format(**fmt)
        except Exception:
            pass
    return s


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
    def __init__(self, user, guild_id=None):
        super().__init__(timeout=300)
        self.user = user
        self._guild_id = guild_id
        loc = get_locale(guild_id, user.id) if guild_id else "vi"

        # Row 0
        btn_roles = discord.ui.Button(
            label=ta(guild_id, user.id, "btn_roles"), style=discord.ButtonStyle.primary, row=0
        )
        async def _roles(interaction, _self=self):
            await show_rank_role_select(interaction, _self.user)
        btn_roles.callback = _roles
        self.add_item(btn_roles)

        btn_lore = discord.ui.Button(
            label=ta(guild_id, user.id, "btn_lore"), style=discord.ButtonStyle.primary, row=0
        )
        async def _lore(interaction, _self=self):
            gid = interaction.guild_id
            view = LoreTopicView(_self.user)
            await view.setup(interaction)
            await interaction.response.edit_message(
                embed=knight_embed(ta(gid, _self.user.id, "lore_title")), view=view
            )
        btn_lore.callback = _lore
        self.add_item(btn_lore)

        # Row 1
        btn_monsters = discord.ui.Button(
            label=ta(guild_id, user.id, "btn_monsters"), style=discord.ButtonStyle.primary, row=1
        )
        async def _monsters(interaction, _self=self):
            gid = interaction.guild_id
            view = MonsterLevelView(_self.user)
            await view.setup(interaction)
            await interaction.response.edit_message(
                embed=knight_embed(ta(gid, _self.user.id, "monsters_title")), view=view
            )
        btn_monsters.callback = _monsters
        self.add_item(btn_monsters)

        # Row 2
        btn_edit = discord.ui.Button(
            label=ta(guild_id, user.id, "btn_edit_player"), style=discord.ButtonStyle.danger, row=2
        )
        async def _edit(interaction, _self=self):
            await interaction.response.send_modal(EditPlayerModal(_self.user, interaction.guild_id))
        btn_edit.callback = _edit
        self.add_item(btn_edit)

        btn_del = discord.ui.Button(
            label=ta(guild_id, user.id, "btn_reset_player"), style=discord.ButtonStyle.danger, row=2
        )
        async def _del(interaction, _self=self):
            await interaction.response.send_modal(DeletePlayerModal(_self.user, interaction.guild_id))
        btn_del.callback = _del
        self.add_item(btn_del)

        btn_reset = discord.ui.Button(
            label=ta(guild_id, user.id, "btn_reset_server"), style=discord.ButtonStyle.danger, row=2
        )
        async def _reset(interaction, _self=self):
            gid = interaction.guild_id
            await interaction.response.edit_message(
                embed=knight_embed(ta(gid, _self.user.id, "reset_server_warn")),
                view=ResetConfirmView(_self.user, gid),
            )
        btn_reset.callback = _reset
        self.add_item(btn_reset)

        # Row 3
        btn_lobby = discord.ui.Button(
            label="🗿 Lobby" if loc == "en" else "🗿 Sảnh chờ",
            style=discord.ButtonStyle.secondary, row=3
        )
        async def _lobby(interaction, _self=self):
            await go_lobby(interaction, _self.user)
        btn_lobby.callback = _lobby
        self.add_item(btn_lobby)

        btn_exit = discord.ui.Button(
            label="🚪 Exit" if loc == "en" else "🚪 Thoát",
            style=discord.ButtonStyle.danger, row=3
        )
        async def _exit(interaction):
            await exit_bot(interaction)
        btn_exit.callback = _exit
        self.add_item(btn_exit)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


# ============== RANK ROLE SETUP ==============
class RankRoleSelectView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    async def _build_buttons(self, interaction):
        # Clear and rebuild with locale so labels reflect current language
        # (called in interaction_check context, not __init__ — locale available)
        pass

    async def on_check_failure(self, interaction):
        pass

    async def _fill(self, interaction):
        gid = interaction.guild_id
        for rk in RANKS:
            rank_name = RANK_INFO[rk]["name_en"] if get_locale(gid, self.user.id) == "en" else RANK_INFO[rk]["name"]
            btn = discord.ui.Button(
                label=f"{'Rank' if get_locale(gid, self.user.id) == 'en' else 'Hạng'} {rk}",
                style=discord.ButtonStyle.secondary,
            )
            async def cb(interaction, r=rk):
                locale = get_locale(interaction.guild_id, self.user.id)
                rn = RANK_INFO[r]["name_en"] if locale == "en" else RANK_INFO[r]["name"]
                view2 = RolePickerView(self.user, r, interaction.guild_id)
                await view2._setup_buttons(interaction)
                await interaction.response.edit_message(
                    embed=knight_embed(ta(interaction.guild_id, self.user.id, "roles_pick_role", rk=r, rank_name=rn)),
                    view=view2,
                )
            btn.callback = cb
            self.add_item(btn)

        back = discord.ui.Button(
            label="◀ Back" if get_locale(gid, self.user.id) == "en" else "◀ Quay lại",
            style=discord.ButtonStyle.secondary, row=4,
        )
        async def back_cb(interaction):
            await interaction.response.edit_message(
                embed=knight_embed(ta(interaction.guild_id, self.user.id, "admin_title")),
                view=AdminView(self.user, interaction.guild_id),
            )
        back.callback = back_cb
        self.add_item(back)

    @classmethod
    async def create(cls, user, interaction):
        v = cls(user)
        await v._fill(interaction)
        return v


async def show_rank_role_select(interaction, user):
    gid = interaction.guild_id
    locale = get_locale(gid, user.id)
    view = RankRoleSelectView(user)
    for rk in RANKS:
        rn = RANK_INFO[rk]["name_en"] if locale == "en" else RANK_INFO[rk]["name"]
        btn = discord.ui.Button(
            label=f"{'Rank' if locale == 'en' else 'Hạng'} {rk}",
            style=discord.ButtonStyle.secondary,
        )
        async def cb(interaction, r=rk):
            loc2 = get_locale(interaction.guild_id, user.id)
            rn2 = RANK_INFO[r]["name_en"] if loc2 == "en" else RANK_INFO[r]["name"]
            view2 = RolePickerView(user, r, interaction.guild_id)
            await view2._setup_buttons(interaction)
            await interaction.response.edit_message(
                embed=knight_embed(ta(interaction.guild_id, user.id, "roles_pick_role", rk=r, rank_name=rn2)),
                view=view2,
            )
        btn.callback = cb
        view.add_item(btn)

    back = discord.ui.Button(
        label="◀ Back" if locale == "en" else "◀ Quay lại",
        style=discord.ButtonStyle.secondary, row=4,
    )
    async def back_cb(interaction):
        await interaction.response.edit_message(
            embed=knight_embed(ta(interaction.guild_id, user.id, "admin_title")),
            view=AdminView(user, interaction.guild_id),
        )
    back.callback = back_cb
    view.add_item(back)
    await interaction.response.edit_message(
        embed=knight_embed(ta(gid, user.id, "roles_pick")),
        view=view,
    )


class RolePickerView(discord.ui.View):
    def __init__(self, user, rank, guild_id=None):
        super().__init__(timeout=300)
        self.user = user
        self.rank = rank
        locale = get_locale(guild_id, user.id) if guild_id else "vi"
        self.add_item(RoleSelect(rank, locale))

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    async def _setup_buttons(self, interaction):
        gid = interaction.guild_id
        clear = discord.ui.Button(
            label=ta(gid, self.user.id, "btn_clear_role"),
            style=discord.ButtonStyle.danger, row=1,
        )
        async def clear_cb(interaction):
            g = get_guild(interaction.guild_id)
            g["config"]["rank_roles"].pop(self.rank, None)
            persist()
            await interaction.response.edit_message(
                embed=knight_embed(ta(interaction.guild_id, self.user.id, "role_cleared", rk=self.rank)),
                view=AdminView(self.user, interaction.guild_id),
            )
        clear.callback = clear_cb
        self.add_item(clear)

        back = discord.ui.Button(
            label="◀ Back" if get_locale(gid, self.user.id) == "en" else "◀ Quay lại",
            style=discord.ButtonStyle.secondary, row=1,
        )
        async def back_cb(interaction):
            await show_rank_role_select(interaction, self.user)
        back.callback = back_cb
        self.add_item(back)


async def show_role_picker(interaction, user, rank):
    view = RolePickerView(user, rank, interaction.guild_id)
    await view._setup_buttons(interaction)
    gid = interaction.guild_id
    locale = get_locale(gid, user.id)
    rn = RANK_INFO[rank]["name_en"] if locale == "en" else RANK_INFO[rank]["name"]
    await interaction.response.edit_message(
        embed=knight_embed(ta(gid, user.id, "roles_pick_role", rk=rank, rank_name=rn)),
        view=view,
    )


class RoleSelect(discord.ui.RoleSelect):
    def __init__(self, rank, locale: str = "vi"):
        placeholder = "Select a role…" if locale == "en" else "Chọn role…"
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, row=0)
        self.rank = rank

    async def callback(self, interaction):
        role = self.values[0]
        g = get_guild(interaction.guild_id)
        g["config"]["rank_roles"][self.rank] = str(role.id)
        persist()
        await interaction.response.edit_message(
            embed=knight_embed(
                ta(interaction.guild_id, interaction.user.id, "role_assigned",
                   role_mention=role.mention, rk=self.rank)
            ),
            view=AdminView(interaction.user, interaction.guild_id),
        )


# ============== EDIT / RESET PLAYER ==============
class EditPlayerModal(discord.ui.Modal):
    def __init__(self, user, guild_id):
        locale = get_locale(guild_id, user.id)
        title = "✏️ Edit Player Stats" if locale == "en" else "✏️ Chỉnh sửa chỉ số người chơi"
        super().__init__(title=title)
        self.user = user
        self.guild_id = guild_id
        self.uid = discord.ui.TextInput(
            label="User ID / @mention",
            required=True,
        )
        self.tank = discord.ui.TextInput(label="🛡 Tank", required=True)
        self.dps = discord.ui.TextInput(label="🗡 DPS", required=True)
        self.health = discord.ui.TextInput(label="💊 Health", required=True)
        self.wins = discord.ui.TextInput(
            label="⚔️ Win count" if locale == "en" else "⚔️ Số trận thắng",
            required=True,
        )
        for i in (self.uid, self.tank, self.dps, self.health, self.wins):
            self.add_item(i)

    async def on_submit(self, interaction):
        target_id = parse_user_id(self.uid.value)
        gid = interaction.guild_id
        uid = self.user.id
        if not target_id:
            await interaction.response.send_message(
                embed=knight_embed(ta(gid, uid, "edit_bad_user")), ephemeral=True
            )
            return
        try:
            t_, d_, h_, w_ = (
                int(self.tank.value), int(self.dps.value),
                int(self.health.value), int(self.wins.value),
            )
        except ValueError:
            await interaction.response.send_message(
                embed=knight_embed(ta(gid, uid, "edit_bad_stats")), ephemeral=True
            )
            return
        p = get_player(gid, target_id)
        p["tank"], p["dps"], p["health"], p["wins"] = t_, d_, h_, w_
        p["rank"] = compute_rank(p)
        persist()
        await interaction.response.send_message(
            embed=knight_embed(ta(gid, uid, "edit_success",
                                  uid=target_id, tank=t_, dps=d_, health=h_, wins=w_, rank=p["rank"])),
            ephemeral=True,
        )


class DeletePlayerModal(discord.ui.Modal):
    def __init__(self, user, guild_id):
        locale = get_locale(guild_id, user.id)
        title = "🗑 Reset Player" if locale == "en" else "🗑 Reset người chơi"
        super().__init__(title=title)
        self.user = user
        self.guild_id = guild_id
        self.uid = discord.ui.TextInput(label="User ID / @mention", required=True)
        self.add_item(self.uid)

    async def on_submit(self, interaction):
        target_id = parse_user_id(self.uid.value)
        gid = interaction.guild_id
        uid = self.user.id
        if not target_id:
            await interaction.response.send_message(
                embed=knight_embed(ta(gid, uid, "reset_bad_user")), ephemeral=True
            )
            return
        g = get_guild(gid)
        if str(target_id) in g["players"]:
            del g["players"][str(target_id)]
            persist()
            await interaction.response.send_message(
                embed=knight_embed(ta(gid, uid, "reset_success", uid=target_id)), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=knight_embed(ta(gid, uid, "reset_not_found")), ephemeral=True
            )


class ResetConfirmView(discord.ui.View):
    def __init__(self, user, guild_id=None):
        super().__init__(timeout=120)
        self.user = user

        btn_confirm = discord.ui.Button(
            label=ta(guild_id, user.id, "btn_confirm_reset"),
            style=discord.ButtonStyle.danger,
        )
        async def _confirm(interaction, _self=self):
            g = get_guild(interaction.guild_id)
            g["players"] = {}
            persist()
            await interaction.response.edit_message(
                embed=knight_embed(ta(interaction.guild_id, _self.user.id, "reset_server_done")),
                view=AdminView(_self.user, interaction.guild_id),
            )
        btn_confirm.callback = _confirm
        self.add_item(btn_confirm)

        btn_cancel = discord.ui.Button(
            label=ta(guild_id, user.id, "btn_cancel"),
            style=discord.ButtonStyle.secondary,
        )
        async def _cancel(interaction, _self=self):
            await interaction.response.edit_message(
                embed=knight_embed(ta(interaction.guild_id, _self.user.id, "admin_title")),
                view=AdminView(_self.user, interaction.guild_id),
            )
        btn_cancel.callback = _cancel
        self.add_item(btn_cancel)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


# ============== LORE MANAGEMENT ==============
LORE_TOPICS = {
    "intro": ("🌅 Lời chào mở đầu", "🌅 Opening Greeting"),
    "outro": ("🌒 Lời chào kết thúc", "🌒 Farewell Greeting"),
    "arena": ("🏛 Về đấu trường này", "🏛 About this arena"),
    "self": ("🌑 Về bản thân ngài", "🌑 About yourself"),
}


def _lore_topic_label(topic: str, locale: str = "vi") -> str:
    vi, en = LORE_TOPICS.get(topic, (topic, topic))
    return en if locale == "en" else vi


def _format_lore_list(g, topic: str, locale: str = "vi") -> str:
    msgs = g["lore"][topic]["messages"]
    default = DEFAULT_LORE[topic]
    default_preview = default[:120] + ("…" if len(default) > 120 else "")
    locked_label = (
        "🔒 **(Default — cannot be edited or deleted)** — " if locale == "en"
        else "🔒 **(Mặc định, không thể sửa/xoá)** — "
    )
    lines = [f"{locked_label}{default_preview}"]
    if not msgs:
        no_admin = (
            "\n_No admin-entered lines yet. The current pool contains only the default._"
            if locale == "en"
            else "\n_Chưa có câu nào do admin nhập. Pool hiện tại chỉ gồm câu mặc định._"
        )
        lines.append(no_admin)
    else:
        for i, m in enumerate(msgs):
            preview = m if len(m) <= 120 else m[:117] + "…"
            lines.append(f"▫️ **#{i+1}** — {preview}")
    return "\n\n".join(lines)


class LoreTopicView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    async def setup(self, interaction):
        gid = interaction.guild_id
        locale = get_locale(gid, self.user.id)
        self.clear_items()
        for topic, (vi_label, en_label) in LORE_TOPICS.items():
            label = en_label if locale == "en" else vi_label
            btn = discord.ui.Button(label=label, style=discord.ButtonStyle.primary, row=0)
            async def cb(interaction, t_=topic):
                await show_lore_list(interaction, self.user, t_)
            btn.callback = cb
            self.add_item(btn)

        back_label = "◀ Back" if locale == "en" else "◀ Quay lại"
        back = discord.ui.Button(label=back_label, style=discord.ButtonStyle.secondary, row=1)
        async def back_cb(interaction):
            await interaction.response.edit_message(
                embed=knight_embed(ta(interaction.guild_id, self.user.id, "admin_title")),
                view=AdminView(self.user, interaction.guild_id),
            )
        back.callback = back_cb
        self.add_item(back)


async def show_lore_topic_view(interaction, user):
    view = LoreTopicView(user)
    await view.setup(interaction)
    await interaction.response.edit_message(
        embed=knight_embed(ta(interaction.guild_id, user.id, "lore_title")),
        view=view,
    )


class LoreSelect(discord.ui.Select):
    def __init__(self, topic: str, guild_data, locale: str = "vi"):
        self.topic = topic
        self.locale = locale
        msgs = guild_data["lore"][topic]["messages"]
        options = []
        for i, m in enumerate(msgs):
            preview = m if len(m) <= 90 else m[:87] + "…"
            options.append(discord.SelectOption(label=f"#{i+1}: {preview}", value=str(i)))
        if not options:
            none_label = "(No admin lines yet)" if locale == "en" else "(Chưa có câu admin nào)"
            options = [discord.SelectOption(label=none_label, value="-1")]
        placeholder = "Select a line to edit / delete…" if locale == "en" else "Chọn câu admin để sửa / xoá..."
        super().__init__(
            placeholder=placeholder,
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
        text = msgs[idx] if 0 <= idx < len(msgs) else ("(does not exist)" if self.locale == "en" else "(không tồn tại)")
        locale = get_locale(interaction.guild_id, interaction.user.id)
        topic_label = _lore_topic_label(self.topic, locale)
        embed = knight_embed(
            f"🧿 **Lore — {topic_label} — {'admin line' if locale == 'en' else 'câu admin'} #{idx+1}**\n\n{text}"
        )
        await interaction.response.edit_message(
            embed=embed,
            view=LoreItemActionView(interaction.user, self.topic, idx, interaction.guild_id),
        )


class LoreManageView(discord.ui.View):
    def __init__(self, user, topic, guild_data, locale: str = "vi"):
        super().__init__(timeout=300)
        self.user = user
        self.topic = topic
        self.add_item(LoreSelect(topic, guild_data, locale))

        add_label = "➕ Add new line" if locale == "en" else "➕ Thêm câu mới"
        add_btn = discord.ui.Button(label=add_label, style=discord.ButtonStyle.success, row=1)
        async def add_cb(interaction):
            await interaction.response.send_modal(LoreAddModal(self.user, self.topic, interaction.guild_id))
        add_btn.callback = add_cb
        self.add_item(add_btn)

        back_label = "◀ Back" if locale == "en" else "◀ Quay lại"
        back = discord.ui.Button(label=back_label, style=discord.ButtonStyle.secondary, row=2)
        async def back_cb(interaction):
            await show_lore_topic_view(interaction, self.user)
        back.callback = back_cb
        self.add_item(back)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


async def show_lore_list(interaction, user, topic: str):
    gid = interaction.guild_id
    locale = get_locale(gid, user.id)
    g = get_guild(gid)
    topic_label = _lore_topic_label(topic, locale)
    bot_note = (
        "_The bot will randomly pick from the pool (default + all admin lines) when a user asks about this topic._"
        if locale == "en"
        else "_Bot sẽ chọn ngẫu nhiên một câu trong pool (gồm câu mặc định + tất cả câu admin nhập) khi user hỏi chủ đề này._"
    )
    embed = knight_embed(
        f"🧿 **Lore — {topic_label}**\n\n"
        f"{_format_lore_list(g, topic, locale)}\n\n"
        f"{bot_note}"
    )
    await interaction.response.edit_message(embed=embed, view=LoreManageView(user, topic, g, locale))


class LoreItemActionView(discord.ui.View):
    def __init__(self, user, topic, idx, guild_id=None):
        super().__init__(timeout=300)
        self.user = user
        self.topic = topic
        self.idx = idx

        loc = get_locale(guild_id, user.id) if guild_id else "vi"

        btn_edit = discord.ui.Button(
            label="✏️ Edit" if loc == "en" else "✏️ Sửa",
            style=discord.ButtonStyle.primary, row=0,
        )
        async def _edit(interaction, _self=self):
            g = get_guild(interaction.guild_id)
            msgs = g["lore"][_self.topic]["messages"]
            current = msgs[_self.idx] if 0 <= _self.idx < len(msgs) else ""
            await interaction.response.send_modal(
                LoreEditModal(_self.user, _self.topic, _self.idx, current, interaction.guild_id)
            )
        btn_edit.callback = _edit
        self.add_item(btn_edit)

        btn_del = discord.ui.Button(
            label="🗑 Delete" if loc == "en" else "🗑 Xoá",
            style=discord.ButtonStyle.danger, row=0,
        )
        async def _del(interaction, _self=self):
            g = get_guild(interaction.guild_id)
            msgs = g["lore"][_self.topic]["messages"]
            if 0 <= _self.idx < len(msgs):
                msgs.pop(_self.idx)
                persist()
            await show_lore_list(interaction, _self.user, _self.topic)
        btn_del.callback = _del
        self.add_item(btn_del)

        btn_back = discord.ui.Button(
            label="◀ Back" if loc == "en" else "◀ Quay lại",
            style=discord.ButtonStyle.secondary, row=1,
        )
        async def _back(interaction, _self=self):
            await show_lore_list(interaction, _self.user, _self.topic)
        btn_back.callback = _back
        self.add_item(btn_back)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


class LoreAddModal(discord.ui.Modal):
    def __init__(self, user, topic, guild_id):
        locale = get_locale(guild_id, user.id)
        title = "➕ Add new lore line" if locale == "en" else "➕ Thêm câu lore mới"
        super().__init__(title=title)
        self.user = user
        self.topic = topic
        label = "Dialogue text (max 2000 characters)" if locale == "en" else "Nội dung lời thoại (tối đa 2000 ký tự)"
        self.text = discord.ui.TextInput(
            label=label,
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


class LoreEditModal(discord.ui.Modal):
    def __init__(self, user, topic, idx, current_text: str, guild_id):
        locale = get_locale(guild_id, user.id)
        title = "✏️ Edit lore line" if locale == "en" else "✏️ Sửa câu lore"
        super().__init__(title=title)
        self.user = user
        self.topic = topic
        self.idx = idx
        label = "Dialogue text (max 2000 characters)" if locale == "en" else "Nội dung lời thoại (tối đa 2000 ký tự)"
        self.text = discord.ui.TextInput(
            label=label,
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
    1: ("🪨 Cấp I", "🪨 Tier I"),
    2: ("🌲 Cấp II", "🌲 Tier II"),
    3: ("🔥 Cấp III", "🔥 Tier III"),
    4: ("🌑 Cấp IV", "🌑 Tier IV"),
    5: ("👑 Cấp V", "👑 Tier V"),
}


def _level_label(lv: int, locale: str = "vi") -> str:
    vi, en = LEVEL_LABELS_ADMIN.get(lv, (str(lv), str(lv)))
    return en if locale == "en" else vi


def _format_monster_list(level: int, locale: str = "vi") -> str:
    monsters = get_monsters_by_level(level)
    if not monsters:
        return "_(No monsters at this tier.)_" if locale == "en" else "_(Chưa có quái nào ở cấp này.)_"
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

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    async def setup(self, interaction):
        gid = interaction.guild_id
        locale = get_locale(gid, self.user.id)
        self.clear_items()
        for lv in [1, 2, 3, 4, 5]:
            label = _level_label(lv, locale)
            btn = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary, row=(lv - 1) // 3)
            async def cb(interaction, lv_=lv):
                await show_monster_list(interaction, self.user, lv_)
            btn.callback = cb
            self.add_item(btn)

        back_label = "◀ Back" if locale == "en" else "◀ Quay lại"
        back = discord.ui.Button(label=back_label, style=discord.ButtonStyle.secondary, row=2)
        async def back_cb(interaction):
            await interaction.response.edit_message(
                embed=knight_embed(ta(interaction.guild_id, self.user.id, "admin_title")),
                view=AdminView(self.user, interaction.guild_id),
            )
        back.callback = back_cb
        self.add_item(back)


async def show_monster_level_view(interaction, user):
    view = MonsterLevelView(user)
    await view.setup(interaction)
    await interaction.response.edit_message(
        embed=knight_embed(ta(interaction.guild_id, user.id, "monsters_title")),
        view=view,
    )


async def show_monster_list(interaction, user, level: int):
    gid = interaction.guild_id
    locale = get_locale(gid, user.id)
    label = _level_label(level, locale)
    body = _format_monster_list(level, locale)
    note = (
        "_Select a monster from the menu to edit / delete, or press **➕ Add new monster**._"
        if locale == "en"
        else "_Chọn một quái trong menu để sửa / xoá, hoặc bấm **➕ Thêm quái mới**._"
    )
    tier_word = "Level" if locale == "en" else "Cấp"
    embed = knight_embed(
        f"🐉 **{'Tier' if locale == 'en' else 'Quái cấp'} {level}** — {label}\n\n{body}\n\n{note}"
    )
    view = MonsterManageView(user, level)
    await view.setup(interaction)
    await interaction.response.edit_message(embed=embed, view=view)


class MonsterSelect(discord.ui.Select):
    def __init__(self, level: int, locale: str = "vi"):
        self.level = level
        options = []
        for i, m in enumerate(get_monsters()):
            if int(m.get("level", 0)) != level:
                continue
            label = f"{m.get('emoji','❓')} {m.get('name','?')}"[:100]
            desc = f"🛡{m.get('tank',0)} 🗡{m.get('dps',0)} 💊{m.get('hp',0)}"[:100]
            options.append(discord.SelectOption(label=label, value=str(i), description=desc))
        if not options:
            none_label = "(No monsters yet)" if locale == "en" else "(Chưa có quái nào)"
            options = [discord.SelectOption(label=none_label, value="-1")]
        placeholder = "Select a monster to edit / delete…" if locale == "en" else "Chọn quái để sửa / xoá..."
        super().__init__(
            placeholder=placeholder,
            min_values=1, max_values=1, row=0, options=options,
        )
        if options[0].value == "-1":
            self.disabled = True
        self._locale = locale

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
        locale = get_locale(interaction.guild_id, interaction.user.id)
        level_word = "Level" if locale == "en" else "Cấp"
        embed = knight_embed(
            f"🐉 **{m.get('emoji','❓')} {m.get('name','?')}** _({level_word} {m.get('level','?')})_\n\n"
            f"🛡 Tank: **{m.get('tank',0)}**\n"
            f"🗡 DPS: **{m.get('dps',0)}**\n"
            f"💊 HP: **{m.get('hp',0)}**"
        )
        await interaction.response.edit_message(
            embed=embed,
            view=MonsterItemView(interaction.user, idx, self.level, interaction.guild_id),
        )


class MonsterManageView(discord.ui.View):
    def __init__(self, user, level: int):
        super().__init__(timeout=300)
        self.user = user
        self.level = level

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    async def setup(self, interaction):
        gid = interaction.guild_id
        locale = get_locale(gid, self.user.id)
        self.clear_items()
        self.add_item(MonsterSelect(self.level, locale))

        add_label = "➕ Add new monster" if locale == "en" else "➕ Thêm quái mới"
        add_btn = discord.ui.Button(label=add_label, style=discord.ButtonStyle.success, row=1)
        async def add_cb(interaction):
            await interaction.response.send_modal(MonsterAddModal(self.user, self.level, interaction.guild_id))
        add_btn.callback = add_cb
        self.add_item(add_btn)

        back_label = "◀ Back to tier selection" if locale == "en" else "◀ Quay lại chọn cấp"
        back = discord.ui.Button(label=back_label, style=discord.ButtonStyle.secondary, row=2)
        async def back_cb(interaction):
            await show_monster_level_view(interaction, self.user)
        back.callback = back_cb
        self.add_item(back)


class MonsterItemView(discord.ui.View):
    def __init__(self, user, idx: int, level: int, guild_id=None):
        super().__init__(timeout=300)
        self.user = user
        self.idx = idx
        self.level = level

        loc = get_locale(guild_id, user.id) if guild_id else "vi"

        btn_edit = discord.ui.Button(
            label="✏️ Edit" if loc == "en" else "✏️ Sửa",
            style=discord.ButtonStyle.primary, row=0,
        )
        async def _edit(interaction, _self=self):
            monsters = get_monsters()
            if not (0 <= _self.idx < len(monsters)):
                await show_monster_list(interaction, _self.user, _self.level)
                return
            await interaction.response.send_modal(
                MonsterEditModal(_self.user, _self.idx, _self.level, monsters[_self.idx], interaction.guild_id)
            )
        btn_edit.callback = _edit
        self.add_item(btn_edit)

        btn_del = discord.ui.Button(
            label="🗑 Delete" if loc == "en" else "🗑 Xoá",
            style=discord.ButtonStyle.danger, row=0,
        )
        async def _del(interaction, _self=self):
            delete_monster(_self.idx)
            await show_monster_list(interaction, _self.user, _self.level)
        btn_del.callback = _del
        self.add_item(btn_del)

        btn_back = discord.ui.Button(
            label="◀ Back" if loc == "en" else "◀ Quay lại",
            style=discord.ButtonStyle.secondary, row=1,
        )
        async def _back(interaction, _self=self):
            await show_monster_list(interaction, _self.user, _self.level)
        btn_back.callback = _back
        self.add_item(btn_back)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


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


class MonsterAddModal(discord.ui.Modal):
    def __init__(self, user, default_level: int, guild_id):
        locale = get_locale(guild_id, user.id)
        title = "➕ Add new monster" if locale == "en" else "➕ Thêm quái mới"
        super().__init__(title=title)
        self.user = user
        self.default_level = default_level
        self.guild_id = guild_id
        name_label = "Monster name + emoji (e.g. 🐉 Fire Dragon)" if locale == "en" else "Tên quái + emoji (vd: 🐉 Rồng Lửa)"
        level_label = "Tier (1-5 or I-V)" if locale == "en" else "Cấp (1-5 hoặc I-V)"
        self.f_name = discord.ui.TextInput(label=name_label, required=True, max_length=80)
        self.f_level = discord.ui.TextInput(label=level_label, required=True, max_length=4, default=str(default_level))
        self.f_tank = discord.ui.TextInput(label="🛡 Tank", required=True, max_length=8)
        self.f_dps = discord.ui.TextInput(label="🗡 DPS", required=True, max_length=8)
        self.f_hp = discord.ui.TextInput(label="💊 HP", required=True, max_length=8)
        for i in (self.f_name, self.f_level, self.f_tank, self.f_dps, self.f_hp):
            self.add_item(i)

    async def on_submit(self, interaction):
        gid = interaction.guild_id
        locale = get_locale(gid, self.user.id)
        lv = _parse_level(self.f_level.value)
        if lv is None:
            await interaction.response.send_message(
                embed=knight_embed(ta(gid, self.user.id, "monster_invalid_level")), ephemeral=True,
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
        add_monster(m)
        await show_monster_list(interaction, self.user, lv)


class MonsterEditModal(discord.ui.Modal):
    def __init__(self, user, idx: int, level: int, current: dict, guild_id):
        locale = get_locale(guild_id, user.id)
        title = "✏️ Edit monster" if locale == "en" else "✏️ Sửa quái"
        super().__init__(title=title)
        self.user = user
        self.idx = idx
        self.level = level
        self.guild_id = guild_id
        cur_full = f"{current.get('emoji','')} {current.get('name','')}".strip()
        name_label = "Monster name + emoji" if locale == "en" else "Tên quái + emoji"
        level_label = "Tier (1-5 or I-V)" if locale == "en" else "Cấp (1-5 hoặc I-V)"
        self.f_name = discord.ui.TextInput(label=name_label, required=True, max_length=80, default=cur_full[:80])
        self.f_level = discord.ui.TextInput(label=level_label, required=True, max_length=4, default=str(current.get("level", level)))
        self.f_tank = discord.ui.TextInput(label="🛡 Tank", required=True, max_length=8, default=str(current.get("tank", 0)))
        self.f_dps = discord.ui.TextInput(label="🗡 DPS", required=True, max_length=8, default=str(current.get("dps", 0)))
        self.f_hp = discord.ui.TextInput(label="💊 HP", required=True, max_length=8, default=str(current.get("hp", 1)))
        for i in (self.f_name, self.f_level, self.f_tank, self.f_dps, self.f_hp):
            self.add_item(i)

    async def on_submit(self, interaction):
        gid = interaction.guild_id
        locale = get_locale(gid, self.user.id)
        lv = _parse_level(self.f_level.value)
        if lv is None:
            await interaction.response.send_message(
                embed=knight_embed(ta(gid, self.user.id, "monster_invalid_level")), ephemeral=True,
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
    """Tách emoji đầu chuỗi và phần còn lại là tên."""
    raw = raw.strip()
    if not raw:
        return ("", "")
    parts = raw.split(None, 1)
    if len(parts) == 1:
        if len(parts[0]) <= 4 and not parts[0][0].isascii():
            return (parts[0], "")
        return ("", parts[0])
    head, tail = parts[0], parts[1]
    if head and not head[0].isalnum():
        return (head, tail)
    return ("", raw)
