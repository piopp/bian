# 币安管理系统后端

这是币安管理系统的后端服务，基于Flask和SQLite构建。

## 项目结构

```
back/
├── api/                 # API路由和控制器
├── models/              # 数据库模型
├── app.py               # 主应用文件
├── config.py            # 配置文件
├── requirements.txt     # 依赖列表
└── run.py               # 入口点脚本
```

## 安装

### 使用conda安装Python环境（推荐）

1. 安装Anaconda或Miniconda（如果尚未安装）:
   - Anaconda: https://www.anaconda.com/products/distribution
   - Miniconda: https://docs.conda.io/en/latest/miniconda.html

2. 创建conda环境:
```bash
conda create -n binance_mgmt python=3.9
```

3. 激活conda环境:
```bash
# Windows
conda activate binance_mgmt

# Linux/Mac
conda activate binance_mgmt
```

4. 安装依赖:
```bash
pip install -r requirements.txt
```

### 使用venv安装（可选）

1. 创建虚拟环境:

```bash
python -m venv venv
```

2. 激活虚拟环境:

- Windows:
```bash
venv\Scripts\activate
```

- Linux/Mac:
```bash
source venv/bin/activate
```

3. 安装依赖:

```bash
pip install -r requirements.txt
```

## 运行

```bash
python run.py
```

服务将在 http://localhost:5000 上运行。

## 初始化数据库

首次运行前需要初始化数据库：

```bash
python init_db.py
```

这将创建所有必要的数据库表。

## 数据迁移

如果要从现有的JSON文件迁移子账号API设置数据到数据库：

```bash
# 确保应用已经激活
export FLASK_APP=run.py   # Linux/Mac
set FLASK_APP=run.py      # Windows

# 运行迁移脚本
flask run-script migrate_api_settings
```

这将把存储在 `data/subaccount_api_settings.json` 文件中的子账号API设置迁移到数据库，并对原JSON文件进行备份。

## API端点

- `GET /`: 欢迎信息
- `POST /api/login`: 用户登录
- `GET /api/users`: 获取用户列表
- `GET /api/assets`: 获取账户资产信息
- `GET /api/markets`: 获取市场行情
- `GET /api/trades`: 获取交易历史
- `GET /api/orders`: 获取订单信息
- `GET /api/api_keys`: 获取API密钥信息
- `GET /api/settings`: 获取系统设置 