# astrbot_portainer_plugin

这是一个为AstrBot设计的Portainer管理插件，提供容器管理、日志查看等功能。

## 功能特性
- ✅ 容器列表查询
- ✅ 容器启动/停止
- ✅ 镜像拉取
- ✅ 节点列表查看
- ✅ 容器日志查看

## 安装配置

1. 将插件文件放入AstrBot的插件目录
2. 在配置文件中添加Portainer连接信息：
```yaml
portainer:
  url: "https://your-portainer-instance"
  username: "admin"
  password: "yourpassword"
  verify_ssl: true
  token_cache_ttl: 3600
```

## 可用命令

### LLM工具
- `list_containers` - 查询容器列表
- `start_container` - 启动容器
- `stop_container` - 停止容器  
- `pull_image` - 拉取镜像
- `list_endpoints` - 查看节点列表
- `get_container_logs` - 获取容器日志

### 直接命令
- `portainer_test` - 测试Portainer连接

## 使用范例
![image](https://github.com/user-attachments/assets/0949dcb9-b101-41f7-93bf-36d79e8970f4)
![NQU8KK K6FFS_XALS 2I6D6](https://github.com/user-attachments/assets/5518905d-07db-4950-a857-5a16b98e6e91)
![)PJEM_GY)FVN7DK R``E )1](https://github.com/user-attachments/assets/a24233cf-10f3-4fe0-9bf6-f817de005a5a)
![T LGM930(LD{(ICM2GPDQ)T](https://github.com/user-attachments/assets/5dc567b1-984c-411c-8745-0201d81c0d01)
![A@17540@RTG9IB~BQ)9UOO4](https://github.com/user-attachments/assets/7da4fa46-74c5-4bf5-943e-901c08003e61)
![Q GZT9 X4FO`EVYO8AI_1UA](https://github.com/user-attachments/assets/ad951e12-b355-4d9c-894f-31b581b87e6e)


## 版本信息
- 当前版本: 0.9
- 开发者: RC-CHN
