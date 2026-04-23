"""Main lobby + chat views (with translation toggle)."""
import discord

from .storage import get_player, get_guild, get_locale, set_locale
from .core import (
    knight_embed, t, RANK_INFO, compute_rank, rank_progress_text,
    get_lore_text, arena_guide, go_lobby, exit_bot,
    unlock_achievements, format_achievements,
    rank_name as rk_name,
)
from .storage import persist


# ============== MAIN MENU ==============
class MainView(discord.ui.View):
    def __init__(self, user: discord.User, guild: discord.Guild | None = None):
        super().__init__(timeout=600)
        self.user = user
        self.guild = guild
        self._show_admin = bool(
            guild and isinstance(user, discord.Member) and user.guild_permissions.administrator
        )
        gid = guild.id if guild else None

        items = [
            (t(gid, user.id, "btn_train"), discord.ButtonStyle.primary, self._train, 0),
            (t(gid, user.id, "btn_challenge"), discord.ButtonStyle.danger, self._challenge, 0),
            (t(gid, user.id, "btn_chat"), discord.ButtonStyle.primary, self._chat, 0),
            (t(gid, user.id, "btn_stats"), discord.ButtonStyle.secondary, self._stats, 1),
            (t(gid, user.id, "btn_board"), discord.ButtonStyle.secondary, self._board, 1),
        ]
        if self._show_admin:
            items.append((t(gid, user.id, "btn_admin"), discord.ButtonStyle.success, self._admin, 1))
        items.append((t(gid, user.id, "btn_exit"), discord.ButtonStyle.danger, self._exit, 2))

        for label, style, cb, row in items:
            btn = discord.ui.Button(label=label, style=style, row=row)
            btn.callback = cb
            self.add_item(btn)

        lang_btn = discord.ui.Button(label=t(gid, user.id, "btn_lang"), style=discord.ButtonStyle.secondary, row=2)

        async def lang_cb(interaction):
            cur = get_locale(interaction.guild_id, self.user.id)
            set_locale(interaction.guild_id, self.user.id, "en" if cur == "vi" else "vi")
            await go_lobby(interaction, self.user)

        lang_btn.callback = lang_cb
        self.add_item(lang_btn)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user.id:
            locale = get_locale(interaction.guild_id, interaction.user.id)
            msg = (
                "Only the one who summoned me may choose."
                if locale == "en"
                else "Chỉ người triệu hồi ta mới có thể chọn."
            )
            await interaction.response.send_message(msg, ephemeral=True)
            return False
        return True

    async def _train(self, interaction):
        from .training import TrainView
        locale = get_locale(interaction.guild_id, self.user.id)
        msg = "Choose your training:" if locale == "en" else "Hãy chọn bài tập phù hợp:"
        await interaction.response.edit_message(
            embed=knight_embed(msg),
            view=TrainView(self.user),
        )

    async def _challenge(self, interaction):
        from .combat import ChallengeMenuView
        await interaction.response.edit_message(
            embed=knight_embed(t(interaction.guild_id, self.user.id, "challenge_intro")),
            view=ChallengeMenuView(self.user),
        )

    async def _stats(self, interaction):
        gid = interaction.guild_id
        uid = self.user.id
        locale = get_locale(gid, uid)
        p = get_player(gid, uid)
        p["rank"] = compute_rank(p)
        unlock_achievements(p)
        persist()
        rinfo = RANK_INFO[p["rank"]]
        rank_display = rk_name(p["rank"], locale)
        wins_label = t(gid, uid, "stats_wins")
        pvp_label = t(gid, uid, "stats_pvp_wins")
        rank_label = t(gid, uid, "stats_rank")
        if locale == "en":
            streak_label = "PvP streak"
        else:
            streak_label = "Streak PvP"
        text = (
            f"**👤 {self.user.display_name}**\n\n"
            f"🏆 {rank_label}: **{rank_display}**\n"
            f"🛡 Tank: **{p['tank']}** | 🗡 DPS: **{p['dps']}** | 💊 Health: **{p['health']}**\n"
            f"🐉 {wins_label}: **{p['wins']}**  |  ⚔️ {pvp_label}: **{p.get('pvp_wins', 0)}**  |  🔥 {streak_label}: **{p.get('pvp_streak', 0)}**\n\n"
            f"{rank_progress_text(p, gid, uid)}\n\n"
            f"{format_achievements(p, locale)}"
        )
        await interaction.response.edit_message(
            embed=knight_embed(text),
            view=PostInfoView(self.user),
        )

    async def _board(self, interaction):
        await interaction.response.edit_message(
            embed=knight_embed(t(interaction.guild_id, self.user.id, "lb_pick")),
            view=BoardPickView(self.user),
        )

    async def _chat(self, interaction):
        await interaction.response.edit_message(
            embed=knight_embed(t(interaction.guild_id, self.user.id, "chat_intro")),
            view=ChatView(self.user),
        )

    async def _admin(self, interaction):
        from .admin import AdminView
        locale = get_locale(interaction.guild_id, self.user.id)
        msg = (
            "🛡️ **Admin Panel** — for server administrators only."
            if locale == "en"
            else "🛡️ **Bảng quản trị (dành cho admin)** — chỉ dành cho quản trị viên server."
        )
        await interaction.response.edit_message(
            embed=knight_embed(msg),
            view=AdminView(self.user),
        )

    async def _exit(self, interaction):
        await exit_bot(interaction)


class BoardPickView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="🐉 Bảng Diệt Quái / Monster Slayer", style=discord.ButtonStyle.danger, row=0)
    async def pve(self, interaction, button):
        await _show_board(interaction, self.user, "pve")

    @discord.ui.button(label="⚔️ Bảng Đấu Sĩ / Duelist Board", style=discord.ButtonStyle.primary, row=0)
    async def pvp(self, interaction, button):
        await _show_board(interaction, self.user, "pvp")

    @discord.ui.button(label="🗿 Lobby / Quay lại sảnh chờ", style=discord.ButtonStyle.secondary, row=1)
    async def lobby(self, interaction, button):
        await go_lobby(interaction, self.user)

    @discord.ui.button(label="🚪 Thoát / Exit", style=discord.ButtonStyle.danger, row=1)
    async def exit(self, interaction, button):
        await exit_bot(interaction)


async def _show_board(interaction, user, kind: str):
    g = get_guild(interaction.guild_id)
    players = list(g["players"].items())
    if kind == "pve":
        title = t(interaction.guild_id, user.id, "lb_pve_title")
        wins_label = t(interaction.guild_id, user.id, "stats_wins")
        key = lambda kv: kv[1].get("wins", 0)
    else:
        title = t(interaction.guild_id, user.id, "lb_pvp_title")
        wins_label = t(interaction.guild_id, user.id, "stats_pvp_wins")
        key = lambda kv: kv[1].get("pvp_wins", 0)

    players = [(uid, p) for uid, p in players if key((uid, p)) > 0]
    top = sorted(players, key=key, reverse=True)[:10]

    lines = [title + "\n"]
    if not top:
        lines.append(t(interaction.guild_id, user.id, "lb_empty"))
    else:
        rank_label = t(interaction.guild_id, user.id, "stats_rank")
        locale = get_locale(interaction.guild_id, user.id)
        for i, (uid, p) in enumerate(top):
            wins_val = key((uid, p))
            rk = p.get("rank", "I")
            stat_block = (
                f"{rank_label} **{rk}** | 🛡{p.get('tank', 5)} 🗡{p.get('dps', 5)} 💊{p.get('health', 5)}"
            )
            if i == 0:
                lines.append(f"🏆 **<@{uid}>** — **{wins_val}** {wins_label} | {stat_block}")
            else:
                medals = ["", "🥈", "🥉"] + ["🔹"] * 7
                lines.append(f"{medals[i]} <@{uid}> — **{wins_val}** {wins_label} | {stat_block}")

    await interaction.response.edit_message(
        embed=knight_embed("\n".join(lines)),
        view=BoardAfterView(user),
    )


class BoardAfterView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="🏆 Bảng khác / Other board", style=discord.ButtonStyle.primary, row=0)
    async def other(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed(t(interaction.guild_id, self.user.id, "lb_pick")),
            view=BoardPickView(self.user),
        )

    @discord.ui.button(label="🗿 Lobby / Quay lại sảnh chờ", style=discord.ButtonStyle.secondary, row=0)
    async def lobby(self, interaction, button):
        await go_lobby(interaction, self.user)

    @discord.ui.button(label="🚪 Thoát / Exit", style=discord.ButtonStyle.danger, row=0)
    async def exit(self, interaction, button):
        await exit_bot(interaction)


class PostInfoView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="🗿 Lobby / Quay lại sảnh chờ", style=discord.ButtonStyle.secondary, row=0)
    async def lobby(self, interaction, button):
        await go_lobby(interaction, self.user)

    @discord.ui.button(label="🚪 Thoát / Exit", style=discord.ButtonStyle.danger, row=0)
    async def exit(self, interaction, button):
        await exit_bot(interaction)


# ============== CHAT ==============
class ChatView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="🏛 Về đấu trường / About this arena", style=discord.ButtonStyle.primary, row=0)
    async def arena(self, interaction, button):
        locale = get_locale(interaction.guild_id, self.user.id)
        await interaction.response.edit_message(
            embed=knight_embed(get_lore_text(interaction.guild_id, "arena", locale=locale)),
            view=ChatAfterView(self.user),
        )

    @discord.ui.button(label="🌑 Về bản thân ngài / About yourself", style=discord.ButtonStyle.primary, row=0)
    async def self_(self, interaction, button):
        locale = get_locale(interaction.guild_id, self.user.id)
        await interaction.response.edit_message(
            embed=knight_embed(get_lore_text(interaction.guild_id, "self", locale=locale)),
            view=ChatAfterView(self.user),
        )

    @discord.ui.button(label="📜 Hướng dẫn / Arena guide", style=discord.ButtonStyle.success, row=1)
    async def guide(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed(arena_guide(interaction.guild_id, self.user.id)),
            view=ChatAfterView(self.user),
        )

    @discord.ui.button(label="🗿 Lobby / Quay lại sảnh chờ", style=discord.ButtonStyle.secondary, row=2)
    async def lobby(self, interaction, button):
        await go_lobby(interaction, self.user)

    @discord.ui.button(label="🚪 Thoát / Exit", style=discord.ButtonStyle.danger, row=2)
    async def exit(self, interaction, button):
        await exit_bot(interaction)


class ChatAfterView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="💬 Hỏi điều khác / Ask something else", style=discord.ButtonStyle.primary, row=0)
    async def again(self, interaction, button):
        await interaction.response.edit_message(
            embed=knight_embed(t(interaction.guild_id, self.user.id, "chat_intro")),
            view=ChatView(self.user),
        )

    @discord.ui.button(label="🗿 Lobby / Quay lại sảnh chờ", style=discord.ButtonStyle.secondary, row=0)
    async def lobby(self, interaction, button):
        await go_lobby(interaction, self.user)

    @discord.ui.button(label="🚪 Thoát / Exit", style=discord.ButtonStyle.danger, row=0)
    async def exit(self, interaction, button):
        await exit_bot(interaction)
