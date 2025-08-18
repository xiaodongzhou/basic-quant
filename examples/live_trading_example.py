"""
实盘交易示例
演示如何使用实盘交易引擎
"""
import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from strategies import MovingAverageStrategy, RSIStrategy
from trading import LiveEngine
from data import DataManager


def run_live_trading_demo():
    """运行实盘交易演示"""
    print("VN.PY量化交易系统 - 实盘交易演示")
    print("="*60)
    
    # 创建交易引擎
    engine = LiveEngine(initial_balance=100000)
    
    try:
        # 启动引擎
        engine.start_engine()
        print("交易引擎已启动")
        
        # 创建策略
        ma_strategy = MovingAverageStrategy(
            name="MA_Demo",
            symbol="BTCUSDT",
            parameters={
                'fast_ma_period': 5,
                'slow_ma_period': 15,
                'volume': 0.01
            }
        )
        
        rsi_strategy = RSIStrategy(
            name="RSI_Demo", 
            symbol="ETHUSDT",
            parameters={
                'rsi_period': 14,
                'oversold': 30,
                'overbought': 70,
                'volume': 0.1
            }
        )
        
        # 添加策略
        engine.add_strategy(ma_strategy)
        engine.add_strategy(rsi_strategy)
        print("策略已添加")
        
        # 模拟手动下单
        print("\n手动下单演示:")
        order_id1 = engine.place_order("BTCUSDT", "BUY", 0.001, order_type="MARKET", strategy_name="Manual")
        if order_id1:
            print(f"市价买单已下达: {order_id1}")
        
        # 等待一段时间让价格更新
        print("\n等待5秒，观察价格和持仓变化...")
        for i in range(5):
            time.sleep(1)
            print(f"等待中... {i+1}/5")
        
        # 查看账户信息
        account_info = engine.get_account_info()
        print(f"\n账户信息:")
        print(f"账户余额: {account_info['balance']:,.2f}")
        print(f"可用资金: {account_info['available']:,.2f}")
        print(f"冻结资金: {account_info['frozen']:,.2f}")
        print(f"总权益: {account_info['total_equity']:,.2f}")
        print(f"浮动盈亏: {account_info['unrealized_pnl']:,.2f}")
        
        # 查看持仓
        positions = engine.get_positions()
        print(f"\n持仓信息:")
        if positions:
            for symbol, pos in positions.items():
                print(f"{symbol}: 数量={pos['size']:.6f}, 均价={pos['avg_price']:.2f}, "
                      f"市值={pos['market_value']:.2f}, 盈亏={pos['pnl']:.2f}")
        else:
            print("无持仓")
        
        # 查看订单统计
        order_stats = engine.order_manager.get_statistics()
        print(f"\n订单统计:")
        print(f"总订单数: {order_stats['total_orders']}")
        print(f"活跃订单: {order_stats['active_orders']}")
        print(f"成交订单: {order_stats['filled_orders']}")
        print(f"成交率: {order_stats['fill_rate']:.2%}")
        
        # 查看成交记录
        trades = engine.order_manager.get_trades()
        print(f"\n成交记录:")
        if trades:
            for trade in trades[-5:]:  # 显示最近5笔成交
                trade_dict = trade.to_dict()
                print(f"{trade_dict['symbol']} {trade_dict['direction']} "
                      f"{trade_dict['volume']}@{trade_dict['price']} "
                      f"时间:{trade_dict['trade_time'][:19]}")
        else:
            print("无成交记录")
        
        # 演示限价单
        print(f"\n限价单演示:")
        current_prices = engine.subscribed_symbols
        if "BTCUSDT" in current_prices:
            current_price = current_prices["BTCUSDT"]
            limit_price = current_price * 0.99  # 低于当前价格1%的限价买单
            order_id2 = engine.place_order(
                "BTCUSDT", "BUY", 0.001, 
                price=limit_price, order_type="LIMIT", 
                strategy_name="Manual_Limit"
            )
            if order_id2:
                print(f"限价买单已下达: {order_id2} @ {limit_price:.2f}")
        
        # 再等待一段时间
        print(f"\n再等待3秒...")
        for i in range(3):
            time.sleep(1)
            print(f"等待中... {i+1}/3")
        
        # 最终状态
        print(f"\n最终状态:")
        final_account = engine.get_account_info()
        print(f"最终权益: {final_account['total_equity']:,.2f}")
        print(f"总盈亏: {final_account['total_pnl']:,.2f}")
        
        final_positions = engine.get_positions()
        print(f"最终持仓数量: {len(final_positions)}")
        
    except KeyboardInterrupt:
        print("\n用户中断演示")
    except Exception as e:
        print(f"\n演示过程中出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        print("\n正在关闭交易引擎...")
        engine.close()
        print("演示结束")


def interactive_trading_demo():
    """交互式交易演示"""
    print("VN.PY量化交易系统 - 交互式交易演示")
    print("="*60)
    
    engine = LiveEngine(initial_balance=50000)
    engine.start_engine()
    
    print("交易引擎已启动，输入 'help' 查看命令")
    print("当前资金: 50,000")
    
    try:
        while True:
            command = input("\ntrade> ").strip().lower()
            
            if command in ['quit', 'exit', 'q']:
                break
            elif command == 'help':
                print("可用命令:")
                print("  buy <symbol> <volume> [price]  - 买入")
                print("  sell <symbol> <volume> [price] - 卖出") 
                print("  account                        - 查看账户")
                print("  positions                      - 查看持仓")
                print("  orders                         - 查看订单")
                print("  prices                         - 查看价格")
                print("  cancel <order_id>              - 撤单")
                print("  quit/exit                      - 退出")
                
            elif command == 'account':
                account = engine.get_account_info()
                print(f"余额: {account['balance']:,.2f}")
                print(f"可用: {account['available']:,.2f}")
                print(f"权益: {account['total_equity']:,.2f}")
                print(f"盈亏: {account['total_pnl']:,.2f}")
                
            elif command == 'positions':
                positions = engine.get_positions()
                if positions:
                    for symbol, pos in positions.items():
                        print(f"{symbol}: {pos['size']:.6f} @ {pos['avg_price']:.2f} "
                              f"盈亏: {pos['pnl']:.2f}")
                else:
                    print("无持仓")
                    
            elif command == 'orders':
                active_orders = engine.order_manager.get_active_orders()
                if active_orders:
                    for order in active_orders:
                        print(f"{order.order_id}: {order.symbol} {order.direction.value} "
                              f"{order.volume} @ {order.price}")
                else:
                    print("无活跃订单")
                    
            elif command == 'prices':
                prices = engine.subscribed_symbols
                for symbol, price in prices.items():
                    print(f"{symbol}: {price:.2f}")
                    
            elif command.startswith('buy ') or command.startswith('sell '):
                parts = command.split()
                if len(parts) >= 3:
                    direction = parts[0].upper()
                    symbol = parts[1].upper()
                    volume = float(parts[2])
                    price = float(parts[3]) if len(parts) > 3 else 0
                    order_type = "LIMIT" if price > 0 else "MARKET"
                    
                    order_id = engine.place_order(symbol, direction, volume, price, order_type)
                    if order_id:
                        print(f"订单已下达: {order_id}")
                    else:
                        print("下单失败")
                else:
                    print("用法: buy/sell <symbol> <volume> [price]")
                    
            elif command.startswith('cancel '):
                parts = command.split()
                if len(parts) == 2:
                    order_id = parts[1]
                    if engine.cancel_order(order_id):
                        print(f"订单 {order_id} 已撤销")
                    else:
                        print("撤单失败")
                else:
                    print("用法: cancel <order_id>")
            else:
                print("未知命令，输入 'help' 查看帮助")
                
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        engine.close()
        print("交易演示结束")


if __name__ == "__main__":
    print("选择演示模式:")
    print("1. 自动演示")
    print("2. 交互式演示")
    
    choice = input("请选择 (1/2): ").strip()
    
    if choice == "1":
        run_live_trading_demo()
    elif choice == "2":
        interactive_trading_demo()
    else:
        print("无效选择")