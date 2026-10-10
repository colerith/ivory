import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, mock_open, patch

# Import without reading or creating real bot configuration.
with patch('builtins.open', mock_open(read_data='{"channels": {}}')):
    panel = importlib.import_module('cogs.panel')


class StartupPanelTests(unittest.IsolatedAsyncioTestCase):
    def make_cog(self):
        bot = Mock()
        bot.fetch_channel = AsyncMock()
        cog = panel.SelfPanel(bot)
        cog.register_persistent_views = Mock()
        cog.run_refresh_logic = AsyncMock()
        return cog

    async def test_once_per_process_and_all_authorized_channels(self):
        cog = self.make_cog()
        with patch.object(panel.db, 'data', {'channels': {'1': {}, '2': {}}}), \
                patch.object(panel.asyncio, 'sleep', new_callable=AsyncMock) as sleep:
            await cog.on_ready()
            await cog.on_ready()
        self.assertEqual(cog.run_refresh_logic.await_count, 2)
        sleep.assert_awaited_once_with(2)

    async def test_failure_does_not_block_next_channel(self):
        cog = self.make_cog()
        cog.run_refresh_logic.side_effect = [RuntimeError('no permission'), None]
        with patch.object(panel.db, 'data', {'channels': {'1': {}, '2': {}}}), \
                patch.object(panel.asyncio, 'sleep', new_callable=AsyncMock), \
                self.assertLogs(panel.log, level='ERROR'):
            await cog.on_ready()
        self.assertEqual(cog.run_refresh_logic.await_count, 2)

    async def test_uncached_channel_is_fetched(self):
        cog = self.make_cog()
        cog.bot.get_channel.return_value = None
        with patch.object(panel.db, 'data', {'channels': {'1': {}}}):
            await cog.on_ready()
        cog.bot.fetch_channel.assert_awaited_once_with(1)
        cog.run_refresh_logic.assert_awaited_once_with(cog.bot.fetch_channel.return_value)

    async def test_concurrent_ready_does_not_duplicate_refresh(self):
        cog = self.make_cog()
        async def refresh(channel):
            await cog.on_ready()
        cog.run_refresh_logic.side_effect = refresh
        with patch.object(panel.db, 'data', {'channels': {'1': {}}}):
            await cog.on_ready()
        cog.run_refresh_logic.assert_awaited_once()

    async def test_refresh_replaces_old_panel_and_saves_new_id(self):
        cog = panel.SelfPanel(Mock())
        channel = Mock(id=1)
        old_message = Mock()
        old_message.delete = AsyncMock()
        channel.fetch_message = AsyncMock(return_value=old_message)
        channel.send = AsyncMock(return_value=SimpleNamespace(id=22))
        config = dict(panel.DEFAULT_TEMPLATE, last_panel_id=11)
        with patch.object(panel.db, 'get_config', return_value=config), \
                patch.object(panel.db, 'set_config') as save:
            await cog.run_refresh_logic(channel)
        channel.fetch_message.assert_awaited_once_with(11)
        old_message.delete.assert_awaited_once()
        channel.send.assert_awaited_once()
        self.assertEqual(save.call_args.args[1]['last_panel_id'], 22)
        self.assertFalse(cog.refresh_locks[1])
