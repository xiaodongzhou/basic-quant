"""
系统配置文件
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 数据库配置
DATABASE_CONFIG = {
    "sqlite": {
        "path": BASE_DIR / "data" / "database" / "market_data.db"
    },
    "mongodb": {
        "url": os.getenv("MONGODB_URL", "mongodb://localhost:27017"),
        "database": os.getenv("DATABASE_NAME", "vnpy_quant")
    },
    "redis": {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", 6379)),
        "db": int(os.getenv("REDIS_DB", 0))
    }
}

# 交易所配置
GATEWAY_CONFIG = {
    "binance": {
        "api_key": os.getenv("BINANCE_API_KEY", ""),
        "secret_key": os.getenv("BINANCE_SECRET_KEY", ""),
        "testnet": os.getenv("BINANCE_TESTNET", "true").lower() == "true",
        "base_url": "https://testnet.binance.vision" if os.getenv("BINANCE_TESTNET", "true").lower() == "true" else "https://api.binance.com"
    },
    "ctp": {
        "用户名": os.getenv("CTP_USERID", ""),
        "密码": os.getenv("CTP_PASSWORD", ""), 
        "经纪商代码": os.getenv("CTP_BROKERID", ""),
        "交易服务器": os.getenv("CTP_TD_ADDRESS", ""),
        "行情服务器": os.getenv("CTP_MD_ADDRESS", "")
    }
}

# 日志配置
LOGGING_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "file": BASE_DIR / "logs" / "vnpy_quant.log",
    "rotation": "1 day",
    "retention": "30 days"
}

# 回测配置
BACKTEST_CONFIG = {
    "start_date": os.getenv("BACKTEST_START_DATE", "2020-01-01"),
    "end_date": os.getenv("BACKTEST_END_DATE", "2023-12-31"),
    "capital": float(os.getenv("BACKTEST_CAPITAL", 1000000)),
    "commission": 0.001,  # 手续费率
    "slippage": 0.0001,   # 滑点
}

# 风险管理配置
RISK_CONFIG = {
    "max_daily_loss": float(os.getenv("MAX_DAILY_LOSS", 50000)),
    "max_position_size": float(os.getenv("MAX_POSITION_SIZE", 0.3)),
    "stop_loss_rate": float(os.getenv("STOP_LOSS_RATE", 0.02))
}

# 数据路径配置
DATA_PATHS = {
    "csv": BASE_DIR / "data" / "csv",
    "database": BASE_DIR / "data" / "database",
    "logs": BASE_DIR / "logs"
}

# 确保数据目录存在
for path in DATA_PATHS.values():
    path.mkdir(parents=True, exist_ok=True)