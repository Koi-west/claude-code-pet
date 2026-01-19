# File: python/app/services/llm.py
# Project: Tip Desktop Assistant
# Description: LLMService and helpers to call Tip Cloud/OpenAI/Ollama for intent generation,
# chat streaming, and capability probes.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

import httpx
import structlog
from openai import AsyncOpenAI, APIStatusError, AuthenticationError

from ..core.settings import LLMProfile, Settings, default_tip_cloud_profile
from ..schemas.common import SelectionRect
from .settings_manager import SettingsManager
from .tip_cloud_auth import TipCloudAuth, TIP_CLOUD_GATEWAY

logger = structlog.get_logger(__name__)

# Tip Cloud 相关的默认值，若环境变量提供则优先使用。
# 这样在开发/测试环境可以快速切换网关或模型，无需修改配置文件。
TIP_CLOUD_DEFAULT_BASE_URL = TIP_CLOUD_GATEWAY
TIP_CLOUD_DEFAULT_MODEL = 'LLM'
TIP_CLOUD_DEFAULT_API_KEY = ''
# 默认 key 为空，由设备 token 或环境变量注入。

def tip_cloud_base_url() -> str:
    # 允许通过环境变量覆盖云端入口，便于灰度或本地代理。
    env_value = os.environ.get('TIP_CLOUD_BASE_URL', '').strip()
    return (env_value or TIP_CLOUD_DEFAULT_BASE_URL).rstrip('/')


def tip_cloud_api_key() -> str:
    # 优先读取环境变量的静态 key，供 GUI Agent 线程使用。
    env_value = os.environ.get('TIP_CLOUD_API_KEY', '').strip()
    return env_value or TIP_CLOUD_DEFAULT_API_KEY


def tip_cloud_model() -> str:
    # Fallback 模型名称，避免未配置时抛出空值。
    env_value = os.environ.get('TIP_CLOUD_MODEL', '').strip()
    return env_value or TIP_CLOUD_DEFAULT_MODEL


PROBE_IMAGE_DATA_URL = (
    # 内置 1x1 PNG（data URL），用于探测模型是否接受图像输入。
    # 选择极小图片以降低请求体积，同时避免额外资产文件。
    # 请求路径不依赖外部资源，方便在打包后也能正常工作。
    'data:image/png;base64,'
    'iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAYAAABccqhmAAAmwUlEQVR4nO1di43sOK6VLyacCWKimQAW2M3h7QIbwEYzQUw8'
    'Vw/Vt90ty/wcUpQsu0TAkER9LNE6h5SrqjulJUuWLFmyZMmSJUuWLFmyZMmSJUuWLFmyZMmSJUuWLFmyZMmSJUuWLFmyZMmS'
    'JUuWLFmyZMmSJUuW3EK2qyewJE7+94885D5//ndtm6fIepI3k1Eg98oih3vJeloTy+xgR2WRwryynsxE8hTAa7IIYR5ZT+I5'
    'gB/9LMMmvwjhOlmWvx/oZ39mTQtcZDBWlrXnBv024TP1LMZlgEUG/WVZeC7gbzd/buiCTYZZRNBPlmWvBf0W/IxGPc8c3BYe'
    'b5FBrCxrjgf+NpgUrH1bzvARYIfuv4ggRpYVxwC/BfS9CSFdCPhmMlhE0CbLetd4ey/gr35HEHHG99StqKCTLIuN9fbbBWQw'
    '6ggQCfqWqGERgUGWpeLAb/H21sgg4r1BD/GG8Ba9KypYJIDJslIf4LeSgZcI0DZXnftRgEcQxIcsIpBlWac/8KN1kt7brvfZ'
    'vwX4raTxIYsIaFlWGQd8bxuPvrVt1Gf9qB4B9CKCDrKsgYPfA+AoYuB0SF1PiXi5F0EGJiJYJPAtyxJjgB9BFJwOqbsr+FvL'
    'nO5D/lxEsAjACP7IcmR0gNTNBH6tzQhi+JB3J4G3XX1H4F8VHVjqR37s1xPMiwga5S1XLYBfA5sX+C2EYdEhdTOH/SPqOF16'
    'RxJ4qxUHen0PuO9OArOAP6IdN7+3I4K3WWmQ128FfuRRgdNZ6mcN/a15b5/07tHAW6zSAP5eAO9BCJpeq7OI57v5PQEfSRBv'
    'TQKPXmFDyB+R73EUuOoYEP3Wv8WTjyCItyGCx64swOv3BH5kFPAkAsizEsGfDyWBR66qE/gjgd/75aCk9woa6kd4/EgiWCQg'
    'yPam4OeA1YMEekYEnE7Sz0QArUCPJAfkheHjSGB7c/BHAXoEGVBlTifp70QAI3TWTw0eRQLbw8FvDfmtupFkgJQ1fauMeOMf'
    'oYskBHLdTyGB7c3BHwl4a52lHi1zukjp8dIPre9Rh8zjsSSwvRn4USAida1tLPNCy5wObcOeoS4gAATQUW087wgeQQLbw8Hf'
    'EvJ72kQeG6Q8VeZ0SJ2VDKLP/a2ePZoYTO8F7kwCt515IPhbAN4yhqaT8kgZrYsigd4EEEEIEVHBo0jglrPuAP4eZNCTAFDw'
    'bxe+/OtNAD1An53ruC0JbG8C/pHA7n0sQMqcrkWizv69wv0RRPE4ErjVbCcD/1UEEAX+zRDuS22sUUBPAlgkYJTtTcBvJYGe'
    'xICM48lTZbQu8vzvCf2tBNAC7N7vB25FAreYZWfw9/b6V0YCkn70+b/F8/eOBnLjXOv8bUhgexPw9/LoI4kAzUu6FtHC/xbP'
    'z9VFAT76aJCBtd6CBKae3YXg70EELUcDNC/pkHop7OfqewB/T3sAf5FAIdPO7ALwR+s8bbT11HmtTtNHhP/IUcAK/D31thlN'
    'Brclgd/S/WUm0LceE6jUk5d0FtmYDb0VujIvjZPBttx9atnHi9ZlR3pb2W7u/UeDv7W+JUXzVDl1OgK0hP+t5/vI+t4RwbRR'
    'wPYA8CcH8CxAjmyLzkdqL+WpMqdDJAeQgBb+RxNAZFu0TtNNSwLbm4PfC+5WAmjx/hbwRz3fbCgj4GgBO6VryaP1Wp2mm5IE'
    'Zn8HIG32UuchBiv4I8aRdJZUylNltO4lWeiThXKdL3WRso/taU/lM1jPrY9aJ9V+Stlu4v2R0HiUZ4+OEJA6xB5cmdP1PAKg'
    '3h+tmyGPzLlMOd1UUcD24Jd+kfnRZCClmo4rt0rPsH9Pe+V7EoKVDKYigVmPADODv5U0rDrNHnWeKnM6SaSwti7veUlHtZGE'
    'Gss6/3LNWqhvzVtS7xq6yzah9+c2dguILCCOIgOL54+IBuo8Ve7p/SO8fqs3b2mL1Fl1SYsEro4CtgeE/i0RQHQZrUPnLqVo'
    '3vO8OU+FbOoeoI8igBbC8IB/+qPAbEcAK/jTxeCPIARJZ11/nafKiJR9tLC/zqPj1+3R8bR7SaG/tZyVfD1fLUXmP1S2yUP/'
    'qAhgBNithKDlkZTTUWVNb/H+Zdl7BIjw/pFtPJGBpJPSOn9ZFLDdMPRHAF/mtTovsL1jaXOWdJqd6jxVtgoHfA8JWInAC+4o'
    'okhgXQJ0ZVrnLyOBWY4AFu8v6SgAcXVUPQfqkQSAkIFmlzrfEgHs7akQds9rujRJ+FuG8amaM9WmrufqNBtIbS6VbdIv/CAp'
    'mm/16L1JQctb0jpPlXtGAEja4v0tOqveGjFoeUt6WRQwQwSArhjxeKgHjgB/FAFEkYCUl3SUlBuT83hlHk25/qM8vqTPxZy4'
    'dlIEUObRdfVePzSBO734Q/Mt4OxVp82PWouk0+xH2TgyAkAjASQKaPH+PepGRgN1fmgUMEME8BJuxRYvtzFlTtcCcG/fUSTA'
    '2TQyAij1tefTvGLt+bRyr0jAGg2UOi2iodadOq7RJdsNvL+ms3jdCOC3EoQ2b3Tdmg0pO4+MACI9v+bFkfqWSMEbEUi6Mr0s'
    'Cthu8uIPzXvIwAp8tG0y1EllyRZlKuWpshf4V4AfBTjSpoVQNJ2WR9KhJHDVEQBdGbK5S1DUOqrdZqzvRRSRJFDXU3bi7FpK'
    'Ztrkorzn97abUZfAcgLr6vmjeysXY6P1lH2o9Unr5gRtFyrbzb0/B7IUCOLWflIfbe5UntNR9qv1KSgK4CIAxPOX+SjPH9En'
    'A/2QuWvrRtJhUcAVEYC2Is2TbUyZ01H3swLY068nCXCEKeWpcgK9H+XZd32py1U+CflIz8/Nv1yDtR/VV4oKOFuVeW093vXe'
    '8lMAaRPXbfa8VE4BwOXmGXVJ4yWw3EoClH2ljU8Bvsxr4b92BKA2vFRnFW58RKQjUa1HiKDsw9lvqFjYccSbf02nAYnTe9v1'
    'uizzR23D2Zcre8P/Mm8N/7VQm9OPulJjuySUE6Ajbd/zGHD1S0Bq49Zt9jxVpjY5BSBq7Bkuac4aCXA2lEiA0yFh7l6mPBcS'
    '/pdlziNe4gUd0YIWGWx3iQK2G3h/pKzpZ7/Q9Ui2olLK9pQ+G6MAKdU84UwePwdHCtq6JVtdEgVc+RKQ26yUjipz/RCwcfOa'
    '4aLmkjqSAFdXev2yLKWJyXNRwJUePzN6BGmUN6/1m1JOih2HyPYg74/WW68fkxABV5bSOk+VUa9viQAsUUDv6+cg75/vGAWM'
    'jgCQzai1qUFA9Y8GYupAJOiY1JqlPGU3xM6l1y51G5PfUy4CkKIASjYCuC1CrSdCMqGrbeaJAqQ2j30JyOk48FF9OMCi8+hJ'
    'BJ7oITUQAWVHKs/ZIoHg3zdpCVoU+DXQuePADycZeICfDW03x5GAKmtEMES2C8N/auNqG93jQXsA9segowO1Rs5WtS1r21Nl'
    '6zFAC2G5EDkNCuV/XnQsyMIaaz1lK07X/RgwMgLgNmWtozYt10cCDtLO2886bsRV37O2TRQJlN6+LEupFgFEeDbrvKl6dCxP'
    'Py0K2HVIFEDVdZFtopd/2ibvAcBWT+6tk9pqa5NsRNn5I//7H+mflmf591/pP4wn0jx+XZY8osUT/+xQl4MjAm7tko2ofJl2'
    'jQJmegdA6aV2UV5VG9Nzvx/Bx4ME6L/s9fsf6V8Gm5NCEcbff6V/A96f8ngUIOpz/g5ETn4I9ZsjKshAf6tQXnu3AVfW9F1l'
    'FAFQXqmuk8oUYFvnw5GBF4BR5OAhBAr0H/rs31If/bdvy+TyHhUZcGG/9e4SyL/mBIJc0ktjRUg5tgR+CvQ1wXaVbeLw3wKw'
    '1ACwHwZ9iw6dm+Xjwhr4GwN473M+P9TtqP8kgl2HhL8tIfnPYF12hP9l+9RwNEhKfsgxYEQEQIE/KflSh6y0BgzSrm6P6Ll2'
    'LUTjIa0S+B/lCviIHSihvNGh/vM+2x4Z7PMgIoKWj/e4SOA0H0DHefzM6Ms6Sqixtbacl+fydfroPwpKgY1qg5JB3Z7rayEC'
    'K+CRNh7gbyXwAdBb3YRGDF/1OX/rXmRQEQEqOxl4wY6AHwV+Fsal2ngIoiaE7gBHHkDv8J+SlnrIQwJ9Nb2FBNB5oeD/QV2f'
    'INsq8GvzjhDJPnv0URIUOf9IInQ+I8k+m3H/ePZeiqpn/tLWrV4CkpspcCNrD+cK0LtIgfH61Ho4O7QI4sW+IoJt+/7IkYgG'
    'LB7fUtY8P3IsyMK96npUtPGRY8D8EUAg60mb2OMhpDEovbWM1v0AyhL4X8Dfwc/Nn1trfSLflKs+uWsEeii/5viaazl3xh6I'
    'TTy29jzT5Ng/nj24jyOVtfa3IgBKkAVHLVrbvBKQkA1U10Vdh5Cf8foyKEuw65uStk1JCsg9iznuZFUdCXrYyvKspPLG2iFG'
    'tqvB3oUADOf/0yYB2lsNIm12jfWlMjV2FAmQnu8zjKbAz6/tDHpS8mtc4hLteiQDjQhqEvinw8tbwe8lhk3YD5Teuye5Oi3f'
    '9T1AzwjgsBmAthoRoBsCGZt78FTZQghIe/VlWAX+E7BY4BM2sAAdbIsQwVcdQAIcIfSwfQLLV+xJrl2Z3v4IoLFc1EI1JkfK'
    '3rzl+gGAn7KNCHwBwOZNK47FE8Ehr5CANwpofV5WIojcm5KuG9hneQeAGMNqBIl1t8HAp3TQZQD//pKOBCtoF0nIfgIR8PPk'
    'SaAV9COIYEPsAgrXZyjgQwkg4Pyv9bFsDK6/pKPKUt4K/NQJ/Bow6XXqnwDULw3J8cj7/erXgwQ8ttZtKNnpKFvnPcqVh7wH'
    '6BUBUA8BaR91bw/wJZAnUIcA/1RXve3nN+t3yP8lAvBL0Ns+US4/MuTtUd97fwEprqH6dKDJbtX4iI5cR2onAo9YsRF570uO'
    'ABq7tSyQY1pOx9VbSQCpEzc38VEfPc8KWJUXPt6DBr3knbj5UmRwuB8TDVB2/h5SJgHUjuhzoPK1TXZB908rGWj7vwvYZ3sH'
    'wBkBNa7WVnuY3EZACIGqs7Q5tGc+6hPBT87x+Jl9fV9KxwOfJwPSVgYSoNaMgj0Z20hz2Ag9VVfX99ivwwB/BQFoDCv1QzYq'
    '10+ag/Tw6zYoCSBzPlzFWZgaSwP/cT408KM26pkIiHlYSaCygeUixyLtwuss+4Kqj9yvXHmblgAcPwDiJGqRHPARAkI8BtfO'
    'kmrnfuneNfh3JfdNPWnzoZuUAt2v/Pl9BE0CwrrA9wHWVCZUvh1CCpzOKyGYaXkR2OPHQJxh63pNZ7kfMib3YCWPwKUcMBAv'
    'gKx1B5kOfn6+p/G+tgm3X7Zf7Tb9ByzbV91rDt8U9KF/zXU713/3kde9t0XAXv7Ih5pfnZb9qDG4n+lSc6/7WIUbkxqPWset'
    '3gHgm942puS1uLEtedTjRHv/w2NuAP+vL/H8+oEO99uA7+uzfm+fZVuKczlEAvwLztYoAG1X28aat+63K/Bwq5eA3OI0Y9YP'
    'HRm3J/jR9LQJhb/VR52dj3L8zJ3c4Dvwlc/1KcB91+9kQNcf7199PGlZE/OHTTzg7k0CyN5F9i9XN1yu/iYgJ9oG5fpQY1wF'
    'fspDlZ6O6nea08n700A7gp/+irBlgx77HX+KTN1zn+wGvA+oy19pFQXU87mSBDZm7pH79xIZ+fcArEa03EMbuwX80n25VNLJ'
    'Y8qhvzTfX5/J00DdHBv0RARFNMDOodYRRwHMDrhdkTFbSSAB9mkRdL9OSwDeSbYuTvOG0j20jczVoaRx2rj7X/YRz/7SfIXv'
    'C3wAjfl4ripLNqfaHIGnkYAMcm6tX1+Eqv7YaYvNuXloJFAK8mx67OGe/doJAPjYYbvIAJZIANEhHgfxVFxf3PvbwV+2P5bl'
    '3wDw/Wwk4IkCICI1gh8hgx57CJEwnHg/Cow+AqChWOs9PONojI9uIBTcpCdW/pKvxxNp4N/bUN8UPAr9B0VYElBsal4LYRuP'
    'rS1pKUhE0GNfUuO01E/9TUCpDdoOreMeqMUra/dCN+bpH3gIc0W8/1cZ+iKR7TcBX5PQxiXeN7BzZv42QTLaCrU7IpswlpTX'
    '7jVqvz/yUwCOmTWDWR6Qdi8k5cbhNpW+SaWPBZly1jYy8S3BLPxJsGK8bxDLP/Pd+6hzBddarwcm2MBnyImVBLg92x3UT/mj'
    'oFEsiW4YVCwbsYW09DINpG/wF7od+NqcKiL4JTQJ7HW+ucvlus5DvIhs4LiW/i37eTg5zBYBRIjXiFGeg/fYEmD3NnV/xlsy'
    '3p8kJ6KtdFF9xHuxDr2qAI4BnnckUVEAIlN57wi5OwF4vX/rg7R6Dvne9vBfepl3CPuFY4J2z2Nf6e2952NNnQxtNox9ppth'
    '3FuTwmxfBW4dIyIEbLknma9+9usR5ChRAlUGP/8xIEIC9Ji2OWvy9d+FiLF6HelQ6UE+UWO8XQQQJZzxreG/pw3fDwv/kfvv'
    '49V/u+8Y+p/r4fsAx4CeYTdyDPCM+3gZ8X8B6vzVgntT35hYCNy3TQlIaj4cYMi5Nxwjotu07KneUcst8XPXCGC70IDdwj3l'
    'v/N89+VCcekF2vlHROcIQG77NUnh3ur8hTXOFkZvxnFnIo/HE8DsD2CmuZRChfeekP8KmWleW3qIPIkArpBZjzmI7N8N+Mhf'
    'PZk3svtUsghgyZI3lkUAbVKeukP/VtsAyUX8f7u5M/klb0wAM22EmeZCzatMKd2MMtO8cnqI3JUA8oVeIvca4+sv6Wp9z+/k'
    'qXfw9WcC9dg7+DPY9muSwr2RPxSRR9s1YKw8+N6PIIBZwzTtF/FaG21MHjy+OXnafIT3wnyosSj9R7k6JlyxHqrsfUbI859B'
    'huDnrhFAtGheiQOMd1ysH/N+23Bur710+QPhcwRwrofvw76Kp75BYBOvnbX5Z+d8HiVXEUCvcK/Fc0fck8z//Vf6T+Oa8ail'
    'ABzrubk/CkaMeRiDC//tc9Ykf9qMGitPvge8cgkh3T0C0Ixm2Tit90WPAee+/CfZ3DjSX+E/vCNoCN8p8NP9j3XYEYiev9+G'
    'sc80G8a9dSRxdwKgpDXU1FLtXuzGff2/LK396SUZdgyQ5kqRgHRRfcR7AeE/vTbCfpWNEDJBwn/PseZxYJ+FABBGrTdk63hS'
    'W28IiIxrCZHtZYlQqpD+8zN/dU4bBf7ze4FvoSOD1nJdh0ZcPY90lKD7E93P+d0jAAlILWCy3AtJuXE4ctA3qP0YIL2d/yaB'
    '47n9iwiY6zjfX40lwqu9f0v4fxobtK3UX0pb9wtCWhEO5/YEYGHJlrGkB6TlI6MA8l5//5X+Dc61DJW/gcj0+wyZ5fmcw2rp'
    '+pqENm517yTNGQj/EVuhdkckC2NJee1eo/b7lAQwIsRBjSfdu8VzWMF/mK/jjKu12wGukcD57/7Usnv8X14fIRUPSPiIhiYq'
    'fg68rjUKyGncvpTm4anvTwB//hf52Tcs3gUh4RWyKVvDSKrO46kO4ASigG/g6CRQEwb3MaDcr5hn5dHFuR7ayt8YRIm0hQSo'
    '+/XYQ4iE4QTAZNcIYIQB0P4eT4RsEsumq3W5DG2FsF2er50EKEBLNqfaZAf4rd5/P06U4T9KpGgd18YVrSi6O2BnyDsAychR'
    'oQy1qaWyltc8tdae81TIeuUoQCGtjxd5dGhO2YO6qDZf5U0DP6EzeH/u3kgE4H1WaJ4rR+5hrhx1j1t8CmDZoFQfaowIEvCk'
    '9bw/8p8eTtvAR89e6ug/CH4CqhDSS3ak2nwcDxhiOUr1iQFDFnX5Ky1so9kxIrXkNTKI2L+XyGxfBfZsUG3cK0mgnDPypaBf'
    'bTRPef4+/2kN25kIODLg6z+BT3x/4Hx/7d+OCmtiXoz2AL13L1j2LrJ/ubrHEgCyOKsBOGNqjB1NAuhG/bp2Tye+C5CPAqcv'
    '+pBjFETwRQZHQjhen/V7e+aLQ9BciNCfHGO3QeX9rTbV2kWAPxv22xV4cMlvHcZ8TXwrUq5e01nul4Axy3LZp9bXeSqlxkA2'
    'oGSX89xfwPr0nS9A5bp/UU/Mr177t+I1Mn9faU7JAX6OnKR78CRFAx8lAy6fAfBTc20BKTem1DZPEwEQHzt4Jxe1KM5bIQ+W'
    '2jx1PdfOklqigJOOjQSqb/sR96tFAhTXTvqW4NecLC8JG70/lyLg55431V7bUy0SghnvR4BXfBMQYdayTmN/qZ80B4tHsIIf'
    'vqqfCdMbdhNJ4DvPf4mmnpcmVNtjmfm48QR+/sXhV1rYwHKRY5F24XWWfUHVR+5XrhxFNFN+CkAtrnWjSuNrwLd6DA70SJtD'
    '++IlmJUEjn3O3/STwKxt1LPu/OkCPycF/NWarUBH20hzyISeqqvre+zX7kCfgQA0ZmsxAmdc7WFyG6HeQNZNKG1m6SjAz5Mg'
    'ASEa+NXe9hsAmgg2FviZmAc51/oZKKE/akf0OVD52ia7oPsHBT0n2v7PdycAythI+6h7aw9SKqPgp3SWDcyRALcRdlAfwaSt'
    'gyYDWc6gp9ZO/e0CDfzouR8lhXJ8Kwlkxm5UmdO1iBUbeToCMLwI1FiW64NeUn9JJ3kAKo9sRnRD1yTwH4gE0vlLPqQXpsrc'
    'bwDo3wSw4zFen9qoHPgt536PrXUbSnY6Su68R7ly7v0CcIZvAlKL9DCtZGx1QyubCM2bQd9IArVeIgKrTcl+xPi/2tI/V44A'
    'vxf4lrxUlvaSd49S+stkNAFoDBdlDO0BjiAC5PpZ5w0kUB4JSCJgfoOPAk0f6xjyW8B/WncjGXjySLnURe5NSZef9n8BkAVJ'
    'BrZuCmTsSCKwbkppw3MkwNlSJIKXUH/5h7ET2lYCfjnHDIBfIsQetk9g+Yo9ybUr0/kIIOA9QKuRqD4ok3MbCN10Wh1y/QRI'
    'oLQTvzb6D3qchPuTYKJdj39QRAPMRwqA3+v9rc8FedYJ3DvePcnVaflu5//Z/yho1L2sZECVPcTQSgo/iY8Ipfkedfx3/3Gb'
    'nf+KkAb8rzlWb/s/1tPJVpZnJZUza4cYQcaKuteUfw8AqZeYz7MxpDEovbWM1mmejwVIQQLUkYAqn+f8/bHeNynw13dbev3c'
    'fT/Knz8kOsydsQdiE4+tPc80OfaPZw/u40hlrf30PwbiFqH98Ib8AQuht9yzFm38Wmcpaw8WefA/P8c9EPMnkLbf/0j/3D5/'
    'yJNfPwOi5079KCpSyHWUUYrwpn9EFOAFfSkomDWxkGed7wr80AjA8cOglnov89Z9NX3LBkMu7WXY6So9KvFVWm2NLSLZp/wT'
    'Z3XIX18eW1wB+l57L0XVR5z/R0YA2sIsXgxZOWdMLgIo6yh9fX9q80h9TB5fkv1v5v3+R/rXJ/DqiEBaS13v3oT1ewnib/m1'
    'kqAGeA8pcESQiXVawM315epO9rxKfhsI8DpNQr7sm8DfzyegLWVwCfjU2C1g54C+EwFFBrtdDldJBB+T+CSD1x8NENYizY+S'
    'U7v6+wkA8JMD9CgxJEBXrgXRZ8AmKCFIRCDl67SbxMQRn/K/f5z3C5DWeaqs6a3XD0edRe8Z33Kd7LUTQW37T0JwC/MJBAf8'
    'uuy5rEcFrr1VnwPfUXB2kOxV2lgkgqjw/+qXgHWdVN4lauUULKSweTPqJdhJkQAnmSGBL/3ff6X/q8ggVwC22u60hgr0ybHh'
    'W8DfCrZSr9W1CjemVi51kfOZ7h0ARQSUXmoXIRzR1G24uuwEeRny12E/BXbKJvuV63xJBvsaXp8gJINUf6ykXKsG/rosAfPn'
    'ReRAATEHXJQgoJf09zkCBB4DUmP4nwJC7h+d65vDfiIvpfXzSMYNm4OJwHr97FyfgX6WNVFtOXshdg4P/0dHAOgxoK7fDUD1'
    'afHsLf2kqMBzX2kMNuxn8lRqmTc1dwv4y3wvMkABV9eX68mGcZF+lA05O1I2pux7vwig88vA5PCU0V76R+fxuflLtqBsKuUR'
    '4TYrQgISIDm9dPU+KvwMJBrEFpTdpLSL95/tHUCp2xfOlcs+tVisZGHaei6ImD/eE+xiiQCSkK/XU97HQwJeItBA0/Iz4eTs'
    'gwjSn5tLWab6DJffLga+RgRcWQJ7tCE9wEde/GlEJQG/LJf22QDwa+up9RzwubSVCKKucs49xi2Fq9fKaJt7HQEajgHJGP6n'
    'wBA7+qWd99LWSeWltLY/KtzG1MDP5a8iAu76KQDcQwqajrILknYL/686AmQiZPVGAUgYWwtnyaHMS9ybigxKfVku81KahCNA'
    'qsbi5tVKAhKoOP2IixNPX0qvlVXQ3zoCmCgK0Opn8/bauqk8ldZ5SYduVCv470AEGQC7tV5at2bDYd5/hpeAdUq12fOcx6Ii'
    'g1Io6w1nWuL+tbfn9LUdSntJnp+KAvYx0DlyZQ38lO4ORECJ1o7SU2VqXCp9TgQwKApIgZ7f0ydqfHSdlG3KVMpzz0LafDmA'
    'BJDySCJIgX2SoZwMaXfvf/XPgaOiAC4C0CKDNDBa2NfBjY94/dpGlP2SkKfWJ3m9CBKQ8qOIgFtfNvbV9FKZuj+VDpcrXwJq'
    '9dRm3/PacaA2KLrxKfEQCbpehPTQ8H+fK2ordO5UmSMBKyH0IoF6zl6yyEy9pKNshwI9P+4IoBwDrEeA1OEooNW3tJfaavOn'
    '1srpKPvVec7+pUgeM5IEkLKXBCxtM9Ceq5fmr+U1Ow4J/2d4CWhpJ+WRowC3ua3esQ6rkblrdVJ5z1t01DytkQzlSaX8DCSA'
    'tCnbJmN9KVQ7LS8J2u5+EUBgFEDpJG+bAjyztx16b6mM2IKzIWVnj3BEMJoEUhD4pXbJoE9COQG6Mr3E+w8lAPATAQ/4ryIC'
    'T19trui6NdvVeUmHeiNLBHAFCaSJgJ8BW1A2Gwr+Wf4o6G6ATdCX9VI+EWVOt+upza7VRaxRKkvrptJyvpw9Sp113lT5ChKg'
    'dD3qdpF0ZVnKczaP3Fv3iAAuOgpo5egoAdFJZWm9UirlJR26OdGNjpJBJAlQOq0O1VvKCdCV6aXef5YIoPaEWjvKK+55ynNT'
    '5bI9107TR4m0ns2QUv33+Zf38swvBYB/T1sIwUoAFn1ygD0xedTOPffVnBFAYxSwp5yuNTqwRgKIDp2ftjbNTlLe8sy5TWnZ'
    '9BbPaCWBHqTg8fLI2qT0cu8/SwRg9XxJ0NUeG4kOynqqzWgp11TrEBtIEUCpt8wnOcHfSgbRBECNhXp5LQJAbVC3eb8IICgK'
    '2FNNF1WOaGPJIymno8qaXtuYHBFYNj4KfC7v9eAeYtGIweP1p/L+lxJARxJA8yNIAamTdEgq5aly6hABlHkvCVC6XoRgKVvy'
    'SDoN+Gc6ApSG4UJcLq3bJjAfUZbmj6wN7WsZrx6nnj86tqZvIQIE+FGE0FJGAN8E/qvl0gjAEAWUeY8njfDUkeMgc0ZSKU+V'
    '7xoFRBFAa51Vl2b2/lMQQPBRYE8j8x5ge0FvAbwV+NZnnZ1EgBKClwy8ROGJNhJICEg6HfhnPAK0HAXKNAXmqbJ3DWgfLqXa'
    'UONT92sNPSPBz6W98tOBfxa5noL4KAD1gN5jwNV5ZM7a2us8VeZ0s0YBVN0MeSsJcLppvP9L5phFzPuAFhLQ6q2gbg31LWRQ'
    '56kyWqd5KgT8Zb41CqB0VrKIGKcF/HV+GvDPfARAw+hdV6dcXWLy6FFAE89RARFpfXs+CeV6LM/9e0UBddpKChGePTvWotlj'
    'SpmHirCjQJnXIoIeR4TWtuh8pPZSnipzOkS0zV2XUaBYvaqXAFrbpgZiqPPTef+XzDUbPwl40t7HBknnSdE8VU5gveatrOAv'
    '8y2px2O3RhUtaZ2fEvwvmW9G85NAhM6SevKSziOWMLcHEVylezT47/AOAJGXsTdnWkq0rp6fdz1IW+4+ucMRoNYjUQESMntB'
    'OQvobylz0pI9CijzIyMDpA5tg9ZJeUmH1OfOkYCVCFpJoifoM7Duqb3/S+ad2fUkEAV8ra3Uz5OXdC3SCn4PEVjA2Eokbwf+'
    'l8w9u1gS4OqiyMDaxzpXKU+VNX3kMaAuS8DuTQSePrlxrnX+FuB/yfwzHEMCddorYkDn4MlTZbTOehywgp/L9zwatPZ9PPhf'
    'co9ZxpAApesJ9Cs9P/JcNwPgpTYjIwEt7RniZ2CNtwL/S+4z0zlJwJNa6+o8UuZ0LWIF/xUEEJk+Hvwvudds20igzEeE6T2I'
    'wJOnypreKnnQUeAqYGegrZS/Jfhfcr8Z9yMBqa4HcWg6KY+U0boe7wFGEIClbfQ5P6cHgP8l95x1PAlQugiCsNahearM6ZC6'
    'VvCPIACprqXP24L/JfedOU4CZblHVOBtY5kXWuZ0aBsJ9FKb1migNSpobYPM4XHgf8m9Z+8jgTLvjQoi6iz1aJnTRcooAqDq'
    'e9Qh83gk+F9y/xW0k0AvQvDopDxS1vStki9+HzAK8FmY/2PA/5JnrEImAQ/YegHcOw+uzOkkfW/wU7p8IRloOtN5/0ngf8lz'
    'VuIngchQPRr0704AZb7l6IDUvx34X/Ks1dhIoC73AL+1raVO0kn6mQiAq2slBu9YbwX+lzxvRX1JAMn39PjWl35RzzcPfimI'
    '5CPGeGvwv+SZq9JJYBYisNRRZU6H1M1IANMB/8ngf8lzVxYbDUh1PfJIWdNrdT0JYFQUgOYtdW8B/F2ev0I7CdS6Vk8eBXir'
    '90fqURFDqYAooCfAtRd7+V3B/5L3WGX7kSCaCCx1Vh1Sd8UxgNK1AtrbjpvfW4H/Je+z0vhoYESdVYfUPYEEWuo4XXon4O/y'
    'fiuOjwaiQ/uZQv+rjwJauXWstwb/S95z1WOIQCsjwJ7F8/f+VKDW9SSNg/z5psDf5b1X7yOBK738DOAfdRyIKHO6D/nzzcH/'
    'kmWBsUTgbcPpkLq7kwDSZgHfKcsSNhJoAay3jUff2vYlOaCt9zsC3jbSPT9kgf8oyxrjiaBVJ+m97aLIwEIEI3RfsoBPy7LK'
    'OCIYBfzezzRfRATWth+ygC/Lsk5fIuD00aH+jO8ApPoIgC/gB8iyUiwJeF7WeV/ueZ/dFnj2R/tFvCxE6j5kgR+XZal+ROD1'
    '6BGgv+qLQEg7Tx103wV8uyyLXR8VaPUznPt7vA9A+i9v31mW9eaJCtB6tM3oIwDatxn0L1nAj5FlxeuIoAfYZ/gqsKctPN4C'
    'fqwsa85DBjOc8Wd4R3CSBfp+siw7JxG0PJ8ZvgcQ0WcBf4AsC9+HDO7yzJoWuEA/Vpa1700Gs/4a0CQL9NfJsvxzCWFaWYCf'
    'R9aTmFieQggL8PPKejI3k9lJYYH9XrKe1oNkFDkskC9ZsmTJkiVLlixZsmTJkiVLlixZsmTJkiVLlixZsmTJkiVLlixZsmTJ'
    'kiVLlixZsmTJkiVLlixZsmRJGiv/D51JlIPbWRRhAAAAAElFTkSuQmCC'
)


@dataclass
# 意图生成的结构化返回，保留原始回复便于排查。
class IntentGenerationResult:
    suggestions: List[str]
    system_prompt: str
    user_prompt: str
    raw_response: str
    language_label: str


@dataclass
# 聊天 prompt 元数据，便于在 UI 展示或调试。
class ChatPromptMetadata:
    system_prompt: str
    user_prompt: str
    selection_hint: str
    language_label: str


@dataclass
# 视觉模型探测结果，包含是否支持图片及错误信息。
class LLMImageProbeResult:
    supports_image: bool
    provider: str
    model: str
    profile_id: Optional[str] = None
    error_message: Optional[str] = None
    response_preview: Optional[str] = None


class LLMProviderUnavailableError(RuntimeError):
    """Raised when the configured LLM backend cannot be reached."""


class LLMService:
    # 跨 Tip Cloud / OpenAI / Ollama 的统一封装。
    # 负责按配置选择模型、构建多模态消息并处理流式输出。
    def __init__(self, settings_manager: SettingsManager, tip_auth: Optional[TipCloudAuth] = None) -> None:
        # 负责聚合多个 LLM Provider，并按用户配置动态切换。
        self._settings_manager = settings_manager
        self._tip_auth = tip_auth or TipCloudAuth()

    def _get_active_llm_profile(self, settings: Settings) -> LLMProfile:
        try:
            return settings.get_active_llm_profile()
        except Exception:  # pragma: no cover - defensive fallback
            # 如果读取配置失败，回退到内置 Tip Cloud。
            return default_tip_cloud_profile()

    def _get_active_vlm_profile(self, settings: Settings, *, required: bool = True) -> Optional[LLMProfile]:
        profile = None
        try:
            profile = settings.get_active_vlm_profile()
        except Exception:  # pragma: no cover - defensive fallback
            profile = None
        if required and profile is None:
            raise LLMProviderUnavailableError('未设置视觉模型，请在设置中选择 VLM。')
        return profile

    def _select_profile(
        self,
        settings: Settings,
        *,
        needs_image: bool,
        explicit_profile: Optional[LLMProfile] = None,
    ) -> LLMProfile:
        # 优先显式传入的 profile，否则根据是否需要视觉选择 VLM/LLM。
        if explicit_profile:
            return explicit_profile
        if needs_image:
            # VLM 为空时会抛出 LLMProviderUnavailableError。
            return self._get_active_vlm_profile(settings, required=True)  # type: ignore[return-value]
        return self._get_active_llm_profile(settings)

    def _compose_user_content(self, text: Optional[str], image_b64: Optional[str]) -> List[Dict[str, Any]]:
        # OpenAI 风格的多模态消息体，兼容文本+截图。
        content: List[Dict[str, Any]] = []
        if text:
            content.append({'type': 'text', 'text': text})
        if image_b64:
            # 图像以 data URL 形式传递给支持 vision 的模型。
            content.append({'type': 'image_url', 'image_url': {'url': image_b64}})
        return content

    def _tip_model(self, needs_image: bool) -> str:
        # Tip Cloud 的模型命名：VLM/LLM。
        return 'VLM' if needs_image else 'LLM'

    async def _tip_headers(self, *, force_refresh: bool = False) -> Dict[str, str]:
        # 设备 token 需要可刷新，失败时由调用方决定是否重试。
        return await self._tip_auth.auth_headers_async(force_refresh=force_refresh)

    def _normalize_message_fragment(self, fragment: Any) -> str:
        # 递归展开 fragment，兼容字符串/列表/结构化 content。
        if fragment is None:
            return ''
        if isinstance(fragment, str):
            return fragment
        if isinstance(fragment, list):
            # 列表代表多段内容，拼接为单一字符串。
            parts = [self._normalize_message_fragment(item) for item in fragment]
            return ''.join(part for part in parts if part)
        if isinstance(fragment, dict):
            text = fragment.get('text')
            if isinstance(text, str):
                return text
            content = fragment.get('content')
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                # content 可能嵌套列表，递归处理。
                return self._normalize_message_fragment(content)
        return ''

    def _extract_message_content(self, payload: Dict[str, Any]) -> str:
        choices = payload.get('choices') or []
        buffer: List[str] = []
        for choice in choices:
            # ChatCompletion 兼容多个 choice，这里仅简单拼接文本。
            message = choice.get('message') or {}
            fragment = self._normalize_message_fragment(message.get('content'))
            if fragment:
                buffer.append(fragment)
        return ''.join(buffer).strip()

    def _parse_intent_response(self, content: str) -> List[str]:
        # 返回值期望是 JSON 数组；失败时返回空列表。
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                data = data.get('intents') or data.get('candidates') or data.get('titles') or []
            if not isinstance(data, list):
                raise ValueError('intent payload is not list')
            suggestions: List[str] = []
            for item in data:
                if isinstance(item, str):
                    text = item.strip()
                elif isinstance(item, dict):
                    # 兼容 {"title": "..."} 的格式。
                    text = str(item.get('title') or '').strip()
                else:
                    text = str(item or '').strip()
                if text:
                    suggestions.append(text)
            return suggestions
        except Exception:
            logger.warning('llm.intent_parse_failed', preview=content[:120])
            return []

    async def generate_intents(
        self,
        image_b64: Optional[str] = None,
        text: Optional[str] = None,
        language: Optional[str] = None,
    ) -> IntentGenerationResult:
        # 依据是否带截图动态选择 VLM/LLM，并返回意图候选。
        settings = self._settings_manager.get_settings()
        needs_image = bool((image_b64 or '').strip())
        profile = self._select_profile(settings, needs_image=needs_image)
        language_code = self._resolve_language_code(language, settings)
        language_label = self._language_label(language_code)
        # 构造严格 JSON 规范的 system prompt，要求返回短意图标题。
        system_prompt = (
            'You are a macOS assistant that receives context selected on screen.\n'
            'The context can include **plain text copied from the UI**, a **cropped screenshot**, or both.\n'
            'Based on the provided content, brainstorm **up to three** short intent '
            'titles the assistant could execute.\n'
            "Each title should be a concise action phrase written in the user's preferred "
            f'language: {language_label}.\n'
            '\n'
            'Guidelines:\n'
            '- Infer what the user wants to do with this selected context.\n'
            '- Keep every title short and concrete (examples: "翻译此段", "总结图表", "解释代码").\n'
            '- If no meaningful intent can be inferred, return an empty array `[]`.\n'
            '\n'
            'Return format (**strict JSON array of strings**):\n'
            '[\n'
            '  "intent title A",\n'
            '  "intent title B"\n'
            ']\n'
            '\n'
            'Rules:\n'
            '- Always output valid JSON (UTF-8, no trailing commas, no comments).\n'
            '- Limit yourself to clear titles only; no extra descriptions or metadata.'
        )
        user_prompt = ''
        raw_response = ''
        user_content = self._compose_user_content(text, image_b64)
        # Tip/OpenAI 接口都使用 messages 格式，保持兼容。
        payload = {
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_content},
            ],
        }
        suggestions: List[str] = []
        if self._use_tip_cloud(profile):
            model_name = self._tip_model(needs_image)
            try:
                # Tip Cloud 支持多模态，优先尝试。
                raw_response = await self._tip_cloud_complete(payload, profile, model=model_name)
                suggestions = self._parse_intent_response(raw_response)
            except LLMProviderUnavailableError:
                raise
            except Exception as exc:
                logger.warning('llm.generate_intents_failed', provider='tip_cloud', error=str(exc))
        elif self._use_static_openai(profile):
            try:
                # 静态 OpenAI 仅用于文本模型。
                raw_response = await self._static_openai_complete(payload, profile)
                suggestions = self._parse_intent_response(raw_response)
            except LLMProviderUnavailableError:
                raise
            except Exception as exc:
                logger.warning('llm.generate_intents_failed', provider='static_openai', error=str(exc))
        elif self._use_ollama(profile):
            try:
                # 本地 Ollama 走 Chat API。
                raw_response = await self._ollama_complete(system_prompt, user_content, profile)
                suggestions = self._parse_intent_response(raw_response)
            except LLMProviderUnavailableError:
                raise
            except Exception as exc:
                logger.warning('llm.generate_intents_failed', error=str(exc))
        else:
            logger.warning('llm.generate_intents_failed', error='unsupported llm provider')
        if not suggestions:
            logger.warning('llm.intent_empty_result')
        return IntentGenerationResult(
            suggestions=suggestions,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=raw_response,
            language_label=language_label,
        )

    def _compose_chat_payload(
        self,
        intent: str,
        user_message: str,
        image_b64: Optional[str],
        selection: Optional[SelectionRect],
        selection_text: Optional[str],
        settings: Settings,
        profile: LLMProfile,
        base_payload: Dict[str, Any],
    ) -> tuple[Dict[str, Any], ChatPromptMetadata]:
        language_code = self._resolve_language_code(None, settings)
        language_label = self._language_label(language_code)
        # 基于意图/用户消息/选中内容构造系统与用户消息。
        system_prompt = (
            '你是 Tip 桌面助手，基于截图与对话上下文帮助用户完成任务。回答时保持礼貌、简洁，并确保内容准确可执行。'
            f'用户偏好语言：{language_label}，所有输出必须使用该语言，以免混淆。'
        )
        user_segments: List[str] = []
        if intent:
            user_segments.append(f'用户意图：{intent}')
        if user_message:
            user_segments.append(user_message)
        selection_hint = ''
        if selection_text:
            normalized = selection_text.strip()
            if normalized:
                user_segments.append(f'选中文本：\n{normalized}')
                # selection_hint 供界面显示截断版本。
                selection_hint = normalized[:160] + ('…' if len(normalized) > 160 else '')
        user_prompt = '\n\n'.join(user_segments).strip()
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': self._compose_user_content(user_prompt, image_b64)},
        ]
        metadata = ChatPromptMetadata(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            selection_hint=selection_hint,
            language_label=language_label,
        )
        payload = {
            **base_payload,
            'stream': profile.stream,
            'messages': messages,
        }
        return payload, metadata

    async def stream_chat(
        self,
        intent: str,
        user_message: str,
        image_b64: Optional[str] = None,
        selection: Optional[SelectionRect] = None,
        selection_text: Optional[str] = None,
        on_metadata: Optional[Callable[[ChatPromptMetadata], None]] = None,
    ) -> AsyncGenerator[str, None]:
        # 统一的聊天入口，按 provider 选择对应的流式/非流式实现。
        settings = self._settings_manager.get_settings()
        needs_image = bool((image_b64 or '').strip())
        try:
            profile = self._select_profile(settings, needs_image=needs_image)
        except LLMProviderUnavailableError as exc:
            logger.warning('llm.profile_unavailable', error=str(exc))
            yield str(exc)
            return
        base_payload: Dict[str, Any] = {
            'model': profile.apiModel or profile.model,
            'temperature': profile.temperature,
            'max_tokens': profile.maxTokens,
        }
        payload, metadata = self._compose_chat_payload(
            intent,
            user_message,
            image_b64,
            selection,
            selection_text,
            settings,
            profile,
            base_payload,
        )
        if on_metadata:
            # 先回传 prompt 元数据，便于前端展示。
            on_metadata(metadata)

        if self._use_tip_cloud(profile):
            model_name = self._tip_model(needs_image)
            try:
                # Tip Cloud 支持流式；若配置为非流式则一次性返回。
                if profile.stream:
                    async for chunk in self._tip_cloud_stream_chat(payload, profile, model=model_name):
                        yield chunk
                else:
                    text = await self._tip_cloud_complete(payload, profile, model=model_name)
                    if text:
                        yield text
            except LLMProviderUnavailableError as exc:
                logger.warning('llm.tip_cloud_unavailable', error=str(exc))
                yield 'Tip Cloud 接入暂不可用，请稍后重试。'
            except Exception as exc:
                logger.warning('llm.stream_chat_failed', provider='tip_cloud', error=str(exc))
                yield 'LLM 服务暂不可用，请稍后重试。'
            return
        elif self._use_static_openai(profile):
            try:
                # 通过 OpenAI SDK 流式读取。
                async for chunk in self._static_openai_stream_chat(payload, profile):
                    yield chunk
            except LLMProviderUnavailableError as exc:
                logger.warning('llm.openai_unavailable', error=str(exc))
                yield 'OpenAI 接入暂不可用，请检查配置后重试。'
            except Exception as exc:
                logger.warning('llm.stream_chat_failed', provider='static_openai', error=str(exc))
                yield 'LLM 服务暂不可用，请稍后重试。'
            return
        elif self._use_ollama(profile):
            user_content = payload['messages'][1]['content']
            try:
                # Ollama 不同接口的 stream/non-stream 分支。
                if profile.stream:
                    async for chunk in self._ollama_stream_chat(metadata.system_prompt, user_content, profile):
                        yield chunk
                else:
                    text = await self._ollama_complete(metadata.system_prompt, user_content, profile)
                    if text:
                        yield text
            except LLMProviderUnavailableError as exc:
                logger.warning('llm.ollama_unavailable', error=str(exc))
                yield '本地 Ollama 服务未启动，请启动 Ollama 后重试。'
            except Exception as exc:
                logger.warning('llm.stream_chat_failed', error=str(exc))
                yield 'LLM 服务暂不可用，请稍后重试。'
            return

        # 兜底：未知 provider。
        logger.warning('llm.stream_chat_failed', error='unsupported llm provider')
        yield 'LLM 服务暂不可用，请稍后重试。'

    async def probe_image_capability(self, profile_id: Optional[str] = None) -> LLMImageProbeResult:
        # 向当前视觉模型发送 1x1 PNG，验证是否接受图片输入。
        settings = self._settings_manager.get_settings()
        profile: Optional[LLMProfile] = None
        if profile_id:
            for candidate in settings.llmProfiles:
                if candidate.id == profile_id:
                    profile = candidate
                    break
            if profile is None:
                raise KeyError(profile_id)
        else:
            profile = self._get_active_vlm_profile(settings, required=False)
            if profile is None:
                raise LLMProviderUnavailableError('未设置视觉模型，请在设置中选择 VLM。')

        provider = (profile.provider or 'tip_cloud').lower()
        if provider == 'tip_cloud':
            model_name = 'VLM'
        elif provider == 'ollama':
            model_name = profile.ollamaModel or profile.model
        else:
            model_name = profile.apiModel or profile.model
        system_prompt = (
            'You are running a diagnostics check to verify whether the current model accepts image inputs.\n'
            'If you can read the attached image, briefly acknowledge it.'
        )
        user_content = self._compose_user_content(
            '这是一张 1x1 像素的图像，用于检测是否支持视觉输入。请用一句话确认你已接收图像。',
            PROBE_IMAGE_DATA_URL,
        )
        payload = {
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_content},
            ],
        }
        response_preview: Optional[str] = None
        error_message: Optional[str] = None
        supports_image = False

        try:
            if self._use_tip_cloud(profile):
                # Tip Cloud 只要调用成功即视为支持图片。
                response_preview = await self._tip_cloud_complete(payload, profile, model='VLM')
                supports_image = True
            elif self._use_static_openai(profile):
                response_preview = await self._static_openai_complete(payload, profile)
                supports_image = True
            elif self._use_ollama(profile):
                response_preview = await self._ollama_complete(system_prompt, user_content, profile)
                supports_image = True
            else:
                error_message = '当前 LLM provider 未被支持'
        except httpx.HTTPStatusError as exc:
            error_message = self._format_http_error(exc)
            logger.warning(
                'llm.image_probe_failed',
                status_code=exc.response.status_code if exc.response else None,
                error=error_message,
            )
        except LLMProviderUnavailableError as exc:
            error_message = str(exc)
        except Exception as exc:
            error_message = str(exc)
            logger.warning('llm.image_probe_failed', error=error_message)

        # 仅截取预览前 200 个字符，避免 UI 被长回复撑开。
        preview = (response_preview or '').strip()
        return LLMImageProbeResult(
            supports_image=supports_image,
            provider=provider,
            model=model_name,
            profile_id=profile.id if profile else None,
            error_message=error_message,
            response_preview=preview[:200] if preview else None,
        )

    def _format_http_error(self, exc: httpx.HTTPStatusError) -> str:
        # 优先解析 JSON error 字段，其次返回纯文本。
        response = exc.response
        if response is None:
            return str(exc)
        try:
            data = response.json()
        except ValueError:
            data = None
        if isinstance(data, dict):
            error = data.get('error')
            if isinstance(error, dict):
                detail = error.get('message') or error.get('detail')
                if detail:
                    # 优先展示后端返回的 message/detail 字段。
                    return detail
            elif isinstance(error, str) and error:
                return error
        text = response.text.strip()
        if text:
            return text
        return str(exc)

    async def _static_openai_complete(self, payload: Dict[str, Any], profile: LLMProfile) -> str:
        # 仅包装为非流式 OpenAI 调用，便于复用。
        return await self._openai_complete(payload, profile)

    async def _static_openai_stream_chat(
        self,
        payload: Dict[str, Any],
        profile: LLMProfile,
    ) -> AsyncGenerator[str, None]:
        # 静态 OpenAI 直接复用通用流式实现。
        async for chunk in self._openai_stream_chat(payload, profile):
            yield chunk

    async def _tip_cloud_complete(self, payload: Dict[str, Any], profile: LLMProfile, *, model: str) -> str:
        # 两次机会：第一次凭现有 token，失败再强制刷新。
        for attempt in range(2):
            force_refresh = attempt == 1
            headers = await self._tip_headers(force_refresh=force_refresh)
            # Authorization 仅用于 token，本地 openai SDK 需剥离后作为 key。
            device_headers = {
                k: v for k, v in headers.items() if k.lower() != 'authorization'
            }
            raw_token = headers.get('Authorization', '').removeprefix('Bearer ').strip()
            if not raw_token:
                if not force_refresh:
                    continue
                raise LLMProviderUnavailableError('Tip Cloud 设备 token 不可用，请重试。')
            try:
                # 将 tip cloud 的 token + headers 注入到 OpenAI 兼容接口。
                return await self._openai_complete(
                    payload,
                    profile,
                    model_override=model,
                    base_url_override=tip_cloud_base_url(),
                    api_key_override=raw_token,
                    extra_headers=device_headers,
                )
            except (AuthenticationError, APIStatusError) as exc:
                if self._is_auth_error(exc) and not force_refresh:
                    continue
                raise
            except LLMProviderUnavailableError:
                raise
            except Exception as exc:
                if self._is_auth_error(exc) and not force_refresh:
                    continue
                raise

    async def _tip_cloud_stream_chat(
        self,
        payload: Dict[str, Any],
        profile: LLMProfile,
        *,
        model: str,
    ) -> AsyncGenerator[str, None]:
        # 与 _tip_cloud_complete 一致的鉴权重试逻辑，改为流式。
        for attempt in range(2):
            force_refresh = attempt == 1
            headers = await self._tip_headers(force_refresh=force_refresh)
            # 与非流式相同的 token 处理，保持 header 一致性。
            device_headers = {
                k: v for k, v in headers.items() if k.lower() != 'authorization'
            }
            raw_token = headers.get('Authorization', '').removeprefix('Bearer ').strip()
            if not raw_token:
                if not force_refresh:
                    continue
                raise LLMProviderUnavailableError('Tip Cloud 设备 token 不可用，请重试。')
            try:
                async for chunk in self._openai_stream_chat(
                    payload,
                    profile,
                    model_override=model,
                    base_url_override=tip_cloud_base_url(),
                    api_key_override=raw_token,
                    extra_headers=device_headers,
                ):
                    yield chunk
                return
            except (AuthenticationError, APIStatusError) as exc:
                if self._is_auth_error(exc) and not force_refresh:
                    continue
                raise
            except LLMProviderUnavailableError:
                raise
            except Exception as exc:
                if self._is_auth_error(exc) and not force_refresh:
                    continue
                raise

    async def _iter_stream_chunks(self, response: httpx.Response) -> AsyncGenerator[str, None]:
        # 解析 SSE 样式的 data: 行，并提取 delta 内容。
        async for raw_line in response.aiter_lines():
            if not raw_line:
                continue
            # 跳过非 data 开头的 keep-alive。
            if not raw_line.startswith('data:'):
                continue
            data = raw_line.partition('data:')[2].strip()
            # 兼容 OpenAI [DONE] 哨兵。
            if not data or data == '[DONE]':
                continue
            try:
                payload = json.loads(data)
                choices = payload.get('choices') or []
                if not choices:
                    continue
                delta = choices[0].get('delta') or {}
                text = self._normalize_message_fragment(delta.get('content'))
                if text:
                    yield text
            except json.JSONDecodeError:
                logger.debug('llm.stream_chunk_parse_failed', chunk=data[:80])

    def _convert_openai_response(self, payload: Any) -> Dict[str, Any]:
        # openai SDK 对象与 dict 均可转换为统一结构。
        if hasattr(payload, 'model_dump'):
            return payload.model_dump()
        if isinstance(payload, dict):
            return payload
        return {}

    def _extract_openai_stream_text(self, chunk: Any) -> str:
        # 从 OpenAI 流式 delta 中获取字符串片段。
        payload = self._convert_openai_response(chunk)
        choices = payload.get('choices') or []
        if not choices:
            return ''
        delta = choices[0].get('delta') or {}
        return self._normalize_message_fragment(delta.get('content'))

    def _build_openai_request(
        self,
        payload: Dict[str, Any],
        profile: LLMProfile,
        *,
        model_override: Optional[str] = None,
    ) -> tuple[Dict[str, Any], float]:
        # 统一构建 ChatCompletion 参数，同时返回超时秒数。
        messages = payload.get('messages') or []
        model_name = model_override or profile.apiModel or profile.model
        if self._use_static_openai(profile) and not model_override:
            model_name = profile.openaiModel or profile.model or model_name
        request_body: Dict[str, Any] = {
            'model': model_name,
            'messages': messages,
            'temperature': profile.temperature,
            'max_tokens': profile.maxTokens,
            # 明确关闭 reasoning，避免兼容性问题。
            'extra_body': {'reasoning': {'enabled': False}},
        }
        # openai SDK 超时单位为秒，确保至少 1 秒。
        timeout = max(profile.timeoutMs / 1000, 1.0)
        return request_body, timeout

    async def _openai_complete(
        self,
        payload: Dict[str, Any],
        profile: LLMProfile,
        *,
        model_override: Optional[str] = None,
        base_url_override: Optional[str] = None,
        api_key_override: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> str:
        # 通用的非流式 ChatCompletion 调用。
        client = self._build_openai_client(
            profile,
            base_url_override=base_url_override,
            api_key_override=api_key_override,
            extra_headers=extra_headers,
        )
        request_body, timeout = self._build_openai_request(payload, profile, model_override=model_override)
        response = await client.chat.completions.create(**request_body, timeout=timeout)
        data = self._convert_openai_response(response)
        return self._extract_message_content(data)

    async def _openai_stream_chat(
        self,
        payload: Dict[str, Any],
        profile: LLMProfile,
        *,
        model_override: Optional[str] = None,
        base_url_override: Optional[str] = None,
        api_key_override: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> AsyncGenerator[str, None]:
        # 通用的流式 ChatCompletion 调用，封装 stream/non-stream 分支。
        client = self._build_openai_client(
            profile,
            base_url_override=base_url_override,
            api_key_override=api_key_override,
            extra_headers=extra_headers,
        )
        request_body, timeout = self._build_openai_request(payload, profile, model_override=model_override)
        if profile.stream:
            # SDK 的 stream 为异步迭代器，逐块提取 delta。
            stream = await client.chat.completions.create(**request_body, stream=True, timeout=timeout)
            async for chunk in stream:
                text = self._extract_openai_stream_text(chunk)
                if text:
                    yield text
        else:
            # 非流式模式下仍使用相同接口，保持行为一致。
            response = await client.chat.completions.create(**request_body, timeout=timeout)
            data = self._convert_openai_response(response)
            text = self._extract_message_content(data)
            if text:
                yield text

    def _build_openai_client(
        self,
        profile: LLMProfile,
        *,
        base_url_override: Optional[str] = None,
        api_key_override: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> AsyncOpenAI:
        # 构造 openai SDK 客户端，补齐 base_url 与 headers。
        api_key = api_key_override or self._resolve_openai_api_key(profile)
        base_url = (base_url_override or self._openai_base_url(profile)).rstrip('/')
        if not api_key:
            raise LLMProviderUnavailableError('未配置 OpenAI API Key，请在设置中填写。')
        if not base_url:
            raise LLMProviderUnavailableError('未配置 OpenAI Base URL，请在设置中填写。')
        headers = profile.headers.to_dict()
        if extra_headers:
            # tip cloud 的设备 header 与用户 header 合并。
            headers.update(extra_headers)
        client_kwargs: Dict[str, Any] = {'api_key': api_key, 'base_url': base_url}
        if headers:
            client_kwargs['default_headers'] = headers
        return AsyncOpenAI(**client_kwargs)

    def _resolve_openai_api_key(self, profile: LLMProfile) -> str:
        # 多来源依次回退：配置字段、环境变量、Header。
        header_auth = profile.headers.to_dict().get('Authorization', '')
        candidates = [
            (profile.apiKey or '').strip(),
            os.environ.get('TIP_OPENAI_API_KEY', '').strip(),
            os.environ.get('OPENAI_API_KEY', '').strip(),
            header_auth.strip(),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            if candidate.lower().startswith('bearer '):
                # openai SDK 不需要 Bearer 前缀，提前剥离。
                candidate = candidate.split(' ', 1)[1].strip()
            if candidate:
                return candidate
        return ''

    def _openai_base_url(self, profile: LLMProfile) -> str:
        # openaiBaseUrl 优先，其次回退到通用 baseUrl。
        candidate = (profile.openaiBaseUrl or '').strip()
        if candidate:
            return candidate.rstrip('/')
        fallback = (profile.baseUrl or '').strip()
        if fallback:
            return fallback.rstrip('/')
        return ''

    async def _ollama_stream_chat(
        self,
        system_prompt: str,
        user_content: List[Dict[str, Any]],
        profile: LLMProfile,
    ) -> AsyncGenerator[str, None]:
        # 使用 Ollama chat 流式接口，逐行解析 SSE。
        await self._ensure_ollama_ready(profile)
        messages = self._build_ollama_messages(system_prompt, user_content)
        payload = {
            'model': profile.model,
            'messages': messages,
            'stream': True,
            'options': self._ollama_options(profile),
        }
        timeout = profile.timeoutMs / 1000
        chat_url = self._ollama_chat_url(profile)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream('POST', chat_url, json=payload) as response:
                response.raise_for_status()
                async for chunk in self._iter_ollama_stream(response):
                    yield chunk

    async def _ollama_complete(
        self,
        system_prompt: str,
        user_content: List[Dict[str, Any]],
        profile: LLMProfile,
    ) -> str:
        # 非流式 Ollama 调用，返回完整文本。
        await self._ensure_ollama_ready(profile)
        messages = self._build_ollama_messages(system_prompt, user_content)
        payload = {
            'model': profile.model,
            'messages': messages,
            'stream': False,
            'options': self._ollama_options(profile),
        }
        timeout = profile.timeoutMs / 1000
        chat_url = self._ollama_chat_url(profile)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(chat_url, json=payload)
            response.raise_for_status()
            data = response.json()
            return self._extract_ollama_text(data)

    async def _ensure_ollama_ready(self, profile: LLMProfile) -> None:
        # 简单健康检查，确保本地服务已启动。
        base_url = self._ollama_base_url(profile)
        health_url = f'{base_url}/api/version'
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                response.raise_for_status()
        except Exception as exc:
            # 将原始异常包装为用户可读的提示。
            raise LLMProviderUnavailableError('本地 Ollama 服务未启动，请先启动服务后重试。') from exc

    async def _iter_ollama_stream(self, response: httpx.Response) -> AsyncGenerator[str, None]:
        # Ollama 流返回每行 JSON，需要过滤 done 标记。
        async for raw_line in response.aiter_lines():
            if not raw_line:
                continue
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError:
                logger.debug('llm.ollama_stream_parse_failed', chunk=raw_line[:80])
                continue
            if payload.get('done'):
                # Ollama 会发送 done=true 的终止消息。
                continue
            message = payload.get('message') or {}
            text = message.get('content')
            if text:
                yield text

    def _build_ollama_messages(
        self,
        system_prompt: str,
        user_content: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        # 将 OpenAI 风格的 content 转换为 Ollama 兼容格式。
        text, images = self._split_user_content(user_content)
        normalized_text = text or '请结合提供的截图理解用户意图。'
        user_message: Dict[str, Any] = {'role': 'user', 'content': normalized_text}
        if images:
            # Ollama 使用单独的 images 字段传递 base64。
            user_message['images'] = images
        return [
            {'role': 'system', 'content': system_prompt},
            user_message,
        ]

    def _split_user_content(self, user_content: List[Dict[str, Any]]) -> tuple[str, List[str]]:
        # 分离文本与图片 payload；图片保留原始 data URL。
        texts: List[str] = []
        images: List[str] = []
        for part in user_content:
            part_type = part.get('type')
            if part_type == 'text':
                text_value = part.get('text')
                if text_value:
                    texts.append(text_value)
            elif part_type == 'image_url':
                raw_url = (part.get('image_url') or {}).get('url')
                if raw_url:
                    images.append(self._normalize_image_payload(raw_url))
        joined_text = '\n\n'.join(texts).strip()
        # 文本片段按空行分隔，保持语义清晰。
        return joined_text, images

    def _normalize_image_payload(self, reference: str) -> str:
        # 对 data URL 去掉前缀，仅保留 base64 内容。
        if reference.startswith('data:'):
            _, _, payload = reference.partition(',')
            return payload or reference
        return reference

    def _extract_ollama_text(self, payload: Dict[str, Any]) -> str:
        # Ollama 返回 message.content 或 response 字段。
        message = payload.get('message') or {}
        content = message.get('content')
        if content:
            return content.strip()
        fallback = payload.get('response')
        if isinstance(fallback, str):
            return fallback.strip()
        return ''

    def _ollama_options(self, profile: LLMProfile) -> Dict[str, Any]:
        # 选项与 profile 对齐，统一温度/生成长度。
        return {
            'temperature': profile.temperature,
            'num_predict': profile.maxTokens,
            # 未来可按需追加其他 Ollama 配置。
        }

    def _use_ollama(self, profile: LLMProfile) -> bool:
        # provider=ollama
        return (profile.provider or 'tip_cloud').lower() == 'ollama'

    def _use_tip_cloud(self, profile: LLMProfile) -> bool:
        # provider=tip_cloud
        return (profile.provider or 'tip_cloud').lower() == 'tip_cloud'

    def _is_auth_error(self, exc: Exception) -> bool:
        # 统一判定鉴权错误，便于重刷 token。
        status = getattr(exc, 'status_code', None) or getattr(exc, 'http_status', None)
        if status in {401, 403}:
            return True
        text = str(exc).lower()
        return 'unauthorized' in text or 'invalid api key' in text or 'permission' in text

    def _ollama_base_url(self, profile: LLMProfile) -> str:
        # 默认为本地 11434 端口。
        base = profile.ollamaBaseUrl or 'http://127.0.0.1:11434'
        return base.rstrip('/')

    def _ollama_chat_url(self, profile: LLMProfile) -> str:
        # 拼出 chat API 地址。
        return f'{self._ollama_base_url(profile)}/api/chat'

    async def ensure_ollama_available(self) -> None:
        # 给外部路由调用的健康检查封装。
        settings = self._settings_manager.get_settings()
        profile = self._get_active_llm_profile(settings)
        await self._ensure_ollama_ready(profile)

    def _resolve_language_code(self, override: Optional[str], settings: Settings) -> str:
        # 支持系统/显式语言；默认回退中文。
        candidate = (override or settings.language or '').strip()
        if not candidate or candidate == 'system':
            # 默认中文
            return 'zh-CN'
        lower = candidate.lower()
        if lower.startswith('en'):
            return 'en-US'
        if lower.startswith('zh'):
            return 'zh-CN'
        # 其他值直接透传，交由上游判断。
        return candidate

    def _language_label(self, code: str) -> str:
        # 主要用于提示文案，非标准化语言代码。
        lower = code.lower()
        if lower.startswith('en'):
            return 'English'
        if lower.startswith('zh'):
            return '中文'
        return code or '中文'

    def _use_static_openai(self, profile: LLMProfile) -> bool:
        # provider=static_openai
        return (profile.provider or 'tip_cloud').lower() == 'static_openai'
