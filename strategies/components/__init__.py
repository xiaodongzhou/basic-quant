"""
策略组件模块
包含方向分析器、位置管理器、信号生成器的实现
"""

from .direction_analyzers import (
    MovingAverageDirectionAnalyzer,
    TrendlineDirectionAnalyzer, 
    MultiIndicatorDirectionAnalyzer
)

from .position_managers import (
    SupportResistancePositionManager,
    ATRPositionManager,
    FibonacciPositionManager
)

from .signal_generators import (
    PriceActionSignalGenerator,
    BreakoutSignalGenerator
)

__all__ = [
    # Direction Analyzers
    'MovingAverageDirectionAnalyzer',
    'TrendlineDirectionAnalyzer',
    'MultiIndicatorDirectionAnalyzer',
    
    # Position Managers
    'SupportResistancePositionManager', 
    'ATRPositionManager',
    'FibonacciPositionManager',
    
    # Signal Generators
    'PriceActionSignalGenerator',
    'BreakoutSignalGenerator'
]