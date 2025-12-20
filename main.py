# main.py

import discord
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# 1. 创建默认意图对象
intents = discord.Intents.default()
# 2. 必须显式开启成员意图 (这就对应你在开发者后台开的那个开关)
intents.members = True 

# 3. 初始化 Bot 时传入 intents
bot = discord.Bot(intents=intents)
# ================================================

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print("-------------------------")

if __name__ == "__main__":
    # 加载 cogs
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and filename != "__init__.py":
            try:
                bot.load_extension(f'cogs.{filename[:-3]}')
                print(f"⚙️  已加载插件: {filename}")
            except Exception as e:
                print(f"❌ 加载插件 {filename} 失败: {e}")

    if not BOT_TOKEN:
        print("❌ 未找到 Token，请检查 .env 文件")
    else:
        bot.run(BOT_TOKEN)
