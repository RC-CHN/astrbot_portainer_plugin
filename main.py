from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig
import requests
import time
import json

@register("astrbot_portainer_plugin", "RC", "简单查看portainer的情况", "0.9")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        # Portainer配置初始化
        portainer_config = config.get("portainer", {})
        self.portainer_url = portainer_config.get("url", "")
        self.username = portainer_config.get("username", "")
        self.password = portainer_config.get("password", "")
        self.verify_ssl = portainer_config.get("verify_ssl", True)
        self.token_cache_ttl = portainer_config.get("token_cache_ttl", 3600)
        self._token = None
        self._token_time = 0
        self._endpoint_id = None
    
    @filter.command("portainer_test")
    async def portainer_test(self, event: AstrMessageEvent):
        '''调用配置信息测试portainer连接性''' # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        try:
            token = self._get_portainer_token()
            yield event.plain_result(f"Portainer连接测试成功！{user_name}，已获取有效JWT Token")
        except Exception as e:
            yield event.plain_result(f"Portainer连接测试失败：{str(e)}")

    @filter.llm_tool(name="get_container_logs")
    async def get_container_logs(
        self, 
        event: AstrMessageEvent,
        container_id: str,
        endpoint_id: str = None,
        tail: str = 100
    ) -> str:
        '''获取指定容器的日志
        
        Args:
            container_id (string): 容器ID或名称
            endpoint_id (string): 可选，指定节点ID，默认为当前默认节点
            tail (string): 可选，要获取的日志行数(默认100)
            
        Returns:
            string: 格式化后的日志内容或错误信息
        '''
        try:
            token = self._get_portainer_token()
            endpoint = endpoint_id if endpoint_id else self._get_endpoint_id()
            
            url = f"{self.portainer_url}/api/endpoints/{endpoint}/docker/containers/{container_id}/logs"
            params = {
                "stdout": 1,
                "stderr": 1,
                "tail": tail
            }
            headers = {"Authorization": f"Bearer {token}"}
            
            resp = requests.get(url, headers=headers, params=params, verify=self.verify_ssl)
            
            if resp.status_code == 200:
                return resp.text
            else:
                error_msg = resp.text or "Unknown error"
                return f"获取容器日志失败：{resp.status_code} {error_msg}"
                
        except Exception as e:
            return f"获取容器日志出错: {str(e)}"

    async def terminate(self):
        '''可选择实现 terminate 函数，当插件被卸载/停用时会调用。'''

    def _portainer_login(self):
        """登录Portainer获取JWT Token"""
        url = f"{self.portainer_url}/api/auth"
        data = {"Username": self.username, "Password": self.password}
        response = requests.post(url, json=data, verify=self.verify_ssl)
        if response.status_code == 200:
            token = response.json().get("jwt")
            if not token:
                raise Exception("登录Portainer失败：未返回JWT令牌")
            return token
        else:
            raise Exception(f"登录Portainer失败：{response.status_code} {response.text}")

    def _get_portainer_token(self):
        """获取有效的JWT Token（缓存未过期则直接返回，否则重新登录）"""
        if (self._token is None or 
            time.time() - self._token_time > self.token_cache_ttl):
            self._token = self._portainer_login()
            self._token_time = time.time()
            self._endpoint_id = None  # 清除之前缓存的环境ID
            resp = requests.get(f"{self.portainer_url}/api/endpoints",
                             headers={"Authorization": f"Bearer {self._token}"}, 
                             verify=self.verify_ssl)
            if resp.status_code == 200:
                endpoints = resp.json()
                if not endpoints:
                    raise Exception("未找到任何Portainer环境")
                self._endpoint_id = endpoints[0]["Id"]
            else:
                raise Exception(f"获取Portainer环境列表失败：{resp.status_code} {resp.text}")
        return self._token

    def _get_endpoint_id(self):
        """获取默认的Portainer环境ID"""
        self._get_portainer_token()
        if self._endpoint_id is None:
            raise Exception("无法确定Portainer环境ID")
        return self._endpoint_id

    @filter.llm_tool(name="list_containers")
    async def list_containers(self, event: AstrMessageEvent, endpoint_id: str = None) -> str:
        '''获取指定节点上运行的容器列表及其状态信息。在执行前需要先询问用户是否需要查询某个特定节点，除非用户特别指定查询默认节点，否则不执行该工具。
        
        Args:
            endpoint_id (string): 可选，指定节点ID，默认为当前默认节点
            
        Returns:
            string: 格式化后的容器信息，每行包含:
                - 容器ID(短)
                - 容器名称
                - 镜像名称  
                - 运行状态
                - 状态详情
        '''
        try:
            token = self._get_portainer_token()
            endpoint = endpoint_id if endpoint_id else self._get_endpoint_id()
            url = f"{self.portainer_url}/api/endpoints/{endpoint}/docker/containers/json?all=true"
            resp = requests.get(url, 
                              headers={"Authorization": f"Bearer {token}"}, 
                              verify=self.verify_ssl)
            if resp.status_code != 200:
                return f"获取容器列表失败：{resp.status_code}"
            
            containers = resp.json()
            if not containers:
                return "当前没有运行中的容器"
            
            # 构建结构化数据并格式化输出
            result = []
            for c in containers:
                cid = c.get("Id", "")
                short_id = cid[:12] if cid else ""
                names = c.get("Names", [])
                name = names[0] if names else ""
                if name.startswith("/"):
                    name = name[1:]
                result.append(
                    f"容器 {name} (ID: {short_id}): "
                    f"状态 {c.get('State', '未知')}, "
                    f"镜像 {c.get('Image', '未知')}, "
                    f"详情: {c.get('Status', '未知')}"
                )
            
            return "\n".join(result)
            
        except Exception as e:
            return f"获取容器信息出错: {str(e)}"

    @filter.llm_tool(name="start_container")
    async def start_container(self, event: AstrMessageEvent, container: str, endpoint_id: str = None) -> str:
        '''启动指定的Docker容器
        
        Args:
            container (string): 容器ID或名称
            endpoint_id (string): 可选，指定节点ID，默认为当前默认节点
            
        Returns:
            string: 操作结果信息
        '''
        try:
            token = self._get_portainer_token()
            endpoint = endpoint_id if endpoint_id else self._get_endpoint_id()
            url = f"{self.portainer_url}/api/endpoints/{endpoint}/docker/containers/{container}/start"
            resp = requests.post(url, headers={"Authorization": f"Bearer {token}"}, verify=self.verify_ssl)
            
            if resp.status_code == 204:
                return f"容器 {container} 已启动"
            elif resp.status_code == 304:
                return f"容器 {container} 已在运行状态"
            else:
                error_msg = resp.text or "Unknown error"
                return f"启动容器失败：{resp.status_code} {error_msg}"
                
        except Exception as e:
            return f"启动容器出错: {str(e)}"

    @filter.llm_tool(name="stop_container")
    async def stop_container(self, event: AstrMessageEvent, container: str, endpoint_id: str = None) -> str:
        '''停止指定的Docker容器
        
        Args:
            container (string): 容器ID或名称
            endpoint_id (string): 可选，指定节点ID，默认为当前默认节点
            
        Returns:
            string: 操作结果信息
        '''
        try:
            token = self._get_portainer_token()
            endpoint = endpoint_id if endpoint_id else self._get_endpoint_id()
            
            # 先获取容器状态
            status_url = f"{self.portainer_url}/api/endpoints/{endpoint}/docker/containers/{container}/json"
            status_resp = requests.get(status_url, 
                                   headers={"Authorization": f"Bearer {token}"},
                                   verify=self.verify_ssl)
            
            if status_resp.status_code != 200:
                return f"获取容器状态失败：{status_resp.status_code}"
                
            container_info = status_resp.json()
            if not container_info["State"]["Running"]:
                return f"容器 {container} 已处于停止状态"
            
            # 停止容器
            stop_url = f"{self.portainer_url}/api/endpoints/{endpoint}/docker/containers/{container}/stop"
            resp = requests.post(stop_url, 
                             headers={"Authorization": f"Bearer {token}"},
                             verify=self.verify_ssl)
            
            if resp.status_code == 204:
                return f"容器 {container} 已停止"
            elif resp.status_code == 304:
                return f"容器 {container} 已处于停止状态"
            else:
                error_msg = resp.text or "Unknown error"
                return f"停止容器失败：{resp.status_code} {error_msg}"
                
        except Exception as e:
            return f"停止容器出错: {str(e)}"

    @filter.llm_tool(name="pull_image")
    async def pull_image(self, event: AstrMessageEvent, image_name: str, endpoint_id: str = None) -> str:
        '''拉取Docker镜像到指定节点
        
        Args:
            image_name (string): 镜像名称(格式如'nginx:latest'或'ubuntu')
            endpoint_id (string): 可选，指定节点ID，默认为当前默认节点
            
        Returns:
            string: 操作结果信息
        '''
        try:
            token = self._get_portainer_token()
            endpoint = endpoint_id if endpoint_id else self._get_endpoint_id()
            
            # 分离镜像名和标签
            if ":" in image_name:
                img, tag = image_name.split(":", 1)
            else:
                img, tag = image_name, "latest"
                
            url = f"{self.portainer_url}/api/endpoints/{endpoint}/docker/images/create?fromImage={img}&tag={tag}"
            resp = requests.post(url, headers={"Authorization": f"Bearer {token}"}, verify=self.verify_ssl)
            
            if resp.status_code == 200:
                text = resp.text.strip()
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
                raise Exception(f"拉取镜像失败：{resp.status_code} {resp.text}")
                
        except Exception as e:
            return f"拉取镜像出错: {str(e)}"

    @filter.llm_tool(name="list_endpoints")
    async def list_endpoints(self, event: AstrMessageEvent) -> str:
        '''获取Portainer可用节点列表
        
        Returns:
            string: 格式化后的节点信息，每行包含:
                - 节点ID
                - 节点名称
                - 节点URL
                - GPU信息(如果有)
        '''
        try:
            token = self._get_portainer_token()
            url = f"{self.portainer_url}/api/endpoints"
            resp = requests.get(url,
                             headers={"Authorization": f"Bearer {token}"},
                             verify=self.verify_ssl)
            
            if resp.status_code != 200:
                return f"获取节点列表失败：{resp.status_code}"
                
            endpoints = resp.json()
            if not endpoints:
                return "当前没有可用节点"
                
            result = ["可用节点列表:"]
            for ep in endpoints:
                gpu_info = ""
                if "Gpus" in ep and ep["Gpus"]:
                    gpu_info = f", GPU: {ep['Gpus'][0]['name']}"
                    
                result.append(
                    f"ID: {ep.get('Id', '未知')}, "
                    f"名称: {ep.get('Name', '未知')}, "
                    f"URL: {ep.get('URL', '未知')}"
                    f"{gpu_info}"
                )
                
            return "\n".join(result)
            
        except Exception as e:
            return f"获取节点信息出错: {str(e)}"
