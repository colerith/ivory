import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from connection_guard import ConnectionGuard, ReconnectBlocked
from main import GuardedBot
import discord


class ConnectionGuardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.directory.cleanup)
        self.guard = ConnectionGuard(self.directory.name)

    def test_duplicate_process_and_release(self):
        with self.guard:
            with self.assertRaises(RuntimeError):
                with ConnectionGuard(self.directory.name):
                    pass
        with ConnectionGuard(self.directory.name):
            pass

    def test_identify_circuit_survives_restart(self):
        with patch('connection_guard.time.time', return_value=10000):
            self.guard.before_identify()
        with patch('connection_guard.time.time', return_value=10001):
            with self.assertRaises(ReconnectBlocked):
                ConnectionGuard(self.directory.name).before_identify()
        self.assertEqual(self.guard.read()['blocked_until'], 10901)
        with patch('connection_guard.time.time', return_value=10901):
            self.guard.before_identify()

    def test_restart_waits_before_any_login(self):
        self.guard.save({'login': 10000})
        with patch('connection_guard.time.time', side_effect=[10001, 10001, 10120, 10120]), \
                patch('connection_guard.time.sleep') as sleep:
            self.guard.before_login()
        sleep.assert_called_once_with(119)
        self.assertEqual(self.guard.read()['login'], 10120)

    def test_restart_respects_circuit_cooldown(self):
        self.guard.save({'blocked_until': 10900})
        with patch('connection_guard.time.time', side_effect=[10000, 10000, 10900, 10900]), \
                patch('connection_guard.time.sleep') as sleep:
            self.guard.before_login()
        sleep.assert_called_once_with(900)

    def test_corrupt_state_fails_closed(self):
        for value in ('broken', '[]', '{"identify": "bad"}', '{"identify": NaN}'):
            self.guard.path.write_text(value, encoding='utf-8')
            with self.assertRaises(ValueError):
                self.guard.before_identify()

    def test_pycord_hook_blocks_even_initial_identify(self):
        async def scenario():
            bot = GuardedBot(self.guard, intents=discord.Intents.default())
            try:
                await bot.before_identify_hook(None, initial=True)
                with self.assertRaises(ReconnectBlocked):
                    await bot.before_identify_hook(None, initial=True)
            finally:
                await bot.close()
        asyncio.run(scenario())


if __name__ == '__main__':
    unittest.main()
