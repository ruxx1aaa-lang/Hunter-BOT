import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
import base64
import shutil
import json
import subprocess
from collections import deque
import sys

# ─── Auto-Update yt-dlp ────────────────────────────────────────────────────
async def update_ytdlp():
    """تحديث yt-dlp تلقائياً"""
    try:
        print("[Music] Checking for yt-dlp updates...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"], 
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("[Music] yt-dlp updated successfully")
        else:
            print(f"[Music] yt-dlp update failed: {result.stderr}")
    except Exception as e:
        print(f"[Music] yt-dlp update error: {e}")

# ─── Cookies ───────────────────────────────────────────────────────────────
_cookies_content = os.getenv("YOUTUBE_COOKIES", "")
COOKIES_FILE = None
if _cookies_content:
    COOKIES_FILE = "/tmp/cookies.txt"
    try:
        decoded = base64.b64decode(_cookies_content).decode("utf-8")
        with open(COOKIES_FILE, "w") as f:
            f.write(decoded)
    except Exception:
        with open(COOKIES_FILE, "w") as f:
            f.write(_cookies_content)
elif os.path.exists("cookies.txt"):
    COOKIES_FILE = "cookies.txt"

# ─── FFmpeg ────────────────────────────────────────────────────────────────
def ensure_ffmpeg():
    path = shutil.which("ffmpeg")
    if path:
        return path
    print("[Music] ffmpeg not found, installing via apt...")
    try:
        subprocess.run(["apt-get", "update", "-y"], check=True, capture_output=True)
        subprocess.run(["apt-get", "install", "-y", "ffmpeg"], check=True, capture_output=True)
        path = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
        print(f"[Music] ffmpeg installed at {path}")
        return path
    except Exception as e:
        print(f"[Music] apt install failed: {e}")
    return "ffmpeg"

FFMPEG_PATH = ensure_ffmpeg()
print(f"[Music] FFmpeg path: {FFMPEG_PATH}")

FFMPEG_OPTIONS = {
    "executable": FFMPEG_PATH,
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn -bufsize 512k",
}

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "default_search": "scsearch",
    "source_address": "0.0.0.0",
    "extract_flat": False,
}

PLAYLISTS_FILE = "playlists.json"


# ─── Playlist Storage ──────────────────────────────────────────────────────
def load_playlists() -> dict:
    if os.path.exists(PLAYLISTS_FILE):
        with open(PLAYLISTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_playlists(data: dict):
    with open(PLAYLISTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── Player Buttons View ───────────────────────────────────────────────────
class PlayerView(discord.ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=None)
        self.cog = cog
        self.ctx = ctx

    @discord.ui.button(emoji="⏸", style=discord.ButtonStyle.secondary, custom_id="pause_resume")
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.response.send_message("❌ مفيش حاجة بتشتغل.", ephemeral=True)
        if vc.is_playing():
            vc.pause()
            button.emoji = "▶️"
            await interaction.response.edit_message(view=self)
        elif vc.is_paused():
            vc.resume()
            button.emoji = "⏸"
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.send_message("❌ مفيش حاجة بتشتغل.", ephemeral=True)

    @discord.ui.button(emoji="⏭", style=discord.ButtonStyle.secondary, custom_id="skip")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.ctx.voice_client
        if not vc or not vc.is_playing():
            return await interaction.response.send_message("❌ مفيش حاجة بتشتغل.", ephemeral=True)
        vc.stop()
        await interaction.response.send_message("⏭ تم السكيب!", ephemeral=True)

    @discord.ui.button(emoji="⏹", style=discord.ButtonStyle.danger, custom_id="stop")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.response.send_message("❌ مفيش حاجة.", ephemeral=True)
        guild_id = self.ctx.guild.id
        self.cog.queues[guild_id] = deque()
        self.cog.current.pop(guild_id, None)
        self.cog.loop_mode[guild_id] = False
        vc.stop()
        await interaction.response.send_message("⏹ تم إيقاف الموسيقى.", ephemeral=True)

    @discord.ui.button(emoji="🔂", style=discord.ButtonStyle.secondary, custom_id="loop")
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.ctx.guild.id
        self.cog.loop_mode[guild_id] = not self.cog.loop_mode.get(guild_id, False)
        is_loop = self.cog.loop_mode[guild_id]
        button.style = discord.ButtonStyle.success if is_loop else discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("🔂 تكرار شغال" if is_loop else "➡️ تكرار وقف", ephemeral=True)

    @discord.ui.button(emoji="📋", style=discord.ButtonStyle.primary, custom_id="queue")
    async def queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.ctx.guild.id
        queue = self.cog.get_queue(guild_id)
        current = self.cog.current.get(guild_id)
        if not current and not queue:
            return await interaction.response.send_message("📭 الـ queue فاضي.", ephemeral=True)
        embed = discord.Embed(title="🎶 قائمة الأغاني", color=discord.Color.purple())
        if current:
            embed.add_field(
                name="▶️ بيشتغل دلوقتي",
                value=f"**{current['title']}** `{self.cog.fmt(current['duration'])}`",
                inline=False,
            )
        if queue:
            lines = [f"`{i}.` {t['title']} `{self.cog.fmt(t['duration'])}`"
                     for i, t in enumerate(list(queue)[:10], 1)]
            if len(queue) > 10:
                lines.append(f"... و **{len(queue)-10}** أغنية تانية")
            embed.add_field(name="📋 القادم", value="\n".join(lines), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ─── Cog ───────────────────────────────────────────────────────────────────
class MusicCog(commands.Cog, name="Music"):
    def __init__(self, bot):
        self.bot = bot
        self.queues: dict[int, deque] = {}
        self.current: dict[int, dict] = {}
        self.loop_mode: dict[int, bool] = {}
        self.youtube_blocked = False  # تتبع حالة حظر YouTube
        self.last_ytdlp_update = 0  # آخر تحديث لـ yt-dlp
        
        # تحديث yt-dlp عند بدء التشغيل
        asyncio.create_task(self.startup_update())

    async def startup_update(self):
        """تحديث yt-dlp عند بدء التشغيل"""
        await asyncio.sleep(5)  # انتظار حتى يكتمل تحميل البوت
        await update_ytdlp()
        self.last_ytdlp_update = asyncio.get_event_loop().time()

    async def check_ytdlp_update(self):
        """فحص الحاجة لتحديث yt-dlp (كل 6 ساعات)"""
        current_time = asyncio.get_event_loop().time()
        if current_time - self.last_ytdlp_update > 21600:  # 6 ساعات
            await update_ytdlp()
            self.last_ytdlp_update = current_time

    def get_queue(self, guild_id: int) -> deque:
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        return self.queues[guild_id]

    def fmt(self, s: int) -> str:
        if not s:
            return "Live 🔴"
        m, s = divmod(int(s), 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    async def search_and_extract(self, query: str, force_platform: str = None) -> dict | None:
        """استخراج الأغاني مع نظام fallback ذكي"""
        loop = asyncio.get_event_loop()
        
        # فحص تحديث yt-dlp
        await self.check_ytdlp_update()

        def _extract():
            # تحديد المنصة
            is_youtube = "youtube.com" in query or "youtu.be" in query or force_platform == "youtube"
            is_soundcloud = "soundcloud.com" in query or force_platform == "soundcloud"
            is_direct_link = query.startswith("http") and not is_youtube and not is_soundcloud
            
            # محاولة YouTube أولاً (إذا كان مطلوب)
            if is_youtube and not self.youtube_blocked:
                try:
                    opts = YDL_OPTIONS.copy()
                    opts["cookiefile"] = COOKIES_FILE
                    opts["extractor_args"] = {"youtube": {"player_client": ["android", "web_creator", "ios"]}}
                    
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(query, download=False)
                        if info:
                            return self._process_info(info, "YouTube")
                except Exception as e:
                    print(f"[Music] YouTube extraction failed: {e}")
                    if "blocked" in str(e).lower() or "unavailable" in str(e).lower():
                        self.youtube_blocked = True
                        print("[Music] YouTube appears to be blocked, switching to SoundCloud")
            
            # محاولة SoundCloud
            if not is_direct_link:
                try:
                    search_query = query
                    if not query.startswith("http"):
                        search_query = f"scsearch:{query}"
                    
                    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                        info = ydl.extract_info(search_query, download=False)
                        if info and "entries" in info and info["entries"]:
                            return self._process_info(info["entries"][0], "SoundCloud")
                        elif info:
                            return self._process_info(info, "SoundCloud")
                except Exception as e:
                    print(f"[Music] SoundCloud extraction failed: {e}")
            
            # محاولة الروابط المباشرة
            if is_direct_link:
                try:
                    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                        info = ydl.extract_info(query, download=False)
                        if info:
                            return self._process_info(info, "Direct")
                except Exception as e:
                    print(f"[Music] Direct link extraction failed: {e}")
            
            # Fallback: محاولة YouTube مرة أخرى إذا فشل كل شيء
            if not is_youtube and not self.youtube_blocked:
                try:
                    search_query = f"ytsearch:{query}" if not query.startswith("http") else query
                    opts = YDL_OPTIONS.copy()
                    opts["cookiefile"] = COOKIES_FILE
                    opts["extractor_args"] = {"youtube": {"player_client": ["android", "web_creator"]}}
                    
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(search_query, download=False)
                        if info and "entries" in info and info["entries"]:
                            return self._process_info(info["entries"][0], "YouTube")
                        elif info:
                            return self._process_info(info, "YouTube")
                except Exception as e:
                    print(f"[Music] YouTube fallback failed: {e}")
            
            return None

        try:
            result = await loop.run_in_executor(None, _extract)
            if result:
                # إعادة تعيين حالة الحظر إذا نجحت العملية
                if result.get("source") == "YouTube":
                    self.youtube_blocked = False
            return result
        except Exception as e:
            print(f"[Music] Extraction error: {e}")
            return None

    def _process_info(self, info: dict, source: str) -> dict:
        """معالجة معلومات الأغنية"""
        if not info:
            return None

        url = None
        formats = info.get("formats", [])
        
        # البحث عن أفضل format صوتي
        for f in reversed(formats):
            if f.get("acodec") != "none" and f.get("vcodec") == "none":
                url = f.get("url")
                break
        
        if not url:
            url = info.get("url")
        if not url and formats:
            url = formats[-1].get("url")

        return {
            "url": url,
            "title": info.get("title", "Unknown"),
            "duration": info.get("duration", 0),
            "webpage_url": info.get("webpage_url", ""),
            "thumbnail": info.get("thumbnail", ""),
            "uploader": info.get("uploader", "Unknown"),
            "source": source
        }

    def build_now_playing_embed(self, track: dict, queue_len: int, loop: bool) -> discord.Embed:
        embed = discord.Embed(
            description=f"### 🎵 [{track['title']}]({track['webpage_url']})",
            color=0x2B2D31,
        )
        embed.add_field(name="👤 الفنان", value=track["uploader"] or "Unknown", inline=True)
        embed.add_field(name="⏱ المدة", value=self.fmt(track["duration"]), inline=True)
        embed.add_field(name="🔂 تكرار", value="شغال ✅" if loop else "وقف ❌", inline=True)
        
        # إضافة مصدر الأغنية
        source = track.get("source", "Unknown")
        source_emoji = "🔴" if source == "YouTube" else "🟠" if source == "SoundCloud" else "🎵"
        embed.add_field(name="📡 المصدر", value=f"{source_emoji} {source}", inline=True)
        
        embed.set_footer(text=f"📋 {queue_len} أغنية في الـ queue")
        if track.get("thumbnail"):
            embed.set_thumbnail(url=track["thumbnail"])
        return embed

    async def play_next(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return

        if self.loop_mode.get(guild_id) and guild_id in self.current:
            track = self.current[guild_id]
        elif queue:
            track = queue.popleft()
            self.current[guild_id] = track
        else:
            self.current.pop(guild_id, None)
            await ctx.send("✅ خلصت الـ queue.")
            return

        def after(error):
            if error:
                print(f"[Music] Player error: {error}")
            asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

        try:
            source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(source, volume=0.8)
            vc.play(source, after=after)

            embed = self.build_now_playing_embed(track, len(queue), self.loop_mode.get(guild_id, False))
            view = PlayerView(self, ctx)
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            print(f"[Music] Playback error: {e}")
            await ctx.send(f"❌ خطأ في التشغيل: `{e}`")
            await self.play_next(ctx)

    # ─── Commands ──────────────────────────────────────────────────────────

    @commands.command(name="p", aliases=["play", "شغل"])
    async def play(self, ctx: commands.Context, *, query: str):
        """يشغل أغنية | !p <اسم أو رابط YouTube/SoundCloud>"""
        if not ctx.author.voice:
            return await ctx.send("❌ لازم تكون في فويس شانل الأول!")

        channel = ctx.author.voice.channel
        vc = ctx.voice_client

        if not vc:
            vc = await channel.connect(self_deaf=True)
        elif vc.channel != channel:
            await vc.move_to(channel); await vc.guild.change_voice_state(channel=channel, self_deaf=True)

        # تحديد نوع البحث حسب الـ query
        if query.startswith("http"):
            loading_msg = "🔗 بحمل من الرابط..."
        elif "youtube.com" in query or "youtu.be" in query:
            loading_msg = "🔴 بحمل من YouTube..."
        elif "soundcloud.com" in query:
            loading_msg = "🟠 بحمل من SoundCloud..."
        else:
            loading_msg = "🔍 بدور على الأغنية..."
            
        loading = await ctx.send(loading_msg)
        track = await self.search_and_extract(query)
        await loading.delete()

        if not track or not track.get("url"):
            return await ctx.send("❌ مش لاقي الأغنية دي، جرب اسم تاني أو رابط صحيح.")

        queue = self.get_queue(ctx.guild.id)

        if not vc.is_playing() and not vc.is_paused():
            self.current[ctx.guild.id] = track

            def after(error):
                if error:
                    print(f"[Music] Player error: {error}")
                asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

            source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(source, volume=0.8)
            vc.play(source, after=after)

            embed = self.build_now_playing_embed(track, len(queue), self.loop_mode.get(ctx.guild.id, False))
            view = PlayerView(self, ctx)
            await ctx.send(embed=embed, view=view)
        else:
            queue.append(track)
            source = track.get("source", "Unknown")
            source_emoji = "🔴" if source == "YouTube" else "🟠" if source == "SoundCloud" else "🎵"
            
            embed = discord.Embed(
                description=f"### ➕ اتضافت للـ Queue\n**[{track['title']}]({track['webpage_url']})**",
                color=0x5865F2,
            )
            embed.add_field(name="⏱ المدة", value=self.fmt(track["duration"]), inline=True)
            embed.add_field(name="📋 موقعها", value=f"#{len(queue)}", inline=True)
            embed.add_field(name="📡 المصدر", value=f"{source_emoji} {source}", inline=True)
            if track.get("thumbnail"):
                embed.set_thumbnail(url=track["thumbnail"])
            await ctx.send(embed=embed)

    @commands.command(name="skip", aliases=["s", "سكيب"])
    async def skip(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_playing():
            return await ctx.send("❌ مفيش حاجة بتشتغل.")
        vc.stop()

    @commands.command(name="stop", aliases=["وقف"])
    async def stop(self, ctx):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("❌ البوت مش في فويس شانل.")
        self.queues[ctx.guild.id] = deque()
        self.current.pop(ctx.guild.id, None)
        self.loop_mode[ctx.guild.id] = False
        vc.stop()
        await ctx.send("⏹ تم إيقاف الموسيقى.")

    @commands.command(name="pause", aliases=["بوز"])
    async def pause(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send("⏸ تم الإيقاف المؤقت.")
        else:
            await ctx.send("❌ مفيش حاجة بتشتغل.")

    @commands.command(name="resume", aliases=["r", "كمل"])
    async def resume(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await ctx.send("▶️ تم الاستكمال.")
        else:
            await ctx.send("❌ الأغنية مش متوقفة.")

    @commands.command(name="loop", aliases=["لوب"])
    async def loop_cmd(self, ctx):
        self.loop_mode[ctx.guild.id] = not self.loop_mode.get(ctx.guild.id, False)
        await ctx.send("🔂 تكرار شغال" if self.loop_mode[ctx.guild.id] else "➡️ تكرار وقف")

    @commands.command(name="volume", aliases=["vol", "صوت"])
    async def volume(self, ctx, vol: int):
        vc = ctx.voice_client
        if not vc or not vc.source:
            return await ctx.send("❌ مفيش حاجة بتشتغل.")
        if not 1 <= vol <= 100:
            return await ctx.send("❌ الصوت بين 1 و 100.")
        vc.source.volume = vol / 100
        await ctx.send(f"🔊 الصوت {vol}%")

    @commands.command(name="np", aliases=["nowplaying", "شغال"])
    async def nowplaying(self, ctx):
        current = self.current.get(ctx.guild.id)
        if not current:
            return await ctx.send("❌ مفيش حاجة بتشتغل.")
        embed = self.build_now_playing_embed(current, len(self.get_queue(ctx.guild.id)), self.loop_mode.get(ctx.guild.id, False))
        view = PlayerView(self, ctx)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="queue", aliases=["q", "قائمة"])
    async def show_queue(self, ctx):
        queue = self.get_queue(ctx.guild.id)
        current = self.current.get(ctx.guild.id)
        if not current and not queue:
            return await ctx.send("📭 الـ queue فاضي.")
        embed = discord.Embed(title="🎶 قائمة الأغاني", color=0x2B2D31)
        if current:
            embed.add_field(
                name="▶️ بيشتغل دلوقتي",
                value=f"**{current['title']}** `{self.fmt(current['duration'])}`",
                inline=False,
            )
        if queue:
            lines = [f"`{i}.` {t['title']} `{self.fmt(t['duration'])}`"
                     for i, t in enumerate(list(queue)[:10], 1)]
            if len(queue) > 10:
                lines.append(f"... و **{len(queue)-10}** أغنية تانية")
            embed.add_field(name="📋 القادم", value="\n".join(lines), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="join", aliases=["انضم"])
    async def join(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("❌ لازم تكون في فويس شانل الأول!")
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect(self_deaf=True)
        await ctx.send(f"✅ اتضمت لـ **{channel.name}**")

    @commands.command(name="leave", aliases=["dc", "امشي"])
    async def leave(self, ctx):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("❌ البوت مش في فويس شانل.")
        self.queues[ctx.guild.id] = deque()
        self.current.pop(ctx.guild.id, None)
        await vc.disconnect()
        await ctx.send("👋 خرجت من الفويس شانل.")

    @commands.command(name="yt", aliases=["youtube"])
    async def youtube_play(self, ctx: commands.Context, *, query: str):
        """يشغل أغنية من YouTube مباشرة | !yt <اسم أو رابط>"""
        if not ctx.author.voice:
            return await ctx.send("❌ لازم تكون في فويس شانل الأول!")

        channel = ctx.author.voice.channel
        vc = ctx.voice_client

        if not vc:
            vc = await channel.connect(self_deaf=True)
        elif vc.channel != channel:
            await vc.move_to(channel); await vc.guild.change_voice_state(channel=channel, self_deaf=True)

        if self.youtube_blocked:
            return await ctx.send("⚠️ YouTube محظور حالياً، استخدم `!sc` للبحث في SoundCloud أو `!p` للبحث التلقائي.")
        
        loading = await ctx.send("🔴 بحمل من YouTube...")
        track = await self.search_and_extract(query, force_platform="youtube")
        await loading.delete()

        if not track or not track.get("url"):
            # محاولة fallback لـ SoundCloud
            loading2 = await ctx.send("❌ فشل YouTube، جاري المحاولة في SoundCloud...")
            track = await self.search_and_extract(query, force_platform="soundcloud")
            await loading2.delete()
            
            if not track:
                return await ctx.send("❌ مش لاقي الأغنية دي في أي منصة، جرب اسم تاني.")

        queue = self.get_queue(ctx.guild.id)

        if not vc.is_playing() and not vc.is_paused():
            self.current[ctx.guild.id] = track

            def after(error):
                if error:
                    print(f"[Music] Player error: {error}")
                asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

            source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(source, volume=0.8)
            vc.play(source, after=after)

            embed = self.build_now_playing_embed(track, len(queue), self.loop_mode.get(ctx.guild.id, False))
            view = PlayerView(self, ctx)
            await ctx.send(embed=embed, view=view)
        else:
            queue.append(track)
            source_color = 0xFF0000 if track.get("source") == "YouTube" else 0xFF8C00
            source_emoji = "🔴" if track.get("source") == "YouTube" else "🟠"
            
            embed = discord.Embed(
                description=f"### ➕ اتضافت للـ Queue من {track.get('source', 'Unknown')}\n**[{track['title']}]({track['webpage_url']})**",
                color=source_color,
            )
            embed.add_field(name="⏱ المدة", value=self.fmt(track["duration"]), inline=True)
            embed.add_field(name="📋 موقعها", value=f"#{len(queue)}", inline=True)
            embed.add_field(name="📡 المصدر", value=f"{source_emoji} {track.get('source', 'Unknown')}", inline=True)
            if track.get("thumbnail"):
                embed.set_thumbnail(url=track["thumbnail"])
            await ctx.send(embed=embed)

    @commands.command(name="sc", aliases=["soundcloud"])
    async def soundcloud_play(self, ctx: commands.Context, *, query: str):
        """يشغل أغنية من SoundCloud مباشرة | !sc <اسم أو رابط>"""
        if not ctx.author.voice:
            return await ctx.send("❌ لازم تكون في فويس شانل الأول!")

        channel = ctx.author.voice.channel
        vc = ctx.voice_client

        if not vc:
            vc = await channel.connect(self_deaf=True)
        elif vc.channel != channel:
            await vc.move_to(channel); await vc.guild.change_voice_state(channel=channel, self_deaf=True)

        loading = await ctx.send("🟠 بحمل من SoundCloud...")
        track = await self.search_and_extract(query, force_platform="soundcloud")
        await loading.delete()

        if not track or not track.get("url"):
            return await ctx.send("❌ مش لاقي الأغنية دي على SoundCloud، جرب اسم تاني.")

        queue = self.get_queue(ctx.guild.id)

        if not vc.is_playing() and not vc.is_paused():
            self.current[ctx.guild.id] = track

            def after(error):
                if error:
                    print(f"[Music] Player error: {error}")
                asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

            source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(source, volume=0.8)
            vc.play(source, after=after)

            embed = self.build_now_playing_embed(track, len(queue), self.loop_mode.get(ctx.guild.id, False))
            view = PlayerView(self, ctx)
            await ctx.send(embed=embed, view=view)
        else:
            queue.append(track)
            embed = discord.Embed(
                description=f"### ➕ اتضافت للـ Queue من SoundCloud\n**[{track['title']}]({track['webpage_url']})**",
                color=0xFF8C00,
            )
            embed.add_field(name="⏱ المدة", value=self.fmt(track["duration"]), inline=True)
            embed.add_field(name="📋 موقعها", value=f"#{len(queue)}", inline=True)
            embed.add_field(name="📡 المصدر", value="🟠 SoundCloud", inline=True)
            if track.get("thumbnail"):
                embed.set_thumbnail(url=track["thumbnail"])
            await ctx.send(embed=embed)

    @commands.command(name="update-ytdlp")
    @commands.has_permissions(administrator=True)
    async def update_ytdlp_command(self, ctx):
        """تحديث yt-dlp يدوياً (للمشرفين فقط)"""
        loading = await ctx.send("🔄 جاري تحديث yt-dlp...")
        
        try:
            await update_ytdlp()
            self.last_ytdlp_update = asyncio.get_event_loop().time()
            self.youtube_blocked = False  # إعادة تعيين حالة الحظر
            
            embed = discord.Embed(
                title="✅ تم تحديث yt-dlp بنجاح",
                description="تم تحديث مكتبة استخراج الفيديو، جرب تشغيل الأغاني مرة أخرى",
                color=discord.Color.green()
            )
            await loading.edit(content=None, embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ فشل تحديث yt-dlp",
                description=f"حدث خطأ أثناء التحديث: {str(e)[:200]}",
                color=discord.Color.red()
            )
            await loading.edit(content=None, embed=embed)

    @commands.command(name="music-status")
    async def music_status(self, ctx):
        """عرض حالة نظام الموسيقى"""
        embed = discord.Embed(
            title="🎵 حالة نظام الموسيقى",
            color=discord.Color.blue()
        )
        
        # حالة YouTube
        yt_status = "❌ محظور" if self.youtube_blocked else "✅ يعمل"
        embed.add_field(name="🔴 YouTube", value=yt_status, inline=True)
        
        # حالة SoundCloud
        embed.add_field(name="🟠 SoundCloud", value="✅ يعمل", inline=True)
        
        # آخر تحديث
        import time
        last_update = time.time() - self.last_ytdlp_update
        hours = int(last_update // 3600)
        embed.add_field(name="🔄 آخر تحديث", value=f"منذ {hours} ساعة", inline=True)
        
        # إحصائيات
        total_guilds = len(self.queues)
        active_players = sum(1 for guild_id in self.queues if self.current.get(guild_id))
        
        embed.add_field(name="📊 الإحصائيات", 
                       value=f"السيرفرات: {total_guilds}\nالمشغلات النشطة: {active_players}", 
                       inline=False)
        
        if self.youtube_blocked:
            embed.add_field(name="⚠️ تحذير", 
                           value="YouTube محظور حالياً، استخدم `!update-ytdlp` للمحاولة مرة أخرى", 
                           inline=False)
        
        embed.set_footer(text="استخدم !update-ytdlp لتحديث النظام يدوياً")
        await ctx.send(embed=embed)

    # ─── Playlist Commands ─────────────────────────────────────────────────

    @commands.group(name="pl", aliases=["playlist"], invoke_without_command=True)
    async def playlist(self, ctx):
        """إدارة الـ playlists | !pl help"""
        embed = discord.Embed(title="🎵 Playlist Commands", color=0x5865F2)
        embed.add_field(name="!pl create <اسم>", value="إنشاء playlist جديدة", inline=False)
        embed.add_field(name="!pl add <اسم> <أغنية>", value="إضافة أغنية للـ playlist", inline=False)
        embed.add_field(name="!pl remove <اسم> <رقم>", value="حذف أغنية من الـ playlist", inline=False)
        embed.add_field(name="!pl play <اسم>", value="تشغيل playlist كاملة", inline=False)
        embed.add_field(name="!pl list", value="عرض كل الـ playlists", inline=False)
        embed.add_field(name="!pl show <اسم>", value="عرض أغاني playlist معينة", inline=False)
        embed.add_field(name="!pl delete <اسم>", value="حذف playlist كاملة", inline=False)
        await ctx.send(embed=embed)

    @playlist.command(name="create")
    async def pl_create(self, ctx, *, name: str):
        """إنشاء playlist جديدة"""
        data = load_playlists()
        key = f"{ctx.author.id}_{name}"
        if key in data:
            return await ctx.send(f"❌ عندك playlist بالاسم ده بالفعل.")
        data[key] = {"name": name, "owner": ctx.author.id, "owner_name": str(ctx.author), "songs": []}
        save_playlists(data)
        await ctx.send(f"✅ اتعملت playlist **{name}** بنجاح!")

    @playlist.command(name="add")
    async def pl_add(self, ctx, name: str, *, query: str):
        """إضافة أغنية لـ playlist"""
        data = load_playlists()
        key = f"{ctx.author.id}_{name}"
        if key not in data:
            return await ctx.send(f"❌ مش لاقي playlist بالاسم **{name}**.")
        loading = await ctx.send("🔍 بدور على الأغنية...")
        track = await self.search_and_extract(query)
        await loading.delete()
        if not track or not track.get("url"):
            return await ctx.send("❌ مش لاقي الأغنية دي.")
        data[key]["songs"].append({
            "title": track["title"],
            "webpage_url": track["webpage_url"],
            "duration": track["duration"],
            "uploader": track["uploader"],
            "query": query,
        })
        save_playlists(data)
        embed = discord.Embed(
            description=f"✅ اتضافت **{track['title']}** لـ playlist **{name}**",
            color=0x57F287,
        )
        embed.set_footer(text=f"إجمالي الأغاني: {len(data[key]['songs'])}")
        await ctx.send(embed=embed)

    @playlist.command(name="remove")
    async def pl_remove(self, ctx, name: str, index: int):
        """حذف أغنية من playlist"""
        data = load_playlists()
        key = f"{ctx.author.id}_{name}"
        if key not in data:
            return await ctx.send(f"❌ مش لاقي playlist **{name}**.")
        songs = data[key]["songs"]
        if index < 1 or index > len(songs):
            return await ctx.send(f"❌ الرقم غلط، الـ playlist فيها {len(songs)} أغنية.")
        removed = songs.pop(index - 1)
        save_playlists(data)
        await ctx.send(f"🗑️ اتحذفت **{removed['title']}** من **{name}**.")

    @playlist.command(name="play")
    async def pl_play(self, ctx, *, name: str):
        """تشغيل playlist كاملة"""
        if not ctx.author.voice:
            return await ctx.send("❌ لازم تكون في فويس شانل الأول!")
        data = load_playlists()
        key = f"{ctx.author.id}_{name}"
        if key not in data:
            return await ctx.send(f"❌ مش لاقي playlist **{name}**.")
        songs = data[key]["songs"]
        if not songs:
            return await ctx.send(f"❌ الـ playlist **{name}** فاضية.")

        channel = ctx.author.voice.channel
        vc = ctx.voice_client
        if not vc:
            vc = await channel.connect(self_deaf=True)
        elif vc.channel != channel:
            await vc.move_to(channel); await vc.guild.change_voice_state(channel=channel, self_deaf=True)

        queue = self.get_queue(ctx.guild.id)
        loading = await ctx.send(f"⏳ بيحمل **{name}** ({len(songs)} أغنية)...")

        added = 0
        for song in songs:
            track = await self.search_and_extract(song.get("query") or song["title"])
            if track and track.get("url"):
                queue.append(track)
                added += 1

        await loading.delete()

        embed = discord.Embed(
            description=f"### 🎵 Playlist: **{name}**\nاتضافت **{added}** أغنية للـ queue",
            color=0x5865F2,
        )
        embed.set_footer(text=f"بتاع {data[key]['owner_name']}")
        await ctx.send(embed=embed)

        if not vc.is_playing() and not vc.is_paused():
            await self.play_next(ctx)

    @playlist.command(name="list")
    async def pl_list(self, ctx):
        """عرض كل الـ playlists"""
        data = load_playlists()
        user_pls = {k: v for k, v in data.items() if v["owner"] == ctx.author.id}
        if not user_pls:
            return await ctx.send("📭 مش عندك أي playlist.")
        embed = discord.Embed(title=f"🎵 Playlists بتاعت {ctx.author.display_name}", color=0x5865F2)
        for k, v in user_pls.items():
            embed.add_field(
                name=f"📋 {v['name']}",
                value=f"{len(v['songs'])} أغنية",
                inline=True,
            )
        await ctx.send(embed=embed)

    @playlist.command(name="show")
    async def pl_show(self, ctx, *, name: str):
        """عرض أغاني playlist"""
        data = load_playlists()
        key = f"{ctx.author.id}_{name}"
        if key not in data:
            return await ctx.send(f"❌ مش لاقي playlist **{name}**.")
        songs = data[key]["songs"]
        if not songs:
            return await ctx.send(f"📭 الـ playlist **{name}** فاضية.")
        embed = discord.Embed(title=f"🎵 {name}", color=0x5865F2)
        lines = [f"`{i}.` [{s['title']}]({s['webpage_url']}) `{self.fmt(s['duration'])}`"
                 for i, s in enumerate(songs[:20], 1)]
        if len(songs) > 20:
            lines.append(f"... و **{len(songs)-20}** أغنية تانية")
        embed.description = "\n".join(lines)
        embed.set_footer(text=f"إجمالي: {len(songs)} أغنية")
        await ctx.send(embed=embed)

    @playlist.command(name="delete")
    async def pl_delete(self, ctx, *, name: str):
        """حذف playlist كاملة"""
        data = load_playlists()
        key = f"{ctx.author.id}_{name}"
        if key not in data:
            return await ctx.send(f"❌ مش لاقي playlist **{name}**.")
        del data[key]
        save_playlists(data)
        await ctx.send(f"🗑️ اتحذفت playlist **{name}** بنجاح.")


async def setup(bot):
    await bot.add_cog(MusicCog(bot))
