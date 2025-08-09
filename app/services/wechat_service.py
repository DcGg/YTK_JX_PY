"""微信服务

实现微信小程序登录、用户信息获取、消息推送等功能。

Author: 云推客严选开发团队
Date: 2024
"""

import json
import time
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

import httpx
from loguru import logger

from ..core.config import get_settings
from ..core.database import get_db_client
from ..models.user import UserRole

# 获取配置
settings = get_settings()


class WeChatService:
    """微信服务类
    
    提供微信小程序相关的服务功能。
    """
    
    def __init__(self):
        self.app_id = settings.WECHAT_APP_ID
        self.app_secret = settings.WECHAT_APP_SECRET
        self.mch_id = settings.WECHAT_MCH_ID
        self.api_key = settings.WECHAT_API_KEY
        self.notify_url = settings.WECHAT_NOTIFY_URL
        
        # 微信API基础URL
        self.base_url = "https://api.weixin.qq.com"
        self.sns_base_url = "https://api.weixin.qq.com/sns"
        
        # 缓存access_token
        self._access_token = None
        self._access_token_expires_at = None
    
    async def code_to_session(self, js_code: str) -> Dict[str, Any]:
        """通过code获取session_key和openid
        
        Args:
            js_code: 微信小程序登录时获取的code
            
        Returns:
            Dict[str, Any]: 包含openid、session_key等信息
            
        Raises:
            Exception: 微信API调用失败
        """
        url = f"{self.sns_base_url}/jscode2session"
        params = {
            "appid": self.app_id,
            "secret": self.app_secret,
            "js_code": js_code,
            "grant_type": "authorization_code"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                if "errcode" in data:
                    logger.error(f"微信登录失败: {data}")
                    raise Exception(f"微信登录失败: {data.get('errmsg', '未知错误')}")
                
                logger.info(f"微信登录成功: openid={data.get('openid')}")
                return data
                
        except httpx.RequestError as e:
            logger.error(f"微信API请求失败: {e}")
            raise Exception(f"微信API请求失败: {str(e)}")
    
    async def get_access_token(self) -> str:
        """获取微信access_token
        
        Returns:
            str: access_token
            
        Raises:
            Exception: 获取access_token失败
        """
        # 检查缓存的token是否有效
        if (
            self._access_token and 
            self._access_token_expires_at and 
            datetime.utcnow() < self._access_token_expires_at
        ):
            return self._access_token
        
        url = f"{self.base_url}/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                if "errcode" in data:
                    logger.error(f"获取access_token失败: {data}")
                    raise Exception(f"获取access_token失败: {data.get('errmsg', '未知错误')}")
                
                # 缓存token（提前5分钟过期）
                self._access_token = data["access_token"]
                expires_in = data.get("expires_in", 7200)
                self._access_token_expires_at = datetime.utcnow() + timedelta(
                    seconds=expires_in - 300
                )
                
                logger.info("获取access_token成功")
                return self._access_token
                
        except httpx.RequestError as e:
            logger.error(f"获取access_token请求失败: {e}")
            raise Exception(f"获取access_token请求失败: {str(e)}")
    
    async def get_user_info(self, openid: str, access_token: str) -> Dict[str, Any]:
        """获取微信用户信息
        
        Args:
            openid: 用户openid
            access_token: 访问令牌
            
        Returns:
            Dict[str, Any]: 用户信息
            
        Raises:
            Exception: 获取用户信息失败
        """
        url = f"{self.sns_base_url}/userinfo"
        params = {
            "access_token": access_token,
            "openid": openid,
            "lang": "zh_CN"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                if "errcode" in data:
                    logger.error(f"获取用户信息失败: {data}")
                    raise Exception(f"获取用户信息失败: {data.get('errmsg', '未知错误')}")
                
                return data
                
        except httpx.RequestError as e:
            logger.error(f"获取用户信息请求失败: {e}")
            raise Exception(f"获取用户信息请求失败: {str(e)}")
    
    def decrypt_data(self, encrypted_data: str, iv: str, session_key: str) -> Dict[str, Any]:
        """解密微信加密数据
        
        Args:
            encrypted_data: 加密数据
            iv: 初始向量
            session_key: 会话密钥
            
        Returns:
            Dict[str, Any]: 解密后的数据
            
        Raises:
            Exception: 解密失败
        """
        try:
            from Crypto.Cipher import AES
            import base64
            
            session_key = base64.b64decode(session_key)
            encrypted_data = base64.b64decode(encrypted_data)
            iv = base64.b64decode(iv)
            
            cipher = AES.new(session_key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(encrypted_data)
            
            # 去除填充
            decrypted = decrypted[:-decrypted[-1]]
            
            return json.loads(decrypted.decode('utf-8'))
            
        except Exception as e:
            logger.error(f"解密微信数据失败: {e}")
            raise Exception(f"解密微信数据失败: {str(e)}")
    
    async def send_template_message(
        self, 
        openid: str, 
        template_id: str, 
        data: Dict[str, Any],
        url: Optional[str] = None,
        miniprogram: Optional[Dict[str, str]] = None
    ) -> bool:
        """发送模板消息
        
        Args:
            openid: 用户openid
            template_id: 模板ID
            data: 模板数据
            url: 跳转URL
            miniprogram: 小程序信息
            
        Returns:
            bool: 发送是否成功
        """
        try:
            access_token = await self.get_access_token()
            
            url_api = f"{self.base_url}/cgi-bin/message/template/send"
            params = {"access_token": access_token}
            
            payload = {
                "touser": openid,
                "template_id": template_id,
                "data": data
            }
            
            if url:
                payload["url"] = url
            
            if miniprogram:
                payload["miniprogram"] = miniprogram
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url_api, 
                    params=params, 
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                if result.get("errcode") == 0:
                    logger.info(f"模板消息发送成功: {openid}")
                    return True
                else:
                    logger.error(f"模板消息发送失败: {result}")
                    return False
                    
        except Exception as e:
            logger.error(f"发送模板消息异常: {e}")
            return False
    
    async def send_subscribe_message(
        self, 
        openid: str, 
        template_id: str, 
        data: Dict[str, Any],
        page: Optional[str] = None
    ) -> bool:
        """发送订阅消息（小程序）
        
        Args:
            openid: 用户openid
            template_id: 模板ID
            data: 模板数据
            page: 跳转页面
            
        Returns:
            bool: 发送是否成功
        """
        try:
            access_token = await self.get_access_token()
            
            url_api = f"{self.base_url}/cgi-bin/message/subscribe/send"
            params = {"access_token": access_token}
            
            payload = {
                "touser": openid,
                "template_id": template_id,
                "data": data
            }
            
            if page:
                payload["page"] = page
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url_api, 
                    params=params, 
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                if result.get("errcode") == 0:
                    logger.info(f"订阅消息发送成功: {openid}")
                    return True
                else:
                    logger.error(f"订阅消息发送失败: {result}")
                    return False
                    
        except Exception as e:
            logger.error(f"发送订阅消息异常: {e}")
            return False
    
    def generate_payment_sign(
        self, 
        prepay_id: str, 
        timestamp: str, 
        nonce_str: str
    ) -> str:
        """生成微信支付签名
        
        Args:
            prepay_id: 预支付ID
            timestamp: 时间戳
            nonce_str: 随机字符串
            
        Returns:
            str: 支付签名
        """
        # 构造签名字符串
        sign_str = f"appId={self.app_id}&nonceStr={nonce_str}&package=prepay_id={prepay_id}&signType=MD5&timeStamp={timestamp}&key={self.api_key}"
        
        # MD5加密
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
        
        return sign
    
    async def create_unified_order(
        self, 
        openid: str, 
        out_trade_no: str, 
        total_fee: int, 
        body: str,
        attach: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建统一下单
        
        Args:
            openid: 用户openid
            out_trade_no: 商户订单号
            total_fee: 总金额（分）
            body: 商品描述
            attach: 附加数据
            
        Returns:
            Dict[str, Any]: 下单结果
            
        Raises:
            Exception: 下单失败
        """
        import xml.etree.ElementTree as ET
        import uuid
        
        # 生成随机字符串
        nonce_str = str(uuid.uuid4()).replace('-', '')
        
        # 构造参数
        params = {
            'appid': self.app_id,
            'mch_id': self.mch_id,
            'nonce_str': nonce_str,
            'body': body,
            'out_trade_no': out_trade_no,
            'total_fee': str(total_fee),
            'spbill_create_ip': '127.0.0.1',
            'notify_url': self.notify_url,
            'trade_type': 'JSAPI',
            'openid': openid
        }
        
        if attach:
            params['attach'] = attach
        
        # 生成签名
        sign_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())]) + f"&key={self.api_key}"
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
        params['sign'] = sign
        
        # 构造XML
        root = ET.Element('xml')
        for k, v in params.items():
            elem = ET.SubElement(root, k)
            elem.text = str(v)
        
        xml_data = ET.tostring(root, encoding='utf-8')
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'https://api.mch.weixin.qq.com/pay/unifiedorder',
                    content=xml_data,
                    headers={'Content-Type': 'application/xml'}
                )
                response.raise_for_status()
                
                # 解析XML响应
                result_root = ET.fromstring(response.content)
                result = {elem.tag: elem.text for elem in result_root}
                
                if result.get('return_code') == 'SUCCESS' and result.get('result_code') == 'SUCCESS':
                    logger.info(f"统一下单成功: {out_trade_no}")
                    return result
                else:
                    error_msg = result.get('err_code_des') or result.get('return_msg')
                    logger.error(f"统一下单失败: {error_msg}")
                    raise Exception(f"统一下单失败: {error_msg}")
                    
        except httpx.RequestError as e:
            logger.error(f"统一下单请求失败: {e}")
            raise Exception(f"统一下单请求失败: {str(e)}")
    
    async def query_order(self, out_trade_no: str) -> Dict[str, Any]:
        """查询订单
        
        Args:
            out_trade_no: 商户订单号
            
        Returns:
            Dict[str, Any]: 订单信息
            
        Raises:
            Exception: 查询失败
        """
        import xml.etree.ElementTree as ET
        import uuid
        
        # 生成随机字符串
        nonce_str = str(uuid.uuid4()).replace('-', '')
        
        # 构造参数
        params = {
            'appid': self.app_id,
            'mch_id': self.mch_id,
            'nonce_str': nonce_str,
            'out_trade_no': out_trade_no
        }
        
        # 生成签名
        sign_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())]) + f"&key={self.api_key}"
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
        params['sign'] = sign
        
        # 构造XML
        root = ET.Element('xml')
        for k, v in params.items():
            elem = ET.SubElement(root, k)
            elem.text = str(v)
        
        xml_data = ET.tostring(root, encoding='utf-8')
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'https://api.mch.weixin.qq.com/pay/orderquery',
                    content=xml_data,
                    headers={'Content-Type': 'application/xml'}
                )
                response.raise_for_status()
                
                # 解析XML响应
                result_root = ET.fromstring(response.content)
                result = {elem.tag: elem.text for elem in result_root}
                
                if result.get('return_code') == 'SUCCESS':
                    logger.info(f"订单查询成功: {out_trade_no}")
                    return result
                else:
                    error_msg = result.get('return_msg')
                    logger.error(f"订单查询失败: {error_msg}")
                    raise Exception(f"订单查询失败: {error_msg}")
                    
        except httpx.RequestError as e:
            logger.error(f"订单查询请求失败: {e}")
            raise Exception(f"订单查询请求失败: {str(e)}")
    
    async def get_user_phone_number(
        self, 
        code: str
    ) -> Dict[str, Any]:
        """获取用户手机号
        
        Args:
            code: 手机号获取凭证
            
        Returns:
            Dict[str, Any]: 手机号信息
            
        Raises:
            Exception: 获取失败
        """
        try:
            access_token = await self.get_access_token()
            
            url = f"{self.base_url}/wxa/business/getuserphonenumber"
            params = {"access_token": access_token}
            payload = {"code": code}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, 
                    params=params, 
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                
                if data.get("errcode") == 0:
                    logger.info("获取用户手机号成功")
                    return data["phone_info"]
                else:
                    logger.error(f"获取用户手机号失败: {data}")
                    raise Exception(f"获取用户手机号失败: {data.get('errmsg', '未知错误')}")
                    
        except httpx.RequestError as e:
            logger.error(f"获取用户手机号请求失败: {e}")
            raise Exception(f"获取用户手机号请求失败: {str(e)}")
    
    async def check_content_security(self, content: str) -> bool:
        """内容安全检测
        
        Args:
            content: 待检测内容
            
        Returns:
            bool: 内容是否安全
        """
        try:
            access_token = await self.get_access_token()
            
            url = f"{self.base_url}/wxa/msg_sec_check"
            params = {"access_token": access_token}
            payload = {"content": content}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, 
                    params=params, 
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                
                # errcode为0表示内容安全
                return data.get("errcode") == 0
                
        except Exception as e:
            logger.error(f"内容安全检测异常: {e}")
            # 检测异常时默认认为内容安全
            return True
    
    async def generate_qr_code(
        self, 
        scene: str, 
        page: Optional[str] = None,
        width: int = 430
    ) -> bytes:
        """生成小程序二维码
        
        Args:
            scene: 场景值
            page: 页面路径
            width: 二维码宽度
            
        Returns:
            bytes: 二维码图片数据
            
        Raises:
            Exception: 生成失败
        """
        try:
            access_token = await self.get_access_token()
            
            url = f"{self.base_url}/wxa/getwxacodeunlimit"
            params = {"access_token": access_token}
            
            payload = {
                "scene": scene,
                "width": width
            }
            
            if page:
                payload["page"] = page
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, 
                    params=params, 
                    json=payload
                )
                response.raise_for_status()
                
                # 检查是否返回错误信息
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    data = response.json()
                    logger.error(f"生成二维码失败: {data}")
                    raise Exception(f"生成二维码失败: {data.get('errmsg', '未知错误')}")
                
                logger.info("生成小程序二维码成功")
                return response.content
                
        except httpx.RequestError as e:
            logger.error(f"生成二维码请求失败: {e}")
            raise Exception(f"生成二维码请求失败: {str(e)}")


# 全局微信服务实例
wechat_service = WeChatService()