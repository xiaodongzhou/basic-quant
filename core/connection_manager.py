#!/usr/bin/env python3
"""
ConnectionManager - 连接管理模块
实现模拟交易网关连接管理功能

Milestone 1.2 核心模块
"""

import json
import threading
import time
from datetime import datetime
from typing import Dict, Optional, Callable
from enum import Enum

class ConnectionStatus(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

class ConnectionManager:
    """
    连接管理器 - 模拟版本
    负责管理与交易网关的连接，支持模拟和实盘环境
    """
    
    def __init__(self, config: dict):
        """
        初始化连接管理器
        
        Args:
            config: 连接配置字典
        """
        self.config = config
        self.gateway_name = config.get("gateway", {}).get("name", "SIMULATION")
        self.gateway_settings = config.get("gateway", {}).get("settings", {})
        
        # 连接状态
        self.status = ConnectionStatus.DISCONNECTED
        self.connected_time = None
        self.error_message = ""
        self.connection_count = 0
        
        # 事件回调
        self.status_callbacks = []
        
        # 重连机制
        self.auto_reconnect = True
        self.reconnect_interval = 5  # 秒
        self.max_reconnect_attempts = 3
        self.current_reconnect_attempts = 0
        
        # 模拟数据
        self.simulation_mode = self.gateway_name == "SIMULATION"
        
        print(f"✅ ConnectionManager初始化完成: {self.gateway_name}")
    
    def connect_gateway(self) -> bool:
        """
        连接网关
        
        Returns:
            bool: 连接是否成功
        """
        print(f"🔌 开始连接网关: {self.gateway_name}")
        
        try:
            self._set_status(ConnectionStatus.CONNECTING)
            
            if self.simulation_mode:
                return self._connect_simulation()
            else:
                return self._connect_real_gateway()
                
        except Exception as e:
            self._set_status(ConnectionStatus.ERROR, str(e))
            print(f"❌ 连接失败: {e}")
            return False
    
    def _connect_simulation(self) -> bool:
        """连接模拟网关"""
        print("🔄 连接模拟网关...")
        
        # 模拟连接过程
        time.sleep(1)  # 模拟连接延时
        
        # 验证配置
        required_settings = ["mode", "symbols"]
        for setting in required_settings:
            if setting not in self.gateway_settings:
                raise ValueError(f"缺少必要配置: {setting}")
        
        # 连接成功
        self.connected_time = datetime.now()
        self.connection_count += 1
        self.current_reconnect_attempts = 0
        
        self._set_status(ConnectionStatus.CONNECTED)
        print("✅ 模拟网关连接成功")
        
        return True
    
    def _connect_real_gateway(self) -> bool:
        """连接真实网关（预留接口）"""
        print("🔄 连接真实网关...")
        
        # TODO: 实现真实CTP网关连接
        # 这里预留VN.PY MainEngine集成代码
        
        raise NotImplementedError("真实网关连接将在后续版本实现")
    
    def disconnect_gateway(self) -> bool:
        """
        断开网关连接
        
        Returns:
            bool: 断开是否成功
        """
        print(f"🔌 断开网关连接: {self.gateway_name}")
        
        try:
            if self.status == ConnectionStatus.CONNECTED:
                self._set_status(ConnectionStatus.DISCONNECTED)
                self.connected_time = None
                print("✅ 网关断开成功")
            
            return True
            
        except Exception as e:
            print(f"❌ 断开连接失败: {e}")
            return False
    
    def get_connection_status(self) -> Dict:
        """
        获取连接状态信息
        
        Returns:
            dict: 连接状态字典
        """
        uptime = None
        if self.connected_time:
            uptime = (datetime.now() - self.connected_time).total_seconds()
        
        return {
            "connected": self.status == ConnectionStatus.CONNECTED,
            "status": self.status.value,
            "gateway_name": self.gateway_name,
            "connected_time": self.connected_time.isoformat() if self.connected_time else None,
            "uptime_seconds": uptime,
            "connection_count": self.connection_count,
            "error_message": self.error_message,
            "auto_reconnect": self.auto_reconnect,
            "reconnect_attempts": self.current_reconnect_attempts,
            "simulation_mode": self.simulation_mode
        }
    
    def _set_status(self, status: ConnectionStatus, error_msg: str = ""):
        """
        设置连接状态并触发回调
        
        Args:
            status: 新的连接状态
            error_msg: 错误消息（如果有）
        """
        old_status = self.status
        self.status = status
        self.error_message = error_msg
        
        # 打印状态变化
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 连接状态: {old_status.value} -> {status.value}")
        
        if error_msg:
            print(f"[{timestamp}] 错误信息: {error_msg}")
        
        # 触发回调
        self._notify_status_change(status, old_status)
        
        # 处理重连逻辑
        if status == ConnectionStatus.ERROR and self.auto_reconnect:
            self._schedule_reconnect()
    
    def _notify_status_change(self, new_status: ConnectionStatus, old_status: ConnectionStatus):
        """通知状态变化"""
        for callback in self.status_callbacks:
            try:
                callback(new_status, old_status)
            except Exception as e:
                print(f"⚠️ 状态回调执行失败: {e}")
    
    def register_status_callback(self, callback: Callable):
        """
        注册状态变化回调函数
        
        Args:
            callback: 回调函数 (new_status, old_status) -> None
        """
        self.status_callbacks.append(callback)
        print(f"✅ 状态回调注册成功: {callback.__name__}")
    
    def _schedule_reconnect(self):
        """安排重连"""
        if self.current_reconnect_attempts >= self.max_reconnect_attempts:
            print(f"❌ 达到最大重连次数 ({self.max_reconnect_attempts})，停止重连")
            return
        
        self.current_reconnect_attempts += 1
        print(f"⏰ 安排重连 ({self.current_reconnect_attempts}/{self.max_reconnect_attempts})，{self.reconnect_interval}秒后执行")
        
        def reconnect():
            time.sleep(self.reconnect_interval)
            if self.status == ConnectionStatus.ERROR:
                print(f"🔄 执行自动重连 (第{self.current_reconnect_attempts}次)")
                self.connect_gateway()
        
        thread = threading.Thread(target=reconnect, daemon=True)
        thread.start()
    
    def switch_environment(self, env_type: str) -> bool:
        """
        切换环境类型
        
        Args:
            env_type: 环境类型 (SIMULATION/LIVE)
            
        Returns:
            bool: 切换是否成功
        """
        print(f"🔄 切换环境: {self.gateway_name} -> {env_type}")
        
        # 先断开当前连接
        if self.status == ConnectionStatus.CONNECTED:
            self.disconnect_gateway()
        
        # 更新配置
        old_name = self.gateway_name
        self.gateway_name = env_type
        self.simulation_mode = (env_type == "SIMULATION")
        
        print(f"✅ 环境切换完成: {old_name} -> {env_type}")
        return True
    
    def get_gateway_info(self) -> Dict:
        """获取网关信息"""
        return {
            "name": self.gateway_name,
            "simulation_mode": self.simulation_mode,
            "settings": self.gateway_settings,
            "capabilities": {
                "market_data": True,
                "trading": True,
                "account": True
            }
        }
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.status == ConnectionStatus.CONNECTED
    
    def get_uptime(self) -> Optional[float]:
        """获取连接持续时间（秒）"""
        if self.connected_time:
            return (datetime.now() - self.connected_time).total_seconds()
        return None


# 辅助函数
def create_connection_manager(config_file: str = "system_config.json") -> ConnectionManager:
    """
    创建连接管理器的便捷函数
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        ConnectionManager: 连接管理器实例
    """
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        return ConnectionManager(config)
        
    except FileNotFoundError:
        print(f"⚠️ 配置文件不存在: {config_file}")
        # 使用默认配置
        default_config = {
            "gateway": {
                "name": "SIMULATION",
                "settings": {
                    "mode": "simulation",
                    "symbols": ["rb2405", "i2405"]
                }
            }
        }
        return ConnectionManager(default_config)
        
    except Exception as e:
        print(f"❌ 创建连接管理器失败: {e}")
        raise


if __name__ == "__main__":
    """模块测试代码"""
    print("=" * 50)
    print("ConnectionManager 模块测试")
    print("=" * 50)
    
    # 创建连接管理器
    cm = create_connection_manager()
    
    # 注册状态回调
    def status_callback(new_status, old_status):
        print(f"📢 状态变化通知: {old_status.value} -> {new_status.value}")
    
    cm.register_status_callback(status_callback)
    
    # 测试连接
    print("\n🧪 测试连接功能...")
    success = cm.connect_gateway()
    print(f"连接结果: {success}")
    
    # 检查状态
    print("\n📊 连接状态:")
    status = cm.get_connection_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # 测试断开
    print("\n🧪 测试断开连接...")
    cm.disconnect_gateway()
    
    print("\n✅ ConnectionManager 测试完成")