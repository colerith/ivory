import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup, Option
import json
import os
import re

# ================= 配置 =================
QA_FILE = "qa_data.json"
ADMIN_ROLE_ID = 1420698551138385982  # 指定的有权限操作的身份组ID
PAGE_SIZE = 25

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

# 1. 右键菜单专用的选择视图
class RightClickSelectView(discord.ui.View):
    def __init__(self, cog, target_message, page=0):
        super().__init__(timeout=120)
        self.cog = cog
        self.target_message = target_message
        self.keys = list(cog.qa_data.keys())
        self.page = max(0, page)
        self.total_pages = max(1, (len(self.keys) + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page = min(self.page, self.total_pages - 1)
        self.refresh_items()

    def page_text(self):
        return f"请选择要回复的条目（第 {self.page + 1}/{self.total_pages} 页）："

    def get_page_slice(self):
        start = self.page * PAGE_SIZE
        end = start + PAGE_SIZE
        return start, self.keys[start:end]

    def refresh_items(self):
        self.clear_items()
        self.add_item(RightClickSelect(self))

        prev_btn = RightClickPageButton(-1)
        next_btn = RightClickPageButton(1)
        prev_btn.disabled = self.page <= 0
        next_btn.disabled = self.page >= self.total_pages - 1
        self.add_item(prev_btn)
        self.add_item(next_btn)


class RightClickPageButton(discord.ui.Button):
    def __init__(self, step):
        self.step = step
        label = "⬅️ 上一页" if step < 0 else "下一页 ➡️"
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, RightClickSelectView):
            return await interaction.response.send_message("❌ 视图状态异常，请重新打开菜单。", ephemeral=True)

        new_page = view.page + self.step
        new_page = max(0, min(new_page, view.total_pages - 1))
        if new_page == view.page:
            return await interaction.response.defer()

        view.page = new_page
        view.refresh_items()
        await interaction.response.edit_message(content=view.page_text(), view=view)

class RightClickSelect(discord.ui.Select):
    def __init__(self, parent_view: RightClickSelectView):
        self.parent_view = parent_view
        start, page_keys = parent_view.get_page_slice()

        options = []
        for offset, k in enumerate(page_keys):
            label = k[:100]
            options.append(discord.SelectOption(label=label, value=str(start + offset)))

        if not options:
            options.append(discord.SelectOption(label="暂无可用条目", value="-1", default=True))

        super().__init__(
            placeholder="👇 请选择要回复的答疑内容...",
            min_values=1,
            max_values=1,
            options=options,
            disabled=(len(page_keys) == 0),
        )

    async def callback(self, interaction: discord.Interaction):
        picked = self.values[0]
        if picked == "-1":
            return await interaction.response.defer()

        idx = int(picked)
        if not (0 <= idx < len(self.parent_view.keys)):
            return await interaction.response.edit_message(content="❌ 条目不存在或已被删除，请重新打开菜单。", view=None)

        query = self.parent_view.keys[idx]
        try:
            embeds = self.parent_view.cog.get_qa_payload(query)
            await self.parent_view.target_message.reply(content=None, embeds=embeds, mention_author=True)
            await interaction.response.edit_message(content=f"✅ 已成功回复关于 **{query}** 的内容！", view=None)
        except discord.Forbidden:
            await interaction.response.edit_message(content="❌ 无法回复该消息（可能我没有权限或被拉黑）。", view=None)
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.edit_message(content=f"❌ 发送失败: {e}", view=None)

# 2. 新增条目的 Modal (弹窗)
class AddEntryModal(discord.ui.Modal):
    def __init__(self, cog):
        super().__init__(title="新增答疑条目")
        self.cog = cog
        
        self.add_item(discord.ui.InputText(
            label="标题 (关键词)", 
            placeholder="例如：如何使用酒馆",
            max_length=100
        ))
        
        self.add_item(discord.ui.InputText(
            label="内容 (支持Markdown)", 
            placeholder="请输入详细的回答内容...",
            style=discord.InputTextStyle.long,
            max_length=3000
        ))

    async def callback(self, interaction: discord.Interaction):
        title = self.children[0].value.strip()
        content = self.children[1].value.strip()
        
        if title in self.cog.qa_data:
            return await interaction.response.send_message("❌ 该标题已存在，请使用【修改】功能。", ephemeral=True)
            
        self.cog.qa_data[title] = content
        self.cog.save_data()
        await interaction.response.send_message(f"✅ 已添加新条目：`{title}`", ephemeral=True)

# 3. 修改条目的 Modal (弹窗 - 自动填充旧内容)
class EditEntryModal(discord.ui.Modal):
    def __init__(self, cog, old_title, old_content):
        super().__init__(title="修改答疑条目")
        self.cog = cog
        self.original_title = old_title
        
        # 自动填入旧标题
        self.add_item(discord.ui.InputText(
            label="标题 (关键词)", 
            value=old_title,
            max_length=100
        ))
        
        # 自动填入旧内容
        self.add_item(discord.ui.InputText(
            label="内容", 
            value=old_content,
            style=discord.InputTextStyle.long,
            max_length=3000
        ))

    async def callback(self, interaction: discord.Interaction):
        new_title = self.children[0].value.strip()
        new_content = self.children[1].value.strip()
        
        # 如果改了标题，需要判断新标题是否冲突
        if new_title != self.original_title and new_title in self.cog.qa_data:
             return await interaction.response.send_message("❌ 修改后的标题已存在其他条目中，修改失败。", ephemeral=True)
        
        # 如果改了标题，删除旧key
        if new_title != self.original_title:
            del self.cog.qa_data[self.original_title]
            
        self.cog.qa_data[new_title] = new_content
        self.cog.save_data()
        
        msg = f"✅ 已更新条目：`{new_title}`"
        if new_title != self.original_title:
            msg += f" (原标题: {self.original_title})"
            
        await interaction.response.send_message(msg, ephemeral=True)


# ================= 主逻辑 Cog =================

class QuickQA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.qa_data = {}
        self.load_data()

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

    def get_qa_payload(self, query):
        content = self.qa_data[query]
        images = re.findall(r'(https?://.*?\.(?:png|jpg|jpeg|gif|webp))', content, re.IGNORECASE)
        clean_text = content
        clean_text = re.sub(r'!\[.*?\]\(https?://.*?\.(?:png|jpg|jpeg|gif|webp).*?\)', '', clean_text, flags=re.IGNORECASE)
        for img in images:
            clean_text = clean_text.replace(img, "")
        clean_text = clean_text.strip()
        if not clean_text:
            clean_text = "（请查看下方图片详情）"

        embeds = []
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

    # ================= 命令注册 =================

    @commands.message_command(name="快速答疑")
    async def quick_qa_context(self, ctx, message: discord.Message):
        if not self.qa_data:
            return await ctx.respond("❌ 答疑库为空，请先添加内容。", ephemeral=True)
        view = RightClickSelectView(self, message)
        await ctx.respond(view.page_text(), view=view, ephemeral=True)

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
        await ctx.respond(content=f"{user.mention} 👇", embeds=embeds)

   # ================= 管理功能 =================
    def is_qa_admin():
        def predicate(ctx):
            # 1. 先检查是否是服务器管理员 (拥有 Administrator 权限)
            if ctx.author.guild_permissions.administrator:
                return True
            
            # 2. 如果不是管理员，再检查是否有指定的身份组ID
            role = discord.utils.get(ctx.author.roles, id=ADMIN_ROLE_ID)
            return role is not None
        return commands.check(predicate)

    # 升级点 1: 新增改为弹出 Modal
    @qa_group.command(name="新增", description="[管理] 弹出窗口添加新的答疑条目")
    @is_qa_admin()
    async def add_entry(self, ctx):
        # 直接弹出模态框
        modal = AddEntryModal(self)
        await ctx.send_modal(modal)

    # 升级点 2: 修改改为弹出 Modal 并自动抓取旧内容
    @qa_group.command(name="修改", description="[管理] 弹出窗口修改已有条目")
    @is_qa_admin()
    async def edit_entry(self, ctx, title: Option(str, "选择要修改的条目", autocomplete=search_qa_titles)):
        # 1. 检查是否存在
        if title not in self.qa_data:
            return await ctx.respond("❌ 未找到该条目。", ephemeral=True)
        
        # 2. 抓取旧内容
        old_content = self.qa_data[title]
        
        # 3. 传入 Modal 并显示
        modal = EditEntryModal(self, title, old_content)
        await ctx.send_modal(modal)

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

