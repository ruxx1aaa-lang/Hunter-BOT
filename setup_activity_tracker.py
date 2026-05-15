#!/usr/bin/env python3
"""
إعداد سريع لنظام تتبع الأنشطة
Quick setup for Activity Tracker system
"""

import asyncio
import aiosqlite
import os

async def setup_activity_tracker():
    """إعداد نظام تتبع الأنشطة"""
    print("🚀 إعداد نظام تتبع الأنشطة...")
    
    db_path = "hunter.db"
    
    # التحقق من وجود قاعدة البيانات
    if not os.path.exists(db_path):
        print("📁 إنشاء قاعدة بيانات جديدة...")
    else:
        print("📁 استخدام قاعدة البيانات الموجودة...")
    
    async with aiosqlite.connect(db_path) as db:
        print("🔧 إنشاء جداول نظام تتبع الأنشطة...")
        
        # جدول تتبع آخر نشاط للأعضاء
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_activity (
                user_id INTEGER,
                guild_id INTEGER,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        print("  ✅ جدول user_activity")
        
        # جدول الأنشطة المهمة
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
        print("  ✅ جدول missed_activities")
        
        # جدول إعدادات التتبع لكل سيرفر
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
        print("  ✅ جدول activity_settings")
        
        # إنشاء فهارس لتحسين الأداء
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_missed_activities_guild_timestamp 
            ON missed_activities(guild_id, timestamp)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_missed_activities_user_guild 
            ON missed_activities(user_id, guild_id)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_activity_user_guild 
            ON user_activity(user_id, guild_id)
        """)
        
        print("  ✅ فهارس الأداء")
        
        await db.commit()
        print("💾 تم حفظ التغييرات")
    
    print("\n📋 ملخص الإعداد:")
    print("  • تم إنشاء 3 جداول جديدة")
    print("  • تم إنشاء فهارس لتحسين الأداء")
    print("  • النظام جاهز للاستخدام")
    
    print("\n🎮 الأوامر المتاحة:")
    print("  • !missed - عرض الأنشطة المفقودة")
    print("  • !recent - آخر الأنشطة")
    print("  • !activity status - حالة النظام (للإداريين)")
    
    print("\n✅ تم إكمال الإعداد بنجاح!")

async def check_existing_data():
    """فحص البيانات الموجودة"""
    db_path = "hunter.db"
    
    if not os.path.exists(db_path):
        print("📭 لا توجد قاعدة بيانات موجودة")
        return
    
    async with aiosqlite.connect(db_path) as db:
        # فحص الجداول الموجودة
        cursor = await db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE '%activity%'
        """)
        tables = await cursor.fetchall()
        
        if tables:
            print("📊 الجداول الموجودة:")
            for table in tables:
                print(f"  • {table[0]}")
                
                # عد السجلات
                cursor = await db.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = (await cursor.fetchone())[0]
                print(f"    السجلات: {count}")
        else:
            print("📭 لا توجد جداول أنشطة")

async def main():
    """تشغيل الإعداد"""
    print("🏹 Werjo Bot - Activity Tracker Setup")
    print("=" * 50)
    
    # فحص البيانات الموجودة
    await check_existing_data()
    print()
    
    # إعداد النظام
    await setup_activity_tracker()
    
    print("\n" + "=" * 50)
    print("🎉 مرحباً بك في نظام What You Missed!")

if __name__ == "__main__":
    asyncio.run(main())