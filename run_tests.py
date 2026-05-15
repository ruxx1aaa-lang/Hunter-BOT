#!/usr/bin/env python3
"""
تشغيل اختبارات نظام تتبع الأنشطة
Run Activity Tracker Tests
"""

import asyncio
import os
import sys

async def run_setup():
    """تشغيل الإعداد"""
    print("🔧 تشغيل إعداد النظام...")
    from setup_activity_tracker import main as setup_main
    await setup_main()

async def run_tests():
    """تشغيل الاختبارات"""
    print("\n🧪 تشغيل الاختبارات...")
    from test_activity_tracker import main as test_main
    await test_main()

async def check_files():
    """فحص الملفات المطلوبة"""
    print("📁 فحص الملفات المطلوبة...")
    
    required_files = [
        "cogs/activity_tracker.py",
        "cogs/missed_view.py", 
        "activity_config.py",
        "setup_activity_tracker.py",
        "test_activity_tracker.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
        else:
            print(f"  ✅ {file}")
    
    if missing_files:
        print("\n❌ ملفات مفقودة:")
        for file in missing_files:
            print(f"  • {file}")
        return False
    
    print("✅ جميع الملفات موجودة")
    return True

async def main():
    """تشغيل جميع العمليات"""
    print("🏹 Werjo Bot - Activity Tracker Test Suite")
    print("=" * 60)
    
    # فحص الملفات
    if not await check_files():
        print("\n❌ يرجى التأكد من وجود جميع الملفات المطلوبة")
        return
    
    print("\n" + "=" * 60)
    
    # تشغيل الإعداد
    await run_setup()
    
    print("\n" + "=" * 60)
    
    # تشغيل الاختبارات
    await run_tests()
    
    print("\n" + "=" * 60)
    print("🎉 تم إكمال جميع العمليات بنجاح!")
    print("\n📋 الخطوات التالية:")
    print("  1. تشغيل البوت: python bot.py")
    print("  2. اختبار الأمر: !missed")
    print("  3. اختبار الأمر: !recent")
    print("  4. اختبار إعدادات الإدارة: !activity status")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ تم إيقاف العملية بواسطة المستخدم")
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        import traceback
        traceback.print_exc()