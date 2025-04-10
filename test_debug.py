import asyncio
import aiohttp
import json

def detect_encoding(data):
    """简单的编码检测实现"""
    # 检查UTF-8 BOM
    if len(data) >= 3 and data[:3] == b'\xef\xbb\xbf':
        return 'utf-8-sig'
    
    # 检查UTF-16/UTF-32 BOM
    if len(data) >= 2:
        if data[:2] == b'\xff\xfe':
            return 'utf-16'
        if data[:2] == b'\xfe\xff':
            return 'utf-16-be'
    
    # 启发式检测中文编码
    try:
        # 尝试GB18030解码，统计有效中文字符
        decoded = data.decode('gb18030', errors='strict')
        chinese_chars = sum(1 for c in decoded if '\u4e00' <= c <= '\u9fff')
        if chinese_chars > len(decoded) * 0.1:  # 中文字符占比超过10%
            return 'gb18030'
    except:
        pass
    
    # 默认返回UTF-8
    return 'utf-8'

async def get_portainer_token(url, username, password, verify_ssl=True):
    """独立实现获取Portainer Token逻辑"""
    session = aiohttp.ClientSession()
    try:
        # 获取CSRF Token
        settings_url = f"{url}/api/settings"
        async with session.get(settings_url, ssl=verify_ssl) as resp:
            csrf_token = resp.headers.get('X-Csrf-Token', '')

        # 登录获取JWT Token
        auth_url = f"{url}/api/auth"
        headers = {
            'X-Csrf-Token': csrf_token,
            'Referer': url,
            'Origin': url
        }
        data = {"Username": username, "Password": password}

        async with session.post(auth_url, json=data, headers=headers, ssl=verify_ssl) as resp:
            if resp.status != 200:
                raise Exception(f"登录失败: {resp.status} {await resp.text()}")
            jwt_token = (await resp.json()).get("jwt")
            if not jwt_token:
                raise Exception("未获取到JWT Token")
            return jwt_token, session
    except Exception as e:
        await session.close()
        raise

async def get_container_logs(url, token, container_id, endpoint_id, verify_ssl=True):
    """独立实现获取容器日志逻辑"""
    headers = {
        'Authorization': f"Bearer {token}",
        'Referer': url,
        'Origin': url,
        'Accept': 'text/plain',
        'Content-Type': 'text/plain; charset=utf-8'
    }
    params = {
        "stdout": 1,
        "stderr": 1,
        "tail": 100
    }
    logs_url = f"{url}/api/endpoints/{endpoint_id}/docker/containers/{container_id}/logs"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(logs_url, params=params, headers=headers, ssl=verify_ssl) as resp:
            if resp.status == 200:
                data = await resp.read()
                
                # 使用简单编码检测
                encoding = detect_encoding(data)
                print(f"检测到编码: {encoding}")
                
                # 尝试检测到的编码
                if encoding:
                    try:
                        decoded = data.decode(encoding)
                        if encoding.lower() != 'utf-8':
                            # 如果不是UTF-8，转换为UTF-8确保一致性
                            decoded = decoded.encode('utf-8', errors='ignore').decode('utf-8')
                        return decoded
                    except UnicodeDecodeError:
                        pass
                
                # 保底方案：尝试常见编码
                for enc in ['utf-8', 'gb18030', 'gbk', 'big5']:
                    try:
                        decoded = data.decode(enc)
                        if enc != 'utf-8':
                            decoded = decoded.encode('utf-8', errors='ignore').decode('utf-8')
                        return decoded
                    except UnicodeDecodeError:
                        continue
                
                # 最终方案：损失性解码
                return data.decode('utf-8', errors='ignore')
            else:
                raise Exception(f"获取日志失败: {resp.status} {await resp.text()}")

async def main():
    # 用户提供的配置
    PORTAL_URL = "https://portainer.wanghu.rcfortress.site:8443"
    USERNAME = "admin"
    PASSWORD = "1145141919810"
    VERIFY_SSL = True
    
    # 测试参数
    CONTAINER_ID = "acf8ee16e73532e1380b139509264f11e8affbd8534315dbd25a3d80c5ce0df9"
    ENDPOINT_ID = "12"

    try:
        print("1. 正在获取Portainer Token...")
        token, session = await get_portainer_token(PORTAL_URL, USERNAME, PASSWORD, VERIFY_SSL)
        print(f"获取Token成功: {token[:20]}...")

        print("\n2. 正在获取容器日志...")
        print(f"容器ID: {CONTAINER_ID}, 节点ID: {ENDPOINT_ID}")
        logs = await get_container_logs(PORTAL_URL, token, CONTAINER_ID, ENDPOINT_ID, VERIFY_SSL)
        
        print("\n3. 日志获取结果:")
        print(logs)
        
    except Exception as e:
        print(f"\n测试失败: {str(e)}")
    finally:
        if 'session' in locals():
            await session.close()

if __name__ == "__main__":
    asyncio.run(main())
