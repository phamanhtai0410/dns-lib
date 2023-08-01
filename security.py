# -*- coding: utf-8 -*-
"""
   Description:
        -
        -
"""
import base64
import hashlib
import json
import traceback
from datetime import timezone
from functools import wraps
from urllib.parse import urlparse

import jwt
import werkzeug
import sentry_sdk
from eth_account.messages import defunct_hash_message
from flask import request, g, current_app
from pydash import get
from marshmallow import Schema
from bson import json_util
from sentry_sdk import capture_exception

from .exception import BadRequest, Forbidden
from .utils import util_web3, dt_utcnow


def auth_error_callback(status_code):
    if status_code == 403:
        return {
            "me"
        }


def auth_token_key(user: str, subdomain: str) -> str:
    if not subdomain:
        subdomain = 'innovaz'
    return f'inzdapp:tokens:{subdomain}:{user}'


def auth_api_key(api_key: str) -> str:
    return f'inzdapp:api_keys:{api_key}'


class HTTPSecurity:
    def __init__(self, redis, *args, **kwargs):
        self.redis = redis
        pass

    def get_token_info(self, token):
        try:
            return jwt.decode(token, algorithm="RS256", options={"verify_signature": False})
        except:
            traceback.print_exc()
            capture_exception()
            return False

    def get_api_key(self) -> str:
        return request.headers.get('apikey')

    def get_token(self):
        _rq_token = request.headers.get('Authorization')

        if not _rq_token or 'Bearer ' not in _rq_token:
            _rq_token = request.args.get('access_token', type=str)
            if not _rq_token:
                return None, None
        else:
            _rq_tokens = _rq_token.split(' ')
            if len(_rq_tokens) < 1:
                return None, None
            _rq_token = _rq_tokens[1]

        # Get pos token on Redis pos info
        _data = self.get_token_info(_rq_token)
        if not isinstance(_data, dict):
            return None, None
        if not _data.get('payload'):
            return None, None

        return _data.get('payload'), _rq_token

    def verify_token(self, subdomain):

        try:
            _token_info, _rq_token = self.get_token()

            if not _token_info:
                return False

            _token_subdomain = get(_token_info, 'subdomain')
            if _token_subdomain != subdomain:
                return False

            # _token_existed = self.redis.get(auth_token_key(user=get(_token_info, 'user._id')))
            #
            # if not _token_existed or _token_existed != _rq_token:
            #     return False

            return _token_info
        except:
            sentry_sdk.capture_exception()
            traceback.print_exc()
            return False

    def checksum(self, secret_key, data: dict, code):
        _keys = list(data.keys())
        _keys.sort()
        _ms = ','.join([f'{key}:{data[key]}' for key in _keys])
        _request_hash = hashlib.md5(
            (secret_key + _ms).encode()).hexdigest()
        return _request_hash == code

    def verify_api_key(self, data):

        try:
            _api_key = self.get_api_key()

            if not _api_key:
                return None

            _info = self.redis.get(auth_api_key(api_key=_api_key))
            print('_info', _info)
            if not _info:
                return False

            _info = json.loads(_info)
            if not self.checksum(secret_key=_info.get('secret_key'), data=data, code=request.args.get('code')):
                return False

            return _info
        except:
            sentry_sdk.capture_exception()
            traceback.print_exc()
        return False

    def ensure_sync(self, f):
        try:
            return current_app.ensure_sync(f)
        except AttributeError:  # pragma: no cover
            return f

    def _verify_data(self, f=None, schema=None, response=None):
        def verify_data_internal(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                return self.ensure_sync(f)(*args, **kwargs)

            return decorated

        if f:
            return verify_data_internal(f)
        return verify_data_internal

    def get_user_roles(self, user):
        return get(user, 'roles', default=[])

    def get_headers(self):
        return dict(request.headers)

    def authorize(self, role, user):
        if role is None:
            return True
        if isinstance(role, (list, tuple)):
            roles = role
        else:
            roles = [role]

        user_roles = self.ensure_sync(self.get_user_roles)(user)
        if user_roles is None:
            user_roles = {}
        elif not isinstance(user_roles, (list, tuple)):
            user_roles = {user_roles}
        else:
            user_roles = set(user_roles)
        for role in roles:
            if isinstance(role, (list, tuple)):
                role = set(role)
                if role & user_roles == role:
                    return True
            elif role in user_roles:
                return True

    def get_subdomain(self):  # Update according to domain
        try:
            _rq_host = get(request.headers, 'Origin') or get(request.headers, 'origin')
            # print("** Header debug subdomain : ", dict(request.headers))
            if _rq_host:
                _rq_host = _rq_host.replace('https://', '')
                _lt = _rq_host.split('.')
                if len(_lt) == 3 and _lt[1] == 'innovaz':
                    return _lt[0].replace('-stag', '')
        except:
            traceback.print_exc()
            pass
        return ""

    def http(self, f=None,
             form_data: Schema = None,
             params: Schema = None,
             response: Schema = None,
             login_required: bool = None,
             roles: list = [],
             pass_login=False,
             is_use_subdomain=False,
             is_blockchain=False,
             is_forward=False,
             api_key=False,
             *args,
             **kwargs):
        #
        """
        :param is_blockchain: (boolean) True if request relevant to nft api
        :param is_use_subdomain:
        :param form_data: (marshmallow.Schema) dumps data to dict from body or form
        :param params: (marshmallow.Schema) loads data from params
        :param response: (marshmallow.Schema) loads data from controller
        :param login_required: (boolean) Check if api need to be login
        :param roles: (list) List of user's roles
        :param pass_login: (boolean) Debug param to pass login required
        :param f:
        :return:
        """

        def http_internal(f):
            @wraps(f)
            def decorated(*args, **kwargs):

                res = {
                    'data': {},
                    'errors': [],
                    'msg': '',
                    'error_code': ''
                }

                status = 200
                _data = None
                _user = None
                _subdomain = self.get_subdomain()
                try:

                    # Get subdomain
                    if is_use_subdomain:
                        _params = request.args.to_dict()
                        if 'debug' in _params:
                            if 'subdomain' in _params:
                                _subdomain = _params['subdomain']
                        kwargs['subdomain'] = _subdomain

                    # Get contract
                    if is_blockchain:
                        _contract = request.headers.get('contract')
                        kwargs['contract'] = _contract

                    # Verify request
                    if login_required:
                        _login_info = self.verify_token(subdomain=_subdomain)

                        if not _login_info:
                            if pass_login:
                                kwargs['login_info'] = None
                            else:
                                raise Forbidden(
                                    msg='Please login to continue.',
                                    errors=[{
                                        'token': 'Invalid.'
                                    }]
                                )

                        if roles:
                            _user = get(_login_info, 'user')
                            if not self.authorize(role=roles, user=_user):
                                raise Forbidden(errors=[{
                                    "scope_required": roles
                                }])
                        kwargs['login_info'] = _login_info
                    if api_key:
                        _data = {}
                        if request.method == 'GET':
                            _data = request.args.to_dict()
                            if 'code' not in _data:
                                raise Forbidden(
                                    msg='Failed.',
                                    errors=[{
                                        'code': 'Invalid.'
                                    }]
                                )
                            del _data['code']
                        else:
                            _data = request.json

                        _api_key = self.verify_api_key(_data)

                        if not _api_key:
                            raise Forbidden(
                                msg='Failed.',
                                errors=[{
                                    'api_key': 'Invalid.'
                                }]
                            )

                        kwargs['api_key'] = api_key
                    # Get body data
                    if form_data:

                        if request.content_type and request.content_type.startswith("multipart/form-data"):
                            _data = request.form.to_dict()
                        else:
                            _data = request.json

                        _validate = form_data.validate(_data)
                        if _validate:
                            _errors = _validate if isinstance(_validate, list) else [_validate]
                            raise BadRequest(msg="Invalid data", errors=_errors)
                        _data = form_data.dump(_data)

                        kwargs['form_data'] = _data

                    # Get query params
                    if params:
                        _params = request.args.to_dict()
                        _validate_query = params.validate(_params)
                        if _validate_query:
                            _errors = _validate_query if isinstance(_validate_query, list) else [_validate_query]
                            raise BadRequest(msg="Invalid params", errors=_errors)
                        _params = params.dump(_params)
                        kwargs['params'] = _params

                    _result = self.ensure_sync(f)(*args, **kwargs)
                    if response:
                        _result = response.load(_result)
                    res['data'] = _result

                    if is_forward:
                        res = _result

                except Exception as e:

                    if isinstance(e, werkzeug.wrappers.request.BadRequest):
                        res['msg'] = str(e)
                        status = 400
                        res['error_code'] = 'E_BAD_REQUEST'
                    else:
                        if hasattr(e, 'status_code'):
                            status = e.status_code
                        else:
                            status = 500

                        if hasattr(e, 'msg'):
                            res['msg'] = e.msg
                        else:
                            res['msg'] = "Internal Server Error"

                        if hasattr(e, 'error_code'):
                            res['error_code'] = e.error_code
                        else:
                            res['error_code'] = "E_SERVER"

                        if hasattr(e, 'errors'):
                            res['errors'] = e.errors if isinstance(e.errors, list) else [e.errors]

                        if status == 500:
                            sentry_sdk.capture_exception()
                            traceback.print_exc()

                return res, status

            return decorated

        if f:
            return http_internal(f)
        return http_internal
