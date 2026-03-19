import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "!hunt ")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))

# Anti-Spam settings
SPAM_MESSAGE_LIMIT = 5       # عدد الرسائل
SPAM_TIME_WINDOW = 5         # في كم ثانية
SPAM_MUTE_DURATION = 300     # مدة الميوت بالثواني (5 دقايق)

# Anti-Raid settings
RAID_JOIN_LIMIT = 10         # عدد الانضمامات
RAID_TIME_WINDOW = 10        # في كم ثانية
NEW_ACCOUNT_DAYS = 7         # الأكونت أقل من كام يوم يتعتبر جديد

# Moderation
WARN_KICK_THRESHOLD = 3      # عدد التحذيرات قبل الكيك
WARN_BAN_THRESHOLD = 5       # عدد التحذيرات قبل الباند

# Forbidden words (أضف الكلمات اللي عايز تفلترها)
FORBIDDEN_WORDS = []

# Suspicious link patterns
SUSPICIOUS_LINKS = ["discord.gg", "bit.ly", "tinyurl.com"]
