
import hashlib
import hmac
import json
import os
import uuid

from flask import Flask, request, abort, jsonify
from github import Github

import requests


AUTH_TOKEN = os.environ.get('AUTH_TOKEN')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
LAMBCI_URL = os.environ.get('LAMBCI_URL')

APP = Flask(__name__)
GITHUB = Github(GITHUB_TOKEN)


@APP.route('/webhooks/contentful/<string:org>/<string:repo>')
@APP.route('/webhooks/contentful/<string:org>/<string:repo>/<string:branch>')
def contentful(org, repo, branch='master'):
    token = request.headers.get('Authorization').replace('Bearer ', '')

    if token != AUTH_TOKEN:
        print('bad token')
        return abort(404)

    real_repo = GITHUB.get_repo("{}/{}".format(org, repo))
    if not real_repo:
        print('no repo')
        return abort(404)

    real_branch = real_repo.get_branch(branch)
    if not real_branch:
        print('no branch')
        return abort(404)

    payload = json.dumps(_build_lambci_payload(real_repo, real_branch)).encode('UTF-8')
    signature = _generate_signature(AUTH_TOKEN, payload)

    req = requests.post(
        '/'.join((LAMBCI_URL, 'lambci', 'webhook')),
        headers={
            'Content-Type': 'application/json',
            'X-GitHub-Event': 'push',
            'X-GitHub-Delivery': str(uuid.uuid4()),
            'X-Hub-Signature': signature,
        },
        data=payload,
    )
    return req.content, req.status_code


def _build_lambci_payload(repo, branch):
    return {
         'ref': 'refs/heads/{}'.format(branch.name),
         'after': branch.commit.sha,
         'created': False,
         'deleted': False,
         'forced': False,
         'before': branch.commit.commit.tree.sha,
         'clone_url': repo.html_url,
         'head_commit': {
             'id': branch.commit.sha,
             'message': branch.commit.commit.message,
         },
         'pusher': {
             'name': branch.commit.commit.author.name,
             'username': branch.commit.author.login,
         },
         'repository': {
             'full_name': repo.full_name,
             'private': repo.private,
         },
    }


def _generate_signature(secret, payload):
    return '='.join((
        'sha1',
        hmac.new(secret.encode('utf-8'), payload, hashlib.sha1).hexdigest()
    ))


if __name__ == "__main__":
    APP.run(debug=True)
