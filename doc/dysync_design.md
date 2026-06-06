# dysync.net 抖音红心收藏夹同步工具 - 设计文档

## 1. 项目概述

**项目名称**: dysync.net（抖小云）

**项目地址**: 
- Gitee: https://gitee.com/deathvicky/dysync.net
- GitHub: https://github.com/jianzhichu/dysync.net

**技术栈**:
- 后端: .NET Core 6.0
- 前端: Vue.js (SPA)
- 数据库: SQLite
- 视频处理: FFmpeg
- 部署方式: Docker

**核心功能**: 
同步抖音收藏夹、「我喜欢」的视频及指定博主作品，解决收藏视频失效问题，支持 Emby/Jellyfin 媒体库集成。

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Vue.js Frontend                      │
│              (Web UI - 端口 10101)                      │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP/REST
┌─────────────────────▼───────────────────────────────────┐
│                 .NET Core 6.0 Backend                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ Controllers │  │  Services   │  │     Utils       │  │
│  │ - Video     │  │ - Video     │  │ - RequestParam  │  │
│  │ - Follow    │  │ - Follow    │  │ - FFmpeg        │  │
│  │ - Config    │  │ - Common     │  │ - NfoGenerator  │  │
│  │ - Auth      │  │ - QuartzJob  │  │                 │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                    SQLite Database                       │
│         (存储配置、同步记录、视频元数据)                  │
└─────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   File System                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │
│  │ /collect │  │ /favorite │  │  /uper   │  │  /db    │  │
│  │ 收藏视频  │  │ 喜欢视频  │  │ 博主视频  │  │ 数据库   │  │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 核心模块设计

### 3.1 认证模块 (AuthController)

**功能**: 用户登录认证

**关键凭证**:
| 凭证 | 说明 | 获取方式 |
|------|------|----------|
| Cookie | 抖音登录态 | F12 → Network → 复制完整 Cookie |
| sec_user_id | 用户唯一标识 | 抖音主页 URL 或请求 Headers |

**默认账号**: 
- 用户名: `douyin`
- 密码: `douyin2025` (新版), `douyin2026`

### 3.2 视频同步模块 (VideoController)

**API 端点**: `/api/video`

**核心接口**:

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/video/paged` | 分页查询收藏视频 |
| GET | `/api/video/statics` | 查询统计数据 |
| GET | `/api/video/play/{vid}` | 播放视频 |

**视频分类**:
1. **收藏视频** (`collect`) - 用户收藏夹中的视频
2. **喜欢视频** (`favorite`) - 用户「我喜欢」的视频
3. **博主作品** (`uper`) - 指定博主发布的视频

### 3.3 关注同步模块 (FollowController)

**API 端点**: `/api/follow`

**核心接口**:

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/follow/paged` | 分页查询关注列表 |
| GET | `/api/follow/sync` | 重新同步关注列表 |
| POST | `/api/follow/add` | 添加关注对象 |
| POST | `/api/follow/openOrCloseSync` | 修改同步状态 |
| POST | `/api/follow/delete` | 删除关注对象 |

### 3.4 配置模块 (ConfigController)

**API 端点**: `/api/config`

**功能**:
- 抖音授权配置 (Cookie, sec_user_id)
- 同步策略配置 (定时周期、批量大小)
- 路径映射配置

---

## 4. 抖音 API 对接设计

### 4.1 API 请求参数管理 (DouyinRequestParamManager)

**核心配置**:

```csharp
// 基础请求参数
BaseParams = {
    device_platform: "webapp",
    aid: "6383",
    channel: "channel_pc_web",
    pc_client_type: "1",
    browser_language: "zh-CN",
    browser_platform: "Win32",
    browser_name: "Chrome",
    os_name: "Windows",
    os_version: "10",
    platform: "PC"
}

// API 域名
DouyinHost = "https://www.douyin.com"
```

### 4.2 核心 API 端点

| 功能 | API 端点 | 说明 |
|------|----------|------|
| 收藏列表 | `v1/web/aweme/listcollection` | 获取用户收藏夹 |
| 喜欢列表 | `v1/web/aweme/like` | 获取用户喜欢视频 |
| 关注列表 | `aweme/v1/web/follow/follow/list/` | 获取关注博主 |
| 博主视频 | `aweme/v1/web/aweme/post/` | 获取博主作品 |
| 视频详情 | `aweme/v1/web/aweme/detail/` | 获取视频详细信息 |

### 4.3 请求流程

```
1. 构建请求参数
   ├─ 基础参数 (device_platform, aid, channel...)
   ├─ 用户参数 (sec_user_id, cookie)
   └─ 业务参数 (cursor, count, max_cursor...)

2. 签名参数 (MSToken, Xgplayer)

3. 发送 HTTP 请求
   └─ GET/POST https://www.douyin.com/{endpoint}

4. 解析响应
   └─ JSON → DouyinCollectListResponse / DouyinVideoInfoResponse
```

---

## 5. 数据模型设计

### 5.1 响应模型

**DouyinCollectListResponse** (收藏夹列表响应):
```csharp
{
    collects_list: List<DouyinCollectItem>,  // 收藏列表
    cursor: int,                              // 分页游标
    has_more: bool,                           // 是否有更多
    status_code: int,                         // 状态码 (0=成功)
    total_number: int                         // 总数
}
```

**DouyinVideoInfoResponse** (视频信息响应):
```csharp
{
    aweme_list: List<Aweme>,    // 视频列表
    cursor: string,             // 分页游标
    max_cursor: string,         // 最大游标
    uid: string,                // 用户ID
    has_more: int,              // 是否有更多
    status_code: int            // 状态码
}
```

**Aweme** (视频实体):
```csharp
{
    aweme_id: string,           // 视频ID
    author: Author,             // 作者信息
    author_user_id: long,       // 作者用户ID
    // 视频流信息 (在 play_addr 或 download_addr)
    // 封面信息 (在 cover 或 thumbnail)
    // 标题信息 (在 desc)
}
```

### 5.2 数据库实体

**AppConfig** (应用配置):
- Id, Cron (同步周期), BatchCount (批量数)
- Cookie, SecUserId (抖音授权)
- VideoEncoder (视频编码器)

**DouyinVideo** (视频记录):
- Vid (视频ID), Title, Author, CoverUrl
- FilePath, DownloadTime, VideoType (收藏/喜欢/博主)
- Status, IsDeleted

**DouyinFollowed** (关注博主):
- SecUid, Nickname, SyncEnabled, FullSyncEnabled
- SavePath, LastSyncTime

---

## 6. 视频下载流程

```
1. 获取视频列表
   └─ 调用抖音 API → 解析 aweme_list

2. 遍历视频项
   ├─ 检查是否已下载 (查数据库)
   └─ 提取视频信息 (标题、作者、封面)

3. 下载视频
   ├─ 提取播放地址 (play_addr.download_url)
   ├─ HTTP 下载视频文件
   └─ FFmpeg 处理 (可选: 合并音视频、添加封面)

4. 保存文件
   ├─ 生成文件名 (标题_视频ID.mp4)
   ├─ 保存到对应目录 (collect/favorite/uper)
   └─ 写入数据库记录

5. 生成元数据
   └─ NfoFileGenerator 生成 .nfo 文件
       (供 Emby/Jellyfin 刮削使用)
```

---

## 7. 路径映射规则

**容器内路径 → 宿主机路径**:

| 容器路径 | 说明 | 用途 |
|----------|------|------|
| `/app/collect` | 收藏视频 | 存储收藏夹同步的视频 |
| `/app/favorite` | 喜欢视频 | 存储「我喜欢」的视频 |
| `/app/uper` | 博主视频 | 存储关注博主的作品 |
| `/app/db` | 数据库 | SQLite 数据库文件 |
| `/app/mp3` | 音频素材 | 图文视频合成用音频 |
| `/app/mix` | 合集 | 抖音合集视频 |
| `/app/series` | 短剧 | 短剧视频 |

**重要**: 路径映射必须与配置页面一致，否则 Emby/Jellyfin 无法访问。

---

## 8. 媒体库集成

### 8.1 NFO 元数据文件

工具会自动生成 NFO 文件，包含:
- 标题 (title)
- 作者 (artist/actor)
- 封面 (thumb)
- 年份 (year)
- 简介 (plot)

### 8.2 Emby/Jellyfin 配置

将 `collect`、`favorite`、`uper` 目录映射为媒体库，内容类型选择「影片」。

---

## 9. 定时同步机制

**QuartzJob 调度**:
- 支持 Cron 表达式配置同步周期
- 默认周期: 30 分钟
- 支持手动触发全量同步

**风控策略**:
- 全量同步需谨慎 (易触发抖音风控)
- 建议分批同步，控制请求频率

---

## 10. 技术亮点

| 特性 | 实现方式 |
|------|----------|
| 无水印下载 | 解析 `download_addr` 而非 `play_addr` |
| 图文视频 | FFmpeg 合成图片+音频 |
| 断点续传 | 数据库记录已下载状态 |
| 去重下载 | MD5 比对视频文件 |
| 媒体库兼容 | NFO + 封面元数据 |
| 多账号支持 | 独立 Cookie/sec_user_id 配置 |

---

## 11. 参考资料

- 项目地址: https://gitee.com/deathvicky/dysync.net
- Docker 镜像: `registry.cn-hangzhou.aliyuncs.com/jianzhichu/dysync.net`
- 问题反馈 Q 群: 759876963
