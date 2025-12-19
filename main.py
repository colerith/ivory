import discord
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# 初始化 Bot
bot = discord.Bot()

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print("-------------------------")

# 自动加载 cogs 文件夹下的所有 py 文件
if __name__ == "__main__":
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                bot.load_extension(f'cogs.{filename[:-3]}')
                print(f"⚙️  已加载插件: {filename}")
            except Exception as e:
                print(f"❌ 加载插件 {filename} 失败: {e}")

    if not BOT_TOKEN:
        print("❌ 未找到 Token，请检查 .env 文件")
    else:
        bot.run(BOT_TOKEN)
