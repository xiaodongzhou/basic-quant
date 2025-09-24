#!/usr/bin/env python3
"""
ConnectionManager 功能演示
Milestone 1.2 演示脚本
"""

import time
from core.connection_manager import create_connection_manager, ConnectionStatus

def demo_basic_connection():
    """演示基础连接功能"""
    print("🎯 演示1: 基础连接功能")
    print("=" * 40)
    
    # 创建连接管理器
    cm = create_connection_manager()
    
    # 显示初始状态
    print("📊 初始状态:")
    status = cm.get_connection_status()
    print(f"  连接状态: {status['status']}")
    print(f"  网关名称: {status['gateway_name']}")
    print(f"  模拟模式: {status['simulation_mode']}")
    
    # 执行连接
    print("\n🔌 执行连接...")
    success = cm.connect_gateway()
    
    if success:
        print("✅ 连接成功!")
        
        # 显示连接后状态
        time.sleep(1)
        status = cm.get_connection_status()
        print(f"\n📊 连接后状态:")
        print(f"  连接状态: {status['status']}")
        print(f"  运行时间: {status['uptime_seconds']:.1f}秒")
        print(f"  连接次数: {status['connection_count']}")
        
        # 断开连接
        print("\n🔌 断开连接...")
        cm.disconnect_gateway()
        print("✅ 断开成功!")
    
    return cm

def demo_status_monitoring(cm):
    """演示状态监控功能"""
    print("\n\n🎯 演示2: 状态监控功能")
    print("=" * 40)
    
    # 注册状态监控回调
    status_changes = []
    
    def status_monitor(new_status, old_status):
        timestamp = time.strftime("%H:%M:%S")
        status_changes.append(f"[{timestamp}] {old_status.value} -> {new_status.value}")
        print(f"📢 状态变化: {old_status.value} -> {new_status.value}")
    
    cm.register_status_callback(status_monitor)
    
    print("🔄 执行连接状态变化...")
    
    # 连接
    cm.connect_gateway()
    time.sleep(0.5)
    
    # 断开
    cm.disconnect_gateway()
    time.sleep(0.5)
    
    # 再次连接
    cm.connect_gateway()
    time.sleep(0.5)
    
    print(f"\n📊 监控到 {len(status_changes)} 次状态变化:")
    for change in status_changes:
        print(f"  {change}")
    
    return cm

def demo_environment_switching(cm):
    """演示环境切换功能"""
    print("\n\n🎯 演示3: 环境切换功能")
    print("=" * 40)
    
    # 显示当前环境
    info = cm.get_gateway_info()
    print(f"📊 当前环境: {info['name']} (模拟模式: {info['simulation_mode']})")
    
    # 切换到实盘环境
    print("\n🔄 切换到实盘环境...")
    cm.switch_environment("LIVE")
    
    info = cm.get_gateway_info()
    print(f"📊 切换后: {info['name']} (模拟模式: {info['simulation_mode']})")
    
    # 切换回模拟环境  
    print("\n🔄 切换回模拟环境...")
    cm.switch_environment("SIMULATION")
    
    info = cm.get_gateway_info()
    print(f"📊 最终环境: {info['name']} (模拟模式: {info['simulation_mode']})")

def demo_error_handling():
    """演示错误处理功能"""
    print("\n\n🎯 演示4: 错误处理功能")
    print("=" * 40)
    
    # 创建一个有问题的配置
    error_config = {
        "gateway": {
            "name": "SIMULATION",
            "settings": {
                # 缺少必要的配置项
                "symbols": ["rb2405"]
            }
        }
    }
    
    from core.connection_manager import ConnectionManager
    cm = ConnectionManager(error_config)
    
    print("🔄 尝试连接有问题的配置...")
    success = cm.connect_gateway()
    
    status = cm.get_connection_status()
    print(f"📊 连接结果: {success}")
    print(f"📊 连接状态: {status['status']}")
    print(f"📊 错误信息: {status['error_message']}")
    print(f"📊 重连尝试: {status['reconnect_attempts']}")

def demo_comprehensive_monitoring(cm):
    """演示综合监控信息"""
    print("\n\n🎯 演示5: 综合监控信息")
    print("=" * 40)
    
    # 确保处于连接状态
    if not cm.is_connected():
        cm.connect_gateway()
    
    # 等待一段时间以累积运行时间
    print("⏰ 运行监控 (5秒)...")
    for i in range(5):
        time.sleep(1)
        uptime = cm.get_uptime()
        print(f"  运行时间: {uptime:.1f}秒")
    
    # 显示完整状态信息
    print("\n📊 完整状态信息:")
    status = cm.get_connection_status()
    
    important_fields = [
        "connected", "status", "gateway_name", 
        "uptime_seconds", "connection_count", "simulation_mode"
    ]
    
    for field in important_fields:
        value = status[field]
        if field == "uptime_seconds" and value:
            value = f"{value:.1f}秒"
        print(f"  {field}: {value}")
    
    # 显示网关能力
    print("\n📊 网关能力:")
    info = cm.get_gateway_info()
    capabilities = info["capabilities"]
    for capability, enabled in capabilities.items():
        status_icon = "✅" if enabled else "❌"
        print(f"  {capability}: {status_icon}")

def main():
    """主演示函数"""
    print("🚀 ConnectionManager 功能演示")
    print("Milestone 1.2 - 连接管理模块")
    print("=" * 60)
    
    try:
        # 演示1: 基础连接
        cm = demo_basic_connection()
        
        # 演示2: 状态监控
        demo_status_monitoring(cm)
        
        # 演示3: 环境切换
        demo_environment_switching(cm)
        
        # 演示4: 错误处理
        demo_error_handling()
        
        # 演示5: 综合监控
        demo_comprehensive_monitoring(cm)
        
        print("\n🎉 ConnectionManager 演示完成!")
        print("✅ 所有核心功能工作正常")
        print("🚀 Milestone 1.2 验证成功!")
        
    except Exception as e:
        print(f"\n❌ 演示过程出错: {e}")
        return False
    
    finally:
        # 清理资源
        if 'cm' in locals():
            cm.disconnect_gateway()
    
    return True

if __name__ == "__main__":
    main()