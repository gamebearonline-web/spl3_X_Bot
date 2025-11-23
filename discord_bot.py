import discord
from discord.ext import commands
import requests
import io
import os

# ===============================
# 設定
# ===============================

TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Render 環境変数から読み込み

IMAGE_URL = "https://raw.githubusercontent.com/gamebearonline-web/spl3_X_Bot/main/Thumbnail/Thumbnail.png"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


# ===============================
# Slash Command
# ===============================
@bot.tree.command(name="schedule", description="最新のスプラ3画像を送信します")
async def schedule(interaction: discord.Interaction):

    await interaction.response.defer()  # 読み込みマークを出す（2秒対策）

    try:
        img_bytes = requests.get(IMAGE_URL, timeout=10).content
        file = discord.File(io.BytesIO(img_bytes), filename="schedule.png")
    except Exception as e:
        await interaction.followup.send(f"画像取得に失敗しました：{e}")
        return

    await interaction.followup.send(
        content="🦑【スプラトゥーン3】最新スケジュールです！",
        file=file
    )


# ===============================
# BOT 起動
# ===============================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()  # Slash Command をサーバーへ同期
    print("Slash commands synced")


bot.run(TOKEN)
