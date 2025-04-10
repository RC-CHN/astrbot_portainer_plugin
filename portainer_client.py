import aiohttp
import time
import json

class PortainerClient:
    def __init__(self, portainer_url, username, password, verify_ssl=True, token_cache_ttl=3600):
        self.portainer_url = portainer_url
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.token_cache_ttl = token_cache_ttl
        self.session = aiohttp.ClientSession()
        self._token = None
        self._token_time = 0
        self._endpoint_id = None

    async def close(self):
        await self.session.close()

    async def _portainer_login(self):
        """登录Portainer获取JWT Token和CSRF Token"""
        url = f"{self.portainer_url}/api/auth"
        data = {"Username": self.username, "Password": self.password}
        
        # 确保session headers是干净的
        self.session.headers.clear()
        
        print(f"\n[DEBUG] 登录请求URL: {url}")
        print(f"[DEBUG] 登录请求Headers: {dict(self.session.headers)}")
        
        async with self.session.post(url, json=data, ssl=self.verify_ssl) as response:
            print(f"[DEBUG] 登录响应状态: {response.status}")
            print(f"[DEBUG] 登录响应Headers: {dict(response.headers)}")
            if response.status == 200:
                json_data = await response.json()
                token = json_data.get("jwt")
                if not token:
                    raise Exception("登录Portainer失败：未返回JWT令牌")
                
                # 尝试获取CSRF token，但不强制要求
                csrf_token = response.headers.get('X-CSRF-TOKEN', '')
                
                # 更新session headers
                headers = {
                    'Authorization': f"Bearer {token}"
                }
                if csrf_token:
                    headers['X-CSRF-TOKEN'] = csrf_token
                
                self.session.headers.update(headers)
                return token
            else:
                text = await response.text()
                raise Exception(f"登录Portainer失败：{response.status} {text}")

    async def _get_portainer_token(self):
        """获取有效的JWT Token（缓存未过期则直接返回，否则重新登录）"""
        if (self._token is None or 
            time.time() - self._token_time > self.token_cache_ttl):
            # 强制重新登录获取最新token和CSRF token
            self._token = await self._portainer_login()
            self._token_time = time.time()
            self._endpoint_id = None  # 清除之前缓存的环境ID
            
            # 获取端点列表验证token有效性
            async with self.session.get(
                f"{self.portainer_url}/api/endpoints",
                ssl=self.verify_ssl
            ) as resp:
                if resp.status == 200:
                    endpoints = await resp.json()
                    if not endpoints:
                        raise Exception("未找到任何Portainer环境")
                    self._endpoint_id = endpoints[0]["Id"]
                else:
                    text = await resp.text()
                    raise Exception(f"获取Portainer环境列表失败：{resp.status} {text}")
        return self._token

    async def _get_endpoint_id(self):
        """获取默认的Portainer环境ID"""
        await self._get_portainer_token()
        if self._endpoint_id is None:
            url = f"{self.portainer_url}/api/endpoints"
            print(f"\n[DEBUG] 获取端点请求URL: {url}")
            print(f"[DEBUG] 获取端点请求Headers: {dict(self.session.headers)}")
            
            async with self.session.get(url, ssl=self.verify_ssl) as resp:
                print(f"[DEBUG] 获取端点响应状态: {resp.status}")
                print(f"[DEBUG] 获取端点响应Headers: {dict(resp.headers)}")
                if resp.status == 200:
                    endpoints = await resp.json()
                    if not endpoints:
                        raise Exception("未找到任何Portainer环境")
                    self._endpoint_id = endpoints[0]["Id"]
                else:
                    text = await resp.text()
                    raise Exception(f"获取Portainer环境列表失败：{resp.status} {text}")
        return self._endpoint_id

    async def list_containers(self, endpoint_id=None):
        '''获取指定节点上运行的容器列表'''
        try:
            await self._get_portainer_token()
            endpoint = endpoint_id if endpoint_id else await self._get_endpoint_id()
            url = f"{self.portainer_url}/api/endpoints/{endpoint}/docker/containers/json?all=true"
            
            async with self.session.get(url, ssl=self.verify_ssl) as resp:
                if resp.status != 200:
                    return f"获取容器列表失败：{resp.status}"
                
                containers = await resp.json()
                if not containers:
                    return "当前没有运行中的容器"
                
                # 格式化输出
                result = ["容器列表:"]
                for c in containers:
                    cid = c.get("Id", "")[:12]
                    names = c.get("Names", [])
                    name = names[0][1:] if names and names[0].startswith("/") else ""
                    result.append(
                        f"{name} (ID: {cid}): "
                        f"状态 {c.get('State', '未知')}, "
                        f"镜像 {c.get('Image', '未知')}"
                    )
                
                return "\n".join(result)
            
        except Exception as e:
            return f"获取容器信息出错: {str(e)}"

    async def pull_image(self, image_name, endpoint_id=None):
        '''拉取Docker镜像到指定节点'''
        try:
            await self._get_portainer_token()
            endpoint = endpoint_id if endpoint_id else await self._get_endpoint_id()
            
            # 分离镜像名和标签
            if ":" in image_name:
                img, tag = image_name.split(":", 1)
            else:
                img, tag = image_name, "latest"
                
            url = f"{self.portainer_url}/api/endpoints/{endpoint}/docker/images/create?fromImage={img}&tag={tag}"
            
            # 打印调试信息
            print(f"\n[DEBUG] 请求URL: {url}")
            print(f"[DEBUG] 请求Headers: {dict(self.session.headers)}")
            
            async with self.session.post(url, ssl=self.verify_ssl) as resp:
                print(f"[DEBUG] 响应状态: {resp.status}")
                print(f"[DEBUG] 响应Headers: {dict(resp.headers)}")
                if resp.status == 200:
                    text = (await resp.text()).strip()
                    if not text:
                        return f"镜像 {image_name} 拉取成功"
                        
                    lines = text.splitlines()
                    last_line = lines[-1].strip() if lines else ""
                    
                    if last_line.startswith("{"):
                        try:
                            last_json = json.loads(last_line)
                            status_msg = last_json.get("status") or last_json.get("error")
                            if status_msg:
                                return f"镜像拉取结果：{status_msg}"
                        except:
                            pass
                            
                    return f"镜像 {image_name} 拉取成功"
                else:
                    text = await resp.text()
                    raise Exception(f"拉取镜像失败：{resp.status} {text}")
                
        except Exception as e:
            return f"拉取镜像出错: {str(e)}"
