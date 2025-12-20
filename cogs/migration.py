import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup, Option
import asyncio
import time

def is_admin():
    def predicate(ctx):
        # 只要有管理身份组权限即可
        return ctx.author.guild_permissions.manage_roles
    return commands.check(predicate)

class RoleMigration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    migration_group = SlashCommandGroup("身份组管理", "批量操作身份组")

    @migration_group.command(name="迁移", description="[管理员] 稳重迁移：逐个将源身份组人员赋予目标身份组")
    @is_admin()
    async def migrate_roles(
        self, 
        ctx: discord.ApplicationContext,
        source_role: Option(discord.Role, "源身份组"),
        target_role: Option(discord.Role, "目标身份组")
    ):
        # 1. 基础检查
        if source_role.id == target_role.id:
            return await ctx.respond("❌ 源身份组和目标身份组不能相同。", ephemeral=True)
        
        if target_role >= ctx.guild.me.top_role:
            return await ctx.respond("❌ 机器人的权限不足（Bot 必须位于目标身份组之上）。", ephemeral=True)

        await ctx.defer() # 挂起响应，防止超时

        # 2. 筛选名单
        # 依然先筛选出需要处理的人，避免无意义的 API 调用
        members_to_process = [
            m for m in source_role.members 
            if target_role not in m.roles
        ]
        
        total = len(members_to_process)
        if total == 0:
            return await ctx.respond(f"✅ 没有任何成员需要处理！\n({source_role.mention} 的所有成员都已经拥有 {target_role.mention} 了)", ephemeral=True)

        # 3. 初始化面板
        start_time = time.time()
        success_count = 0
        fail_count = 0
        
        embed = discord.Embed(
            title="🐢 稳重迁移模式启动",
            description=f"**源**: {source_role.mention}\n**目标**: {target_role.mention}\n**待处理人数**: {total}",
            color=0x3498db
        )
        embed.add_field(name="进度", value="0/0 (0%)", inline=True)
        embed.add_field(name="状态", value="正在逐个处理...", inline=False)
        
        # 获取消息对象
        msg = await ctx.respond(embed=embed)

        # 4. 开始循环处理 (串行)
        for i, member in enumerate(members_to_process, 1):
            try:
                # 执行添加身份组
                await member.add_roles(target_role, reason=f"批量迁移: {ctx.author.name}")
                success_count += 1
            except discord.Forbidden:
                fail_count += 1
                print(f"权限不足无法操作: {member.name}")
            except Exception as e:
                fail_count += 1
                print(f"操作 {member.name} 失败: {e}")

            # 5. 更新 UI (策略：每处理5个人，或者最后一个人时更新一次)
            # 这样可以避免 "已在短时间内编辑该消息太多次" 的限制
            if i % 5 == 0 or i == total:
                elapsed = int(time.time() - start_time)
                percent = int((i / total) * 100)
                
                # 进度条绘制
                bar_len = 15
                filled = int(bar_len * i // total)
                bar = "█" * filled + "░" * (bar_len - filled)
                
                new_embed = discord.Embed(title="🐢 迁移进行中...", color=0xe67e22)
                new_embed.description = f"**源**: {source_role.mention} -> **目标**: {target_role.mention}"
                new_embed.add_field(name="进度", value=f"`{bar}` {percent}%", inline=False)
                new_embed.add_field(name="统计", value=f"✅ 成功: {success_count}\n❌ 失败: {fail_count}\n👥 剩余: {total - i}", inline=True)
                new_embed.add_field(name="耗时", value=f"{elapsed}秒", inline=True)
                
                try:
                    await msg.edit(embed=new_embed)
                except:
                    pass # 如果更新失败（比如网络波动），不影响主流程继续

            # 6. 安全延时 (稳重模式核心)
            # 暂停 0.5 秒，防止触发 API 速率限制
            await asyncio.sleep(0.5)

        # 7. 结束
        total_time = int(time.time() - start_time)
        final_embed = discord.Embed(title="✅ 迁移完成", color=0x2ecc71)
        final_embed.description = f"**源**: {source_role.mention} -> **目标**: {target_role.mention}"
        final_embed.add_field(name="最终结果", value=f"总耗时: {total_time}秒\n成功: {success_count} 人\n失败: {fail_count} 人", inline=False)
        
        await msg.edit(embed=final_embed)

    @migrate_roles.error
    async def error_handler(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.respond("🚫 你没有权限管理身份组。", ephemeral=True)
        else:
            await ctx.respond(f"❌ 发生错误: {error}", ephemeral=True)

def setup(bot):
    bot.add_cog(RoleMigration(bot))
