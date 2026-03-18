# 30天减脂打卡 · 后端 API

**技术栈**：Python · FastAPI · SQLite

---

## 📁 文件结构

```
backend/
├── main.py           # 入口，注册路由
├── database.py       # SQLite 连接 & 建表
├── auth_utils.py     # 密码哈希 + JWT 工具
├── auth_router.py    # /auth  注册/登录
├── plan_router.py    # /plans 计划管理
├── checkin_router.py # /checkins 打卡记录
├── requirements.txt
└── checkin.db        # 自动生成，勿上传 git
```

---

## 🚀 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务（开发模式，自动热重载）
uvicorn main:app --reload --port 8000

py -m uvicorn main:app --reload --port 8000

# 3. 访问交互文档
open http://localhost:8000/docs
```

---

## 🔌 API 一览

### 认证 `/auth`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 注册，返回 token |
| POST | `/auth/login`    | 登录，返回 token |
| GET  | `/auth/me`       | 获取当前用户信息（需 token） |

**请求头**（需要认证的接口）：
```
Authorization: Bearer <token>
```

---

### 计划 `/plans`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST   | `/plans`         | 创建新一轮计划 |
| GET    | `/plans`         | 我的所有计划 |
| GET    | `/plans/active`  | 当前活跃计划 |
| DELETE | `/plans/{id}`    | 删除计划 |

**创建计划请求体**：
```json
{
  "title": "第二轮减脂",
  "start_date": "2025-06-01"
}
```

---

### 打卡 `/checkins`

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/checkins/{plan_id}/{date}` | 保存/更新某天打卡 |
| GET | `/checkins/{plan_id}`        | 获取30天全部记录 |
| GET | `/checkins/{plan_id}/{date}` | 获取某天详情 |
| GET | `/checkins/{plan_id}/stats/summary` | 统计摘要 |

**打卡请求体**（所有字段均可选，只传有变化的）：
```json
{
  "weight": 120.5,
  "waist": 72.0,
  "thigh": 52.0,
  "sports": ["跑步", "跳绳"],
  "lunch": "糙米饭 + 鸡胸肉 + 西兰花",
  "snack": "酸奶100g",
  "dinner": "燕麦粥 + 水煮蛋",
  "is_done": true,
  "mood": 4,
  "water_ml": 2000,
  "note": "今天状态很好！"
}
```

---

## 🔒 生产环境注意事项

1. **修改 `SECRET_KEY`**（`auth_utils.py` 第6行），换成随机长字符串，建议通过环境变量注入：
   ```python
   import os
   SECRET_KEY = os.environ.get("SECRET_KEY", "fallback_dev_key")
   ```

2. **CORS 配置**（`main.py`），将 `allow_origins=["*"]` 改为你的前端域名：
   ```python
   allow_origins=["https://yourdomain.com"]
   ```

3. `checkin.db` 加入 `.gitignore`，不要提交到代码仓库。

---

## 🔄 前端改造要点

原前端用 `localStorage` 存数据，接入后端后只需：

1. 注册/登录后将 `token` 存入 `localStorage`
2. 每次 `onFieldChange` / `onCheckChange` 时改为调用 `PUT /checkins/{plan_id}/{date}`
3. 页面加载时调用 `GET /checkins/{plan_id}` 替换原来的 `loadData()`
