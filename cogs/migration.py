import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup, Option
import asyncio
import time

# 指定只有管理员能用 
def is_admin():
    def predicate(ctx):
        return ctx.author.guild_permissions.manage_roles
    return commands.check(predicate)

class RoleMigration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_tasks = {} 

    migration_group = SlashCommandGroup("身份组管理", "批量操作身份组")

    @migration_group.command(name="迁移", description="[管理员] 将用户从一个身份组批量迁移/复制到另一个")
    @is_admin()
    async def migrate_roles(
        self, 
        ctx: discord.ApplicationContext,
        source_role: Option(discord.Role, "源身份组（要把这些人选出来）"),
        target_role: Option(discord.Role, "目标身份组（要赋予的新身份）"),
        mode: Option(str, "模式", choices=["复制 (保留源身份组)", "移动 (移除源身份组)"], default="复制 (保留源身份组)")
    ):
        # 1. 安全检查
        if source_role.id == target_role.id:
            return await ctx.respond("❌ 源身份组和目标身份组不能相同。", ephemeral=True)
        
        if target_role >= ctx.guild.me.top_role:
            return await ctx.respond("❌ 机器人的权限不足，无法分配该目标身份组（Bot必须在目标身份组之上）。", ephemeral=True)

        # 2. 获取成员列表
        members_to_process = source_role.members
        total = len(members_to_process)
        
        if total == 0:
            return await ctx.respond(f"⚠️ 源身份组 {source_role.mention} 下没有任何成员。", ephemeral=True)

        # 3. 初始化日志面板
        is_move = "移动" in mode
        action_text = "移动" if is_move else "复制"
        
        embed = discord.Embed(
            title=f"🔄 身份组{action_text}任务开始",
            description=f"**源**: {source_role.mention}\n**目标**: {target_role.mention}\n**总人数**: {total}",
            color=0x3498db
        )
        embed.add_field(name="进度", value="0/0 (0%)", inline=True)
        embed.add_field(name="状态", value="🚀 正在启动...", inline=False)
        
        # 发送初始消息并获取对象以便后续编辑
        log_msg = await ctx.respond(embed=embed)
        
        # 4. 开始处理循环
        success_count = 0
        fail_count = 0
        start_time = time.time()
        
        for index, member in enumerate(members_to_process, 1):
            try:
                # 添加目标身份组
                if target_role not in member.roles:
                    await member.add_roles(target_role, reason=f"批量迁移: 由 {ctx.author} 执行")
                
                # 如果是移动模式，移除源身份组
                if is_move and source_role in member.roles:
                    await member.remove_roles(source_role, reason=f"批量迁移: 由 {ctx.author} 执行")
                
                success_count += 1
                
            except discord.Forbidden:
                fail_count += 1
            except Exception as e:
                print(f"迁移错误 {member}: {e}")
                fail_count += 1
            
            # 5. 更新日志 (每处理5个或者最后时刻更新一次，避免API限制)
            if index % 5 == 0 or index == total:
                progress_percent = int((index / total) * 100)
                elapsed = int(time.time() - start_time)
                
                # 构建进度条
                bar_length = 20
                filled_length = int(bar_length * index // total)
                bar = "█" * filled_length + "░" * (bar_length - filled_length)
                
                new_embed = discord.Embed(
                    title=f"🔄 身份组{action_text}进行中...",
                    color=0xe67e22 if index < total else 0x2ecc71
                )
                new_embed.description = f"**源**: {source_role.mention} -> **目标**: {target_role.mention}"
                new_embed.add_field(name="进度条", value=f"`{bar}` {progress_percent}%", inline=False)
                new_embed.add_field(name="统计", value=f"✅ 成功: {success_count}\n❌ 失败: {fail_count}\n👥 剩余: {total - index}", inline=True)
                new_embed.add_field(name="耗时", value=f"{elapsed}秒", inline=True)
                
                if index == total:
                    new_embed.title = f"✅ 身份组{action_text}完成"
                    new_embed.add_field(name="结果", value="所有操作已执行完毕。", inline=False)
                
                await log_msg.edit_original_response(embed=new_embed)
                
            # 必须加延时防止被Discord判定为滥用API (429 Rate Limit)
            await asyncio.sleep(1) 

    @migrate_roles.error
    async def error_handler(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.respond("🚫 你没有权限管理身份组。", ephemeral=True)
        else:
            await ctx.respond(f"❌ 发生错误: {error}", ephemeral=True)

def setup(bot):
    bot.add_cog(RoleMigration(bot))