import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

import discord
from dotenv import load_dotenv
from connection_guard import ConnectionGuard, ReconnectBlocked

BASE_DIR = Path(__file__).resolve().parent
log = logging.getLogger(__name__)

class GuardedBot(discord.Bot):
    def __init__(self, guard, **kwargs):
        self.connection_guard = guard
        super().__init__(**kwargs)

    async def before_identify_hook(self, shard_id, *, initial=False):
        self.connection_guard.before_identify()
        await super().before_identify_hook(shard_id, initial=initial)

    async def on_ready(self):
        log.info('已登录为 %s', self.user)

    async def on_disconnect(self):
        log.warning('Discord 连接断开，交由 Pycord 尝试恢复会话。')

    async def on_resumed(self):
        log.info('Discord 会话已恢复 (RESUME)。')


def main():
    os.chdir(BASE_DIR)
    load_dotenv(BASE_DIR / '.env')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        handlers=[logging.StreamHandler(), RotatingFileHandler(
            BASE_DIR / 'bot.log', maxBytes=2_000_000, backupCount=3, encoding='utf-8')],
    )
    token = os.getenv('BOT_TOKEN', '').strip()
    if not token:
        log.error('未找到 BOT_TOKEN，请检查 .env 文件。')
        return
    try:
        with ConnectionGuard(BASE_DIR / '.runtime') as guard:
            guard.before_login()
            intents = discord.Intents.default()
            intents.members = True
            bot = GuardedBot(guard, intents=intents)
            for path in sorted((BASE_DIR / 'cogs').glob('*.py')):
                if path.stem != '__init__':
                    bot.load_extension(f'cogs.{path.stem}')
                    log.info('已加载插件: %s', path.name)
            bot.run(token, reconnect=True)
    except ReconnectBlocked as exc:
        log.error('%s 请检查网络和部署重启日志后重新启动。', exc)
    except discord.LoginFailure:
        log.error('Token 无效或已被重置，请在开发者后台获取新 Token 并更新 .env。')
    except discord.PrivilegedIntentsRequired:
        log.error('请在 Discord 开发者后台启用 Server Members Intent 后重新启动。')
    except Exception:
        log.exception('机器人停止；请检查错误后重新启动。')

if __name__ == '__main__':
    main()
