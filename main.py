import discord
from discord.ext import commands
from discord.commands import Option
import json
import os
import re
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# ================= 配置区域 =================
# 从环境变量获取 Token
BOT_TOKEN = os.getenv('BOT_TOKEN') 
ADMIN_ID = 1353777207042113576
DEFAULT_CHANNEL_ID = 1441432695988162560
DATA_FILE = "data.json"

# ================= 默认数据 =================
DEFAULT_HOME_CONTENT = {
    "title": "🏛️象牙塔自助小餐车",
    "author": "电波系",
    "version": "1.0.0 Ver",
    "welcome": "> 欢迎使用【象牙塔自助bot】！本bot旨在小伙伴们遇到问题时可以快速解决/自助答疑（让电波系偷懒一下），宝宝们如果遇到问题，可以在bot菜单里自查；如果无法解决，欢迎**带上截图和清晰报错**在本频道提问~\n\n**回顶链接：** https://discord.com/channels/1384945301780955246/1441432695988162560/1441432695988162560",
    "downloads": "## ⬇️下载直达\n**预设本体：** https://discord.com/channels/1384945301780955246/1441432695988162560/1445783278068961310\n**最新版正则：** https://discord.com/channels/1384945301780955246/1441432695988162560/1445783366636015747\n**快速回复：** https://discord.com/channels/1384945301780955246/1441432695988162560/1445783419081719838"
}

DEFAULT_QA_LIST = [
    {"q": "心绪回响显示不全/塔罗没有角色心声模块", "a": "寸不己……！是我没调整好！下个版本改😭古风版本的心绪回响和状态栏也在计划中了!"},
    {"q": "容易截断或者空回", "a": "推荐开非流，如果是玩比较敏感的内容，可以看说明打开底部模块三选一"},
    {"q": "美化太多了有点卡", "a": "可选部分的正则美化都是可选的，如果太卡了关掉就可以啦!可以直接看原始文字内容"},
    {"q": "🚗总是容易一轮游", "a": "玩🚗的时候一定一定要把【涩个不停】+【一键开关】+【课堂摘要】一起打开哦!不喊停绝不停，推荐字数也适当调低一下"},
    {"q": "开抢话不抢/开不抢话使劲抢", "a": "3.0的神秘bug……可以开一条抢/不抢，下一条是你想要的抢/不抢最终效果，哈基米可以学习到变化，下个版本也对抢话检查做了优化，目前感觉很有效"},
    {"q": "角色突然超雄变得很凶", "a": "【研究课题-灰色】是给凶角色防软化用的，如果你的角色不是这种类型不要打开，下个版本也会设计一个介于灰色和温柔中间的研究课题"},
    {"q": "想用来玩克劳德可以吗", "a": "正常用的话当然!只适合官，曲奇不行，但是因为我不玩所以不太清楚具体效果怎么样"},
    {"q": "角色老是读取用户心理", "a": "推荐发消息的时候，用不同格式把用户的对话、心理区分开，又想了一个防全知的办法总之下个版本试试……"},
    {"q": "文字出现错乱和乱码问题", "a": "温度调太高了，在象牙塔页面把温度调到1即可"},
    {"q": "各种奇怪的符号词语增殖/短句泛滥", "a": "删掉异常的消息，执行一下大总结，隐藏前文然后再继续聊"}
]

# ================= 数据管理 =================
class DataManager:
    def __init__(self):
        self.data = {
            "allowed_channels": [DEFAULT_CHANNEL_ID],
            "home_content": DEFAULT_HOME_CONTENT,
            "qa_list": DEFAULT_QA_LIST,
            "active_panels": {} # {str(channel_id): message_id}
        }
        self.load_data()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                self.data.update(loaded)
        else:
            self.save_data()

    def save_data(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value
        self.save_data()

db = DataManager()
bot = discord.Bot()

# ================= 辅助函数 =================
def is_admin(user_id):
    return user_id == ADMIN_ID

async def refresh_panel(channel: discord.TextChannel):
    """
    删除旧面板，发送新面板，实现“永远在最新”
    """
    panels = db.get("active_panels")
    channel_id_str = str(channel.id)
    
    # 尝试删除旧消息
    if channel_id_str in panels:
        old_msg_id = panels[channel_id_str]
        try:
            old_msg = await channel.fetch_message(old_msg_id)
            await old_msg.delete()
        except discord.NotFound:
            pass # 消息可能已经被手动删除了
        except Exception as e:
            print(f"删除旧面板时出错 (ID: {old_msg_id}): {e}")

    # 构建 Embed
    home = db.get("home_content")
    embed = discord.Embed(
        title=home["title"],
        description=f"作者：{home['author']}\n适用版本：{home['version']}\n\n{home['welcome']}\n\n---\n{home['downloads']}",
        color=0xffc0cb # 象牙色/粉色系
    )
    
    # 发送新消息
    view = MainPanelView()
    msg = await channel.send(embed=embed, view=view)
    
    # 更新数据库
    panels[channel_id_str] = msg.id
    db.set("active_panels", panels)

# ================= UI 组件 (Views & Modals) =================

# 1. 主面板按钮
class MainPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # 持久化视图

    @discord.ui.button(label="🗳️ 自助答疑", style=discord.ButtonStyle.primary, custom_id="ivory_qa_btn")
    async def callback(self, button, interaction: discord.Interaction):
        # 点击后展示下拉菜单，Ephemeral=True
        view = QADropdownView()
        await interaction.response.send_message("请选择您遇到的问题：", view=view, ephemeral=True)

# 2. Q&A 下拉菜单
class QADropdownView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180) 
        self.add_item(QASelect())

# ================= 修改 QASelect 类 =================

class QASelect(discord.ui.Select):
    def __init__(self):
        qa_list = db.get("qa_list")
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
        qa_list = db.get("qa_list")
        
        if 0 <= idx < len(qa_list):
            qa = qa_list[idx]
            raw_text = qa['a']
            
            # --- 核心逻辑：提取多张图片并清洗文本 ---
            
            # 1. 提取 Markdown 图片链接 ![xxx](url)
            md_images = re.findall(r'!\[.*?\]\((https?://.*?\.(?:png|jpg|jpeg|gif|webp).*?)\)', raw_text, re.IGNORECASE)
            
            # 2. 提取裸露的图片链接 http://xxx.jpg (排除掉已经在 markdown 里的)
            # 这一步比较复杂，为了简单起见，我们优先处理 MD 格式。
            # 如果你的习惯是只用 MD 格式，上面那行就够了。
            
            # 3. 清洗文本：把 ![xxx](url) 从文本中删掉，只保留文字描述
            # 这样文字显示在上方，图片显示在下方，不会重复显示
            clean_text = re.sub(r'!\[.*?\]\(https?://.*?\)', '', raw_text).strip()
            
            # 如果清洗后没字了（只有图），就放个占位符，或者保留原标题
            if not clean_text:
                clean_text = "（查看下方图片详情）"

            # --- 构建 Embed 列表 ---
            embeds = []
            
            # 第一个 Embed：主要负责显示 标题 和 文字内容
            main_embed = discord.Embed(title=f"Q: {qa['q']}", description=clean_text, color=0x7289da)
            
            # 如果有一张或多张图
            if md_images:
                # 把第一张图设为第一个 Embed 的主图
                main_embed.set_image(url=md_images[0])
                embeds.append(main_embed)
                
                # 如果还有第2、3...张图，为它们创建单独的 Embed
                # Discord 限制一条消息最多 10 个 Embed
                for img_url in md_images[1:4]: # 限制最多额外显示3张（共4张），防止太长
                    img_embed = discord.Embed(url="https://discord.com", color=0x7289da) # url 设为同一个可以更紧凑
                    img_embed.set_image(url=img_url)
                    embeds.append(img_embed)
            else:
                # 如果没图，就只发文字 Embed
                embeds.append(main_embed)

            # 发送 Embeds 列表 (注意参数是 embeds=[...])
            await interaction.response.send_message(embeds=embeds, ephemeral=True)
            
        else:
            await interaction.response.send_message("未找到该问题内容。", ephemeral=True)

# 3. 添加 Q&A 的弹窗
class AddQAModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="问题 (Q)", placeholder="请输入问题标题..."))
        self.add_item(discord.ui.InputText(label="回答 (A)", placeholder="支持 Markdown 格式...", style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        q = self.children[0].value
        a = self.children[1].value
        
        qa_list = db.get("qa_list")
        qa_list.append({"q": q, "a": a})
        db.set("qa_list", qa_list)
        
        await interaction.response.send_message(f"✅ 已添加问题：{q}", ephemeral=True)
        # 刷新当前频道的面板
        if interaction.channel_id in db.get("allowed_channels"):
            await refresh_panel(interaction.channel)

# 4. 编辑主页内容的弹窗
class EditHomeModal(discord.ui.Modal):
    def __init__(self, current_data):
        super().__init__(title="编辑主页内容")
        self.add_item(discord.ui.InputText(label="标题", value=current_data["title"]))
        self.add_item(discord.ui.InputText(label="版本号", value=current_data["version"]))
        self.add_item(discord.ui.InputText(label="欢迎语 (支持MD)", value=current_data["welcome"], style=discord.InputTextStyle.long))
        self.add_item(discord.ui.InputText(label="下载链接区 (支持MD)", value=current_data["downloads"], style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        new_data = {
            "title": self.children[0].value,
            "author": db.get("home_content")["author"], # 作者保持不变
            "version": self.children[1].value,
            "welcome": self.children[2].value,
            "downloads": self.children[3].value
        }
        db.set("home_content", new_data)
        await interaction.response.send_message("✅ 主页内容已更新，正在刷新面板...", ephemeral=True)
        
        if interaction.channel_id in db.get("allowed_channels"):
            await refresh_panel(interaction.channel)

# 5. 删除 Q&A 的选择视图
class DeleteQAView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(DeleteQASelect())

class DeleteQASelect(discord.ui.Select):
    def __init__(self):
        qa_list = db.get("qa_list")
        options = []
        for idx, item in enumerate(qa_list[:25]):
            label = item["q"][:95]
            options.append(discord.SelectOption(label=label, value=str(idx), emoji="🗑️"))
        
        super().__init__(placeholder="选择要删除的问题...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        qa_list = db.get("qa_list")
        
        if 0 <= idx < len(qa_list):
            removed = qa_list.pop(idx)
            db.set("qa_list", qa_list)
            await interaction.response.send_message(f"✅ 已删除：{removed['q']}", ephemeral=True)
            # 刷新面板
            if interaction.channel_id in db.get("allowed_channels"):
                await refresh_panel(interaction.channel)
        else:
            await interaction.response.send_message("删除失败，索引无效。", ephemeral=True)

# ================= Bot 事件与指令 =================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("--------------------------------------------------")
    print(f"管理员 ID: {ADMIN_ID}")
    print(f"默认频道 ID: {DEFAULT_CHANNEL_ID}")
    print("--------------------------------------------------")
    # 注册持久化视图，确保重启后按钮依然有效
    bot.add_view(MainPanelView())

# --- 管理员指令 ---

@bot.slash_command(name="setup_panel", description="[管理员] 初始化或刷新当前频道的自助餐车面板")
async def setup_panel(ctx):
    if not is_admin(ctx.author.id):
        return await ctx.respond("❌ 你没有权限执行此操作。", ephemeral=True)
    
    allowed = db.get("allowed_channels")
    if ctx.channel.id not in allowed:
        return await ctx.respond(f"❌ 此频道 ({ctx.channel.id}) 未被授权。请先使用 `/add_channel`。", ephemeral=True)

    await ctx.respond("🔄 正在生成/刷新面板...", ephemeral=True)
    await refresh_panel(ctx.channel)

@bot.slash_command(name="add_qa", description="[管理员] 新增一条 Q&A 内容")
async def add_qa(ctx):
    if not is_admin(ctx.author.id):
        return await ctx.respond("❌ 你没有权限执行此操作。", ephemeral=True)
    
    modal = AddQAModal(title="新增自助答疑内容")
    await ctx.send_modal(modal)

@bot.slash_command(name="delete_qa", description="[管理员] 删除一条 Q&A 内容")
async def delete_qa(ctx):
    if not is_admin(ctx.author.id):
        return await ctx.respond("❌ 你没有权限执行此操作。", ephemeral=True)
    
    qa_list = db.get("qa_list")
    if not qa_list:
        return await ctx.respond("目前没有 Q&A 内容。", ephemeral=True)
        
    await ctx.respond("请选择要删除的问题：", view=DeleteQAView(), ephemeral=True)

@bot.slash_command(name="edit_home", description="[管理员] 修改面板主页内容")
async def edit_home(ctx):
    if not is_admin(ctx.author.id):
        return await ctx.respond("❌ 你没有权限执行此操作。", ephemeral=True)
    
    current_data = db.get("home_content")
    modal = EditHomeModal(current_data)
    await ctx.send_modal(modal)

@bot.slash_command(name="add_channel", description="[管理员] 授权当前频道使用 Bot")
async def add_channel(ctx):
    if not is_admin(ctx.author.id):
        return await ctx.respond("❌ 你没有权限执行此操作。", ephemeral=True)
    
    allowed = db.get("allowed_channels")
    if ctx.channel.id not in allowed:
        allowed.append(ctx.channel.id)
        db.set("allowed_channels", allowed)
        await ctx.respond(f"✅ 已授权频道：{ctx.channel.name} (ID: {ctx.channel.id})", ephemeral=True)
    else:
        await ctx.respond("⚠️ 当前频道已在授权列表中。", ephemeral=True)

@bot.slash_command(name="remove_channel", description="[管理员] 移除当前频道的授权")
async def remove_channel(ctx):
    if not is_admin(ctx.author.id):
        return await ctx.respond("❌ 你没有权限执行此操作。", ephemeral=True)
    
    allowed = db.get("allowed_channels")
    if ctx.channel.id in allowed:
        allowed.remove(ctx.channel.id)
        db.set("allowed_channels", allowed)
        await ctx.respond(f"✅ 已移除频道授权：{ctx.channel.name}", ephemeral=True)
    else:
        await ctx.respond("⚠️ 当前频道不在授权列表中。", ephemeral=True)

# ================= 自动监听消息 =================

@bot.event
async def on_message(message):
    # 1. 如果是 Bot 自己发的消息，直接忽略，防止无限循环
    if message.author.id == bot.user.id:
        return

    # 2. 检查这条消息是否在“授权频道”里
    allowed_channels = db.get("allowed_channels")
    if message.channel.id in allowed_channels:
        # 3. 触发刷新面板：删除旧面板 -> 发送新面板
        # 这样面板就会永远保持在最新一条
        try:
            await refresh_panel(message.channel)
        except Exception as e:
            print(f"自动刷新面板失败: {e}")

# 启动 Bot
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ 错误：未在环境变量或 .env 文件中找到 BOT_TOKEN。")
        print("请创建一个 .env 文件并添加：BOT_TOKEN=你的Token")
    else:
        bot.run(BOT_TOKEN)