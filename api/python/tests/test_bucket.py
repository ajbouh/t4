import json
from mock import patch
from urllib.parse import urlparse

try:
    import unittest.mock as mock
except ImportError:
    import mock

import botocore.session
from botocore.stub import Stubber
import pandas as pd
import pytest

from t4 import Bucket
from t4.data_transfer import s3_client
from t4.util import QuiltException

def test_bucket_construct():
    bucket = Bucket('s3://test-bucket')

def test_bucket_meta():
    with Stubber(s3_client) as stubber:
        test_meta = {
            'helium': json.dumps({'target': 'json'})
        }
        response = {
            'Metadata': test_meta,
            'ContentLength': 123
        }
        params = {
            'Bucket': 'test-bucket',
            'Key': 'test'
        }
        stubber.add_response('head_object', response, params)
        bucket = Bucket('s3://test-bucket')
        meta = bucket.get_meta('test')
        assert meta == {'target': 'json'}


        head_meta = {
            'helium': json.dumps({"target": "json"})
        }
        head_response = {
            'Metadata': head_meta,
            'ContentLength': 123
        }
        head_params = {
            'Bucket': 'test-bucket',
            'Key': 'test'
        }
        stubber.add_response('head_object', head_response, head_params)
        new_test_meta = {
            'helium': json.dumps({
                'target': 'json',
                'user_meta': {}
            })
        }
        response = {}
        params = {
            'CopySource': {
                'Bucket': 'test-bucket',
                'Key': 'test'
            },
            'Bucket': 'test-bucket',
            'Key': 'test',
            'Metadata': new_test_meta,
            'MetadataDirective': 'REPLACE'
        }
        stubber.add_response('copy_object', response, params)
        bucket.set_meta('test', {})

def test_bucket_fetch():
    with Stubber(s3_client) as stubber:
        response = {
            'IsTruncated': False
        }
        params = {
            'Bucket': 'test-bucket',
            'Prefix': 'does/not/exist/'
        }
        stubber.add_response('list_objects_v2', response, params)
        with pytest.raises(QuiltException):
            Bucket('s3://test-bucket').fetch('does/not/exist/', './')


def test_bucket_select():
    # Stubber doesn't have an accurate shape for the results of select_object_content
    chunks = [
        b'{"foo": ',
        b'9, "b',
        b'ar": 3',
        b'}\n{"foo"',
        b': 9, "bar": 1}\n{"foo": 6, "bar": 9}\n{"foo":',
        b' 1, "bar": 7}\n{"foo":',
        b' 6, "bar": 1}\n{"foo": 6, "bar": 6}',
        b'\n{"foo": 9, "bar": 6}',
        b'\n{"foo": 6, "bar": 4}\n',
        b'{"foo": 2, "bar": 0}',
        b'\n{"foo": 2, "bar": 0}\n',
        ]
    records = [{'Records': {'Payload': chunk}} for chunk in chunks]
    # noinspection PyTypeChecker
    records.append({'Stats': {
        'BytesScanned': 100,
        'BytesProcessed': 100,
        'BytesReturned': 210,
        }})
    records.append({'End': {}})

    expected_result = pd.DataFrame.from_records([
        {'foo': 9, 'bar': 3},
        {'foo': 9, 'bar': 1},
        {'foo': 6, 'bar': 9},
        {'foo': 1, 'bar': 7},
        {'foo': 6, 'bar': 1},
        {'foo': 6, 'bar': 6},
        {'foo': 9, 'bar': 6},
        {'foo': 6, 'bar': 4},
        {'foo': 2, 'bar': 0},
        {'foo': 2, 'bar': 0},
        ])

    # test normal use from extension
    expected_args = {
        'Bucket': 'test-bucket',
        'Key': 'test',
        'Expression': 'select * from S3Object',
        'ExpressionType': 'SQL',
        'InputSerialization': {
            'CompressionType': 'NONE',
            'JSON': {'Type': 'DOCUMENT'}
            },
        'OutputSerialization': {'JSON': {}},
        }

    test_meta = {
        'helium': json.dumps({'target': 'json'})
    }
    response = {
        'Metadata': test_meta,
        'ContentLength': 123
    }
    params = {
        'Bucket': 'test-bucket',
        'Key': 'test'
    }

    with Stubber(s3_client) as stubber:
        stubber.add_response('head_object', response, params)

        boto_return_val = {'Payload': iter(records)}
        patched_s3 = patch.object(
            s3_client,
            'select_object_content',
            return_value=boto_return_val,
            autospec=True,
        )

        with patched_s3 as patched:
            bucket = Bucket('s3://test-bucket')

            result = bucket.select('test', 'select * from S3Object')

            patched.assert_called_once_with(**expected_args)
            assert result.equals(expected_result)

    # Further testing specific to select() is in test_data_transfer


def test_bucket_put():
    with patch("t4.bucket.copy_file") as copy_mock:
        bucket = Bucket('s3://test-bucket')
        bucket.put_file(key='README.md', path='./README') # put local file to bucket
        copy_src = copy_mock.call_args_list[0][0][0]
        assert urlparse(copy_src).scheme == 'file'
        copy_dest = copy_mock.call_args_list[0][0][1]
        assert urlparse(copy_dest).scheme == 's3'


@patch('t4.data_transfer.s3_client')
def test_remote_delete(s3_client):
    bucket = Bucket('s3://test-bucket')
    bucket.delete('file.json')
    call_kwargs = {'Bucket': 'test-bucket', 'Key': 'file.json'}
    s3_client.head_object.assert_called_with(**call_kwargs)
    s3_client.delete_object.assert_called_with(**call_kwargs)

    with pytest.raises(QuiltException):
        bucket.delete('s3://test-bucket/dir/')


@patch('t4.data_transfer.s3_client')
def test_remote_delete_dir(s3_client):
    s3_client.list_objects_v2.return_value = {
        'IsTruncated': False,
        'Contents': [{'Key': 'a'}, {'Key': 'b'}],
    }
    bucket = Bucket('s3://test-bucket')
    bucket.delete_dir('s3://test-bucket/dir/')

    a_kwargs = {'Bucket': 'test-bucket', 'Key': 'a'}
    b_kwargs = {'Bucket': 'test-bucket', 'Key': 'b'}
    s3_client.delete_object.assert_any_call(**a_kwargs)
    s3_client.delete_object.assert_any_call(**b_kwargs)

    with pytest.raises(ValueError):
        bucket.delete_dir('s3://test-bucket/dir')
