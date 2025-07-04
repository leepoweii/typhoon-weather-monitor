#!/usr/bin/env python3
"""
測試颱風近況回覆功能
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import monitor, line_notifier

async def test_typhoon_status_reply():
    """測試颱風近況回覆功能"""
    print("🧪 測試颱風近況功能...")
    
    try:
        # 1. 取得監控資料
        print("1. 取得監控資料...")
        result = await monitor.check_all_conditions()
        print(f"   ✅ 狀態: {result['status']}")
        print(f"   ✅ 警告數量: {len(result['warnings'])}")
        print(f"   ✅ 航班風險: {result['travel_risk']}")
        print(f"   ✅ 體檢風險: {result['checkup_risk']}")
        
        # 2. 測試 Flex Message 建構
        print("\n2. 測試 Flex Message 建構...")
        flex_container = line_notifier.flex_builder.create_typhoon_status_flex(result)
        print(f"   ✅ Flex Message 類型: {flex_container.type}")
        
        # 3. 測試文字訊息格式化
        print("\n3. 測試文字訊息格式化...")
        text_message = line_notifier.format_typhoon_status(result)
        print(f"   ✅ 文字訊息長度: {len(text_message)} 字元")
        print("   ✅ 文字訊息預覽:")
        print("   " + "\n   ".join(text_message.split('\n')[:5]) + "...")
        
        print("\n🎉 颱風近況功能測試通過！")
        print("\n📱 當用戶發送 '颱風近況' 時，系統會:")
        print("   1. 檢查所有監控條件")
        print("   2. 生成 Flex Message（如果支援）")
        print("   3. 回退到文字訊息（如果 Flex Message 失敗）")
        print("   4. 回覆給用戶")
        
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_typhoon_status_reply())
    sys.exit(0 if success else 1)
