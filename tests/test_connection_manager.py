#!/usr/bin/env python3
"""
ConnectionManager 单元测试
Milestone 1.2 验证测试
"""

import sys
import os
import time
import threading
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.connection_manager import ConnectionManager, ConnectionStatus

class TestConnectionManager:
    """ConnectionManager测试类"""
    
    def __init__(self):
        self.test_config = {
            "gateway": {
                "name": "SIMULATION",
                "settings": {
                    "mode": "simulation",
                    "symbols": ["rb2405", "i2405", "j2405"],
                    "trading_hours": "09:00-15:00"
                }
            }
        }
        self.test_results = []
    
    def run_test(self, test_name: str, test_func):
        """运行单个测试"""
        print(f"\n🧪 测试: {test_name}")
        print("-" * 40)
        
        try:
            result = test_func()
            status = "✅ 通过" if result else "❌ 失败"
            print(f"结果: {status}")
            self.test_results.append((test_name, result))
            return result
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            self.test_results.append((test_name, False))
            return False
    
    def test_connection_manager_creation(self) -> bool:
        """测试连接管理器创建"""
        try:
            cm = ConnectionManager(self.test_config)
            
            # 验证初始状态
            assert cm.gateway_name == "SIMULATION"
            assert cm.status == ConnectionStatus.DISCONNECTED
            assert cm.simulation_mode == True
            assert cm.is_connected() == False
            
            print("✅ 连接管理器创建成功")
            return True
            
        except Exception as e:
            print(f"❌ 创建失败: {e}")
            return False
    
    def test_simulation_connection(self) -> bool:
        """测试模拟环境连接"""
        try:
            cm = ConnectionManager(self.test_config)
            
            # 测试连接
            result = cm.connect_gateway()
            assert result == True
            assert cm.is_connected() == True
            assert cm.status == ConnectionStatus.CONNECTED
            
            # 检查连接信息
            status_info = cm.get_connection_status()
            assert status_info["connected"] == True
            assert status_info["gateway_name"] == "SIMULATION"
            assert status_info["simulation_mode"] == True
            
            print("✅ 模拟连接成功")
            return True
            
        except Exception as e:
            print(f"❌ 连接测试失败: {e}")
            return False
    
    def test_connection_status_monitoring(self) -> bool:
        """测试连接状态监控"""
        try:
            cm = ConnectionManager(self.test_config)
            
            # 测试初始状态
            status = cm.get_connection_status()
            assert status["connected"] == False
            assert status["uptime_seconds"] is None
            
            # 连接后检查状态
            cm.connect_gateway()
            time.sleep(0.1)  # 等待状态更新
            
            status = cm.get_connection_status()
            assert status["connected"] == True
            assert status["uptime_seconds"] is not None
            assert status["uptime_seconds"] > 0
            assert status["connection_count"] == 1
            
            print("✅ 状态监控正常")
            return True
            
        except Exception as e:
            print(f"❌ 状态监控测试失败: {e}")
            return False
    
    def test_status_callback(self) -> bool:
        """测试状态回调机制"""
        try:
            cm = ConnectionManager(self.test_config)
            
            # 设置回调
            callback_events = []
            
            def test_callback(new_status, old_status):
                callback_events.append((old_status, new_status))
            
            cm.register_status_callback(test_callback)
            
            # 触发状态变化
            cm.connect_gateway()
            time.sleep(0.1)
            
            cm.disconnect_gateway()
            time.sleep(0.1)
            
            # 验证回调被调用
            assert len(callback_events) >= 2
            
            print(f"✅ 状态回调正常 (收到{len(callback_events)}个事件)")
            return True
            
        except Exception as e:
            print(f"❌ 回调测试失败: {e}")
            return False
    
    def test_disconnect_functionality(self) -> bool:
        """测试断开连接功能"""
        try:
            cm = ConnectionManager(self.test_config)
            
            # 先连接
            cm.connect_gateway()
            assert cm.is_connected() == True
            
            # 断开连接
            result = cm.disconnect_gateway()
            assert result == True
            assert cm.is_connected() == False
            assert cm.status == ConnectionStatus.DISCONNECTED
            
            status = cm.get_connection_status()
            assert status["connected"] == False
            
            print("✅ 断开连接功能正常")
            return True
            
        except Exception as e:
            print(f"❌ 断开测试失败: {e}")
            return False
    
    def test_environment_switching(self) -> bool:
        """测试环境切换功能"""
        try:
            cm = ConnectionManager(self.test_config)
            
            # 测试初始环境
            assert cm.gateway_name == "SIMULATION"
            assert cm.simulation_mode == True
            
            # 切换环境
            result = cm.switch_environment("LIVE")
            assert result == True
            assert cm.gateway_name == "LIVE"
            assert cm.simulation_mode == False
            
            # 切换回模拟环境
            cm.switch_environment("SIMULATION")
            assert cm.gateway_name == "SIMULATION"
            assert cm.simulation_mode == True
            
            print("✅ 环境切换功能正常")
            return True
            
        except Exception as e:
            print(f"❌ 环境切换测试失败: {e}")
            return False
    
    def test_gateway_info(self) -> bool:
        """测试网关信息获取"""
        try:
            cm = ConnectionManager(self.test_config)
            
            info = cm.get_gateway_info()
            assert "name" in info
            assert "simulation_mode" in info
            assert "settings" in info
            assert "capabilities" in info
            
            # 验证能力信息
            capabilities = info["capabilities"]
            assert capabilities["market_data"] == True
            assert capabilities["trading"] == True
            assert capabilities["account"] == True
            
            print("✅ 网关信息获取正常")
            return True
            
        except Exception as e:
            print(f"❌ 网关信息测试失败: {e}")
            return False
    
    def test_uptime_calculation(self) -> bool:
        """测试运行时间计算"""
        try:
            cm = ConnectionManager(self.test_config)
            
            # 连接前uptime应为None
            assert cm.get_uptime() is None
            
            # 连接后等待一段时间
            cm.connect_gateway()
            time.sleep(0.2)
            
            uptime = cm.get_uptime()
            assert uptime is not None
            assert uptime >= 0.1  # 至少运行了0.1秒
            
            print(f"✅ 运行时间计算正常: {uptime:.3f}秒")
            return True
            
        except Exception as e:
            print(f"❌ 运行时间测试失败: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """测试错误处理"""
        try:
            # 测试无效配置
            invalid_config = {"gateway": {"name": "SIMULATION", "settings": {}}}
            cm = ConnectionManager(invalid_config)
            
            # 连接应该失败
            result = cm.connect_gateway()
            assert result == False
            assert cm.status == ConnectionStatus.ERROR
            
            print("✅ 错误处理正常")
            return True
            
        except Exception as e:
            print(f"❌ 错误处理测试失败: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """运行所有测试"""
        print("=" * 60)
        print("ConnectionManager 单元测试 - Milestone 1.2")
        print("=" * 60)
        
        tests = [
            ("连接管理器创建", self.test_connection_manager_creation),
            ("模拟环境连接", self.test_simulation_connection),
            ("连接状态监控", self.test_connection_status_monitoring),
            ("状态回调机制", self.test_status_callback),
            ("断开连接功能", self.test_disconnect_functionality),
            ("环境切换功能", self.test_environment_switching),
            ("网关信息获取", self.test_gateway_info),
            ("运行时间计算", self.test_uptime_calculation),
            ("错误处理", self.test_error_handling)
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # 汇总结果
        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)
        
        print(f"\n{'='*60}")
        print("测试结果汇总:")
        print(f"{'='*60}")
        
        for test_name, result in self.test_results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{test_name:<20}: {status}")
        
        print(f"\n📊 总体结果: {passed}/{total} 测试通过")
        success_rate = (passed / total) * 100
        print(f"📈 成功率: {success_rate:.1f}%")
        
        if passed == total:
            print("\n🎉 Milestone 1.2 单元测试全部通过!")
            return True
        else:
            print(f"\n⚠️ {total - passed} 个测试失败，需要检查")
            return False


def main():
    """主测试函数"""
    tester = TestConnectionManager()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ ConnectionManager模块验证成功")
        print("🚀 可以进入下一阶段开发")
    else:
        print("\n❌ ConnectionManager模块验证失败")
        print("🔧 需要修复问题后重新测试")
    
    return success


if __name__ == "__main__":
    main()