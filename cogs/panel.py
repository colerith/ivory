import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup, Option
import json
import os
import asyncio
import re

DATA_FILE = "data.json"
SUPER_ADMIN_ID = 1353777207042113576

DEFAULT_TEMPLATE = {
    "manager_id": 0,
    "color": 0xffc0cb,
    "title": "🛒预设自助小餐车",
    "author": "未知",
    "version": "未知",
    "welcome": "> 欢迎使用自助答疑系统\n\n贴主可使用命令自行配置\n\n请点击下方按钮开始使用。",
    "downloads": "## ⬇️下载直达\n暂无链接",
    "qa_list": [],
    "sub_role_ids": []
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
        config = self.data["channels"].get(str(channel_id))
        if config and "sub_role_ids" not in config:
            config["sub_role_ids"] = []
        return config

    def set_config(self, channel_id, config):
        self.data["channels"][str(channel_id)] = config
        self.save_data()
    
    # 【新增】删除配置的方法
    def delete_config(self, channel_id):
        if str(channel_id) in self.data["channels"]:
            del self.data["channels"][str(channel_id)]
            self.save_data()
            return True
        return False

    def is_authorized(self, channel_id):
        return str(channel_id) in self.data["channels"]

db = DataManager()

# ================= UI Views (主面板与展示) =================
class MainPanelView(discord.ui.View):
    def __init__(self, channel_id_str):
        super().__init__(timeout=None)
        self.channel_id_str = channel_id_str

    @discord.ui.button(label="🗳️ 自助答疑", style=discord.ButtonStyle.primary, custom_id="ivory_qa_btn", row=0)
    async def qa_callback(self, button, interaction: discord.Interaction):
        view = QADropdownView(str(interaction.channel_id))
        config = db.get_config(str(interaction.channel_id))
        if not config or not config["qa_list"]:
             await interaction.response.send_message("暂无自助答疑内容。", ephemeral=True)
             return
        await interaction.response.send_message("请选择您遇到的问题：", view=view, ephemeral=True)

    @discord.ui.button(label="🔔 订阅更新", style=discord.ButtonStyle.success, custom_id="ivory_sub_btn", row=0)
    async def sub_callback(self, button, interaction: discord.Interaction):
        config = db.get_config(str(interaction.channel_id))
        if not config: return

        role_ids = config.get("sub_role_ids", [])
        if not role_ids:
            return await interaction.response.send_message("⚠️ 本频道尚未配置订阅身份组，请联系负责人设置。", ephemeral=True)

        guild = interaction.guild
        member = interaction.user
        
        added_roles = []
        already_has = True

        for rid in role_ids:
            role = guild.get_role(rid)
            if role:
                if role not in member.roles:
                    try:
                        await member.add_roles(role, reason="自助面板订阅")
                        added_roles.append(role.name)
                        already_has = False
                    except discord.Forbidden:
                        return await interaction.response.send_message(f"❌ 无法分配身份组 `{role.name}`，Bot 权限不足。", ephemeral=True)
        
        if already_has:
            await interaction.response.send_message("✅ 您已经订阅过了（已拥有所有相关身份组）。", ephemeral=True)
        else:
            roles_str = "`, `".join(added_roles)
            await interaction.response.send_message(f"✅ 订阅成功！已为您添加：`{roles_str}`", ephemeral=True)

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

# ================= 编辑功能组件 =================

class EditQAView(discord.ui.View):
    def __init__(self, channel_id_str, cog_ref):
        super().__init__(timeout=60)
        self.add_item(EditQASelect(channel_id_str, cog_ref))

class EditQASelect(discord.ui.Select):
    def __init__(self, channel_id_str, cog_ref):
        self.channel_id_str = channel_id_str
        self.cog_ref = cog_ref
        
        config = db.get_config(channel_id_str)
        qa_list = config["qa_list"] if config else []
        
        options = []
        for idx, item in enumerate(qa_list[:25]):
            label = item["q"][:95]
            options.append(discord.SelectOption(label=label, value=str(idx), emoji="📝"))
            
        super().__init__(placeholder="👇 请选择要修改的答疑...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        config = db.get_config(self.channel_id_str)
        if config and 0 <= idx < len(config["qa_list"]):
            item = config["qa_list"][idx]
            modal = EditQAModal(self.channel_id_str, self.cog_ref, idx, item["q"], item["a"])
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("❌ 该条目似乎已被删除。", ephemeral=True)

class EditQAModal(discord.ui.Modal):
    def __init__(self, channel_id_str, cog_ref, idx, old_q, old_a):
        super().__init__(title="修改答疑条目")
        self.channel_id_str = channel_id_str
        self.cog_ref = cog_ref
        self.idx = idx
        self.add_item(discord.ui.InputText(label="问题", value=old_q, placeholder="输入新的标题..."))
        self.add_item(discord.ui.InputText(label="回答", value=old_a, placeholder="输入新的内容...", style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        config = db.get_config(self.channel_id_str)
        if config:
            new_q = self.children[0].value
            new_a = self.children[1].value
            if 0 <= self.idx < len(config["qa_list"]):
                config["qa_list"][self.idx] = {"q": new_q, "a": new_a}
                db.set_config(self.channel_id_str, config)
                await interaction.response.send_message(f"✅ 已成功修改问题：`{new_q}`", ephemeral=True)
                await self.cog_ref.run_refresh_logic(interaction.channel)
            else:
                await interaction.response.send_message("❌ 修改失败，该条目可能已被删除。", ephemeral=True)

class ConfigSubRoleView(discord.ui.View):
    def __init__(self, channel_id_str):
        super().__init__(timeout=60)
        self.channel_id_str = channel_id_str
    
    @discord.ui.role_select(placeholder="选择点击按钮后要分配的身份组（可多选）", min_values=0, max_values=5)
    async def callback(self, select, interaction: discord.Interaction):
        roles = select.values 
        role_ids = [r.id for r in roles]
        config = db.get_config(self.channel_id_str)
        if config:
            config["sub_role_ids"] = role_ids
            db.set_config(self.channel_id_str, config)
            names = [r.name for r in roles]
            msg = f"✅ 已设置订阅身份组：`{', '.join(names)}`" if names else "✅ 已清空订阅身份组。"
            await interaction.response.send_message(msg, ephemeral=True)

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

class EditProfileModal(discord.ui.Modal):
    def __init__(self, config, cog_ref):
        super().__init__(title="编辑面板外观")
        self.channel_id_str = str(config.get("channel_id", 0)) 
        self.cog_ref = cog_ref
        self.add_item(discord.ui.InputText(label="标题", value=config["title"]))
        self.add_item(discord.ui.InputText(label="作者名", value=config["author"]))
        self.add_item(discord.ui.InputText(label="版本号", value=config["version"]))
        hex_color = "#{:06x}".format(config["color"])
        self.add_item(discord.ui.InputText(label="颜色 (Hex格式)", value=hex_color, min_length=7, max_length=7))

    async def callback(self, interaction: discord.Interaction):
        config = db.get_config(interaction.channel.id)
        if config:
            config["title"] = self.children[0].value
            config["author"] = self.children[1].value
            config["version"] = self.children[2].value
            try:
                color_int = int(self.children[3].value.replace("#", ""), 16)
            except:
                color_int = 0xffc0cb
            config["color"] = color_int
            db.set_config(str(interaction.channel.id), config)
            await interaction.response.send_message("✅ 外观信息已更新。", ephemeral=True)
            await self.cog_ref.run_refresh_logic(interaction.channel)

class EditContentModal(discord.ui.Modal):
    def __init__(self, config, cog_ref):
        super().__init__(title="编辑面板正文")
        self.cog_ref = cog_ref
        self.add_item(discord.ui.InputText(label="欢迎语 (支持MD)", value=config["welcome"], style=discord.InputTextStyle.long))
        self.add_item(discord.ui.InputText(label="下载链接区 (支持MD)", value=config["downloads"], style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        config = db.get_config(str(interaction.channel.id))
        if config:
            config["welcome"] = self.children[0].value
            config["downloads"] = self.children[1].value
            db.set_config(str(interaction.channel.id), config)
            await interaction.response.send_message("✅ 正文内容已更新。", ephemeral=True)
            await self.cog_ref.run_refresh_logic(interaction.channel)

class DeleteQAView(discord.ui.View):
    def __init__(self, channel_id_str, cog_ref):
        super().__init__(timeout=60)
        self.add_item(DeleteQASelect(channel_id_str, cog_ref))

class DeleteQASelect(discord.ui.Select):
    def __init__(self, channel_id_str, cog_ref):
        self.channel_id_str = channel_id_str
        self.cog_ref = cog_ref
        config = db.get_config(channel_id_str)
        qa_list = config["qa_list"] if config else []
        options = []
        for idx, item in enumerate(qa_list[:25]):
            label = item["q"][:95]
            options.append(discord.SelectOption(label=label, value=str(idx), emoji="🗑️"))
        super().__init__(placeholder="选择要删除的问题...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        config = db.get_config(self.channel_id_str)
        if config and 0 <= idx < len(config["qa_list"]):
            removed = config["qa_list"].pop(idx)
            db.set_config(self.channel_id_str, config)
            await interaction.response.send_message(f"✅ 已删除：{removed['q']}", ephemeral=True)
            await self.cog_ref.run_refresh_logic(interaction.channel)
        else:
            await interaction.response.send_message("删除失败。", ephemeral=True)

# ================= Cog =================
class SelfPanel(discord.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduled_tasks = {}
        self.refresh_locks = {}

    async def run_refresh_logic(self, channel: discord.TextChannel):
        cid = channel.id
        if self.refresh_locks.get(cid, False): return
        self.refresh_locks[cid] = True
        try:
            config = db.get_config(cid)
            if not config: return

            try:
                messages_to_delete = []
                # 扫描历史消息寻找旧面板
                async for message in channel.history(limit=30):
                    if message.author.id != self.bot.user.id: continue
                    is_panel_message = False
                    # 通过标题判断
                    if message.embeds and message.embeds[0].title == config["title"]:
                        is_panel_message = True
                    # 通过按钮ID判断
                    if not is_panel_message and message.components:
                        for component in message.components:
                            if isinstance(component, discord.ActionRow):
                                for child in component.children:
                                    if hasattr(child, "custom_id") and child.custom_id in ["ivory_qa_btn", "ivory_sub_btn"]:
                                        is_panel_message = True
                                        break
                            if is_panel_message: break
                    if is_panel_message:
                        messages_to_delete.append(message)
                
                if messages_to_delete:
                    if len(messages_to_delete) == 1:
                        await messages_to_delete[0].delete()
                    else:
                        await channel.delete_messages(messages_to_delete)
            except Exception as e:
                print(f"清理旧面板异常: {e}")

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
            if not task.done(): task.cancel()
        
        async def wait_and_run():
            try:
                await asyncio.sleep(4)
                await self.run_refresh_logic(channel)
            except asyncio.CancelledError: pass
            finally:
                if cid in self.scheduled_tasks and self.scheduled_tasks[cid] == asyncio.current_task():
                    del self.scheduled_tasks[cid]
        self.scheduled_tasks[cid] = asyncio.create_task(wait_and_run())

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.bot.user.id: return
        if db.is_authorized(message.channel.id):
            await self.schedule_refresh(message.channel)

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

    # 【新增】取消授权功能
    @panel_group.command(name="取消授权", description="[超管] 移除本频道的授权并清理面板")
    async def revoke_channel(self, ctx):
        # 1. 权限检查
        if ctx.author.id != SUPER_ADMIN_ID:
            return await ctx.respond("❌ 仅超级管理员可用", ephemeral=True)

        cid = str(ctx.channel.id)
        config = db.get_config(cid)

        # 2. 检查是否已授权
        if not config:
            return await ctx.respond("⚠️ 此频道尚未授权或已被移除。", ephemeral=True)

        await ctx.defer(ephemeral=True)

        # 3. 清理 Discord 频道内的旧面板消息
        # 逻辑：复用 run_refresh_logic 的清理部分，但不重发新面板
        try:
            messages_to_delete = []
            async for message in ctx.channel.history(limit=100): 
                if message.author.id != self.bot.user.id: continue
                
                is_target = False
                
                # 判定方式 A: Embed 标题匹配
                if message.embeds and message.embeds[0].title == config.get("title"):
                    is_target = True
                
                # 判定方式 B: 按钮 ID 匹配 (更稳健，防止标题已改)
                if not is_target and message.components:
                    for component in message.components:
                        if isinstance(component, discord.ActionRow):
                            for child in component.children:
                                if hasattr(child, "custom_id") and child.custom_id in ["ivory_qa_btn", "ivory_sub_btn"]:
                                    is_target = True
                                    break
                        if is_target: break
                
                if is_target:
                    messages_to_delete.append(message)

            if messages_to_delete:
                if len(messages_to_delete) == 1:
                    await messages_to_delete[0].delete()
                else:
                    await ctx.channel.delete_messages(messages_to_delete)
        except Exception as e:
            print(f"删除面板消息时出错: {e}")

        # 4. 从数据库移除配置
        success = db.delete_config(cid)

        # 5. 停止可能的定时任务
        if ctx.channel.id in self.scheduled_tasks:
            self.scheduled_tasks[ctx.channel.id].cancel()
            del self.scheduled_tasks[ctx.channel.id]
        
        # 6. 反馈
        if success:
            await ctx.followup.send("✅ 已取消授权，配置已删除，面板已清理。", ephemeral=True)
        else:
            await ctx.followup.send("❌ 删除配置时出现未知错误。", ephemeral=True)

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

    @panel_group.command(name="修改答疑", description="修改面板中已有的自助问答")
    async def edit_qa(self, ctx):
        perm, msg = self.check_perm(ctx)
        if not perm: return await ctx.respond(msg, ephemeral=True)
        config = db.get_config(ctx.channel.id)
        if not config or not config["qa_list"]:
            return await ctx.respond("❌ 暂无 QA 内容，请先添加。", ephemeral=True)
        await ctx.respond("请选择要修改的问题：", view=EditQAView(str(ctx.channel.id), self), ephemeral=True)

    @panel_group.command(name="删除答疑", description="删除面板中的自助问答")
    async def delete_qa(self, ctx):
        perm, msg = self.check_perm(ctx)
        if not perm: return await ctx.respond(msg, ephemeral=True)
        config = db.get_config(ctx.channel.id)
        if not config or not config["qa_list"]:
            return await ctx.respond("暂无 QA 内容。", ephemeral=True)
        await ctx.respond("请选择要删除的问题：", view=DeleteQAView(str(ctx.channel.id), self), ephemeral=True)

    @panel_group.command(name="修改外观", description="修改标题、作者、版本、颜色")
    async def edit_profile(self, ctx):
        perm, msg = self.check_perm(ctx)
        if not perm: return await ctx.respond(msg, ephemeral=True)
        config = db.get_config(ctx.channel.id)
        await ctx.send_modal(EditProfileModal(config, self))

    @panel_group.command(name="修改内容", description="修改欢迎语和下载链接")
    async def edit_content(self, ctx):
        perm, msg = self.check_perm(ctx)
        if not perm: return await ctx.respond(msg, ephemeral=True)
        config = db.get_config(ctx.channel.id)
        await ctx.send_modal(EditContentModal(config, self))

    @panel_group.command(name="设置订阅", description="配置点击“订阅更新”按钮时分配的身份组")
    async def config_sub_roles(self, ctx):
        if ctx.author.id != SUPER_ADMIN_ID:
            return await ctx.respond("❌ 仅超级管理员可用", ephemeral=True)
        
        if not db.is_authorized(ctx.channel.id):
            return await ctx.respond("❌ 此频道未授权，无法设置", ephemeral=True)

        view = ConfigSubRoleView(str(ctx.channel.id))
        await ctx.respond("请选择该频道的订阅身份组（可多选）：", view=view, ephemeral=True)

def setup(bot):
    bot.add_cog(SelfPanel(bot))