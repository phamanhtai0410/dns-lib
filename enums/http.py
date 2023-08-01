# -*- coding: utf-8 -*-
"""
   Description:
        -
        -
"""


class ErrorCode(object):
    BAD_REQUEST = 'BAD_REQUEST'
    REQUIRED_AUTH = 'REQUIRED_AUTH'
    UNKNOWN_ERROR = 'UNKNOWN_ERROR'
    NOT_FOUND = 'NOT_FOUND'


class StatusInt(object):
    Ok = 200
    Bad = 400
    NotFound = 404
    Forbidden = 403
    Unknown = 500


class SortType:
    ASC = 'ASC'
    DESC = 'DESC'
    DEFAULT = 'DEFAULT'
