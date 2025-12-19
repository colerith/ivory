import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup, Option
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
            await self.cog_ref.refresh_panel(interaction.channel)

# ================= Cog =================
class SelfPanel(discord.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 刷新锁：防止同一频道并发刷新
        self.refresh_locks = {} 
        # 清理锁：标记频道是否正在进行大扫除
        self.cleaning_flags = {}

    async def refresh_panel(self, channel: discord.TextChannel):
        """
        核心刷新逻辑：删除旧Bot消息 -> 发送新面板
        """
        cid = channel.id
        
        # 1. 如果正在进行大扫除，立刻中止，不执行自动刷新
        if self.cleaning_flags.get(cid, False):
            return

        # 2. 如果正在刷新中，简单的并发控制
        if self.refresh_locks.get(cid, False):
            return
        
        self.refresh_locks[cid] = True

        try:
            config = db.get_config(cid)
            if not config: return

            # 3. 扫荡旧消息 (只删除 Bot 发的面板相关消息)
            # 逻辑：查找最近30条，如果是自己发的，删掉。
            try:
                # 提示：history是异步迭代器
                messages_to_delete = []
                async for message in channel.history(limit=30):
                    if message.author.id == self.bot.user.id:
                        messages_to_delete.append(message)
                
                # 批量删除比逐个删除更防炸 (如果有权限)
                if len(messages_to_delete) > 0:
                    if len(messages_to_delete) == 1:
                        await messages_to_delete[0].delete()
                    else:
                        # bulk_delete 只能删除14天内的消息
                        await channel.delete_messages(messages_to_delete)
            except Exception as e:
                # 如果 bulk_delete 失败（比如消息太旧），尝试逐条删除
                print(f"批量删除失败，尝试逐条删除: {e}")
                try:
                    async for message in channel.history(limit=30):
                        if message.author.id == self.bot.user.id:
                            await message.delete()
                except:
                    pass

            # 4. 发送新面板
            embed = discord.Embed(
                title=config["title"],
                description=f"作者：{config['author']} | 版本：{config['version']}\n\n{config['welcome']}\n\n---\n{config['downloads']}",
                color=config["color"]
            )
            view = MainPanelView(str(cid))
            await channel.send(embed=embed, view=view)

        finally:
            self.refresh_locks[cid] = False

    # --- 监听用户消息，实现“置底” ---
    @commands.Cog.listener()
    async def on_message(self, message):
        # 排除机器人自己
        if message.author.id == self.bot.user.id:
            return
        
        # 检查是否是授权频道
        if db.is_authorized(message.channel.id):
            # 触发刷新（refresh_panel 内部会检查 cleaning_flags，如果正在清理则不会执行）
            await self.refresh_panel(message.channel)

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
        # 强制刷新，不考虑 cleaning 锁（既然是手动指令）
        self.cleaning_flags[ctx.channel.id] = False 
        await self.refresh_panel(ctx.channel)

    @panel_group.command(name="新增答疑", description="向面板添加自助问答")
    async def add_qa(self, ctx):
        perm, msg = self.check_perm(ctx)
        if not perm: return await ctx.respond(msg, ephemeral=True)
        await ctx.send_modal(AddQAModal(str(ctx.channel.id), self))

    @panel_group.command(name="清理旧消息", description="[重要] 保留最新N条消息，其余删除，并在结束后刷新面板")
    async def clean_chat(self, ctx, limit: Option(int, "保留的消息数量（例如 50）", default=50)):
        """
        这就是你要的功能：
        1. 开启清理锁 -> 暂停 on_message 的自动刷新
        2. 执行批量删除
        3. 关闭清理锁
        4. 发送最新面板到最底部
        """
        perm, msg = self.check_perm(ctx)
        if not perm: return await ctx.respond(msg, ephemeral=True)

        cid = ctx.channel.id
        
        # 1. 开启锁：此时用户发消息不会触发面板刷新
        self.cleaning_flags[cid] = True
        
        await ctx.respond(f"🧹 正在清理频道，仅保留最近 {limit} 条消息，请稍候...\n(清理期间面板停止自动刷新)", ephemeral=True)
        
        try:
            # 2. 执行清理逻辑
            # 获取所有历史消息 (限制一个较大的数，比如1000，避免卡死)
            # Py-cord 的 purge/delete_messages 逻辑
            # 我们需要先手动筛选出要保留的 top N
            
            # 收集所有消息
            messages = await ctx.channel.history(limit=1000).flatten()
            
            if len(messages) > limit:
                # 要删除的消息 = 总消息 - 前N条
                # messages[limit:] 就是旧消息 (history 默认是按时间倒序，[0]是最新的)
                to_delete = messages[limit:]
                
                # 分批删除，Discord 限制一次删100条
                # 并且不能删超过14天的，这里做个简单处理
                
                # 过滤掉超过14天的（这里简化处理，如果报错就跳过）
                # 实际上 delete_messages 会自动忽略旧消息或报错，我们需要 try catch
                
                # 分块处理，每块100条
                chunk_size = 100
                for i in range(0, len(to_delete), chunk_size):
                    batch = to_delete[i:i + chunk_size]
                    try:
                        await ctx.channel.delete_messages(batch)
                        await asyncio.sleep(1) # 避免速率限制
                    except discord.HTTPException:
                        # 如果批量删除失败（通常是因为包含旧消息），尝试逐条删
                        # 或者为了速度，干脆就不删太旧的了
                        pass
            
            await ctx.respond("✅ 清理完成！正在恢复面板...", ephemeral=True)

        except Exception as e:
            await ctx.respond(f"❌ 清理过程中遇到错误: {e}", ephemeral=True)
        
        finally:
            # 3. 关闭锁
            self.cleaning_flags[cid] = False
            
            # 4. 强制执行一次刷新，确保面板在最下面
            await self.refresh_panel(ctx.channel)

def setup(bot):
    bot.add_cog(SelfPanel(bot))
