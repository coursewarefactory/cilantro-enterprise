import configparser, os, json

CIL_CONF_PATH = '/etc/cilantro_ee.conf'
VK_IP_JSON_PATH = '/etc/vk_ip_map.json'


class ConfMeta(type):
    def __new__(cls, clsname, bases, clsdict):
        clsobj = super().__new__(cls, clsname, bases, clsdict)

        assert hasattr(clsobj, 'setup'), "Class obj {} expected to have method called 'setup'".format(clsobj)
        clsobj.setup()

        return clsobj


class CilantroConf(metaclass=ConfMeta):

    HOST_IP = None
    BOOTNODES = []
    RESET_DB = False
    CONSTITUTION_FILE = None
    SSL_ENABLED = None
    NONCE_ENABLED = None
    VK_IP_MAP = {}

    @classmethod
    def setup(cls):
        # Logger is just for debugging
        from cilantro_ee.logger.base import get_logger
        log = get_logger("CilantroConf")

        if os.path.exists(CIL_CONF_PATH):
            config = configparser.ConfigParser()
            config.read(CIL_CONF_PATH)
            config = config['DEFAULT']

            cls.HOST_IP = config['ip']
            cls.CONSTITUTION_FILE = config['constitution_file']
            cls.BOOTNODES = config['boot_ips'].split(',')
            cls.RESET_DB = config.getboolean('reset_db')
            cls.SSL_ENABLED = config.getboolean('ssl_enabled')
            cls.NONCE_ENABLED = config.getboolean('nonce_enabled') or False

            # DEBUG -- TODO DELETE
            log.important("BOOT IP FROM CONFIG FILE: {}".format(config['boot_ips']))
            log.important("BOOT IP CLASS VAR: {}".format(cls.BOOTNODES))
            log.important("HOST IP CLASS VAR: {}".format(cls.HOST_IP))
            log.important("SSL ENABLED CLASS VAR: {}".format(cls.SSL_ENABLED))
            log.important("NONCE ENABLED CLASS VAR: {}".format(cls.NONCE_ENABLED))
            # END DEBUG

        if os.path.exists(VK_IP_JSON_PATH):
            with open(VK_IP_JSON_PATH, 'r') as f:
                cls.VK_IP_MAP = json.load(f)