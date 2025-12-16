import os
from typing import Dict, List, Optional

from openai import OpenAI

from app.core.config_manager import ConfigManager
from app.core.logger import logger


class ChatBot:
    """聊天机器人客户端"""

    def __init__(
        self,
        provider: str = "kimi",
        kimi_api_key: Optional[str] = None,
        doubao_ak: Optional[str] = None,
        doubao_sk: Optional[str] = None,
        doubao_endpoint_id: Optional[str] = None,
        model: str = "kimi-k2-0905-preview",
        temperature: float = 0.3,
        token_json_path: Optional[str] = None,
    ):
        """
        初始化客户端
        :param provider: 服务提供商 "kimi" | "doubao"
        :param kimi_api_key: Kimi API Key
        :param doubao_ak: 豆包 AccessKey
        :param doubao_sk: 豆包 SecretKey
        :param doubao_endpoint_id: 豆包 Endpoint ID
        :param model: 模型名称
        :param temperature: 温度参数
        :param token_json_path: 自定义 token.json 路径
        """
        self.provider = provider.lower()
        self.model = model
        self.temperature = temperature
        self._client = None
        self._messages: List[Dict[str, str]] = []

        # 获取配置
        config = self._get_config(
            kimi_api_key, doubao_ak, doubao_sk, doubao_endpoint_id, token_json_path
        )

        # 初始化客户端
        self._initialize_client(config)

    def _get_config(
        self,
        kimi_api_key: Optional[str],
        doubao_ak: Optional[str],
        doubao_sk: Optional[str],
        doubao_endpoint_id: Optional[str],
        token_json_path: Optional[str],
    ) -> Dict[str, str]:
        """获取配置信息"""
        config = {}

        # 1) 显式参数优先
        config["moonshot_key"] = self._get_stripped_value(
            kimi_api_key, "MOONSHOT_API_KEY"
        )
        config["ak"] = self._get_stripped_value(doubao_ak, "VOLC_ACCESSKEY")
        config["sk"] = self._get_stripped_value(doubao_sk, "VOLC_SECRETKEY")
        config["endpoint_id"] = self._get_stripped_value(
            doubao_endpoint_id, "ARK_ENDPOINT_ID"
        )

        # 2) 其次尝试从 token.json
        token_cfg = self._load_token_config(token_json_path)

        if not config["moonshot_key"]:
            config["moonshot_key"] = token_cfg.get("moonshot_api_key", "").strip()
        if not config["ak"]:
            config["ak"] = token_cfg.get("volcano_access_key", "").strip()
        if not config["sk"]:
            config["sk"] = token_cfg.get("volcano_secret_key", "").strip()
        if not config["endpoint_id"]:
            config["endpoint_id"] = token_cfg.get("ark_endpoint_id", "").strip()

        return config

    def _get_stripped_value(self, explicit_value: Optional[str], env_var: str) -> str:
        """获取处理后的值（显式参数 > 环境变量）"""
        value = explicit_value or os.getenv(env_var, "")
        return value.strip()

    def _load_token_config(self, token_json_path: Optional[str]) -> Dict[str, str]:
        """从 token.json 加载配置"""
        token_path = token_json_path or os.getenv(
            "TOKEN_JSON_PATH", "./config/token.json"
        )

        if not os.path.exists(token_path):
            return {}

        try:
            cfg_manager = ConfigManager(token_path)
            return cfg_manager.load()
        except Exception as e:
            logger.warning(f"加载 token.json 失败，将忽略该文件: {e}")
            return {}

    def _initialize_client(self, config: Dict[str, str]) -> None:
        """初始化客户端"""
        if self.provider == "kimi":
            self._initialize_kimi_client(config)
        elif self.provider == "doubao":
            self._initialize_doubao_client(config)
        else:
            raise ValueError("provider 必须是 'kimi' 或 'doubao'")

    def _initialize_kimi_client(self, config: Dict[str, str]) -> None:
        """初始化 Kimi 客户端"""
        moonshot_key = config["moonshot_key"]
        if not moonshot_key:
            raise ValueError(
                "Kimi 需要提供 MOONSHOT_API_KEY（可通过参数、环境变量或 token.json 提供）"
            )

        self._client = OpenAI(
            api_key=moonshot_key, base_url="https://api.moonshot.cn/v1"
        )
        logger.info("已初始化 Kimi 客户端")

    def _initialize_doubao_client(self, config: Dict[str, str]) -> None:
        """初始化豆包客户端"""
        ak, sk, endpoint_id = config["ak"], config["sk"], config["endpoint_id"]

        if not all([ak, sk, endpoint_id]):
            missing = []
            if not ak:
                missing.append("VOLC_ACCESSKEY")
            if not sk:
                missing.append("VOLC_SECRETKEY")
            if not endpoint_id:
                missing.append("ARK_ENDPOINT_ID")
            raise ValueError(
                f"豆包需提供 AK/SK/EndpointID（可通过参数、环境变量或 token.json 提供）: {', '.join(missing)}"
            )

        # TODO: 实现豆包客户端初始化
        # self._client = Ark(api_key=sk, region="cn-beijing")
        self._model = endpoint_id
        logger.info("已初始化豆包(Ark)客户端")

    def reply(
        self,
        message: str,
        system: Optional[str] = None,
        use_history: bool = True,
        stream: bool = False,
    ) -> str:
        """
        发送消息并获取回复
        :param message: 用户消息
        :param system: 系统提示词
        :param use_history: 是否使用历史记录
        :param stream: 是否使用流式输出
        :return: 助手回复
        """
        # 构建消息列表
        messages = self._build_messages(message, system, use_history)

        try:
            if self.provider == "kimi":
                return self._call_kimi(messages, stream)
            elif self.provider == "doubao":
                return self._call_doubao(messages, stream)
            else:
                raise ValueError(f"不支持的 provider: {self.provider}")
        except Exception as e:
            logger.error(f"调用 {self.provider} API 失败: {e}")
            raise

    def _build_messages(
        self, message: str, system: Optional[str], use_history: bool
    ) -> List[Dict[str, str]]:
        """构建消息列表"""
        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        if use_history:
            messages.extend(self._messages)

        messages.append({"role": "user", "content": message})
        return messages

    def _call_kimi(self, messages: List[Dict[str, str]], stream: bool) -> str:
        """调用 Kimi API"""
        if not self._client:
            raise RuntimeError("Kimi 客户端未正确初始化")

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            stream=stream,
        )

        if stream:
            # 处理流式响应
            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
            return full_response
        else:
            return response.choices[0].message.content

    def _call_doubao(self, messages: List[Dict[str, str]], stream: bool) -> str:
        """调用豆包 API"""
        # TODO: 实现豆包 API 调用
        raise NotImplementedError("豆包 API 调用暂未实现")

    def clear_history(self) -> None:
        """清空对话历史"""
        self._messages.clear()

    def get_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return self._messages.copy()
