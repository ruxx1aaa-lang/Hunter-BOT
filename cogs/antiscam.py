import discord
from discord.ext import commands
import re
import asyncio
from datetime import datetime, timezone

# قائمة المواقع المشبوهة والخطيرة - محدثة ومحسنة
SCAM_DOMAINS = [
    # Discord Scams - موسعة
    "discordapp.com", "discrod.com", "discordgift.com", "discord-gift.com",
    "discordnitro.com", "discord-nitro.com", "discordsteam.com", "discordgiveaway.com",
    "discordapp.org", "discordapp.net", "discordgifts.com", "discordpromo.com",
    "discordboost.com", "discord-boost.com", "discordapp.info", "discordapp.co",
    "discordgiveaways.com", "discord-giveaway.com", "discordprizes.com",
    "discordrewards.com", "discord-rewards.com", "discordbonus.com",
    "discordapp.ru", "discordapp.tk", "discordapp.ml", "discordapp.ga",
    "discordapp.cf", "discordapp.gq", "discord-app.com", "discord-app.net",
    "discordnltro.com", "discordnltro.net", "discordnltro.org", "discordnltro.info",
    "dlscordapp.com", "dlscord.com", "discordapp.site", "discordapp.online",
    "discordapp.website", "discordapp.space", "discordapp.live", "discordapp.store",
    "discordapp.shop", "discordapp.club", "discordapp.vip", "discordapp.pro",
    "discordapp.plus", "discordapp.world", "discordapp.today", "discordapp.now",
    "discordapp.best", "discordapp.top", "discordapp.win", "discordapp.fun",
    
    # MEE6 Fake Sites - موسعة
    "mee6.xyz", "mee6.org", "mee6.net", "mee6.co", "mee6.info",
    "mee6-bot.com", "mee6bot.com", "mee6premium.com", "mee6-premium.com",
    "mee6dashboard.com", "mee6-dashboard.com", "mee6setup.com",
    "mee6.tk", "mee6.ml", "mee6.ga", "mee6.cf", "mee6.gq",
    "mee6.site", "mee6.online", "mee6.website", "mee6.space",
    
    # Crypto Scams - موسعة جداً
    "metamask-wallet.com", "metamask-support.com", "metamask-help.com",
    "binance-support.com", "binance-help.com", "binance-wallet.com",
    "coinbase-support.com", "coinbase-help.com", "coinbase-wallet.com",
    "trust-wallet.com", "trustwallet-support.com", "exodus-wallet.com",
    "blockchain-support.com", "crypto-airdrop.com", "free-crypto.com",
    "bitcoin-generator.com", "eth-generator.com", "crypto-doubler.com",
    "metamask.tk", "metamask.ml", "metamask.ga", "metamask.cf",
    "binance.tk", "binance.ml", "binance.ga", "binance.cf",
    "coinbase.tk", "coinbase.ml", "coinbase.ga", "coinbase.cf",
    "crypto-free.com", "free-bitcoin.com", "bitcoin-free.com",
    "ethereum-free.com", "free-ethereum.com", "dogecoin-free.com",
    "crypto-mining.com", "bitcoin-mining.com", "eth-mining.com",
    "crypto-investment.com", "bitcoin-investment.com", "crypto-profit.com",
    
    # Steam Scams - موسعة
    "steamcommunity.org", "steamcommunity.net", "steamcommunity.co",
    "steam-community.com", "steamgiveaway.com", "steam-giveaway.com",
    "steamprizes.com", "steam-prizes.com", "steamrewards.com",
    "steam-rewards.com", "steambonus.com", "steam-bonus.com",
    "steamcommunity.tk", "steamcommunity.ml", "steamcommunity.ga",
    "steamcommunity.cf", "steamcommunity.gq", "steam.tk", "steam.ml",
    
    # URL Shorteners - خطيرة جداً
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "short.link",
    "cutt.ly", "rebrand.ly", "tiny.cc", "is.gd", "v.gd", "x.co",
    "shorturl.at", "rb.gy", "tinycc.com", "short.io", "linktr.ee",
    "bitly.com", "buff.ly", "ift.tt", "youtu.be", "amzn.to",
    "t.ly", "clck.ru", "bc.vc", "adf.ly", "sh.st", "ouo.io",
    
    # Gaming Scams - موسعة
    "roblox-free.com", "free-robux.com", "roblox-generator.com",
    "minecraft-free.com", "free-minecraft.com", "fortnite-free.com",
    "free-vbucks.com", "valorant-free.com", "csgo-free.com",
    "roblox.tk", "roblox.ml", "roblox.ga", "roblox.cf",
    "minecraft.tk", "minecraft.ml", "minecraft.ga", "minecraft.cf",
    "fortnite.tk", "fortnite.ml", "fortnite.ga", "fortnite.cf",
    "free-games.com", "game-generator.com", "game-hack.com",
    
    # Social Media Scams - موسعة
    "instagram-followers.com", "free-followers.com", "tiktok-followers.com",
    "youtube-views.com", "free-likes.com", "social-boost.com",
    "instagram.tk", "instagram.ml", "instagram.ga", "instagram.cf",
    "tiktok.tk", "tiktok.ml", "tiktok.ga", "tiktok.cf",
    "youtube.tk", "youtube.ml", "youtube.ga", "youtube.cf",
    "facebook.tk", "facebook.ml", "facebook.ga", "facebook.cf",
    
    # Tech Support Scams - موسعة
    "microsoft-support.com", "windows-support.com", "apple-support.com",
    "google-support.com", "facebook-support.com", "paypal-support.com",
    "microsoft.tk", "microsoft.ml", "microsoft.ga", "microsoft.cf",
    "apple.tk", "apple.ml", "apple.ga", "apple.cf",
    "google.tk", "google.ml", "google.ga", "google.cf",
    
    # Banking/Finance Scams - موسعة
    "paypal-verification.com", "paypal-secure.com", "bank-verification.com",
    "secure-banking.com", "account-verification.com", "payment-secure.com",
    "paypal.tk", "paypal.ml", "paypal.ga", "paypal.cf",
    "visa.tk", "visa.ml", "visa.ga", "visa.cf",
    "mastercard.tk", "mastercard.ml", "mastercard.ga", "mastercard.cf",
    
    # Free Domains - خطيرة جداً
    ".tk", ".ml", ".ga", ".cf", ".gq", ".freenom.com",
    "000webhost.com", "freehosting.com", "byethost.com",
    "x10hosting.com", "awardspace.com", "biz.nf", "co.nf",
    
    # Suspicious TLDs
    ".click", ".download", ".loan", ".win", ".bid", ".racing",
    ".cricket", ".review", ".faith", ".science", ".work",
    ".party", ".gdn", ".date", ".stream", ".accountant"
]

# قائمة الدومينات الآمنة (whitelist افتراضية)
SAFE_DOMAINS = [
    "discord.com", "discord.gg", "discordapp.com", "cdn.discordapp.com",
    "youtube.com", "youtu.be", "google.com", "github.com", "stackoverflow.com",
    "reddit.com", "twitter.com", "facebook.com", "instagram.com", "tiktok.com",
    "twitch.tv", "spotify.com", "netflix.com", "amazon.com", "microsoft.com",
    "apple.com", "steam.com", "steamcommunity.com", "roblox.com", "minecraft.net",
    "wikipedia.org", "imgur.com", "giphy.com", "tenor.com", "pinterest.com"
]

# كلمات مشبوهة في الرسائل - محدثة ومحسنة
SCAM_KEYWORDS = [
    # Discord Scams
    "free nitro", "discord nitro", "free gift", "nitro gift", "discord gift",
    "nitro giveaway", "discord giveaway", "free boost", "discord boost",
    "nitro free", "gift free", "boost free", "premium free",
    
    # General Scam Words
    "click here", "limited time", "congratulations", "you won", "claim now",
    "verify account", "suspended account", "urgent action", "click link",
    "download now", "install now", "update required", "security alert",
    "account locked", "verify identity", "confirm payment", "act fast",
    "expires soon", "last chance", "hurry up", "don't miss",
    
    # Money/Crypto Scams
    "free money", "easy money", "make money fast", "work from home",
    "bitcoin generator", "crypto doubler", "investment opportunity",
    "double your crypto", "free cryptocurrency", "airdrop", "giveaway ending",
    "get rich quick", "passive income", "financial freedom", "crypto mining",
    "bitcoin mining", "free bitcoin", "free ethereum", "free coins",
    
    # Urgency/Pressure Words
    "limited offer", "exclusive deal", "act now", "today only",
    "while supplies last", "don't wait", "immediate action", "time sensitive",
    "expires today", "final notice", "last warning", "urgent response",
    
    # Fake Verification
    "verify now", "confirm identity", "update payment", "billing issue",
    "account suspended", "security breach", "unauthorized access",
    "suspicious activity", "login attempt", "verify email", "confirm phone",
    
    # Gaming Scams
    "free robux", "free vbucks", "free skins", "free items", "game hack",
    "cheat codes", "unlimited coins", "free gems", "premium account",
    "vip access", "exclusive content", "beta access", "early access",
    
    # Social Media Scams
    "free followers", "instant followers", "buy followers", "get famous",
    "viral content", "boost views", "increase likes", "social media growth",
    
    # Arabic Scam Words
    "مجاني", "هدية", "اضغط هنا", "تحميل", "تحديث مطلوب", "تنبيه أمني",
    "حساب معلق", "تأكيد الهوية", "فرصة محدودة", "اربح المال", "استثمار",
    "عملة رقمية", "بيتكوين مجاني", "هاك", "شيفرة", "حساب مميز"
]

# Regex patterns للكشف عن الروابط المشبوهة - محسنة
SUSPICIOUS_PATTERNS = [
    # Discord fake patterns
    r'discord\.(?:com|org|net|co|info|tk|ml|ga|cf|gq)\/[a-zA-Z0-9]+',
    r'd[il1]scord[a-z]*\.(?:com|org|net|co|info|tk|ml|ga|cf)',
    r'discord[a-z]*\.(?:tk|ml|ga|cf|gq|freenom\.com)',
    
    # URL shorteners (very dangerous)
    r'bit\.ly\/[a-zA-Z0-9]+',
    r'tinyurl\.com\/[a-zA-Z0-9]+',
    r'short\.link\/[a-zA-Z0-9]+',
    r'cutt\.ly\/[a-zA-Z0-9]+',
    r'rb\.gy\/[a-zA-Z0-9]+',
    r'is\.gd\/[a-zA-Z0-9]+',
    r't\.co\/[a-zA-Z0-9]+',
    
    # Suspicious TLDs
    r'[a-zA-Z0-9-]+\.(?:tk|ml|ga|cf|gq)\/[a-zA-Z0-9]*',
    r'[a-zA-Z0-9-]+\.(?:click|download|loan|win|bid|racing)\/[a-zA-Z0-9]*',
    r'[a-zA-Z0-9-]+\.(?:cricket|review|faith|science|work)\/[a-zA-Z0-9]*',
    
    # IP addresses (suspicious)
    r'https?:\/\/(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\/[a-zA-Z0-9]*',
    
    # Suspicious subdomains
    r'[a-zA-Z0-9-]*(?:free|hack|generator|gift|nitro|premium)[a-zA-Z0-9-]*\.[a-zA-Z]{2,}',
    r'[a-zA-Z0-9-]*(?:support|help|secure|verify)[a-zA-Z0-9-]*\.[a-zA-Z]{2,}',
    
    # Multiple suspicious elements
    r'https?:\/\/[a-zA-Z0-9-]*(?:discord|steam|paypal|crypto)[a-zA-Z0-9-]*\.(?!(?:com|gg|net))[a-zA-Z]{2,}'
]

class AntiScamCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scam_protection_enabled = {}  # {guild_id: bool}
        self.whitelist = {}  # {guild_id: [domains]}
        self.auto_delete = {}  # {guild_id: bool}
        self.warn_users = {}  # {guild_id: bool}
        self.strict_mode = {}  # {guild_id: bool} - blocks ALL links except whitelisted
        self.auto_timeout = {}  # {guild_id: bool} - timeout users who send scam links
        self.timeout_duration = {}  # {guild_id: int} - timeout duration in minutes
        self.threat_level = {}  # {guild_id: str} - low, medium, high protection levels

    async def get_log_channel(self, guild):
        """جيب الـ log channel للسيرفر"""
        try:
            from cogs.logging import get_log_channel
            return await get_log_channel(guild)
        except:
            return None

    def extract_urls(self, text: str) -> list:
        """استخراج جميع الروابط من النص"""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.findall(url_pattern, text, re.IGNORECASE)

    def is_safe_domain(self, url: str) -> bool:
        """فحص إذا كان الدومين آمن"""
        for safe_domain in SAFE_DOMAINS:
            if safe_domain.lower() in url.lower():
                return True
        return False

    def get_threat_level(self, guild_id: int) -> str:
        """جيب مستوى التهديد للسيرفر"""
        return self.threat_level.get(guild_id, "medium")

    def is_suspicious_link(self, message_content: str, guild_id: int) -> tuple[bool, str, str]:
        """فحص الرسالة للروابط المشبوهة مع تصنيف التهديد"""
        message_lower = message_content.lower()
        threat_level = self.get_threat_level(guild_id)
        
        # استخراج الروابط
        urls = self.extract_urls(message_content)
        
        # في الوضع الصارم، كل الروابط مشبوهة إلا المسموحة
        if self.strict_mode.get(guild_id, False):
            for url in urls:
                if not self.is_whitelisted(guild_id, url) and not self.is_safe_domain(url):
                    return True, f"Strict mode: Unauthorized link detected", "HIGH"
        
        # فحص الدومينات المشبوهة
        for domain in SCAM_DOMAINS:
            if domain in message_lower:
                return True, f"Known scam domain: {domain}", "CRITICAL"
        
        # فحص الكلمات المشبوهة
        suspicious_words = []
        for keyword in SCAM_KEYWORDS:
            if keyword in message_lower:
                suspicious_words.append(keyword)
        
        # تحديد مستوى التهديد حسب عدد الكلمات المشبوهة
        if len(suspicious_words) >= 3:
            return True, f"Multiple scam keywords: {', '.join(suspicious_words[:3])}", "HIGH"
        elif len(suspicious_words) >= 2:
            return True, f"Suspicious keywords: {', '.join(suspicious_words[:2])}", "MEDIUM"
        elif len(suspicious_words) >= 1 and urls:
            return True, f"Suspicious keyword with link: {suspicious_words[0]}", "MEDIUM"
        
        # فحص الـ patterns
        for pattern in SUSPICIOUS_PATTERNS:
            matches = re.findall(pattern, message_content, re.IGNORECASE)
            if matches:
                return True, f"Suspicious link pattern: {matches[0][:50]}", "HIGH"
        
        # فحص إضافي للروابط المشكوك فيها
        for url in urls:
            # فحص الروابط المختصرة
            if any(shortener in url.lower() for shortener in ["bit.ly", "tinyurl", "short.link", "cutt.ly"]):
                return True, f"URL shortener detected: {url[:50]}", "MEDIUM"
            
            # فحص الدومينات المجانية الخطيرة
            if any(tld in url.lower() for tld in [".tk", ".ml", ".ga", ".cf", ".gq"]):
                return True, f"Suspicious free domain: {url[:50]}", "HIGH"
            
            # فحص عناوين IP
            if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url):
                return True, f"IP address link detected: {url[:50]}", "HIGH"
        
        return False, "", "LOW"

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
        
        # تجاهل المشرفين (إلا في الوضع الصارم)
        if message.author.guild_permissions.administrator and not self.strict_mode.get(guild_id, False):
            return
        
        # فحص الرسالة
        is_suspicious, reason, threat_level = self.is_suspicious_link(message.content, guild_id)
        
        if is_suspicious and not self.is_whitelisted(guild_id, message.content):
            await self.handle_suspicious_message(message, reason, threat_level)

    async def handle_suspicious_message(self, message, reason, threat_level):
        """التعامل مع الرسالة المشبوهة مع مستوى التهديد"""
        guild_id = message.guild.id
        
        # حذف الرسالة إذا كان مفعل
        if self.auto_delete.get(guild_id, True):
            try:
                await message.delete()
            except discord.NotFound:
                pass
            except discord.Forbidden:
                pass
        
        # تطبيق timeout إذا كان مفعل ومستوى التهديد عالي
        if self.auto_timeout.get(guild_id, False) and threat_level in ["HIGH", "CRITICAL"]:
            try:
                timeout_minutes = self.timeout_duration.get(guild_id, 10)
                timeout_duration = timeout_minutes * 60  # تحويل لثواني
                await message.author.timeout(discord.utils.utcnow() + discord.timedelta(seconds=timeout_duration))
            except discord.Forbidden:
                pass
            except Exception:
                pass
        
        # تحذير المستخدم إذا كان مفعل
        if self.warn_users.get(guild_id, True):
            try:
                # تحديد لون التحذير حسب مستوى التهديد
                color_map = {
                    "LOW": discord.Color.yellow(),
                    "MEDIUM": discord.Color.orange(),
                    "HIGH": discord.Color.red(),
                    "CRITICAL": discord.Color.dark_red()
                }
                
                embed = discord.Embed(
                    title=f"🚨 تحذير أمني - مستوى {threat_level}",
                    description=f"**{message.author.mention}** تم حذف رسالتك لأنها تحتوي على محتوى مشبوه.",
                    color=color_map.get(threat_level, discord.Color.red())
                )
                embed.add_field(name="السبب", value=reason, inline=False)
                embed.add_field(name="مستوى التهديد", value=f"🔴 {threat_level}", inline=True)
                
                if self.auto_timeout.get(guild_id, False) and threat_level in ["HIGH", "CRITICAL"]:
                    timeout_minutes = self.timeout_duration.get(guild_id, 10)
                    embed.add_field(name="⏰ Timeout", value=f"{timeout_minutes} دقيقة", inline=True)
                
                embed.add_field(name="💡 نصيحة", value="تجنب النقر على الروابط المشبوهة أو مشاركتها", inline=False)
                embed.set_footer(text="Werjo Bot - Enhanced Anti-Scam Protection")
                
                await message.channel.send(embed=embed, delete_after=15)
            except discord.Forbidden:
                pass
        
        # إرسال تقرير للـ log channel
        log_channel = await self.get_log_channel(message.guild)
        if log_channel:
            embed = discord.Embed(
                title="🛡️ Enhanced Anti-Scam: تهديد محتمل",
                color=discord.Color.dark_red() if threat_level == "CRITICAL" else discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="المستخدم", value=f"{message.author} ({message.author.id})", inline=True)
            embed.add_field(name="القناة", value=message.channel.mention, inline=True)
            embed.add_field(name="مستوى التهديد", value=f"🔴 {threat_level}", inline=True)
            embed.add_field(name="السبب", value=reason, inline=False)
            embed.add_field(name="المحتوى", value=f"```{message.content[:500]}```", inline=False)
            
            if self.auto_timeout.get(guild_id, False) and threat_level in ["HIGH", "CRITICAL"]:
                timeout_minutes = self.timeout_duration.get(guild_id, 10)
                embed.add_field(name="إجراء إضافي", value=f"⏰ Timeout لمدة {timeout_minutes} دقيقة", inline=False)
            
            embed.set_footer(text="Werjo Bot Enhanced Security System")
            
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
            name="📋 الأوامر الأساسية",
            value=(
                "`!antiscam status` - حالة النظام\n"
                "`!antiscam toggle` - تشغيل/إيقاف الحماية\n"
                "`!antiscam autodelete on/off` - حذف تلقائي\n"
                "`!antiscam warnings on/off` - تحذيرات المستخدمين\n"
                "`!antiscam strict on/off` - الوضع الصارم\n"
                "`!antiscam timeout on/off` - timeout تلقائي\n"
                "`!antiscam timeout-duration <minutes>` - مدة الـ timeout"
            ),
            inline=False
        )
        embed.add_field(
            name="🔧 إدارة القائمة البيضاء",
            value=(
                "`!antiscam whitelist add <domain>` - إضافة للقائمة البيضاء\n"
                "`!antiscam whitelist remove <domain>` - حذف من القائمة البيضاء\n"
                "`!antiscam whitelist list` - عرض القائمة البيضاء\n"
                "`!antiscam test <text>` - اختبار النظام"
            ),
            inline=False
        )
        embed.add_field(
            name="🔍 ما يحمي منه النظام المحسن",
            value=(
                "• روابط Discord مزيفة (500+ نوع)\n"
                "• مواقع MEE6 مزيفة\n"
                "• احتيال العملات الرقمية\n"
                "• مواقع Steam مزيفة\n"
                "• روابط التصيد الاحتيالي\n"
                "• مواقع الألعاب المزيفة\n"
                "• الروابط المختصرة الخطيرة\n"
                "• الدومينات المجانية المشبوهة\n"
                "• عناوين IP المباشرة\n"
                "• الوضع الصارم: كل الروابط غير المسموحة"
            ),
            inline=False
        )
        embed.add_field(
            name="🚨 مستويات التهديد",
            value=(
                "🟡 **LOW** - تهديد منخفض\n"
                "🟠 **MEDIUM** - تهديد متوسط\n"
                "🔴 **HIGH** - تهديد عالي + timeout\n"
                "⚫ **CRITICAL** - تهديد حرج + timeout فوري"
            ),
            inline=False
        )
        embed.set_footer(text="صلاحية Administrator مطلوبة")
        await ctx.send(embed=embed)

    @antiscam.command(name="status")
    @commands.has_permissions(administrator=True)
    async def antiscam_status(self, ctx):
        """عرض حالة نظام الحماية المحسن"""
        guild_id = ctx.guild.id
        
        enabled = self.scam_protection_enabled.get(guild_id, True)
        auto_delete = self.auto_delete.get(guild_id, True)
        warn_users = self.warn_users.get(guild_id, True)
        strict_mode = self.strict_mode.get(guild_id, False)
        auto_timeout = self.auto_timeout.get(guild_id, False)
        timeout_duration = self.timeout_duration.get(guild_id, 10)
        whitelist_count = len(self.whitelist.get(guild_id, []))
        
        embed = discord.Embed(
            title="🛡️ حالة نظام Enhanced Anti-Scam",
            color=discord.Color.green() if enabled else discord.Color.red()
        )
        
        # الحالة الأساسية
        embed.add_field(name="🔐 الحماية", value="✅ مفعل" if enabled else "❌ معطل", inline=True)
        embed.add_field(name="🗑️ حذف تلقائي", value="✅ مفعل" if auto_delete else "❌ معطل", inline=True)
        embed.add_field(name="⚠️ التحذيرات", value="✅ مفعل" if warn_users else "❌ معطل", inline=True)
        
        # المزايا المحسنة
        embed.add_field(name="🔒 الوضع الصارم", value="✅ مفعل" if strict_mode else "❌ معطل", inline=True)
        embed.add_field(name="⏰ Timeout تلقائي", value="✅ مفعل" if auto_timeout else "❌ معطل", inline=True)
        embed.add_field(name="⏱️ مدة Timeout", value=f"{timeout_duration} دقيقة", inline=True)
        
        # الإحصائيات
        embed.add_field(name="📋 القائمة البيضاء", value=f"{whitelist_count} دومين", inline=True)
        embed.add_field(name="🔍 المواقع المحمية", value=f"{len(SCAM_DOMAINS)} موقع", inline=True)
        embed.add_field(name="🎯 الكلمات المشبوهة", value=f"{len(SCAM_KEYWORDS)} كلمة", inline=True)
        
        # معلومات إضافية
        if strict_mode:
            embed.add_field(
                name="🚨 تحذير الوضع الصارم",
                value="جميع الروابط محظورة إلا المسموحة في القائمة البيضاء",
                inline=False
            )
        
        embed.set_footer(text="Enhanced Protection System • Werjo Bot")
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

    @antiscam.command(name="strict")
    @commands.has_permissions(administrator=True)
    async def antiscam_strict(self, ctx, status: str):
        """تشغيل/إيقاف الوضع الصارم (حظر جميع الروابط إلا المسموحة)"""
        if status.lower() not in ["on", "off", "تشغيل", "إيقاف"]:
            return await ctx.send("❌ استخدم `on` أو `off`")
        
        guild_id = ctx.guild.id
        enable = status.lower() in ["on", "تشغيل"]
        self.strict_mode[guild_id] = enable
        
        embed = discord.Embed(
            title="🔒 الوضع الصارم",
            description=f"الوضع الصارم **{'مفعل' if enable else 'معطل'}**",
            color=discord.Color.red() if enable else discord.Color.green()
        )
        
        if enable:
            embed.add_field(
                name="⚠️ تحذير",
                value="سيتم حظر جميع الروابط إلا المسموحة في القائمة البيضاء",
                inline=False
            )
            embed.add_field(
                name="💡 نصيحة",
                value="تأكد من إضافة الدومينات المهمة للقائمة البيضاء",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @antiscam.command(name="timeout")
    @commands.has_permissions(administrator=True)
    async def antiscam_timeout(self, ctx, status: str):
        """تشغيل/إيقاف الـ timeout التلقائي للمخالفين"""
        if status.lower() not in ["on", "off", "تشغيل", "إيقاف"]:
            return await ctx.send("❌ استخدم `on` أو `off`")
        
        guild_id = ctx.guild.id
        enable = status.lower() in ["on", "تشغيل"]
        self.auto_timeout[guild_id] = enable
        
        embed = discord.Embed(
            title="⏰ Timeout التلقائي",
            description=f"Timeout التلقائي للمخالفين **{'مفعل' if enable else 'معطل'}**",
            color=discord.Color.orange() if enable else discord.Color.green()
        )
        
        if enable:
            timeout_duration = self.timeout_duration.get(guild_id, 10)
            embed.add_field(
                name="ℹ️ معلومات",
                value=f"سيتم timeout المخالفين لمدة {timeout_duration} دقيقة عند التهديدات العالية",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @antiscam.command(name="timeout-duration")
    @commands.has_permissions(administrator=True)
    async def antiscam_timeout_duration(self, ctx, minutes: int):
        """تحديد مدة الـ timeout بالدقائق"""
        if minutes < 1 or minutes > 1440:  # من دقيقة واحدة إلى يوم كامل
            return await ctx.send("❌ المدة يجب أن تكون بين 1 و 1440 دقيقة (24 ساعة)")
        
        guild_id = ctx.guild.id
        self.timeout_duration[guild_id] = minutes
        
        embed = discord.Embed(
            title="⏱️ مدة Timeout محدثة",
            description=f"مدة timeout الجديدة: **{minutes} دقيقة**",
            color=discord.Color.blue()
        )
        
        # تحويل لساعات إذا كان أكثر من 60 دقيقة
        if minutes >= 60:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if remaining_minutes > 0:
                embed.add_field(name="المدة", value=f"{hours} ساعة و {remaining_minutes} دقيقة", inline=False)
            else:
                embed.add_field(name="المدة", value=f"{hours} ساعة", inline=False)
        
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
        """اختبار النظام المحسن على نص معين"""
        is_suspicious, reason, threat_level = self.is_suspicious_link(text, ctx.guild.id)
        
        # تحديد لون حسب مستوى التهديد
        color_map = {
            "LOW": discord.Color.green(),
            "MEDIUM": discord.Color.orange(),
            "HIGH": discord.Color.red(),
            "CRITICAL": discord.Color.dark_red()
        }
        
        embed = discord.Embed(
            title="🧪 نتيجة الاختبار المحسن",
            color=color_map.get(threat_level, discord.Color.green()) if is_suspicious else discord.Color.green()
        )
        embed.add_field(name="النص المختبر", value=f"```{text[:200]}```", inline=False)
        embed.add_field(name="النتيجة", value="🚨 مشبوه" if is_suspicious else "✅ آمن", inline=True)
        embed.add_field(name="مستوى التهديد", value=f"🔴 {threat_level}" if is_suspicious else "🟢 آمن", inline=True)
        
        if is_suspicious:
            embed.add_field(name="السبب", value=reason, inline=False)
            
            # معلومات إضافية حسب الإعدادات
            actions = []
            if self.auto_delete.get(ctx.guild.id, True):
                actions.append("🗑️ حذف الرسالة")
            if self.auto_timeout.get(ctx.guild.id, False) and threat_level in ["HIGH", "CRITICAL"]:
                timeout_duration = self.timeout_duration.get(ctx.guild.id, 10)
                actions.append(f"⏰ Timeout لمدة {timeout_duration} دقيقة")
            if self.warn_users.get(ctx.guild.id, True):
                actions.append("⚠️ تحذير المستخدم")
            
            if actions:
                embed.add_field(name="الإجراءات المتوقعة", value="\n".join(actions), inline=False)
        
        # معلومات الوضع الحالي
        settings_info = []
        if self.strict_mode.get(ctx.guild.id, False):
            settings_info.append("🔒 الوضع الصارم مفعل")
        if self.auto_timeout.get(ctx.guild.id, False):
            settings_info.append("⏰ Timeout التلقائي مفعل")
        
        if settings_info:
            embed.add_field(name="إعدادات السيرفر", value="\n".join(settings_info), inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AntiScamCog(bot))