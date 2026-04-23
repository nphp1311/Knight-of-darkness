"""Entry point for the Hiệp Sĩ Hắc Ám Discord bot (with auto reconnect)."""
import logging
import os

import discord
from discord.ext import commands

from .core import knight_embed, get_lore_text
from .menu import MainView


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("knight-bot")


intents = discord.Intents.default()
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


@bot.tree.command(name="knightofdarkness", description="Triệu hồi 🤺 Hiệp Sĩ Hắc Ám")
async def knightofdarkness(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message(
            embed=knight_embed("💀 Ta chỉ xuất hiện trên chiến trường — không phải trong tin nhắn riêng."),
            ephemeral=True,
        )
        return
    await interaction.response.send_message(
        embed=knight_embed(get_lore_text(interaction.guild_id, "intro")),
        view=MainView(interaction.user, interaction.guild),
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
