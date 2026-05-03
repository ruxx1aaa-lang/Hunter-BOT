import discord
from discord.ext import commands
import re
import asyncio
from datetime import datetime, timezone

# قائمة المواقع المشبوهة والخطيرة
SCAM_DOMAINS = [
    # Discord Scams
    "discordapp.com", "discrod.com", "discordgift.com", "discord-gift.com",
    "discordnitro.com", "discord-nitro.com", "discordsteam.com", "discordgiveaway.com",
    "discordapp.org", "discordapp.net", "discordgifts.com", "discordpromo.com",
    "discordboost.com", "discord-boost.com", "discordapp.info", "discordapp.co",
    "discordgiveaways.com", "discord-giveaway.com", "discordprizes.com",
    "discordrewards.com", "discord-rewards.com", "discordbonus.com",
    
    # MEE6 Fake Sites
    "mee6.xyz", "mee6.org", "mee6.net", "mee6.co", "mee6.info",
    "mee6-bot.com", "mee6bot.com", "mee6premium.com", "mee6-premium.com",
    "mee6dashboard.com", "mee6-dashboard.com", "mee6setup.com",
    
    # Crypto Scams
    "metamask-wallet.com", "metamask-support.com", "metamask-help.com",
    "binance-support.com", "binance-help.com", "binance-wallet.com",
    "coinbase-support.com", "coinbase-help.com", "coinbase-wallet.com",
    "trust-wallet.com", "trustwallet-support.com", "exodus-wallet.com",
    "blockchain-support.com", "crypto-airdrop.com", "free-crypto.com",
    "bitcoin-generator.com", "eth-generator.com", "crypto-doubler.com",
    
    # Steam Scams
    "steamcommunity.org", "steamcommunity.net", "steamcommunity.co",
    "steam-community.com", "steamgiveaway.com", "steam-giveaway.com",
    "steamprizes.com", "steam-prizes.com", "steamrewards.com",
    "steam-rewards.com", "steambonus.com", "steam-bonus.com",
    
    # General Phishing
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "short.link",
    "cutt.ly", "rebrand.ly", "tiny.cc", "is.gd", "v.gd", "x.co",
    
    # Gaming Scams
    "roblox-free.com", "free-robux.com", "roblox-generator.com",
    "minecraft-free.com", "free-minecraft.com", "fortnite-free.com",
    "free-vbucks.com", "valorant-free.com", "csgo-free.com",
    
    # Social Media Scams
    "instagram-followers.com", "free-followers.com", "tiktok-followers.com",
    "youtube-views.com", "free-likes.com", "social-boost.com",
    
    # Tech Support Scams
    "microsoft-support.com", "windows-support.com", "apple-support.com",
    "google-support.com", "facebook-support.com", "paypal-support.com",
    
    # Banking/Finance Scams
    "paypal-verification.com", "paypal-secure.com", "bank-verification.com",
    "secure-banking.com", "account-verification.com", "payment-secure.com"
]

# كلمات مشبوهة في الرسائل
SCAM_KEYWORDS = [
    "free nitro", "discord nitro", "free gift", "click here", "limited time",
    "congratulations", "you won", "claim now", "verify account", "suspended account",
    "urgent action", "click link", "download now", "install now", "update required",
    "security alert", "account locked", "verify identity", "confirm payment",
    "free money", "easy money", "make money fast", "work from home",
    "bitcoin generator", "crypto doubler", "investment opportunity",
    "double your crypto", "free cryptocurrency", "airdrop", "giveaway ending",
    "last chance", "act now", "limited offer", "exclusive deal",
    "مجاني", "هدية", "اضغط هنا", "تحميل", "تحديث مطلوب", "تنبيه أمني"
]

# Regex patterns للكشف عن الروابط المشبوهة
SUSPICIOUS_PATTERNS = [
    r'discord\.(?:com|org|net|co|info)\/[a-zA-Z0-9]+',  # Discord fake links
    r'bit\.ly\/[a-zA-Z0-9]+',  # Bitly links
    r'tinyurl\.com\/[a-zA-Z0-9]+',  # TinyURL links
    r'[a-zA-Z0-9-]+\.tk\/[a-zA-Z0-9]*',  # .tk domains (often used for scams)
    r'[a-zA-Z0-9-]+\.ml\/[a-zA-Z0-9]*',  # .ml domains
    r'[a-zA-Z0-9-]+\.ga\/[a-zA-Z0-9]*',  # .ga domains
    r'[a-zA-Z0-9-]+\.cf\/[a-zA-Z0-9]*',  # .cf domains
]

class AntiScamCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scam_protection_enabled = {}  # {guild_id: bool}
        self.whitelist = {}  # {guild_id: [domains]}
        self.auto_delete = {}  # {guild_id: bool}
        self.warn_users = {}  # {guild_id: bool}

    async def get_log_channel(self, guild):
        """جيب الـ log channel للسيرفر"""
        try:
            from cogs.logging import get_log_channel
            return await get_log_channel(guild)
        except:
            return None

    def is_suspicious_link(self, message_content: str) -> tuple[bool, str]:
        """فحص الرسالة للروابط المشبوهة"""
        message_lower = message_content.lower()
        
        # فحص الدومينات المشبوهة
        for domain in SCAM_DOMAINS:
            if domain in message_lower:
                return True, f"Suspicious domain detected: {domain}"
        
        # فحص الكلمات المشبوهة
        suspicious_words = []
        for keyword in SCAM_KEYWORDS:
            if keyword in message_lower:
                suspicious_words.append(keyword)
        
        if len(suspicious_words) >= 2:  # إذا كان فيه كلمتين مشبوهتين أو أكتر
            return True, f"Suspicious keywords: {', '.join(suspicious_words[:3])}"
        
        # فحص الـ patterns
        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, message_content, re.IGNORECASE):
                return True, f"Suspicious link pattern detected"
        
        return False, ""

    def is_whitelisted(self, guild_id: int, content: str) -> bool:
        """فحص إذا كان الرابط في الـ whitelist"""
        if guild_id not in self.whitelist:
            return False
        
        for domain in self.whitelist[guild_id]:
            if domain.lower() in content.lower():
                return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        
        guild_id = message.guild.id
        
        # تحقق من تفعيل الحماية
        if not self.scam_protection_enabled.get(guild_id, True):
            return
        
        # تجاهل المشرفين
        if message.author.guild_permissions.administrator:
            return
        
        # فحص الرسالة
        is_suspicious, reason = self.is_suspicious_link(message.content)
        
        if is_suspicious and not self.is_whitelisted(guild_id, message.content):
            await self.handle_suspicious_message(message, reason)

    async def handle_suspicious_message(self, message, reason):
        """التعامل مع الرسالة المشبوهة"""
        guild_id = message.guild.id
        
        # حذف الرسالة إذا كان مفعل
        if self.auto_delete.get(guild_id, True):
            try:
                await message.delete()
            except discord.NotFound:
                pass
            except discord.Forbidden:
                pass
        
        # تحذير المستخدم إذا كان مفعل
        if self.warn_users.get(guild_id, True):
            try:
                embed = discord.Embed(
                    title="⚠️ تحذير أمني",
                    description=f"**{message.author.mention}** تم حذف رسالتك لأنها تحتوي على محتوى مشبوه.",
                    color=discord.Color.red()
                )
                embed.add_field(name="السبب", value=reason, inline=False)
                embed.add_field(name="💡 نصيحة", value="تجنب النقر على الروابط المشبوهة أو مشاركتها", inline=False)
                embed.set_footer(text="Werjo Bot - Anti-Scam Protection")
                
                await message.channel.send(embed=embed, delete_after=10)
            except discord.Forbidden:
                pass
        
        # إرسال تقرير للـ log channel
        log_channel = await self.get_log_channel(message.guild)
        if log_channel:
            embed = discord.Embed(
                title="🛡️ Anti-Scam: رسالة مشبوهة محذوفة",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="المستخدم", value=f"{message.author} ({message.author.id})", inline=True)
            embed.add_field(name="القناة", value=message.channel.mention, inline=True)
            embed.add_field(name="السبب", value=reason, inline=False)
            embed.add_field(name="المحتوى", value=f"```{message.content[:500]}```", inline=False)
            embed.set_footer(text="Werjo Bot Security System")
            
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass

    @commands.group(name="antiscam", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def antiscam(self, ctx):
        """إدارة نظام الحماية من الاحتيال"""
        embed = discord.Embed(
            title="🛡️ Anti-Scam Protection",
            description="**نظام حماية متطور ضد الاحتيال والروابط المشبوهة**",
            color=0x2B2D31
        )
        embed.add_field(
            name="📋 الأوامر المتاحة",
            value=(
                "`!antiscam status` - حالة النظام\n"
                "`!antiscam toggle` - تشغيل/إيقاف الحماية\n"
                "`!antiscam autodelete on/off` - حذف تلقائي\n"
                "`!antiscam warnings on/off` - تحذيرات المستخدمين\n"
                "`!antiscam whitelist add <domain>` - إضافة للقائمة البيضاء\n"
                "`!antiscam whitelist remove <domain>` - حذف من القائمة البيضاء\n"
                "`!antiscam whitelist list` - عرض القائمة البيضاء\n"
                "`!antiscam test <text>` - اختبار النظام"
            ),
            inline=False
        )
        embed.add_field(
            name="🔍 ما يحمي منه النظام",
            value=(
                "• روابط Discord مزيفة\n"
                "• مواقع MEE6 مزيفة\n"
                "• احتيال العملات الرقمية\n"
                "• مواقع Steam مزيفة\n"
                "• روابط التصيد الاحتيالي\n"
                "• مواقع الألعاب المزيفة"
            ),
            inline=False
        )
        embed.set_footer(text="صلاحية Administrator مطلوبة")
        await ctx.send(embed=embed)

    @antiscam.command(name="status")
    @commands.has_permissions(administrator=True)
    async def antiscam_status(self, ctx):
        """عرض حالة نظام الحماية"""
        guild_id = ctx.guild.id
        
        enabled = self.scam_protection_enabled.get(guild_id, True)
        auto_delete = self.auto_delete.get(guild_id, True)
        warn_users = self.warn_users.get(guild_id, True)
        whitelist_count = len(self.whitelist.get(guild_id, []))
        
        embed = discord.Embed(
            title="🛡️ حالة نظام Anti-Scam",
            color=discord.Color.green() if enabled else discord.Color.red()
        )
        embed.add_field(name="🔐 الحماية", value="✅ مفعل" if enabled else "❌ معطل", inline=True)
        embed.add_field(name="🗑️ حذف تلقائي", value="✅ مفعل" if auto_delete else "❌ معطل", inline=True)
        embed.add_field(name="⚠️ التحذيرات", value="✅ مفعل" if warn_users else "❌ معطل", inline=True)
        embed.add_field(name="📋 القائمة البيضاء", value=f"{whitelist_count} دومين", inline=True)
        embed.add_field(name="🔍 المواقع المحمية", value=f"{len(SCAM_DOMAINS)} موقع", inline=True)
        embed.add_field(name="🎯 الكلمات المشبوهة", value=f"{len(SCAM_KEYWORDS)} كلمة", inline=True)
        
        await ctx.send(embed=embed)

    @antiscam.command(name="toggle")
    @commands.has_permissions(administrator=True)
    async def antiscam_toggle(self, ctx):
        """تشغيل/إيقاف نظام الحماية"""
        guild_id = ctx.guild.id
        current = self.scam_protection_enabled.get(guild_id, True)
        self.scam_protection_enabled[guild_id] = not current
        
        status = "تم تشغيل" if not current else "تم إيقاف"
        color = discord.Color.green() if not current else discord.Color.red()
        
        embed = discord.Embed(
            title=f"🛡️ {status} نظام Anti-Scam",
            description=f"نظام الحماية من الاحتيال **{'مفعل' if not current else 'معطل'}** الآن",
            color=color
        )
        await ctx.send(embed=embed)

    @antiscam.command(name="autodelete")
    @commands.has_permissions(administrator=True)
    async def antiscam_autodelete(self, ctx, status: str):
        """تشغيل/إيقاف الحذف التلقائي"""
        if status.lower() not in ["on", "off", "تشغيل", "إيقاف"]:
            return await ctx.send("❌ استخدم `on` أو `off`")
        
        guild_id = ctx.guild.id
        enable = status.lower() in ["on", "تشغيل"]
        self.auto_delete[guild_id] = enable
        
        embed = discord.Embed(
            title="🗑️ الحذف التلقائي",
            description=f"الحذف التلقائي للرسائل المشبوهة **{'مفعل' if enable else 'معطل'}**",
            color=discord.Color.green() if enable else discord.Color.red()
        )
        await ctx.send(embed=embed)

    @antiscam.command(name="warnings")
    @commands.has_permissions(administrator=True)
    async def antiscam_warnings(self, ctx, status: str):
        """تشغيل/إيقاف تحذيرات المستخدمين"""
        if status.lower() not in ["on", "off", "تشغيل", "إيقاف"]:
            return await ctx.send("❌ استخدم `on` أو `off`")
        
        guild_id = ctx.guild.id
        enable = status.lower() in ["on", "تشغيل"]
        self.warn_users[guild_id] = enable
        
        embed = discord.Embed(
            title="⚠️ تحذيرات المستخدمين",
            description=f"تحذير المستخدمين عند حذف رسائلهم **{'مفعل' if enable else 'معطل'}**",
            color=discord.Color.green() if enable else discord.Color.red()
        )
        await ctx.send(embed=embed)

    @antiscam.group(name="whitelist", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def whitelist(self, ctx):
        """إدارة القائمة البيضاء"""
        await ctx.send("استخدم `add`, `remove`, أو `list`")

    @whitelist.command(name="add")
    @commands.has_permissions(administrator=True)
    async def whitelist_add(self, ctx, domain: str):
        """إضافة دومين للقائمة البيضاء"""
        guild_id = ctx.guild.id
        if guild_id not in self.whitelist:
            self.whitelist[guild_id] = []
        
        domain = domain.lower().replace("http://", "").replace("https://", "").replace("www.", "")
        
        if domain in self.whitelist[guild_id]:
            return await ctx.send(f"❌ `{domain}` موجود بالفعل في القائمة البيضاء")
        
        self.whitelist[guild_id].append(domain)
        await ctx.send(f"✅ تم إضافة `{domain}` للقائمة البيضاء")

    @whitelist.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def whitelist_remove(self, ctx, domain: str):
        """حذف دومين من القائمة البيضاء"""
        guild_id = ctx.guild.id
        if guild_id not in self.whitelist:
            return await ctx.send("❌ القائمة البيضاء فاضية")
        
        domain = domain.lower().replace("http://", "").replace("https://", "").replace("www.", "")
        
        if domain not in self.whitelist[guild_id]:
            return await ctx.send(f"❌ `{domain}` مش موجود في القائمة البيضاء")
        
        self.whitelist[guild_id].remove(domain)
        await ctx.send(f"✅ تم حذف `{domain}` من القائمة البيضاء")

    @whitelist.command(name="list")
    @commands.has_permissions(administrator=True)
    async def whitelist_list(self, ctx):
        """عرض القائمة البيضاء"""
        guild_id = ctx.guild.id
        domains = self.whitelist.get(guild_id, [])
        
        if not domains:
            return await ctx.send("📭 القائمة البيضاء فاضية")
        
        embed = discord.Embed(
            title="📋 القائمة البيضاء",
            description="\n".join(f"• `{domain}`" for domain in domains),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"إجمالي: {len(domains)} دومين")
        await ctx.send(embed=embed)

    @antiscam.command(name="test")
    @commands.has_permissions(administrator=True)
    async def antiscam_test(self, ctx, *, text: str):
        """اختبار النظام على نص معين"""
        is_suspicious, reason = self.is_suspicious_link(text)
        
        embed = discord.Embed(
            title="🧪 نتيجة الاختبار",
            color=discord.Color.red() if is_suspicious else discord.Color.green()
        )
        embed.add_field(name="النص المختبر", value=f"```{text[:200]}```", inline=False)
        embed.add_field(name="النتيجة", value="🚨 مشبوه" if is_suspicious else "✅ آمن", inline=True)
        
        if is_suspicious:
            embed.add_field(name="السبب", value=reason, inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AntiScamCog(bot))