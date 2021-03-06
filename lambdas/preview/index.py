"""
Preview file types in S3 by returning preview HTML and other metadata from
a lambda function.
"""
import json
import os
from tempfile import NamedTemporaryFile

from jsonschema import Draft4Validator, ValidationError
from nbconvert import HTMLExporter
import nbformat
import pandas as pd
import pyarrow as pa
import requests

WEB_ORIGIN = os.environ['WEB_ORIGIN']


SCHEMA = {
    'type': 'object',
    'properties': {
        'url': {
            'type': 'string'
        },
        'input': {
            'enum': ['ipynb', 'parquet']
        }
    },
    'required': ['url', 'input'],
    'additionalProperties': False
}

Draft4Validator.check_schema(SCHEMA)
VALIDATOR = Draft4Validator(SCHEMA)


def lambda_handler(event, _):
    """
    dynamically handle preview requests for bytes in S3

    caller must specify input_type (since there may be no file extension)
    """
    params = event['queryStringParameters'] or {}
    headers = event['headers'] or {}

    try:
        VALIDATOR.validate(params)
    except ValidationError as ex:
        return {
            "body": ex.message,
            "statusCode": 400
        }

    url = params['url']
    input_type = params.get('input')

    resp = requests.get(url)
    if resp.ok:
        with NamedTemporaryFile() as fd:
            for chunk in resp.iter_content(chunk_size=1024):
                fd.write(chunk)
            fd.seek(0)

            if input_type == 'ipynb':
                html_exporter = HTMLExporter()
                html_exporter.template_file = 'basic'

                notebook = nbformat.read(fd, 4)
                html, _ = html_exporter.from_notebook_node(notebook)
            elif input_type == 'parquet':
                meta = pa.parquet.read_metadata(fd)
                columns = {k.decode():json.loads(meta.metadata[k]) for k in meta.metadata}

                fd.seek(0)
                data = pd.read_parquet(fd.name)
                desc = data.describe().to_dict()
                html = data._repr_html_() # pylint: disable=protected-access
                shape = data.shape
            else:
                assert False

        ret_val = {
            'columns': columns,
            'description': desc,
            'html': html,
            'metadata': meta,
            'shape': shape
        }
    else:
        ret_val = {
            'error': resp.reason
        }

    response_headers = {
        "Content-Type": 'application/json'
    }
    if headers.get('origin') == WEB_ORIGIN:
        response_headers.update({
            'access-control-allow-origin': '*',
            'access-control-allow-methods': 'GET',
            'access-control-allow-headers': '*',
            'access-control-max-age': 86400
        })

    return {
        "statusCode": 200,
        "body": json.dumps(ret_val),
        "headers": response_headers
    }
