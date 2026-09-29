import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if os.getenv("DB_ENGINE") == "mysql":
    import pymysql
    pymysql.version_info = (2, 2, 1, "final", 0)  # satisfy Django's mysqlclient version check
    pymysql.install_as_MySQLdb()
