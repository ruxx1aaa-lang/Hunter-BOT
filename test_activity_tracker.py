#!/usr/bin/env python3
"""
اختبار نظام تتبع الأنشطة
Test script for Activity Tracker system
"""

import asyncio
import aiosqlite
from datetime import datetime, timedelta
import json

async def test_database_setup():
    """اختبار إعداد قاعدة البيانات"""
    print("🔧 اختبار إعداد قاعدة البيانات...")
    
    async with aiosqlite.connect("test_hunter.db") as db:
        # إنشاء الجداول
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_activity (
                user_id INTEGER,
                guild_id INTEGER,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS missed_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                activity_type TEXT,
                user_id INTEGER,
                username TEXT,
                description TEXT,
                channel_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS activity_settings (
                guild_id INTEGER PRIMARY KEY,
                enabled BOOLEAN DEFAULT 1,
                track_joins BOOLEAN DEFAULT 1,
                track_leaves BOOLEAN DEFAULT 1,
                track_messages BOOLEAN DEFAULT 1,
                track_voice BOOLEAN DEFAULT 1,
                track_games BOOLEAN DEFAULT 1,
                max_activities INTEGER DEFAULT 50,
                activity_hours INTEGER DEFAULT 24
            )
        """)
        
        await db.commit()
        print("✅ تم إنشاء الجداول بنجاح")

async def test_sample_data():
    """إضافة بيانات تجريبية"""
    print("📊 إضافة بيانات تجريبية...")
    
    guild_id = 123456789
    sample_activities = [
        (guild_id, "join", 111111, "Ahmed123", "انضم للسيرفر", None, datetime.now() - timedelta(hours=2)),
        (guild_id, "message", 222222, "محمد", "كتب رسالة في #general", 555555, datetime.now() - timedelta(hours=1)),
        (guild_id, "voice_join", 333333, "سارة", "دخلت Gaming Voice", 666666, datetime.now() - timedelta(minutes=30)),
        (guild_id, "game_start", 444444, "أحمد", "بدأ يلعب PUBG", None, datetime.now() - timedelta(minutes=15)),
        (guild_id, "leave", 555555, "فاطمة", "غادرت السيرفر", None, datetime.now() - timedelta(minutes=5)),
    ]
    
    async with aiosqlite.connect("test_hunter.db") as db:
        for activity in sample_activities:
            await db.execute("""
                INSERT INTO missed_activities 
                (guild_id, activity_type, user_id, username, description, channel_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, activity)
        
        # إضافة نشاط للمستخدم
        await db.execute("""
            INSERT OR REPLACE INTO user_activity (user_id, guild_id, last_seen)
            VALUES (?, ?, ?)
        """, (999999, guild_id, datetime.now() - timedelta(hours=3)))
        
        await db.commit()
        print("✅ تم إضافة البيانات التجريبية")

async def test_get_missed_activities():
    """اختبار استرجاع الأنشطة المفقودة"""
    print("🔍 اختبار استرجاع الأنشطة...")
    
    user_id = 999999
    guild_id = 123456789
    
    async with aiosqlite.connect("test_hunter.db") as db:
        # الحصول على آخر نشاط للمستخدم
        cursor = await db.execute("""
            SELECT last_seen FROM user_activity 
            WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))
        result = await cursor.fetchone()
        
        if result:
            since_time = datetime.fromisoformat(result[0])
            print(f"📅 آخر نشاط للمستخدم: {since_time}")
        else:
            since_time = datetime.now() - timedelta(hours=24)
            print("📅 لا يوجد سجل سابق، استخدام آخر 24 ساعة")
        
        # الحصول على الأنشطة المفقودة
        cursor = await db.execute("""
            SELECT activity_type, user_id, username, description, channel_id, timestamp, data
            FROM missed_activities 
            WHERE guild_id = ? AND timestamp > ? AND user_id != ?
            ORDER BY timestamp DESC
            LIMIT 50
        """, (guild_id, since_time, user_id))
        
        activities = await cursor.fetchall()
        
        print(f"📋 تم العثور على {len(activities)} نشاط:")
        for activity in activities:
            activity_type, user_id, username, description, channel_id, timestamp, data = activity
            print(f"  • {username}: {description} ({activity_type}) - {timestamp}")

async def test_activity_grouping():
    """اختبار تجميع الأنشطة"""
    print("📊 اختبار تجميع الأنشطة...")
    
    guild_id = 123456789
    
    async with aiosqlite.connect("test_hunter.db") as db:
        cursor = await db.execute("""
            SELECT activity_type, COUNT(*) FROM missed_activities 
            WHERE guild_id = ? GROUP BY activity_type
        """, (guild_id,))
        
        activity_types = await cursor.fetchall()
        
        print("📈 إحصائيات الأنشطة:")
        for activity_type, count in activity_types:
            print(f"  • {activity_type}: {count}")

async def test_cleanup():
    """اختبار تنظيف البيانات"""
    print("🧹 اختبار تنظيف البيانات...")
    
    guild_id = 123456789
    
    async with aiosqlite.connect("test_hunter.db") as db:
        # عد الأنشطة قبل التنظيف
        cursor = await db.execute("""
            SELECT COUNT(*) FROM missed_activities WHERE guild_id = ?
        """, (guild_id,))
        before_count = (await cursor.fetchone())[0]
        
        # تنظيف الأنشطة الأقدم من ساعة واحدة (للاختبار)
        cutoff_time = datetime.now() - timedelta(hours=1)
        await db.execute("""
            DELETE FROM missed_activities 
            WHERE guild_id = ? AND timestamp < ?
        """, (guild_id, cutoff_time))
        await db.commit()
        
        # عد الأنشطة بعد التنظيف
        cursor = await db.execute("""
            SELECT COUNT(*) FROM missed_activities WHERE guild_id = ?
        """, (guild_id,))
        after_count = (await cursor.fetchone())[0]
        
        print(f"📊 قبل التنظيف: {before_count} نشاط")
        print(f"📊 بعد التنظيف: {after_count} نشاط")
        print(f"🗑️ تم حذف: {before_count - after_count} نشاط")

async def main():
    """تشغيل جميع الاختبارات"""
    print("🚀 بدء اختبار نظام تتبع الأنشطة")
    print("=" * 50)
    
    try:
        await test_database_setup()
        print()
        
        await test_sample_data()
        print()
        
        await test_get_missed_activities()
        print()
        
        await test_activity_grouping()
        print()
        
        await test_cleanup()
        print()
        
        print("=" * 50)
        print("✅ تم إكمال جميع الاختبارات بنجاح!")
        
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())