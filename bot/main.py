"""Entry point for the Hiệp Sĩ Hắc Ám Discord bot (with auto reconnect)."""
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

from .core import knight_embed, get_lore_text
from .combat import end_pvp_in_channel, get_active_pvp
from .menu import MainView
from .storage import get_locale


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("knight-bot")


intents = discord.Intents.default()
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


@bot.event
async def on_ready():
    log.info("Bot logged in as %s (id=%s)", bot.user, bot.user.id if bot.user else "?")
    try:
        synced = await bot.tree.sync()
        log.info("Synced %d slash commands.", len(synced))
    except Exception as e:
        log.exception("Failed to sync slash commands: %s", e)


@bot.event
async def on_disconnect():
    log.warning("Bot disconnected from gateway — discord.py sẽ tự reconnect.")


@bot.event
async def on_resumed():
    log.info("Bot session resumed (reconnected).")


@bot.tree.command(
    name="end_pvp",
    description="(Admin) Hủy ngay trận PvP đang diễn ra trong kênh hiện tại.",
)
@app_commands.default_permissions(administrator=True)
async def end_pvp(interaction: discord.Interaction):
    # Server-side guard: even if Discord exposes the command, only administrators may run it.
    if interaction.guild is None or interaction.user is None:
        await interaction.response.send_message(
            embed=knight_embed("⚠️ Lệnh này chỉ dùng được trong server."),
            ephemeral=True,
        )
        return
    member = interaction.user if isinstance(interaction.user, discord.Member) else None
    if member is None or not member.guild_permissions.administrator:
        await interaction.response.send_message(
            embed=knight_embed("⛔ Chỉ **quản trị viên** mới được dùng lệnh này."),
            ephemeral=True,
        )
        return

    # If the admin runs the command from inside the private duel thread, the
    # channel id we get is the thread's; resolve back to the parent channel.
    target_channel_id = interaction.channel_id
    chan = interaction.channel
    if isinstance(chan, discord.Thread) and chan.parent_id is not None:
        target_channel_id = chan.parent_id

    state = get_active_pvp(interaction.guild_id, target_channel_id)
    if state is None:
        await interaction.response.send_message(
            embed=knight_embed("ℹ️ Hiện không có trận PvP nào đang diễn ra trong kênh này."),
            ephemeral=True,
        )
        return

    await end_pvp_in_channel(interaction.guild_id, target_channel_id)
    u1 = state.get("u1")
    u2 = state.get("u2")
    names = ""
    if u1 is not None and u2 is not None:
        names = f"\n\n⚔️ {u1.mention} vs {u2.mention}"
    await interaction.response.send_message(
        embed=knight_embed(
            "🛑 **Đã gửi tín hiệu hủy trận đấu PvP đang diễn ra.**\n"
            "Trận đấu sẽ kết thúc sau lượt hiện tại — không ghi nhận thắng/thua, "
            "phòng đấu riêng sẽ được dọn dẹp ngay sau đó." + names
        ),
        ephemeral=True,
    )


@bot.tree.command(name="knightofdarkness", description="Triệu hồi 🤺 Hiệp Sĩ Hắc Ám")
async def knightofdarkness(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message(
            embed=knight_embed("💀 Ta chỉ xuất hiện trên chiến trường — không phải trong tin nhắn riêng."),
            ephemeral=True,
        )
        return
    locale = get_locale(interaction.guild_id, interaction.user.id)
    await interaction.response.send_message(
        embed=knight_embed(get_lore_text(interaction.guild_id, "intro", locale=locale)),
        view=MainView(interaction.user, interaction.guild),
        ephemeral=True,
    )


def main():
    token = (
        os.environ.get("DISCORD_BOT_TOKEN")
        or os.environ.get("TOKEN")
        or os.environ.get("BOT_TOKEN")
    )
    if not token:
        raise SystemExit(
            "Bot token not found. Hãy set 1 trong các biến môi trường: "
            "DISCORD_BOT_TOKEN / TOKEN / BOT_TOKEN trên Railway → tab Variables."
        )
    log.info("Token loaded (length=%d). Connecting to Discord...", len(token))
    # reconnect=True (mặc định) — discord.py sẽ tự kết nối lại khi rớt mạng / Discord restart shard.
    bot.run(token, log_handler=None, reconnect=True)


if __name__ == "__main__":
    main()
