import discord
from discord.ext import commands
import json
import os
import re
import asyncio
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ================= 配置区域 =================
BOT_TOKEN = os.getenv('BOT_TOKEN')
SUPER_ADMIN_ID = 1353777207042113576  # 你的 ID (超级管理员)
DATA_FILE = "data.json"

# ================= 默认模板 =================
# 当新频道被授权时，会使用这份数据初始化
DEFAULT_TEMPLATE = {
    "manager_id": 0,           # 频道负责人 ID
    "color": 0xffc0cb,         # 默认颜色 (粉色)
    "title": "🛒预设自助小餐车",
    "author": "未知",
    "version": "未知",
    "welcome": "> 欢迎使用自助答疑系统\n\n贴主可使用命令自行配置\n\n请点击下方按钮开始使用。",
    "downloads": "## ⬇️下载直达\n暂无链接",
    "qa_list": []              # 默认为空
}

# ================= 数据管理 =================
class DataManager:
    def __init__(self):
        self.data = {
            "channels": {} # 结构: { "channel_id_str": { ...配置... } }
        }
        self.load_data()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"数据文件损坏，已重置: {e}")
                self.save_data()
        else:
            self.save_data()

    def save_data(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def get_channel_config(self, channel_id):
        return self.data["channels"].get(str(channel_id))

    def set_channel_config(self, channel_id, config):
        self.data["channels"][str(channel_id)] = config
        self.save_data()

    def is_authorized(self, channel_id):
        return str(channel_id) in self.data["channels"]

db = DataManager()
bot = discord.Bot()

# ================= 权限检查辅助函数 =================

def is_super_admin(user_id):
    return user_id == SUPER_ADMIN_ID

def check_permission(ctx):
    """
    检查权限：
    1. 超级管理员可以在任何地方操作。
    2. 频道负责人在自己的频道操作。
    """
    cid = str(ctx.channel.id)
    config = db.get_channel_config(cid)
    
    # 1. 如果频道没在数据库里，说明没授权
    if not config:
        return False, "❌ 此频道尚未获得授权，请联系管理员。"

    # 2. 权限判断
    user_id = ctx.author.id
    if user_id == SUPER_ADMIN_ID or user_id == config["manager_id"]:
        return True, None
    else:
        return False, "❌ 你没有权限管理此频道的面板。"

# ================= 核心功能函数 =================

# 用于防止并发刷新的锁标志
is_refreshing = False 

async def refresh_panel(channel: discord.TextChannel):
    """
    刷新面板：扫描旧消息 -> 发送新面板，并加入并发控制
    """
    global is_refreshing
    cid = str(channel.id)
    config = db.get_channel_config(cid)
    
    if not config:
        return # 未授权频道不处理

    # --- 并发控制开始 ---
    # 如果正在刷新，则等待 0.5 秒后再试（简单轮询）
    # 实际应用中更健壮的方式是用 asyncio.Lock，但这里用标志位简化
    while is_refreshing:
        await asyncio.sleep(0.5) # 等待 0.5 秒

    # 标记为正在刷新
    is_refreshing = True
    # --- 并发控制结束 ---

    try:
        # 1. 扫荡旧消息 (只删除 Bot 发的)
        try:
            async for message in channel.history(limit=30):
                if message.author.id == bot.user.id:
                    try:
                        await message.delete()
                    except discord.NotFound:
                        pass
                    except Exception as e:
                        print(f"删除旧消息失败: {e}")
        except Exception as e:
            print(f"读取历史消息失败: {e}")

        # 2. 构建新的 Embed
        embed = discord.Embed(
            title=config["title"],
            description=f"作者：{config['author']}\n适用版本：{config['version']}\n\n{config['welcome']}\n\n---\n{config['downloads']}",
            color=config["color"]
        )
        
        # 3. 发送
        view = MainPanelView(cid) # MainPanelView 的 __init__ 需要传入 channel_id_str
        await channel.send(embed=embed, view=view)
        
        # 4. 更新数据库 (仍然是必要的)
        panels = db.get("channels") # 获取整个 channels 字典
        panels[cid]["last_panel_message_id"] = msg.id # 假设你以后会用这个ID，虽然现在不直接用了
        db.set("channels", panels) # 重新保存

    finally:
        # --- 刷新完毕，解除锁定 ---
        is_refreshing = False


# ================= UI 组件 =================

# 1. 主面板按钮
class MainPanelView(discord.ui.View):
    def __init__(self, channel_id_str):
        super().__init__(timeout=None)
        self.channel_id_str = channel_id_str

    @discord.ui.button(label="🗳️ 自助答疑", style=discord.ButtonStyle.primary, custom_id="ivory_qa_btn")
    async def callback(self, button, interaction: discord.Interaction):
        # 传入当前频道ID，让下拉菜单知道去读哪份数据
        view = QADropdownView(str(interaction.channel_id))
        
        # 检查该频道是否有 QA
        config = db.get_channel_config(str(interaction.channel_id))
        if not config or not config["qa_list"]:
             await interaction.response.send_message("暂无答疑内容。", ephemeral=True)
             return

        await interaction.response.send_message("请选择您遇到的问题：", view=view, ephemeral=True)

# 2. Q&A 下拉菜单
class QADropdownView(discord.ui.View):
    def __init__(self, channel_id_str):
        super().__init__(timeout=180)
        self.add_item(QASelect(channel_id_str))

class QASelect(discord.ui.Select):
    def __init__(self, channel_id_str):
        self.channel_id_str = channel_id_str
        config = db.get_channel_config(channel_id_str)
        qa_list = config["qa_list"] if config else []
        
        options = []
        for idx, item in enumerate(qa_list[:25]): 
            label = item["q"][:95] + "..." if len(item["q"]) > 95 else item["q"]
            options.append(discord.SelectOption(label=label, value=str(idx)))
        
        super().__init__(
            placeholder="🔍 点击这里选择问题...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        config = db.get_channel_config(self.channel_id_str)
        
        if config and 0 <= idx < len(config["qa_list"]):
            qa = config["qa_list"][idx]
            raw_text = qa['a']
            
            # --- 图片提取与清洗逻辑 ---
            md_images = re.findall(r'!\[.*?\]\((https?://.*?\.(?:png|jpg|jpeg|gif|webp).*?)\)', raw_text, re.IGNORECASE)
            clean_text = re.sub(r'!\[.*?\]\(https?://.*?\)', '', raw_text).strip()
            
            if not clean_text:
                clean_text = "（查看下方图片详情）"

            embeds = []
            # 使用频道自定义的颜色
            theme_color = config.get("color", 0xffc0cb)

            main_embed = discord.Embed(title=f"Q: {qa['q']}", description=clean_text, color=theme_color)
            
            if md_images:
                main_embed.set_image(url=md_images[0])
                embeds.append(main_embed)
                for img_url in md_images[1:4]: 
                    img_embed = discord.Embed(url="https://discord.com", color=theme_color)
                    img_embed.set_image(url=img_url)
                    embeds.append(img_embed)
            else:
                embeds.append(main_embed)

            await interaction.response.send_message(embeds=embeds, ephemeral=True)
        else:
            await interaction.response.send_message("未找到该问题内容。", ephemeral=True)

# 3. 弹窗：新增 QA
class AddQAModal(discord.ui.Modal):
    def __init__(self, channel_id_str):
        super().__init__(title="新增自助答疑内容")
        self.channel_id_str = channel_id_str
        self.add_item(discord.ui.InputText(label="问题 (Q)", placeholder="请输入问题标题..."))
        self.add_item(discord.ui.InputText(label="回答 (A)", placeholder="支持 Markdown 和图片链接...", style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        q = self.children[0].value
        a = self.children[1].value
        
        config = db.get_channel_config(self.channel_id_str)
        if config:
            config["qa_list"].append({"q": q, "a": a})
            db.set_channel_config(self.channel_id_str, config)
            await interaction.response.send_message(f"✅ 已添加问题：{q}", ephemeral=True)
            await refresh_panel(interaction.channel)

# 4. 弹窗：编辑基本信息 (Profile) - 标题、作者、颜色
class EditProfileModal(discord.ui.Modal):
    def __init__(self, config):
        super().__init__(title="编辑面板外观")
        self.channel_id_str = str(config["channel_id"]) # 临时存一下方便调用
        
        self.add_item(discord.ui.InputText(label="标题", value=config["title"]))
        self.add_item(discord.ui.InputText(label="作者名", value=config["author"]))
        self.add_item(discord.ui.InputText(label="版本号", value=config["version"]))
        
        # 颜色转换：Int -> Hex String
        hex_color = "#{:06x}".format(config["color"])
        self.add_item(discord.ui.InputText(label="颜色 (Hex格式, 如 #FF0000)", value=hex_color, min_length=7, max_length=7))

    async def callback(self, interaction: discord.Interaction):
        config = db.get_channel_config(interaction.channel.id)
        
        # 处理颜色
        color_str = self.children[3].value
        try:
            # 把 #FF0000 转为 0xFF0000 (int)
            color_int = int(color_str.replace("#", ""), 16)
        except:
            color_int = 0xffc0cb # 转换失败回退默认粉色

        if config:
            config["title"] = self.children[0].value
            config["author"] = self.children[1].value
            config["version"] = self.children[2].value
            config["color"] = color_int
            
            db.set_channel_config(str(interaction.channel.id), config)
            await interaction.response.send_message("✅ 外观信息已更新。", ephemeral=True)
            await refresh_panel(interaction.channel)

# 5. 弹窗：编辑正文内容 (Content)
class EditContentModal(discord.ui.Modal):
    def __init__(self, config):
        super().__init__(title="编辑面板正文")
        self.add_item(discord.ui.InputText(label="欢迎语 (支持MD)", value=config["welcome"], style=discord.InputTextStyle.long))
        self.add_item(discord.ui.InputText(label="下载链接区 (支持MD)", value=config["downloads"], style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        config = db.get_channel_config(str(interaction.channel.id))
        if config:
            config["welcome"] = self.children[0].value
            config["downloads"] = self.children[1].value
            
            db.set_channel_config(str(interaction.channel.id), config)
            await interaction.response.send_message("✅ 正文内容已更新。", ephemeral=True)
            await refresh_panel(interaction.channel)

# 6. 删除 QA 选择视图
class DeleteQAView(discord.ui.View):
    def __init__(self, channel_id_str):
        super().__init__(timeout=60)
        self.channel_id_str = channel_id_str
        self.add_item(DeleteQASelect(channel_id_str))

class DeleteQASelect(discord.ui.Select):
    def __init__(self, channel_id_str):
        self.channel_id_str = channel_id_str
        config = db.get_channel_config(channel_id_str)
        qa_list = config["qa_list"] if config else []
        
        options = []
        for idx, item in enumerate(qa_list[:25]):
            label = item["q"][:95]
            options.append(discord.SelectOption(label=label, value=str(idx), emoji="🗑️"))
        
        super().__init__(placeholder="选择要删除的问题...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        config = db.get_channel_config(self.channel_id_str)
        
        if config and 0 <= idx < len(config["qa_list"]):
            removed = config["qa_list"].pop(idx)
            db.set_channel_config(self.channel_id_str, config)
            await interaction.response.send_message(f"✅ 已删除：{removed['q']}", ephemeral=True)
            await refresh_panel(interaction.channel)
        else:
            await interaction.response.send_message("删除失败。", ephemeral=True)

# ================= Bot 事件与指令 =================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("-------------------------")
    # 注册持久化视图时，这里其实无法预知所有频道ID，
    # 但 MainPanelView 的 custom_id 是固定的，这通常对无状态按钮够用了。
    # 真正的持久化需要更复杂的处理，但在这里只要 Bot 不重启，内存里的 View 都在。
    # 重启后，只要用户点击按钮，会触发 interaction，如果 custom_id 匹配，我们需要重新挂载逻辑。
    # Py-cord 允许在 on_ready 注册一个无状态的 View 类。
    # 但由于我们需要传入 channel_id，这里简化处理：不全局注册，依赖指令重新唤醒面板。
    print("Bot 就绪。请使用 /auth_channel 授权频道。")

@bot.event
async def on_message(message):
    if message.author.id == bot.user.id:
        return
    
    # 只有已授权的频道才触发自动刷新
    if db.is_authorized(message.channel.id):
        await refresh_panel(message.channel)

# --- 核心管理指令 ---

@bot.slash_command(name="auth_channel", description="[超级管理] 授权当前频道并指定负责人")
async def auth_channel(ctx, manager: discord.User):
    """
    只有超级管理员可以用。
    用法: /auth_channel @某人
    """
    if not is_super_admin(ctx.author.id):
        return await ctx.respond("❌ 只有超级管理员可以使用此指令。", ephemeral=True)

    cid = str(ctx.channel.id)
    
    # 初始化该频道的配置
    new_config = DEFAULT_TEMPLATE.copy()
    new_config["manager_id"] = manager.id
    new_config["qa_list"] = [] # 确保新频道是空的 QA
    
    db.set_channel_config(cid, new_config)
    
    await ctx.respond(f"✅ 频道授权成功！\n负责人: {manager.mention}\n现在负责人可以使用 `/setup_panel` 初始化面板了。", ephemeral=True)

@bot.slash_command(name="setup_panel", description="[负责人] 初始化/刷新面板")
async def setup_panel(ctx):
    has_perm, msg = check_permission(ctx)
    if not has_perm:
        return await ctx.respond(msg, ephemeral=True)
    
    await ctx.respond("🔄 正在生成面板...", ephemeral=True)
    await refresh_panel(ctx.channel)

@bot.slash_command(name="add_qa", description="[负责人] 新增 QA")
async def add_qa(ctx):
    has_perm, msg = check_permission(ctx)
    if not has_perm:
        return await ctx.respond(msg, ephemeral=True)
    
    modal = AddQAModal(str(ctx.channel.id))
    await ctx.send_modal(modal)

@bot.slash_command(name="delete_qa", description="[负责人] 删除 QA")
async def delete_qa(ctx):
    has_perm, msg = check_permission(ctx)
    if not has_perm:
        return await ctx.respond(msg, ephemeral=True)
    
    config = db.get_channel_config(ctx.channel.id)
    if not config or not config["qa_list"]:
        return await ctx.respond("暂无 QA 内容。", ephemeral=True)

    await ctx.respond("请选择要删除的问题：", view=DeleteQAView(str(ctx.channel.id)), ephemeral=True)

@bot.slash_command(name="edit_profile", description="[负责人] 修改标题、作者、颜色等")
async def edit_profile(ctx):
    has_perm, msg = check_permission(ctx)
    if not has_perm:
        return await ctx.respond(msg, ephemeral=True)
    
    config = db.get_channel_config(ctx.channel.id)
    # 注入 channel_id 方便 modal 使用
    config["channel_id"] = ctx.channel.id 
    await ctx.send_modal(EditProfileModal(config))

@bot.slash_command(name="edit_content", description="[负责人] 修改欢迎语和下载链接")
async def edit_content(ctx):
    has_perm, msg = check_permission(ctx)
    if not has_perm:
        return await ctx.respond(msg, ephemeral=True)
    
    config = db.get_channel_config(ctx.channel.id)
    await ctx.send_modal(EditContentModal(config))

# 启动
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("未找到 Token")
    else:
        bot.run(BOT_TOKEN)
