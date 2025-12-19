import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
import json
import os
import asyncio
import re

DATA_FILE = "data.json"
SUPER_ADMIN_ID = 1353777207042113576

# 默认模板
DEFAULT_TEMPLATE = {
    "manager_id": 0,
    "color": 0xffc0cb,
    "title": "🛒预设自助小餐车",
    "author": "未知",
    "version": "未知",
    "welcome": "> 欢迎使用自助答疑系统\n\n贴主可使用命令自行配置\n\n请点击下方按钮开始使用。",
    "downloads": "## ⬇️下载直达\n暂无链接",
    "qa_list": [] 
}

class DataManager:
    def __init__(self):
        self.data = {"channels": {}}
        self.load_data()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except:
                self.save_data()
        else:
            self.save_data()

    def save_data(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def get_config(self, channel_id):
        return self.data["channels"].get(str(channel_id))

    def set_config(self, channel_id, config):
        self.data["channels"][str(channel_id)] = config
        self.save_data()

    def is_authorized(self, channel_id):
        return str(channel_id) in self.data["channels"]

db = DataManager()

# ================= UI Views =================
class MainPanelView(discord.ui.View):
    def __init__(self, channel_id_str):
        super().__init__(timeout=None)
        self.channel_id_str = channel_id_str

    @discord.ui.button(label="🗳️ 自助答疑", style=discord.ButtonStyle.primary, custom_id="ivory_qa_btn")
    async def callback(self, button, interaction: discord.Interaction):
        view = QADropdownView(str(interaction.channel_id))
        config = db.get_config(str(interaction.channel_id))
        if not config or not config["qa_list"]:
             await interaction.response.send_message("暂无自助答疑内容。", ephemeral=True)
             return
        await interaction.response.send_message("请选择您遇到的问题：", view=view, ephemeral=True)

class QADropdownView(discord.ui.View):
    def __init__(self, channel_id_str):
        super().__init__(timeout=180)
        self.add_item(QASelect(channel_id_str))

class QASelect(discord.ui.Select):
    def __init__(self, channel_id_str):
        self.channel_id_str = channel_id_str
        config = db.get_config(channel_id_str)
        qa_list = config["qa_list"] if config else []
        options = []
        for idx, item in enumerate(qa_list[:25]): 
            label = item["q"][:95]
            options.append(discord.SelectOption(label=label, value=str(idx)))
        super().__init__(placeholder="🔍 点击这里选择问题...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        config = db.get_config(self.channel_id_str)
        if config and 0 <= idx < len(config["qa_list"]):
            qa = config["qa_list"][idx]
            raw_text = qa['a']
            md_images = re.findall(r'!\[.*?\]\((https?://.*?\.(?:png|jpg|jpeg|gif|webp).*?)\)', raw_text, re.IGNORECASE)
            clean_text = re.sub(r'!\[.*?\]\(https?://.*?\)', '', raw_text).strip() or "（查看图片）"
            
            embed = discord.Embed(title=f"Q: {qa['q']}", description=clean_text, color=config.get("color", 0xffc0cb))
            if md_images: embed.set_image(url=md_images[0])
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("未找到该内容。", ephemeral=True)

# ================= Modals =================
class AddQAModal(discord.ui.Modal):
    def __init__(self, channel_id_str, cog_ref):
        super().__init__(title="新增自助答疑")
        self.channel_id_str = channel_id_str
        self.cog_ref = cog_ref
        self.add_item(discord.ui.InputText(label="问题", placeholder="输入标题..."))
        self.add_item(discord.ui.InputText(label="回答", placeholder="输入内容...", style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        config = db.get_config(self.channel_id_str)
        if config:
            config["qa_list"].append({"q": self.children[0].value, "a": self.children[1].value})
            db.set_config(self.channel_id_str, config)
            await interaction.response.send_message(f"✅ 已添加", ephemeral=True)
            await self.cog_ref.run_refresh_logic(interaction.channel)

# ================= Cog =================
class SelfPanel(discord.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduled_tasks = {}
        self.refresh_locks = {}

    async def run_refresh_logic(self, channel: discord.TextChannel):
        """
        真正的刷新逻辑（执行删除和重发）
        【修改重点】：只删除被识别为“面板”的消息
        """
        cid = channel.id
        
        if self.refresh_locks.get(cid, False):
            return
        self.refresh_locks[cid] = True

        try:
            config = db.get_config(cid)
            if not config: return

            # 1. 精准扫荡旧消息
            try:
                messages_to_delete = []
                # 扫描最近30条
                async for message in channel.history(limit=30):
                    # 必须是机器人自己发的
                    if message.author.id != self.bot.user.id:
                        continue
                    
                    is_panel_message = False

                    # 【判断条件 A】: Embed 标题匹配
                    # 如果消息有 Embed，且标题和当前配置的面板标题一样，判定为旧面板
                    if message.embeds and message.embeds[0].title == config["title"]:
                        is_panel_message = True

                    # 【判断条件 B】: 按钮组件匹配 (更稳健)
                    # 检查消息里是否有 custom_id="ivory_qa_btn" 的按钮
                    # 只有面板有这个按钮，QA回复是没按钮的
                    if not is_panel_message and message.components:
                        for component in message.components:
                            if isinstance(component, discord.ActionRow):
                                for child in component.children:
                                    if hasattr(child, "custom_id") and child.custom_id == "ivory_qa_btn":
                                        is_panel_message = True
                                        break
                            if is_panel_message: break
                    
                    # 只有被判定为面板消息，才加入删除列表
                    if is_panel_message:
                        messages_to_delete.append(message)
                
                if messages_to_delete:
                    if len(messages_to_delete) == 1:
                        await messages_to_delete[0].delete()
                    else:
                        await channel.delete_messages(messages_to_delete)
            
            except Exception as e:
                print(f"清理旧面板异常: {e}")

            # 2. 发送新面板
            embed = discord.Embed(
                title=config["title"],
                description=f"作者：{config['author']} | 版本：{config['version']}\n\n{config['welcome']}\n\n---\n{config['downloads']}",
                color=config["color"]
            )
            view = MainPanelView(str(cid))
            await channel.send(embed=embed, view=view)

        finally:
            self.refresh_locks[cid] = False

    async def schedule_refresh(self, channel: discord.TextChannel):
        cid = channel.id
        if cid in self.scheduled_tasks:
            task = self.scheduled_tasks[cid]
            if not task.done():
                task.cancel()
        
        async def wait_and_run():
            try:
                await asyncio.sleep(4)
                await self.run_refresh_logic(channel)
            except asyncio.CancelledError:
                pass
            finally:
                if cid in self.scheduled_tasks and self.scheduled_tasks[cid] == asyncio.current_task():
                    del self.scheduled_tasks[cid]

        self.scheduled_tasks[cid] = asyncio.create_task(wait_and_run())

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return
        if db.is_authorized(message.channel.id):
            await self.schedule_refresh(message.channel)

    # --- 命令组 ---
    panel_group = SlashCommandGroup("自助面板", "原有的小餐车面板管理")

    def check_perm(self, ctx):
        cid = str(ctx.channel.id)
        config = db.get_config(cid)
        if not config: return False, "❌ 此频道未授权"
        if ctx.author.id == SUPER_ADMIN_ID or ctx.author.id == config["manager_id"]:
            return True, None
        return False, "❌ 无权限"

    @panel_group.command(name="授权频道", description="[超管] 授权当前频道")
    async def auth_channel(self, ctx, manager: discord.User):
        if ctx.author.id != SUPER_ADMIN_ID:
            return await ctx.respond("❌ 仅超级管理员可用", ephemeral=True)
        
        new_config = DEFAULT_TEMPLATE.copy()
        new_config["manager_id"] = manager.id
        db.set_config(ctx.channel.id, new_config)
        await ctx.respond(f"✅ 授权成功，负责人: {manager.mention}", ephemeral=True)

    @panel_group.command(name="初始化", description="手动刷新/重发面板")
    async def setup_panel(self, ctx):
        perm, msg = self.check_perm(ctx)
        if not perm: return await ctx.respond(msg, ephemeral=True)
        await ctx.respond("🔄 正在刷新...", ephemeral=True)
        await self.run_refresh_logic(ctx.channel)

    @panel_group.command(name="新增答疑", description="向面板添加自助问答")
    async def add_qa(self, ctx):
        perm, msg = self.check_perm(ctx)
        if not perm: return await ctx.respond(msg, ephemeral=True)
        await ctx.send_modal(AddQAModal(str(ctx.channel.id), self))

def setup(bot):
    bot.add_cog(SelfPanel(bot))
