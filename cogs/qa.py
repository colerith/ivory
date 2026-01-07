import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup, Option
import json
import os
import re

# ================= 配置 =================
QA_FILE = "qa_data.json"
ADMIN_ROLE_ID = 1420698551138385982  # 指定的有权限操作的身份组ID

# 初始数据文本
INITIAL_MARKDOWN = """
# 快速回复
## ❓ 什么是快速回复：
快速回复，也称quick reply（简称QR），存储了一些快捷指令，如预设中常见的大总结，点击快速回复按钮即可快捷触发
## 💡如何导入预设快速回复
1. 点开“扩展页面”图标（顶部栏从左往右第7个），找到快速回复栏
2. 在【编辑快速回复】处导入快速回复文件
3. 在【全局快速回复】点击➕号找到对应的快速回复添加，并勾选激活

**⚠️注意：**
使用快速回复时需在【编辑快速回复】取消勾选`禁用发送（插入输入字段）、在输入前放置快速回复、自动注入用户输入 `
https://files.catbox.moe/ky692o.png

# 报错
## 🔍常见报错及处理方式
### 1️⃣ 回复截断
将预设页面的流式传输取消勾选，并根据说明打开预设中的越狱条目
### 2️⃣ PROHIBITED CONTENT（简称P一串）
触发情况可能为酒馆内弹红框，或者酒馆后台出现`PROHIBITED CONTENT`报错，可以从以下几个方式逐个尝试：
1. 修改最后一条回复内容，确保和最开始的不一样，然后重新发送
2. 如果只有某个角色卡会触发报错，其他角色卡能正常游玩，删除该角色卡并重新导入
3. 打开预设中的越狱条目
### 3️⃣ 429
- 打开预设顶部的`防429`相关条目
- 检查账号额度是否用尽，如有，切换别的有额度的谷歌账号
### 4️⃣ 500 & 403
切换梯子节点，确保节点不是谷歌不提供服务的区域，并且梯子要足够纯净
### 5️⃣ 200
谷歌官网的短时故障，耐心等待恢复即可

# 自动解析
## 💡 MoM系预设自动解析设置
推理-自动解析-（显示隐藏内容）-前缀`<thinking>`-后缀`</thinking>`-保存

**⚠️注意：【自动解析】仅在酒馆较新版本有，推荐确保你的酒馆升级至1.13版本以上**
https://files.catbox.moe/831kl2.webp

# 大总结
## 💡 大总结方法
1. 下载预设配套的快速回复/使用【MoM通用大总结快速回复】
2. 打开预设内总结相关条目，点击快速回复发送大总结指令
3. 待AI生成总结内容后，你可以这样处理
    - 隐藏除大总结之外的楼层，可以使用快速回复里的【隐藏楼层】功能，也可以在输入框输入`/hide xx-xx`（如`/hide 0-50`就是隐藏0-50层的内容）点击发送，然后即可继续游玩
    - 新建一个角色世界书/在已有的角色世界书里建一个存放大总结的条目，选择`🔵蓝灯 @D⚙️ 深度9999 顺序默认`

# CH
### ❓ 什么是chathistory
chathistory，简称ch，指聊天内所有已发送给AI的总词符数，通常会包括聊天记录、预设提示词、世界书两部分内容
Gemini 2.5 pro推荐控制在8w以下，Gemini 3.0 pro推荐控制在6w以下？（3.0的最佳注意力区间在32k以下左右）超过推荐的词符数时，推荐进行【大总结】
### 🔍如何查看chathistory
**方法一：**
打开预设页面，下滑到`Chat History`条目即可查看；单击条目名称还可以查看当前聊天所有发送给AI的内容
https://files.catbox.moe/cybaxk.png

**方法二：**
找到最新一条char的消息，点击“更多”图标（在编辑图标旁边），找到`提示词`这个按钮（通常在隐藏消息的`眼睛图标`左边），点击即可查看当前聊天发送给AI的词符数
https://files.catbox.moe/4uedrd.png

# 增殖
### ❓ 什么是增殖
当AI回复中的某种情况开始不正常的重复、增加，并且随着楼层数越变越多直到影响整个回复，我们称这种现象为增殖

常见的增殖情况有：
1. 标点符号增殖：如顿号、逗号、省略号
2. 短句泛滥：句子和段落越变越短
3. 词汇增殖：那个那个那个
4. 繁体/语言错乱（八国联军）

### 💡 解决方法
可以参考【大总结】的处理方法，删除所有增殖的异常内容，进行大总结，隐藏前文再继续聊天

# 温度
如果你在回复中发现大量乱码，一般是由于预设界面的温度设置过高了，调节到1即可

# 第三方
抱歉呀宝宝～因为喵喵电波这边也是不提倡使用第三方渠道的，所以还是推荐你用官方渠道哦!!贩子掺水所以会不稳定这样子，比较降智

## __反商业化声明__
**喵喵电波是__严格反商业化__社区，在本服务器内，所有创作者都是__无偿分享自己的创作成果__，所以请喵喵们不要使用第三方api渠道、商业云酒馆。**
-# 简单地说，创作者们花费心血给免费给大家使用，但钱却被无良贩子赚走了，对创作者们非常不公平~长远来看，任何酒馆生态的商业化行为都会破坏目前的良性社区氛围。

### 🚫 在社区用第三方API或云酒馆提问违反社区答疑规则，需要重新进验证区进行答题验证，并不是踢人，完成答题后仍可以在社区内发言活动，并继续通过官方渠道游玩交流

** ⭐ GEMINI游玩是完全免费的！完全不必使用贩子的渠道。而且使用第三方还会有掺水、窃取信息等风险。**

## GEMINI免费游玩攻略：
<a:number_1:1093887092507021332> 如果你使用的是3.0模型,目前只有build反代可以免费玩：
  - 教程  https://discord.com/channels/1134557553011998840/1380129283430940712/1380129283430940712
https://discord.com/channels/1291925535324110879/1429039503808659517

<a:number_2:1093887089730396230> 如果你使用的是2.5pro，可以使用api直连、build反代以及cli反代三种方法（build反代同上）：
### AI studio api教程：
  - [Google AI Studio教程 旅程Wiki](https://wiki.opizontas.org/books/api/page/google-ai-studio)
### cli反代教程（需要把预设的top k参数设置在64以上）
  - [安卓 | Termux ⟡ 酒馆 & ClewdR & gcli2api 一键脚本](https://discord.com/channels/1291925535324110879/1385183883540303872)
  - [安卓一键部署-gemini-cli-termux](https://discord.com/channels/1291925535324110879/1407120550467211264)
  - [电脑部署cli反代 旅程Wiki](https://wiki.opizontas.org/books/api/page/cli)
"""

# ================= 辅助 UI 组件 =================

# 1. 右键菜单专用的选择视图 (替代了之前的 Modal 和 Search Modal)
class RightClickSelectView(discord.ui.View):
    def __init__(self, cog, target_message):
        super().__init__(timeout=60)
        self.add_item(RightClickSelect(cog, target_message))

class RightClickSelect(discord.ui.Select):
    def __init__(self, cog, target_message):
        self.cog = cog
        self.target_message = target_message
        
        # 获取所有 Key，并截取前25个
        keys = list(cog.qa_data.keys())
        options = []
        for k in keys[:25]:
            label = k[:100]
            options.append(discord.SelectOption(label=label, value=k))
            
        super().__init__(
            placeholder="👇 请选择要回复的答疑内容...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        # 1. 获取用户选择的关键词
        query = self.values[0]
        
        try:
            # 2. 获取回复内容 (Payload)
            embeds = self.cog.get_qa_payload(query)
            
            # 3. 对目标消息进行引用回复 (公开)
            await self.target_message.reply(content=None, embeds=embeds, mention_author=True)
            await interaction.response.edit_message(content=f"✅ 已成功回复关于 **{query}** 的内容！", view=None)
                
        except discord.Forbidden:
            await interaction.response.edit_message(content="❌ 无法回复该消息（可能我没有权限或被拉黑）。", view=None)
        except Exception as e:
            print(f"Reply Error: {e}")
            if not interaction.response.is_done():
                await interaction.response.edit_message(content=f"❌ 发送失败: {e}", view=None)


# ================= 主逻辑 Cog =================

class QuickQA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.qa_data = {}
        self.load_data()

    # ================= 数据处理 =================
    def load_data(self):
        if os.path.exists(QA_FILE):
            try:
                with open(QA_FILE, "r", encoding="utf-8") as f:
                    self.qa_data = json.load(f)
            except Exception as e:
                print(f"⚠️ QA数据加载失败: {e}")
                self.qa_data = {}
        
        if not self.qa_data:
            print("⏳ 初始化默认答疑库...")
            self.parse_markdown_to_data(INITIAL_MARKDOWN)
            self.save_data()

    def save_data(self):
        with open(QA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.qa_data, f, ensure_ascii=False, indent=4)

    def parse_markdown_to_data(self, md_text):
        lines = md_text.split('\n')
        new_data = {}
        current_title = None
        current_content = []

        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                if current_title:
                    new_data[current_title] = "\n".join(current_content).strip()
                current_title = line[2:].strip()
                current_content = []
            else:
                if current_title:
                    current_content.append(line)
        
        if current_title:
            new_data[current_title] = "\n".join(current_content).strip()
            
        self.qa_data = new_data
        return len(new_data)

    def export_data_to_markdown(self):
        md_lines = []
        for title, content in self.qa_data.items():
            md_lines.append(f"# {title}")
            md_lines.append(content)
            md_lines.append("")
        return "\n".join(md_lines)

    async def search_qa_titles(self, ctx: discord.AutocompleteContext):
        user_input = ctx.value.lower()
        keys = list(self.qa_data.keys())
        if not user_input:
            return keys[:25]
        filtered = [k for k in keys if user_input in k.lower()]
        return filtered[:25] 

    # ================= 核心功能：生成回复 Payload =================
    def get_qa_payload(self, query):
        """
        【修改】：不再接收 user 参数，Embed 描述中也不再包含 @User
        """
        content = self.qa_data[query]
        
        # 1. 提取所有图片链接
        images = re.findall(r'(https?://.*?\.(?:png|jpg|jpeg|gif|webp))', content, re.IGNORECASE)
        
        # 2. 清洗正文中的链接
        clean_text = content
        clean_text = re.sub(r'!\[.*?\]\(https?://.*?\.(?:png|jpg|jpeg|gif|webp).*?\)', '', clean_text, flags=re.IGNORECASE)
        for img in images:
            clean_text = clean_text.replace(img, "")
        
        clean_text = clean_text.strip()
        if not clean_text:
            clean_text = "（请查看下方图片详情）"

        # 3. 构建多 Embed
        embeds = []
        
        # 主 Embed (注意：Description 去掉了 user.mention)
        main_embed = discord.Embed(
            title=f"💡 关于 {query}",
            description=clean_text, 
            color=0x00ff00
        )
        
        if images:
            main_embed.set_image(url=images[0])
            embeds.append(main_embed)
            for img_url in images[1:4]:
                sub_embed = discord.Embed(url="https://discord.com", color=0x00ff00)
                sub_embed.set_image(url=img_url)
                embeds.append(sub_embed)
        else:
            embeds.append(main_embed)

        return embeds

    # ================= 核心功能：右键菜单处理逻辑 =================
    
    async def send_qa_reply(self, interaction, target_message, query):
        """
        处理右键菜单的最终发送：引用(Reply)目标消息
        """
        # 获取 embeds (不带文字内容，因为 reply 自带引用)
        embeds = self.get_qa_payload(query)
        
        try:
            # 执行引用回复
            # content=None (不发额外的文字)
            # mention_author=True (确保原作者收到通知)
            await target_message.reply(content=None, embeds=embeds, mention_author=True)
            
            # 这里的 interaction 是下拉菜单的 interaction
            if not interaction.response.is_done():
                await interaction.response.send_message("✅ 已成功回复！", ephemeral=True)
            else:
                await interaction.followup.send("✅ 已成功回复！", ephemeral=True)
                
        except discord.Forbidden:
            await interaction.response.send_message("❌ 无法回复该消息（可能权限不足）。", ephemeral=True)
        except Exception as e:
            print(f"Reply Error: {e}")

    # ================= 命令注册 =================

    # 1. 右键菜单 (Message Command)
    @commands.message_command(name="快速答疑")
    async def quick_qa_context(self, ctx, message: discord.Message):
        """
        右键菜单入口：直接发送一个下拉菜单 (Ephemeral)
        """
        if not self.qa_data:
            return await ctx.respond("❌ 答疑库为空，请先添加内容。", ephemeral=True)

        view = RightClickSelectView(self, message)
        await ctx.respond("请选择要回复的条目：", view=view, ephemeral=True)

    # 2. 斜杠命令组
    qa_group = SlashCommandGroup("快速答疑", "答疑库相关操作")

    @qa_group.command(name="回复", description="选择答疑库内容回复指定用户")
    async def reply_user(
        self, 
        ctx: discord.ApplicationContext, 
        user: Option(discord.User, "提问的用户"),
        query: Option(str, "搜索关键词（一级标题）", autocomplete=search_qa_titles)
    ):
        if query not in self.qa_data:
            return await ctx.respond(f"❌ 未找到关键词 `{query}`，请检查拼写。", ephemeral=True)

        embeds = self.get_qa_payload(query)
        
        # 斜杠命令需要手动 @ 用户，因为不是引用回复
        await ctx.respond(content=f"{user.mention} 👇", embeds=embeds)

    # ================= 管理功能 =================
    def is_qa_admin():
        def predicate(ctx):
            role = discord.utils.get(ctx.author.roles, id=ADMIN_ROLE_ID)
            return role is not None
        return commands.check(predicate)

    @qa_group.command(name="新增", description="[管理] 添加新的答疑条目")
    @is_qa_admin()
    async def add_entry(self, ctx, title: str, content: str):
        if title in self.qa_data:
            return await ctx.respond("❌ 该标题已存在，请使用修改或先删除。", ephemeral=True)
        self.qa_data[title] = content
        self.save_data()
        await ctx.respond(f"✅ 已添加条目：`{title}`", ephemeral=True)

    @qa_group.command(name="修改", description="[管理] 修改已有条目的内容")
    @is_qa_admin()
    async def edit_entry(self, ctx, title: Option(str, "选择条目", autocomplete=search_qa_titles), new_content: str):
        if title not in self.qa_data:
            return await ctx.respond("❌ 未找到该条目。", ephemeral=True)
        self.qa_data[title] = new_content
        self.save_data()
        await ctx.respond(f"✅ 已更新条目：`{title}`", ephemeral=True)

    @qa_group.command(name="删除", description="[管理] 删除答疑条目")
    @is_qa_admin()
    async def delete_entry(self, ctx, query: Option(str, "选择要删除的条目", autocomplete=search_qa_titles)):
        if query in self.qa_data:
            del self.qa_data[query]
            self.save_data()
            await ctx.respond(f"🗑️ 已删除条目：`{query}`", ephemeral=True)
        else:
            await ctx.respond("❌ 未找到该条目。", ephemeral=True)

    @qa_group.command(name="导出", description="[管理] 导出当前答疑库为 Markdown")
    @is_qa_admin()
    async def export_data(self, ctx):
        md_content = self.export_data_to_markdown()
        with open("qa_export.md", "w", encoding="utf-8") as f:
            f.write(md_content)
        file = discord.File("qa_export.md")
        await ctx.respond("✅ 当前答疑库备份如下：", file=file, ephemeral=True)
        os.remove("qa_export.md")

    @qa_group.command(name="重载导入", description="[管理] 发送 Markdown 文件覆盖当前库")
    @is_qa_admin()
    async def import_data(self, ctx, file: Option(discord.Attachment, "请上传 .txt 或 .md 文件")):
        if not file.filename.endswith(('.txt', '.md')):
            return await ctx.respond("❌ 请上传 .txt 或 .md 文件", ephemeral=True)
        try:
            content_bytes = await file.read()
            content_str = content_bytes.decode('utf-8')
            count = self.parse_markdown_to_data(content_str)
            self.save_data()
            await ctx.respond(f"✅ 导入成功！共解析出 {count} 个主关键词。", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"❌ 导入失败: {e}", ephemeral=True)

    @qa_group.command(name="初始化重置", description="[管理] ⚠️危险：清空所有数据并恢复为默认预设")
    @is_qa_admin()
    async def reset_to_default(self, ctx):
        self.qa_data = {}
        count = self.parse_markdown_to_data(INITIAL_MARKDOWN)
        self.save_data()
        await ctx.respond(f"✅ 已执行硬重置！数据已恢复为默认预设（共 {count} 条）。", ephemeral=True)

    @add_entry.error
    @edit_entry.error
    @delete_entry.error
    @export_data.error
    @import_data.error
    @reset_to_default.error
    async def admin_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.respond("🚫 你没有权限执行此操作 (需要指定身份组)。", ephemeral=True)
        else:
            await ctx.respond(f"❌ 发生错误: {error}", ephemeral=True)

def setup(bot):
    bot.add_cog(QuickQA(bot))

