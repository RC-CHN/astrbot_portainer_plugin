import asyncio
from portainer_client import PortainerClient

async def main():
    # 配置测试参数
    config = {
        "portainer_url": input("输入Portainer URL: "),
        "username": input("输入用户名: "),
        "password": input("输入密码: "),
        "verify_ssl": False  # 测试环境可关闭SSL验证
    }
    
    client = PortainerClient(**config)
    
    try:
        print("\n=== 开始Portainer客户端测试 ===")
        
        # 测试1: 获取token
        print("\n[测试1] 获取Portainer Token")
        token = await client._get_portainer_token()
        print(f"获取Token成功: {token[:10]}...")
        
        # 测试2: 获取端点ID
        print("\n[测试2] 获取端点ID")
        endpoint_id = await client._get_endpoint_id()
        print(f"获取端点ID成功: {endpoint_id}")
        
        # 测试3: 获取容器列表
        print("\n[测试3] 获取容器列表")
        containers = await client.list_containers()
        print(containers)
        
        # 测试4: 拉取测试镜像
        print("\n[测试4] 拉取hello-world镜像")
        result = await client.pull_image("hello-world:latest")
        print(result)
        
        print("\n=== 所有测试执行完成 ===")
        
    except Exception as e:
        print(f"\n测试失败: {str(e)}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
