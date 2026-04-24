import uvicorn
import pymysql
pymysql.install_as_MySQLdb()
from fastapi import FastAPI, Depends
from starlette.staticfiles import StaticFiles
from config import settings
from utils import handler_error, cors, middlewares

from config.log_config import init_log
from api import routers
from utils.docs_oauth2 import MyOAuth2PasswordBearer


class Server:

    def __init__(self):
        init_log()  # 加载日志的配置
        # 创建自定义的OAuth2的实例
        my_oauth2 = MyOAuth2PasswordBearer(tokenUrl='/api/auth/', schema='JWT')
        # 添加全局的依赖: 让所有的接口，都拥有接口文档的认证
        self.app = FastAPI(dependencies=[Depends(my_oauth2)])
        # 把项目下的static目录作为静态文件的访问目录 作为接口的话其实是不需要的，只要有接口文档即可。
        self.app.mount('/static', StaticFiles(directory='static'), name='my_static')

    def init_app(self):
        # 初始化全局异常处理
        handler_error.init_handler_errors(self.app)
        # 初始化全局中间件
        middlewares.init_middleware(self.app)
        # 初始化全局CORS跨域的处理
        # CORS（Cross-Origin Resource Sharing，跨源资源共享）是一种浏览器安全机制，用于控制一个源（域名、协议或端口）的网页如何与另一个源的资源进行交互。
        cors.init_cors(self.app)
        # 初始化主路由
        routers.init_routers(self.app)

    def run(self):
        self.init_app()
        uvicorn.run(
            app=self.app,
            host=settings.HOST,
            port=settings.PORT
        )


if __name__ == '__main__':
    Server().run()