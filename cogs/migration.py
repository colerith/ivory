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

    @migration_group.command(name="迁移", description="[管理员] 将源身份组的人员批量赋予目标身份组")
    @is_admin()
    async def migrate_roles(
        self, 
        ctx: discord.ApplicationContext,
        source_role: Option(discord.Role, "源身份组（要把这些人选出来）"),
        target_role: Option(discord.Role, "目标身份组（要赋予的新身份）")
    ):
        # 1. 基础检查
        if source_role.id == target_role.id:
            return await ctx.respond("❌ 源身份组和目标身份组不能相同。", ephemeral=True)
        
        if target_role >= ctx.guild.me.top_role:
            return await ctx.respond("❌ 机器人的权限不足（Bot 必须位于目标身份组之上）。", ephemeral=True)

        await ctx.defer() # 告诉 Discord 这是一个耗时操作

        # 2. 内存筛选 (这一步极快)
        # 逻辑：找出所有“有源身份”且“无目标身份”的人
        members_to_process = [
            m for m in source_role.members 
            if target_role not in m.roles
        ]
        
        total = len(members_to_process)
        if total == 0:
            return await ctx.respond(f"✅ 没有任何成员需要处理！\n({source_role.mention} 的所有成员都已经拥有 {target_role.mention} 了)", ephemeral=True)

        # 3. 初始化进度面板
        start_time = time.time()
        success_count = 0
        fail_count = 0
        processed_count = 0

        embed = discord.Embed(
            title="🚀 极速迁移开始",
            description=f"**源**: {source_role.mention}\n**目标**: {target_role.mention}\n**待处理人数**: {total}",
            color=0x3498db
        )
        embed.add_field(name="状态", value="正在通过并发队列处理...", inline=False)
        msg = await ctx.respond(embed=embed)

        # 4. 并发控制
        # Semaphore(10) 表示同时允许 10 个请求发送给 Discord
        # 设置太高会被 Discord 暂时封锁 (429)，10 是个比较安全的数值
        sem = asyncio.Semaphore(10) 

        async def worker(member):
            nonlocal success_count, fail_count, processed_count
            async with sem: # 获取锁
                try:
                    await member.add_roles(target_role, reason=f"批量迁移: {ctx.author.name}")
                    success_count += 1
                except discord.Forbidden:
                    fail_count += 1
                except Exception as e:
                    print(f"Error adding role to {member}: {e}")
                    fail_count += 1
                finally:
                    processed_count += 1

        # 5. 启动更新 UI 的后台任务
        # 我们不希望每次处理完一个可以刷新 UI，那样会因为 UI 刷新限制拖慢速度
        # 所以我们单开一个循环，每 2 秒刷新一次界面
        migration_running = True
        
        async def update_ui_loop():
            last_percent = -1
            while migration_running:
                await asyncio.sleep(2) # 每2秒更新一次
                percent = int((processed_count / total) * 100)
                
                # 只有进度变化了才更新
                if percent != last_percent:
                    elapsed = int(time.time() - start_time)
                    speed = round(processed_count / (elapsed + 0.1), 1) # 避免除以0
                    
                    # 动态进度条
                    bar_len = 15
                    filled = int(bar_len * processed_count // total)
                    bar = "█" * filled + "░" * (bar_len - filled)
                    
                    new_embed = discord.Embed(title="🚀 迁移进行中...", color=0xe67e22)
                    new_embed.description = f"**源**: {source_role.mention} -> **目标**: {target_role.mention}"
                    new_embed.add_field(name="进度", value=f"`{bar}` {percent}%", inline=False)
                    new_embed.add_field(name="统计", value=f"✅ 成功: {success_count}\n❌ 失败: {fail_count}\n👥 剩余: {total - processed_count}", inline=True)
                    new_embed.add_field(name="速度", value=f"{speed} 人/秒", inline=True)
                    
                    try:
                        await msg.edit_original_response(embed=new_embed)
                        last_percent = percent
                    except:
                        pass

        ui_task = asyncio.create_task(update_ui_loop())

        # 6. 开始批量执行
        # asyncio.gather 会同时启动所有任务
        tasks = [worker(member) for member in members_to_process]
        await asyncio.gather(*tasks)

        # 7. 结束处理
        migration_running = False
        await ui_task # 等待 UI 循环结束
        
        # 发送最终结果
        total_time = int(time.time() - start_time)
        final_embed = discord.Embed(title="✅ 迁移完成", color=0x2ecc71)
        final_embed.description = f"**源**: {source_role.mention} -> **目标**: {target_role.mention}"
        final_embed.add_field(name="最终统计", value=f"总耗时: {total_time}秒\n成功: {success_count}\n失败: {fail_count}", inline=False)
        
        await msg.edit_original_response(embed=final_embed)

    @migrate_roles.error
    async def error_handler(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.respond("🚫 你没有权限管理身份组。", ephemeral=True)
        else:
            await ctx.respond(f"❌ 发生错误: {error}", ephemeral=True)

def setup(bot):
    bot.add_cog(RoleMigration(bot))
