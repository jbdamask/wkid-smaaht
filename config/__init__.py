# config/__init__.py

import os
from .local_dev import DevelopmentConfig
from .prod import ProductionConfig

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}

def get_config():
    env = os.getenv('ENV', 'production')
    return config.get(env, ProductionConfig)