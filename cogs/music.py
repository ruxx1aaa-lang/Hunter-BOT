import discord
from discord.ext import commands
import wavelink
import asyncio


class MusicCog(commands.Cog, name="Music"):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        nodes = [
            wavelink.Node(uri="https://lavalink.devamop.in", password="DevamOP"),
            wavelink.Node(uri="https://lavalink.oops.wtf", password="www.lavalink.oops.wtf"),
            wavelink.Node(uri="https://lava.link", password="dismusic"),
        ]
        for node in nodes:
            try:
                await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=100)
                print(f"[Music] Connected to {node.uri}")
                return
            except Exception as e:
                print(f"[Music] Failed to connect to {node.uri}: {e}")
                continue
        print("[Music] WARNING: Could not connect to any Lavalink node!")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"[Music] Node {payload.node.identifier} is ready!")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player: wavelink.Player = payload.player
        if not player or not hasattr(player, "ctx"):
            return
        track = payload.track
        embed = discord.Embed(
            title="🎵 بيشتغل دلوقتي",
            description=f"**[{track.title}]({track.uri})**",
            color=discord.Color.green(),
        )
        embed.add_field(name="👤 الفنان", value=track.author or "Unknown")
        embed.add_field(name="⏱ المدة", value=self._fmt(track.length))
        if hasattr(track, "artwork") and track.artwork:
            embed.set_thumbnail(url=track.artwork)
        await player.ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player: wavelink.Player = payload.player
        if not player:
            return
        if player.queue.is_empty:
            if hasattr(player, "ctx"):
                await player.ctx.send("✅ خلصت الـ queue.")
        else:
            await player.play(player.queue.get())

    def _fmt(self, ms: int) -> str:
        s = ms // 1000
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    # ─────────────────────────────────────────
    # Commands
    # ─────────────────────────────────────────

    @commands.command(name="p", aliases=["play", "شغل"])
    async def play(self, ctx: commands.Context, *, query: str):
        """يشغل أغنية | !p <اسم أو رابط>"""
        if not ctx.author.voice:
            return await ctx.send("❌ لازم تكون في فويس شانل الأول!")

        channel = ctx.author.voice.channel
        player: wavelink.Player = ctx.voice_client

        if not player:
            player = await channel.connect(cls=wavelink.Player)
        elif player.channel != channel:
            await player.move_to(channel)

        player.ctx = ctx
        player.autoplay = wavelink.AutoPlayMode.disabled

        loading = await ctx.send("🔍 بدور على الأغنية...")

        try:
            tracks = await wavelink.Playable.search(query)
        except Exception as e:
            await loading.delete()
            return await ctx.send(f"❌ حصل خطأ: `{e}`")

        await loading.delete()

        if not tracks:
            return await ctx.send("❌ مش لاقي الأغنية دي.")

        track = tracks[0]

        if player.playing:
            player.queue.put(track)
            embed = discord.Embed(
                title="➕ اتضافت للـ Queue",
                description=f"**[{track.title}]({track.uri})**",
                color=discord.Color.blue(),
            )
            embed.add_field(name="⏱ المدة", value=self._fmt(track.length))
            embed.add_field(name="📋 موقعها", value=f"#{player.queue.count}")
            return await ctx.send(embed=embed)

        await player.play(track)

    @commands.command(name="skip", aliases=["s", "سكيب"])
    async def skip(self, ctx: commands.Context):
        """يسكيب الأغنية الحالية"""
        player: wavelink.Player = ctx.voice_client
        if not player or not player.playing:
            return await ctx.send("❌ مفيش حاجة بتشتغل.")
        await player.skip()
        await ctx.send("⏭ تم السكيب!")

    @commands.command(name="stop", aliases=["وقف"])
    async def stop(self, ctx: commands.Context):
        """يوقف الموسيقى ويمسح الـ queue"""
        player: wavelink.Player = ctx.voice_client
        if not player:
            return await ctx.send("❌ البوت مش في فويس شانل.")
        player.queue.clear()
        await player.stop()
        await ctx.send("⏹ تم إيقاف الموسيقى.")

    @commands.command(name="pause", aliases=["بوز"])
    async def pause(self, ctx: commands.Context):
        """يوقف الأغنية مؤقتاً"""
        player: wavelink.Player = ctx.voice_client
        if player and player.playing:
            await player.pause(True)
            await ctx.send("⏸ تم الإيقاف المؤقت.")
        else:
            await ctx.send("❌ مفيش حاجة بتشتغل.")

    @commands.command(name="resume", aliases=["r", "كمل"])
    async def resume(self, ctx: commands.Context):
        """يكمل الأغنية"""
        player: wavelink.Player = ctx.voice_client
        if player and player.paused:
            await player.pause(False)
            await ctx.send("▶️ تم الاستكمال.")
        else:
            await ctx.send("❌ الأغنية مش متوقفة.")

    @commands.command(name="queue", aliases=["q", "قائمة"])
    async def show_queue(self, ctx: commands.Context):
        """يعرض الـ queue"""
        player: wavelink.Player = ctx.voice_client
        if not player:
            return await ctx.send("📭 الـ queue فاضي.")

        embed = discord.Embed(title="🎶 قائمة الأغاني", color=discord.Color.purple())

        if player.current:
            embed.add_field(
                name="▶️ بيشتغل دلوقتي",
                value=f"**{player.current.title}** ({self._fmt(player.current.length)})",
                inline=False,
            )

        if not player.queue.is_empty:
            tracks_list = []
            for i, t in enumerate(list(player.queue)[:10], 1):
                tracks_list.append(f"`{i}.` {t.title} ({self._fmt(t.length)})")
            if player.queue.count > 10:
                tracks_list.append(f"... و {player.queue.count - 10} أغنية تانية")
            embed.add_field(name="📋 القادم", value="\n".join(tracks_list), inline=False)

        if not player.current and player.queue.is_empty:
            return await ctx.send("📭 الـ queue فاضي.")

        await ctx.send(embed=embed)

    @commands.command(name="volume", aliases=["vol", "صوت"])
    async def volume(self, ctx: commands.Context, vol: int):
        """يغير الصوت (1-100)"""
        player: wavelink.Player = ctx.voice_client
        if not player:
            return await ctx.send("❌ مفيش حاجة بتشتغل.")
        if not 1 <= vol <= 100:
            return await ctx.send("❌ الصوت لازم يكون بين 1 و 100.")
        await player.set_volume(vol)
        await ctx.send(f"🔊 الصوت اتغير لـ {vol}%")

    @commands.command(name="np", aliases=["nowplaying", "شغال"])
    async def nowplaying(self, ctx: commands.Context):
        """يعرض الأغنية الحالية"""
        player: wavelink.Player = ctx.voice_client
        if not player or not player.current:
            return await ctx.send("❌ مفيش حاجة بتشتغل.")
        t = player.current
        embed = discord.Embed(
            title="🎵 بيشتغل دلوقتي",
            description=f"**[{t.title}]({t.uri})**",
            color=discord.Color.green(),
        )
        embed.add_field(name="👤 الفنان", value=t.author or "Unknown")
        embed.add_field(name="⏱ المدة", value=self._fmt(t.length))
        if hasattr(t, "artwork") and t.artwork:
            embed.set_thumbnail(url=t.artwork)
        await ctx.send(embed=embed)

    @commands.command(name="join", aliases=["انضم"])
    async def join(self, ctx: commands.Context):
        """يدخل الفويس شانل"""
        if not ctx.author.voice:
            return await ctx.send("❌ لازم تكون في فويس شانل الأول!")
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            player = await channel.connect(cls=wavelink.Player)
            player.ctx = ctx
        await ctx.send(f"✅ اتضمت لـ **{channel.name}**")

    @commands.command(name="leave", aliases=["dc", "امشي"])
    async def leave(self, ctx: commands.Context):
        """يخرج من الفويس شانل"""
        player: wavelink.Player = ctx.voice_client
        if not player:
            return await ctx.send("❌ البوت مش في فويس شانل.")
        await player.disconnect()
        await ctx.send("👋 خرجت من الفويس شانل.")


async def setup(bot):
    await bot.add_cog(MusicCog(bot))
