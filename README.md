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


## 版本信息
- 当前版本: 0.9
- 开发者: RC-CHN
