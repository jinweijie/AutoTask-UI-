import json
import os
from typing import Any, Dict, List, Optional, TypedDict


class ConfigDict(TypedDict, total=False):
    moonshot_api_key: str
    volcano_access_key: str
    volcano_secret_key: str
    ark_endpoint_id: str


class ConfigManager:
    """
    配置管理器，用于读写配置文件
    """

    _DEFAULT_DIR = os.path.abspath("./config")
    _DEFAULT_PATH = os.path.join(_DEFAULT_DIR, "token.json")

    def __init__(self, path: Optional[str] = None):
        """
        初始化配置管理器
        :param path: 配置文件路径，默认为 ./config/token.json
        """
        self._path = path or self._DEFAULT_PATH
        self._dir = os.path.dirname(self._path)
        os.makedirs(self._dir, exist_ok=True)

    def save(
        self,
        *,
        moonshot_api_key: Optional[str] = None,
        volcano_access_key: Optional[str] = None,
        volcano_secret_key: Optional[str] = None,
        ark_endpoint_id: Optional[str] = None,
        ensure_ascii: bool = False,
        indent: int = 2,
    ) -> None:
        """
        持久化保存配置（按需更新提供的字段）
        :param moonshot_api_key: Kimi API Key
        :param volcano_access_key: 豆包 AccessKey
        :param volcano_secret_key: 豆包 SecretKey
        :param ark_endpoint_id: 豆包 Endpoint ID
        :param ensure_ascii: JSON 是否转义非 ASCII
        :param indent: JSON 缩进空格数
        :raises RuntimeError: 读写失败时抛出
        :raises ValueError: 未提供任何字段时抛出
        """
        updates = {
            "moonshot_api_key": moonshot_api_key,
            "volcano_access_key": volcano_access_key,
            "volcano_secret_key": volcano_secret_key,
            "ark_endpoint_id": ark_endpoint_id,
        }

        if not any(v is not None for v in updates.values()):
            raise ValueError("至少需要提供一个非 None 的配置项")

        # 读取现有配置
        data = self._load_existing_config()

        # 更新配置
        updated = False
        for key, value in updates.items():
            if value is not None:
                data[key] = value
                updated = True

        if not updated:
            raise ValueError("未检测到需要更新的字段")

        self._write_config(data, ensure_ascii, indent)

    def _load_existing_config(self) -> Dict[str, Any]:
        """加载现有配置"""
        if not os.path.exists(self._path):
            return {}

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise RuntimeError(f"读取配置文件失败: {e}")

    def _write_config(
        self, data: Dict[str, Any], ensure_ascii: bool, indent: int
    ) -> None:
        """写入配置到文件"""
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
        except OSError as e:
            raise RuntimeError(f"写入配置文件失败: {e}")

    def load(self) -> Dict[str, str]:
        """
        读取全部配置
        :return: 配置字典
        :raises RuntimeError: 读取或解析失败时抛出
        """
        return self._load_existing_config()

    def get(
        self,
        key: str,
        default: Optional[str] = None,
        required: bool = False,
    ) -> Optional[str]:
        """
        获取单个配置项
        :param key: 配置键名
        :param default: 默认值
        :param required: 是否为必填项
        :return: 配置值或默认值
        :raises ValueError: 必填项缺失时抛出
        """
        cfg = self.load()
        value = cfg.get(key, default)

        if required and value is None:
            raise ValueError(f"配置项缺失且为必填: {key}")

        return value

    def get_all_keys(self) -> List[str]:
        """
        获取当前配置文件中所有键名
        :return: 键名列表
        """
        cfg = self.load()
        return list(cfg.keys())

    def remove(self, *keys: str, save: bool = True) -> None:
        """
        从配置中移除指定键
        :param keys: 要移除的键名
        :param save: 是否立即写入文件
        :raises RuntimeError: 写入失败时抛出
        """
        if not keys:
            return

        cfg = self.load()
        removed = False

        for key in keys:
            if key in cfg:
                del cfg[key]
                removed = True

        if removed and save:
            # 创建一个空的更新字典来触发保存
            update_dict = {key: None for key in keys}
            self.save(**update_dict)
