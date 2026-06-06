#!/usr/bin/env python3
"""
X (Twitter) 红心收藏订阅管理模块
负责处理 X 红心内容的订阅、检查和自动下载功能
"""

import os
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# 设置日志
logger = logging.getLogger("savextube")


class XFavoritesSubscriptionManager:
    """X 红心收藏订阅管理器"""

    def __init__(self, download_path: str, proxy_host: Optional[str] = None,
                 cookies_path: Optional[str] = None):
        """
        初始化订阅管理器

        Args:
            download_path: 下载目录路径
            proxy_host: 代理服务器地址
            cookies_path: X cookies文件路径
        """
        self.download_path = Path(download_path)
        self.proxy_host = proxy_host
        self.cookies_path = cookies_path

        # 从环境变量获取检查间隔（分钟）
        self.poll_interval = int(os.getenv("X_POLL_INTERVAL", "60"))

        # 订阅数据文件路径
        self.subscriptions_file = self.download_path / "x_favorites_subscriptions.json"

        # 订阅下载目录
        self.likes_download_path = self.download_path / "Likes"
        self.likes_download_path.mkdir(parents=True, exist_ok=True)

        # 后台任务
        self.check_task: Optional[asyncio.Task] = None

        # 下载回调（由主程序设置）
        self.download_callback = None

        logger.info(f"🎯 X 红心收藏订阅管理器初始化完成")
        logger.info(f"📁 下载目录: {self.likes_download_path}")
        logger.info(f"⏰ 检查间隔: {self.poll_interval} 分钟")
        if self.proxy_host:
            logger.info(f"🌐 使用代理: {self.proxy_host}")
        if self.cookies_path:
            logger.info(f"🍪 使用cookies: {self.cookies_path}")

    def load_subscriptions(self) -> Dict[str, Any]:
        """加载订阅列表"""
        try:
            if self.subscriptions_file.exists():
                with open(self.subscriptions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"🎯 加载 X 收藏订阅失败: {e}")
            return {}

    def save_subscriptions(self, subscriptions: Dict[str, Any]) -> bool:
        """保存订阅列表"""
        try:
            self.subscriptions_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.subscriptions_file, 'w', encoding='utf-8') as f:
                json.dump(subscriptions, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"🎯 保存 X 收藏订阅失败: {e}")
            return False

    async def validate_account(self) -> Dict[str, Any]:
        """
        验证 X 账号认证状态

        Returns:
            验证结果字典
        """
        try:
            if not self.cookies_path or not os.path.exists(self.cookies_path):
                return {
                    "success": False,
                    "error": "未配置 X cookies，请先设置 cookies"
                }

            # TODO: 可以尝试访问简单页面验证 cookies 有效性
            return {
                "success": True,
                "message": "账号验证成功（cookies 已配置）"
            }
        except Exception as e:
            logger.error(f"🎯 验证 X 账号失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def add_subscription(self) -> Dict[str, Any]:
        """
        添加红心订阅（当前仅支持单一用户订阅）

        Returns:
            操作结果字典
        """
        try:
            # 验证账号
            validation_result = await self.validate_account()
            if not validation_result["success"]:
                return validation_result

            # 加载现有订阅
            subscriptions = self.load_subscriptions()

            # 检查是否已订阅
            if "account" in subscriptions:
                return {
                    "success": False,
                    "error": "已订阅 X 红心收藏，无需重复添加"
                }

            # 添加新订阅
            subscriptions["account"] = {
                "added_time": time.time(),
                "last_check": 0,
                "last_item_count": 0,
                "downloaded_ids": [],
                "download_count": 0
            }

            # 保存订阅
            if self.save_subscriptions(subscriptions):
                logger.info("🎯 成功添加 X 红心收藏订阅")

                # 启动检查任务（如果还没启动）
                self.ensure_check_task_running()

                return {
                    "success": True,
                    "message": "订阅成功！系统将定期检查并下载新的红心内容"
                }
            else:
                return {"success": False, "error": "保存订阅失败"}

        except Exception as e:
            logger.error(f"🎯 添加 X 收藏订阅失败: {e}")
            return {"success": False, "error": str(e)}

    def remove_subscription(self) -> Dict[str, Any]:
        """
        移除红心订阅

        Returns:
            操作结果字典
        """
        try:
            subscriptions = self.load_subscriptions()

            if "account" not in subscriptions:
                return {"success": False, "error": "未订阅 X 红心收藏"}

            # 删除订阅
            del subscriptions["account"]

            # 保存订阅
            if self.save_subscriptions(subscriptions):
                logger.info("🎯 成功移除 X 红心收藏订阅")
                return {
                    "success": True,
                    "message": "已取消 X 红心收藏订阅"
                }
            else:
                return {"success": False, "error": "保存订阅失败"}

        except Exception as e:
            logger.error(f"🎯 移除 X 收藏订阅失败: {e}")
            return {"success": False, "error": str(e)}

    def get_subscriptions_list(self) -> List[Dict[str, Any]]:
        """获取订阅列表（X 目前只支持单用户订阅）"""
        try:
            subscriptions = self.load_subscriptions()
            if "account" in subscriptions:
                account = subscriptions["account"]
                return [{
                    "type": "account",
                    "added_time": account.get("added_time", 0),
                    "last_check": account.get("last_check", 0),
                    "last_item_count": account.get("last_item_count", 0),
                    "download_count": account.get("download_count", 0)
                }]
            return []
        except Exception as e:
            logger.error(f"🎯 获取 X 订阅列表失败: {e}")
            return []

    def ensure_check_task_running(self):
        """确保检查任务正在运行"""
        if self.check_task is None or self.check_task.done():
            self.check_task = asyncio.create_task(self._check_loop())
            logger.info(f"🔄 启动 X 红心收藏检查任务，检查间隔: {self.poll_interval} 分钟")
        else:
            logger.info("✅ X 红心收藏检查任务已在运行中")

    def is_check_task_running(self) -> bool:
        """检查任务是否正在运行"""
        return self.check_task is not None and not self.check_task.done()

    async def stop_check_task(self):
        """停止检查任务"""
        if self.check_task and not self.check_task.done():
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass
            logger.info("🎯 X 收藏订阅检查任务已停止")

    async def _check_loop(self):
        """订阅检查循环"""
        logger.info(f"🎯 X 红心收藏订阅检查任务启动，检查间隔: {self.poll_interval} 分钟")

        while True:
            try:
                logger.info(f"⏰ 等待 {self.poll_interval} 分钟后进行下一次检查...")
                await asyncio.sleep(self.poll_interval * 60)  # 转换为秒
                logger.info("🔍 开始执行 X 红心收藏定期检查...")
                await self._check_subscription()
                logger.info("✅ X 红心收藏定期检查完成")
            except asyncio.CancelledError:
                logger.info("🎯 X 收藏订阅检查任务被取消")
                break
            except Exception as e:
                logger.error(f"🎯 X 收藏订阅检查任务异常: {e}")
                logger.info("⏰ 异常后等待5分钟再重试...")
                await asyncio.sleep(300)  # 异常时等待5分钟

    async def _check_subscription(self) -> bool:
        """
        检查订阅

        Returns:
            是否成功检查
        """
        try:
            subscriptions = self.load_subscriptions()
            if "account" not in subscriptions:
                logger.info("🎯 暂无 X 红心收藏订阅")
                return False

            account = subscriptions["account"]

            # 更新检查时间
            account["last_check"] = time.time()

            # 获取红心内容列表
            likes_list = await self._get_likes_content()

            if likes_list:
                current_count = len(likes_list)
                account["last_item_count"] = current_count

                # 下载新增内容
                new_downloads = await self._download_new_likes(likes_list, account)
                account["download_count"] = account.get("download_count", 0) + new_downloads

                logger.info(f"🎯 检查完成，共 {current_count} 条红心内容，新增下载 {new_downloads} 条")
            else:
                logger.info("🎯 未能获取红心内容列表")

            # 保存更新
            self.save_subscriptions(subscriptions)
            return True

        except Exception as e:
            logger.error(f"🎯 检查 X 收藏订阅失败: {e}")
            return False

    async def _get_likes_content(self) -> List[Dict]:
        """
        获取红心内容列表

        Returns:
            内容列表，每个元素包含 id, title, url 等信息
        """
        try:
            import subprocess
            import json
            from pathlib import Path

            # 使用 yt-dlp 配合 cookies 获取 X 红心内容
            likes_url = "https://x.com/i/likes"

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,  # 只提取信息，不下载
                'cookiefile': str(self.cookies_path) if self.cookies_path and os.path.exists(self.cookies_path) else None,
                'ignoreerrors': True,
            }

            if self.proxy_host:
                ydl_opts['proxy'] = self.proxy_host

            # 导入 yt-dlp 提取红心内容
            try:
                import yt_dlp
                likes_list = []

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(likes_url, download=False)

                    if info and 'entries' in info:
                        for entry in info['entries']:
                            if entry:
                                item_info = {
                                    'id': entry.get('id', ''),
                                    'url': entry.get('webpage_url', entry.get('url', '')),
                                    'title': entry.get('title', f'X 内容 {entry.get("id", "未知")}'),
                                    'description': entry.get('description', ''),
                                }
                                likes_list.append(item_info)

                logger.info(f"🎯 获取到 {len(likes_list)} 条红心内容")
                return likes_list

            except Exception as yt_err:
                logger.warning(f"🎯 yt-dlp 方式失败，尝试 gallery-dl...")
                # 回退方案：尝试使用 gallery-dl
                try:
                    return await self._get_likes_with_gallerydl()
                except Exception as gdl_err:
                    logger.error(f"🎯 gallery-dl 也失败: {gdl_err}")
                    return []

        except Exception as e:
            logger.error(f"🎯 获取 X 红心内容失败: {e}")
            return []

    async def _get_likes_with_gallerydl(self) -> List[Dict]:
        """
        使用 gallery-dl 获取 X 红心内容

        Returns:
            内容列表
        """
        try:
            import subprocess
            import json

            # 构建 gallery-dl 命令
            cmd = ['gallery-dl', '--cookies', str(self.cookies_path), '--json',
                   'https://x.com/i/likes']

            if self.proxy_host:
                cmd.extend(['--proxy', self.proxy_host])

            result = subprocess.run(cmd, capture_output=True, text=True)
            likes_list = []

            if result.returncode == 0 and result.stdout:
                # 解析 gallery-dl 输出的 JSON 行
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line:
                        try:
                            item = json.loads(line)
                            likes_list.append({
                                'id': item.get('tweet_id', item.get('id', '')),
                                'url': item.get('tweet_url', item.get('url', '')),
                                'title': f'X 内容 {item.get("tweet_id", item.get("id", "未知"))}',
                                'description': item.get('content', ''),
                            })
                        except json.JSONDecodeError:
                            continue

            logger.info(f"🎯 gallery-dl 获取到 {len(likes_list)} 条红心内容")
            return likes_list

        except Exception as e:
            logger.error(f"🎯 gallery-dl 获取失败: {e}")
            return []

    async def _download_new_likes(self, likes_list: List[Dict], account: Dict) -> int:
        """
        下载新增的红心内容

        Args:
            likes_list: 红心内容列表
            account: 账号订阅信息

        Returns:
            新增下载数量
        """
        downloaded_count = 0
        downloaded_ids = set(account.get("downloaded_ids", []))

        for item in likes_list:
            item_id = item.get("id")
            if not item_id:
                continue

            if item_id in downloaded_ids:
                continue

            # 调用下载回调（由主程序提供）
            if self.download_callback:
                try:
                    url = item.get("url")
                    if url:
                        logger.info(f"🎯 开始下载: {item.get('title', item_id)}")
                        result = await self.download_callback(url, self.likes_download_path)
                        if result.get("success"):
                            downloaded_ids.add(item_id)
                            downloaded_count += 1
                            logger.info(f"✅ 下载成功: {item_id}")
                except Exception as e:
                    logger.error(f"❌ 下载失败 {item_id}: {e}")

        # 更新已下载 ID 列表
        account["downloaded_ids"] = list(downloaded_ids)
        return downloaded_count

    async def manual_check(self) -> Dict[str, Any]:
        """
        手动触发一次检查

        Returns:
            检查结果字典
        """
        try:
            subscriptions = self.load_subscriptions()
            if "account" not in subscriptions:
                return {
                    "success": False,
                    "error": "未订阅 X 红心收藏，请先使用 /xfav add 添加订阅"
                }

            logger.info("🎯 开始手动检查 X 红心收藏...")
            success = await self._check_subscription()

            if success:
                account = subscriptions.get("account", {})
                return {
                    "success": True,
                    "message": "检查完成",
                    "download_count": account.get("download_count", 0),
                    "last_check": account.get("last_check", 0)
                }
            else:
                return {
                    "success": False,
                    "error": "检查失败"
                }

        except Exception as e:
            logger.error(f"🎯 手动检查 X 收藏订阅失败: {e}")
            return {"success": False, "error": str(e)}

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除不安全字符"""
        import re
        # 移除或替换不安全的字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 移除多余的空格和点
        filename = re.sub(r'\s+', ' ', filename).strip()
        filename = filename.strip('.')
        # 限制长度
        if len(filename) > 100:
            filename = filename[:100]
        return filename
