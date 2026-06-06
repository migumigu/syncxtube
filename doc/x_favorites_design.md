# X.com 红心收藏夹同步功能 - 扩展设计文档

## 1. 背景与目标

### 1.1 项目现状

当前项目 (SaveXTube) 基于 `dysync.net` 分支（实为从 SaveXTube 拉取），已支持：
- X.com 视频/图片下载（通过 gallery-dl + yt-dlp）
- B站收藏夹订阅同步 (`bilibili_favsub.py`)
- 多平台多媒体下载

### 1.2 需求目标

新增 **X.com 红心喜欢（Likes/Bookmarks）订阅同步功能**，允许用户：
- 订阅自己的 X 账户红心内容
- 自动检测新的红心视频/图片
- 自动下载新增的红心内容到本地

### 1.3 设计原则

> **尽可能少的调整现有代码，便于后续同步更新**

遵循以下原则：
1. 新增独立模块 `x_favorites_subscription.py`，不修改现有核心逻辑
2. 配置通过 `savextube.toml` 扩展，避免硬编码
3. 参考现有 `BilibiliFavSubscriptionManager` 的订阅模式
4. 复用现有的 X.cookies 认证机制

---

## 2. 技术方案

### 2.1 X.com Likes 获取方式分析

| 方式 | 可行性 | 说明 |
|------|--------|------|
| Twitter API v2 | ⚠️ 需要开发者账号 | 有 official API 但需要审批 |
| gallery-dl | ✅ 可行 | 已有 X 支持，理论上可扩展 |
| 网页抓取 | ⚠️ 风险高 | 易触发风控，不推荐 |

**推荐方案**：扩展 gallery-dl 配置 + 新增订阅管理器

gallery-dl 支持通过 `x_auth` 配置使用 cookies 认证访问用户收藏内容。

### 2.2 整体架构

```
┌─────────────────────────────────────────────────────────┐
│              main.py (最小改动)                         │
│  ┌───────────────────┐  ┌───────────────────────────┐  │
│  │ BilibiliFavSub    │  │ XFavoritesSubscription    │  │
│  │ (已有)            │  │ (新增，结构相似)           │  │
│  └───────────────────┘  └───────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────┐
│              x_favorites_subscription.py                 │
│  ┌─────────────────────────────────────────────────┐    │
│  │ XFavoritesSubscriptionManager                    │    │
│  │  - load_subscriptions()                        │    │
│  │  - add_subscription()                          │    │
│  │  - _check_loop()                               │    │
│  │  - _download_new_favorites()                    │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────┐
│              gallery-dl + x_cookies.txt                  │
│  支持访问用户收藏/红心内容                              │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 模块设计

### 3.1 新增文件

**文件名**: `x_favorites_subscription.py`

**位置**: 与 `bilibili_favsub.py` 同目录

### 3.2 类设计

```python
class XFavoritesSubscriptionManager:
    """X.com 红心收藏订阅管理器"""

    def __init__(self, download_path: str, proxy_host: Optional[str] = None,
                 cookies_path: Optional[str] = None):
        """
        初始化订阅管理器

        Args:
            download_path: 下载目录路径 (e.g., /downloads/X/Likes)
            proxy_host: 代理服务器地址
            cookies_path: X cookies 文件路径
        """
        self.download_path = Path(download_path)
        self.proxy_host = proxy_host
        self.cookies_path = cookies_path
        self.poll_interval = int(os.getenv("X_POLL_INTERVAL", "60"))
        self.subscriptions_file = self.download_path / "x_likes_subscriptions.json"
        self.check_task: Optional[asyncio.Task] = None

    # ===== 订阅管理 =====

    def load_subscriptions(self) -> Dict[str, Any]:
        """加载订阅列表"""

    def save_subscriptions(self, subscriptions: Dict[str, Any]) -> bool:
        """保存订阅列表"""

    async def validate_account(self) -> Dict[str, Any]:
        """验证 X 账户认证状态"""

    async def add_subscription(self, user_id: int) -> Dict[str, Any]:
        """添加红心订阅（当前仅支持单一用户订阅）"""

    def remove_subscription(self) -> Dict[str, Any]:
        """移除红心订阅"""

    def get_subscriptions_list(self) -> List[Dict[str, Any]]:
        """获取订阅列表"""

    # ===== 后台任务 =====

    def ensure_check_task_running(self):
        """确保检查任务正在运行"""

    async def stop_check_task(self):
        """停止检查任务"""

    async def _check_loop(self):
        """订阅检查循环"""

    async def _check_subscription(self) -> bool:
        """检查单个订阅"""

    # ===== 下载逻辑 =====

    async def _get_liked_content(self) -> List[Dict]:
        """获取当前红心内容列表"""

    async def _download_new_favorites(self, new_items: List[Dict]) -> Dict[str, Any]:
        """下载新增的红心内容"""
```

### 3.3 数据结构

**订阅文件**: `x_likes_subscriptions.json`

```json
{
  "account": {
    "username": "user_handle",
    "user_id": "123456789",
    "added_time": 1699999999,
    "last_check": 1699999999,
    "last_item_count": 100,
    "download_count": 50
  }
}
```

---

## 4. 配置扩展

### 4.1 savextube.toml 新增配置项

```toml
[x]
# X (Twitter) 收藏订阅配置
x_poll_interval = 60          # 检查间隔（分钟），默认60
x_likes_cookies = "/app/cookies/x_cookies.txt"  # 复用现有cookies

[x.download]
# X 下载路径配置（可选，默认使用 X 目录下的 Likes 子目录）
likes_path = "/downloads/X/Likes"
```

### 4.2 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `X_POLL_INTERVAL` | 订阅检查间隔（分钟） | 60 |
| `X_LIKES_COOKIES` | Cookies 文件路径 | `/app/cookies/x_cookies.txt` |

---

## 5. 集成方案

### 5.1 main.py 改动点（最小化）

**位置 1**: import 部分（约第 65 行附近）

```python
# 新增 import
try:
    from .x_favorites_subscription import XFavoritesSubscriptionManager
except ImportError:
    from x_favorites_subscription import XFavoritesSubscriptionManager
```

**位置 2**: 类初始化（约第 2150 行附近）

```python
# 在 SaveXTube.__init__ 中新增
self.x_favorites_manager: Optional[XFavoritesSubscriptionManager] = None
```

**位置 3**: 初始化逻辑（约第 2200 行附近）

```python
# 在 setup_directories 方法中新增
self.x_favorites_manager = XFavoritesSubscriptionManager(
    download_path=str(self.x_download_path / "Likes"),
    proxy_host=self.proxy_host,
    cookies_path=str(self.x_cookies_path)
)
```

**位置 4**: Telegram 命令处理（约 `/favsub` 附近）

新增 `/xfav` 命令处理函数：

```python
async def xfav_command_handler(update: Update, context: CallbackContext):
    """处理 X 收藏订阅命令"""
    # /xfav - 查看订阅状态
    # /xfav add - 添加订阅
    # /xfav remove - 移除订阅
    # /xfav check - 手动检查
```

### 5.2 复用现有 X 下载逻辑

X 红心下载直接复用 `main.py` 中现有的 `_download_x` 方法（或 gallery-dl 调用），无需重写下载逻辑。

```python
async def _download_x_item(self, item_url: str) -> Dict[str, Any]:
    """下载单个 X 内容（复用现有下载器）"""
    # 调用现有的 x download 逻辑
    return await self._download_single_video(item_url, ...)
```

---

## 6. API/命令设计

### 6.1 Telegram 命令

| 命令 | 功能 |
|------|------|
| `/xfav` | 查看 X 收藏订阅状态 |
| `/xfav add` | 添加/开启订阅 |
| `/xfav remove` | 移除订阅 |
| `/xfav check` | 手动触发一次检查 |

### 6.2 返回示例

```
📌 X 收藏订阅状态

账户: @username
状态: ✅ 已订阅
检查间隔: 60 分钟
上次检查: 2024-01-15 10:30:00
已下载: 50 条内容
```

---

## 7. 风险与限制

### 7.1 X 平台限制

1. **API 限制**: X/Twitter API 对收藏内容访问有严格限制
2. **风控风险**: 频繁请求可能触发 IP 封禁
3. **认证依赖**: 必须提供有效的 cookies

### 7.2 缓解措施

1. 设置合理的检查间隔（建议 ≥30 分钟）
2. 添加请求延迟和重试机制
3. 使用代理服务器（可选）
4. 仅下载新增内容，避免全量下载

### 7.3 Cookies 过期处理

- 检测到认证失败时，输出警告日志
- 不自动删除订阅，保留用户配置
- 建议用户定期更新 cookies

---

## 8. 开发计划

### Phase 1: 核心模块
- [ ] 创建 `x_favorites_subscription.py`
- [ ] 实现订阅管理基础功能
- [ ] 实现检查循环

### Phase 2: 下载集成
- [ ] 集成现有 X 下载逻辑
- [ ] 实现增量下载（只下新增）
- [ ] 文件名去重处理

### Phase 3: 配置与命令
- [ ] 扩展 `savextube.toml` 配置
- [ ] 添加 Telegram 命令处理
- [ ] 状态查询与显示

### Phase 4: 测试优化
- [ ] 本地测试验证
- [ ] 长周期稳定性测试
- [ ] 文档更新

---

## 9. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `x_favorites_subscription.py` | 新增 | X 收藏订阅管理模块 |
| `savextube.toml` | 修改 | 添加 `[x]` 配置段 |
| `main.py` | 修改 | 约 20-30 行改动（import + 初始化 + 命令） |
| `README.md` | 修改 | 文档更新（非必须） |

**代码改动量估计**: < 50 行新增代码在 main.py 中

---

## 10. 参考资料

- SaveXTube 项目: https://github.com/the1812/SaveXTube
- BilibiliFavSubscriptionManager: `bilibili_favsub.py`
- gallery-dl X 支持: https://github.com/mikf/gallery-dl
- X/Twitter API: https://developer.twitter.com/en/docs/twitter-api
