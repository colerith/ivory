"""Persistent login and IDENTIFY protection for a single deployment."""
import json
import logging
import os
from pathlib import Path
import time

log = logging.getLogger(__name__)
MIN_INTERVAL = 120
COOLDOWN = 900

class ReconnectBlocked(RuntimeError):
    pass

class ConnectionGuard:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory / 'connections.json'
        self.lock_file = None

    def __enter__(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock_file = (self.directory / 'bot.lock').open('a+b')
        self.lock_file.seek(0, 2)
        if self.lock_file.tell() == 0:
            self.lock_file.write(b'0')
            self.lock_file.flush()
        self.lock_file.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lock_file.close()
            raise RuntimeError('已有机器人进程运行，拒绝重复连接。') from None
        return self

    def __exit__(self, *args):
        self.lock_file.close()

    def read(self):
        if not self.path.exists():
            return {}
        state = json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(state, dict) or any(
            type(v) not in (int, float) or not 0 <= v < float('inf')
            for v in state.values()
        ):
            raise ValueError('连接保护记录损坏，请检查 .runtime/connections.json')
        return state

    def save(self, state):
        temporary = self.path.with_suffix('.tmp')
        with temporary.open('w', encoding='utf-8') as handle:
            json.dump(state, handle)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(self.path)

    def before_login(self):
        state = self.read()
        deadline = max(state.get('login', 0) + MIN_INTERVAL,
                       state.get('identify', 0) + MIN_INTERVAL,
                       state.get('blocked_until', 0))
        while deadline > time.time():
            delay = deadline - time.time()
            log.warning('连接保护：等待 %.0f 秒后才允许登录。', delay)
            time.sleep(delay)
        state['login'] = time.time()
        self.save(state)

    def before_identify(self):
        state = self.read()
        now = time.time()
        if (now < state.get('identify', 0) + MIN_INTERVAL
                or now < state.get('blocked_until', 0)):
            state['blocked_until'] = max(state.get('blocked_until', 0), now + COOLDOWN)
            self.save(state)
            # Sleeping here would hit Pycord's 60-second handshake timeout.
            raise ReconnectBlocked('短时间重复 IDENTIFY，已熔断；15 分钟内禁止重新登录。')
        state['identify'] = now
        self.save(state)
        log.info('允许建立新的 Discord 会话 (IDENTIFY)。')
