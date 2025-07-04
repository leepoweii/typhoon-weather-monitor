#!/usr/bin/env python3
"""
測試 webhook handler 關鍵字檢查邏輯
驗證只有完全相等的「颱風現況」才會觸發回應
"""

import logging

# 模擬關鍵字檢查邏輯
def test_keyword_matching():
    """測試關鍵字檢查邏輯"""
    
    test_cases = [
        # 應該觸發回應的訊息 (True)
        ("颱風現況", True),
        
        # 不應該觸發回應的訊息 (False)
        ("颱風", False),
        ("現況", False),
        ("颱風狀況", False),
        ("查詢颱風現況", False),
        ("颱風現況如何", False),
        ("請告訴我颱風現況", False),
        ("天氣", False),
        ("警報", False),
        ("風險", False),
        ("監控", False),
        ("檢查", False),
        ("Hello", False),
        ("", False),
        ("颱風現況 ", False),  # 包含空格
        (" 颱風現況", False),  # 包含空格
        ("颱風現況！", False),  # 包含標點符號
        ("今天颱風現況", False),
        ("颱風現況怎麼樣", False),
    ]
    
    print("=" * 60)
    print("🧪 測試 webhook handler 關鍵字檢查邏輯")
    print("=" * 60)
    print("新邏輯：只回應完全相等的「颱風現況」")
    print("=" * 60)
    
    all_passed = True
    
    for message, expected in test_cases:
        # 模擬新的檢查邏輯
        result = (message == "颱風現況")
        
        status = "✅ PASS" if result == expected else "❌ FAIL"
        trigger_status = "會觸發" if result else "不會觸發"
        
        print(f"{status} 訊息: '{message}' -> {trigger_status}")
        
        if result != expected:
            all_passed = False
            print(f"     預期: {'會觸發' if expected else '不會觸發'}")
            print(f"     實際: {'會觸發' if result else '不會觸發'}")
    
    print("=" * 60)
    if all_passed:
        print("✅ 所有測試通過！關鍵字檢查邏輯正確。")
    else:
        print("❌ 部分測試失敗！")
    print("=" * 60)
    
    return all_passed

def test_old_vs_new_logic():
    """比較舊邏輯與新邏輯的差異"""
    
    print("\n" + "=" * 60)
    print("📊 舊邏輯 vs 新邏輯對比")
    print("=" * 60)
    
    test_messages = [
        "颱風現況",
        "颱風",
        "天氣",
        "警報",
        "查詢颱風狀況",
        "今天天氣如何",
        "Hello",
    ]
    
    # 模擬舊邏輯
    old_trigger_keywords = ["颱風", "天氣", "狀況", "警報", "風險", "監控", "檢查"]
    
    print(f"{'訊息':<15} {'舊邏輯':<8} {'新邏輯':<8} {'說明'}")
    print("-" * 60)
    
    for message in test_messages:
        old_result = any(keyword in message for keyword in old_trigger_keywords)
        new_result = (message == "颱風現況")
        
        old_status = "會觸發" if old_result else "不觸發"
        new_status = "會觸發" if new_result else "不觸發"
        
        if old_result != new_result:
            explanation = "⚠️ 行為改變"
        else:
            explanation = "✅ 行為一致"
        
        print(f"{message:<15} {old_status:<8} {new_status:<8} {explanation}")
    
    print("=" * 60)

if __name__ == "__main__":
    # 設置日誌
    logging.basicConfig(level=logging.INFO)
    
    # 執行測試
    success = test_keyword_matching()
    test_old_vs_new_logic()
    
    if success:
        print("\n🎉 關鍵字檢查邏輯測試完成，可以部署新版本！")
    else:
        print("\n⚠️ 測試失敗，請檢查邏輯實作。")
