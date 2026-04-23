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
            await interaction.response.send_message(
                t(interaction.guild_id, interaction.user.id, "msg_only_summoner"),
                ephemeral=True,
            )
            return False
        return True

    async def _train(self, interaction):
        from .training import TrainView
        await interaction.response.edit_message(
            embed=knight_embed(t(interaction.guild_id, self.user.id, "msg_choose_train")),
            view=TrainView(self.user, interaction.guild_id),
        )

    async def _challenge(self, interaction):
        from .combat import ChallengeMenuView
        await interaction.response.edit_message(
            embed=knight_embed(t(interaction.guild_id, self.user.id, "challenge_intro")),
            view=ChallengeMenuView(self.user, interaction.guild_id),
        )

    async def _stats(self, interaction):
        gid = interaction.guild_id
        uid = self.user.id
        locale = get_locale(gid, uid)
        p = get_player(gid, uid)
        p["rank"] = compute_rank(p)
        unlock_achievements(p)
        persist()
        rank_display = rk_name(p["rank"], locale)
        wins_label = t(gid, uid, "stats_wins")
        pvp_label = t(gid, uid, "stats_pvp_wins")
        rank_label = t(gid, uid, "stats_rank")
        streak_label = "PvP streak" if locale == "en" else "Streak PvP"
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
            view=PostInfoView(self.user, gid),
        )

    async def _board(self, interaction):
        await interaction.response.edit_message(
            embed=knight_embed(t(interaction.guild_id, self.user.id, "lb_pick")),
            view=BoardPickView(self.user, interaction.guild_id),
        )

    async def _chat(self, interaction):
        await interaction.response.edit_message(
            embed=knight_embed(t(interaction.guild_id, self.user.id, "chat_intro")),
            view=ChatView(self.user, interaction.guild_id),
        )

    async def _admin(self, interaction):
        from .admin import AdminView
        await interaction.response.edit_message(
            embed=knight_embed(t(interaction.guild_id, self.user.id, "admin_panel_title")),
            view=AdminView(self.user, interaction.guild_id),
        )

    async def _exit(self, interaction):
        await exit_bot(interaction)


# ============== Helper: lobby + exit buttons ==============
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


class BoardPickView(discord.ui.View):
    def __init__(self, user, guild_id=None):
        super().__init__(timeout=300)
        self.user = user
        gid = guild_id

        pve = discord.ui.Button(
            label=t(gid, user.id, "lb_pve_btn"),
            style=discord.ButtonStyle.danger, row=0,
        )
        async def pve_cb(interaction):
            await _show_board(interaction, self.user, "pve")
        pve.callback = pve_cb
        self.add_item(pve)

        pvp = discord.ui.Button(
            label=t(gid, user.id, "lb_pvp_btn"),
            style=discord.ButtonStyle.primary, row=0,
        )
        async def pvp_cb(interaction):
            await _show_board(interaction, self.user, "pvp")
        pvp.callback = pvp_cb
        self.add_item(pvp)

        _add_lobby_exit(self, user, gid, row=1)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


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
        view=BoardAfterView(user, interaction.guild_id),
    )


class BoardAfterView(discord.ui.View):
    def __init__(self, user, guild_id=None):
        super().__init__(timeout=300)
        self.user = user
        gid = guild_id

        other = discord.ui.Button(
            label=t(gid, user.id, "btn_other_board"),
            style=discord.ButtonStyle.primary, row=0,
        )
        async def other_cb(interaction):
            await interaction.response.edit_message(
                embed=knight_embed(t(interaction.guild_id, self.user.id, "lb_pick")),
                view=BoardPickView(self.user, interaction.guild_id),
            )
        other.callback = other_cb
        self.add_item(other)

        _add_lobby_exit(self, user, gid, row=0)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


class PostInfoView(discord.ui.View):
    def __init__(self, user, guild_id=None):
        super().__init__(timeout=300)
        self.user = user
        _add_lobby_exit(self, user, guild_id, row=0)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


# ============== CHAT ==============
class ChatView(discord.ui.View):
    def __init__(self, user, guild_id=None):
        super().__init__(timeout=300)
        self.user = user
        gid = guild_id

        arena = discord.ui.Button(
            label=t(gid, user.id, "btn_chat_arena"),
            style=discord.ButtonStyle.primary, row=0,
        )
        async def arena_cb(interaction):
            locale = get_locale(interaction.guild_id, self.user.id)
            await interaction.response.edit_message(
                embed=knight_embed(get_lore_text(interaction.guild_id, "arena", locale=locale)),
                view=ChatAfterView(self.user, interaction.guild_id),
            )
        arena.callback = arena_cb
        self.add_item(arena)

        self_btn = discord.ui.Button(
            label=t(gid, user.id, "btn_chat_self"),
            style=discord.ButtonStyle.primary, row=0,
        )
        async def self_cb(interaction):
            locale = get_locale(interaction.guild_id, self.user.id)
            await interaction.response.edit_message(
                embed=knight_embed(get_lore_text(interaction.guild_id, "self", locale=locale)),
                view=ChatAfterView(self.user, interaction.guild_id),
            )
        self_btn.callback = self_cb
        self.add_item(self_btn)

        guide = discord.ui.Button(
            label=t(gid, user.id, "btn_chat_guide"),
            style=discord.ButtonStyle.success, row=1,
        )
        async def guide_cb(interaction):
            await interaction.response.edit_message(
                embed=knight_embed(arena_guide(interaction.guild_id, self.user.id)),
                view=ChatAfterView(self.user, interaction.guild_id),
            )
        guide.callback = guide_cb
        self.add_item(guide)

        _add_lobby_exit(self, user, gid, row=2)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id


class ChatAfterView(discord.ui.View):
    def __init__(self, user, guild_id=None):
        super().__init__(timeout=300)
        self.user = user
        gid = guild_id

        again = discord.ui.Button(
            label=t(gid, user.id, "btn_chat_again"),
            style=discord.ButtonStyle.primary, row=0,
        )
        async def again_cb(interaction):
            await interaction.response.edit_message(
                embed=knight_embed(t(interaction.guild_id, self.user.id, "chat_intro")),
                view=ChatView(self.user, interaction.guild_id),
            )
        again.callback = again_cb
        self.add_item(again)

        _add_lobby_exit(self, user, gid, row=0)

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id
