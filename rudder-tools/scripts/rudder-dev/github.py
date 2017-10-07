import sys
import json
import re
import requests # apt-get install python-requests || pip install requests
from dateutil.parser import parse

# trick to make fake import compatible with regular import
if 'Config' not in vars():
  from common import *
      
Config.HUB_CONFIG_FILE = "~/.config/hub"
Config.PR_VALIDATED_LABEL = "Ready for merge"
Config.PR_VALIDATED_COLOR = "0e8a16"
Config.BOT_CANNOT_MERGE_LABEL = "qa: Can't merge"
Config.BOT_CANNOT_MERGE_COLOR = "ededed"
Config.PR_TOO_OLD_LABEL = "Very old PR"
Config.PR_TOO_OLD_COLOR = "d93f0b"

class PR:
  """A Pull Request"""
  def __init__(self, url):
    self.url = url
    self.info = None
    match = re.search(r'.*?://.*?/(.*?)/(.*?)/pull/(\d+)', url)
    if match:
      self.id = match.group(3)
      self.repo_name = match.group(2)
      self.upstream = match.group(1)
    else:
      raise ValueError("BUG: not a valid PR URL")

  def is_labeled(self, label):
    """Tell if the pull request is labeled with label"""
    url = "https://api.github.com/repos/Normation/{repo}/issues/{pr_id}/labels"
    label_list = github_request(url, None, self.url, repo=self.repo_name)
    labels = [x['name'] for x in label_list]
    return label in labels

  def _request_pr(self):
    if self.info is not None:
      return
    url = "https://api.github.com/repos/Normation/{repo}/pulls/{pr_id}"
    self.info = github_request(url, None, self.url, repo=self.repo_name)

  def repo(self):
    self._request_pr()
    return self.info['head']['repo']['ssh_url']

  def remote_branch(self):
    self._request_pr()
    return self.info['head']['ref']

  def base_branch(self):
    self._request_pr()
    return self.info['base']['ref']

  def author(self):
    self._request_pr()
    return self.info['user']['login']

  def title(self):
    self._request_pr()
    return self.info['title']

  def mergeable(self):
    self._request_pr()
    return self.info['mergeable']

  def _commits(self):
    self._request_pr()
    self.commits = github_call(self.info['commits_url'])

  def commits_titles(self):
    self._commits()
    return [ x['commit']['message'] for x in self.commits ]

  def comment(self, comment):
    url = "https://api.github.com/repos/Normation/{repo}/issues/{pr_id}/comments"
    data = { "body": comment }
    github_request(url, "Posting comment", self.url, json.dumps(data), repo=self.repo_name)

  def label(self, label):
    url = "https://api.github.com/repos/Normation/{repo}/issues/{pr_id}/labels"
    data = [ label ]
    github_request(url, "Changing label", self.url, json.dumps(data), repo=self.repo_name)

  def unlabel(self, label):
    # We need to check if the label exists before removing it
    get_labels_url = "https://api.github.com/repos/Normation/{repo}/issues/{pr_id}/labels"
    existing_labels = github_request(get_labels_url, "Getting labels", self.url, None, self.repo_name, "GET")
    if label in [ lab["name"] for lab in existing_labels]:
      remove_label_url = get_labels_url+"/"+label
      github_request(remove_label_url, "Removing label", self.url, None, self.repo_name, "DELETE")

  def close(self, message=None):
    if message is not None:
      self.comment(message)
    url = "https://api.github.com/repos/Normation/{repo}/pulls/{pr_id}"
    data = { "state": "closed" }
    github_request(url, "Closing PR", self.url, json.dumps(data), self.repo_name, "PATCH")

  # comments can be issue comments or review comments
  def get_comments(self):
    comments = []
    # Issue comments
    url = "https://api.github.com/repos/Normation/{repo}/issues/{pr_id}/comments"
    icomments = github_request(url, None, self.url, repo=self.repo_name)
    for c in icomments:
      comments.append({
            "date": parse(c['updated_at'], ignoretz=True),
            "author": c['user']['login'],
            "body": c['body'],
          })
    # Review comments
    url = "https://api.github.com/repos/Normation/{repo}/pulls/{pr_id}/reviews"
    pcomments = github_request(url, None, self.url, repo=self.repo_name)
    for c in pcomments:
      comments.append({
          "date": parse(c['submitted_at'], ignoretz=True),
          "author": c['user']['login'],
          "body": c['body'],
          })
    return comments


# Get github user as used by the hub command
def get_github_user():
  user_data=github_call("https://api.github.com/user")
  if 'login' in user_data:
    return user_data['login']
  else:
    logfail("Github user not found")
    exit(6)


# Get github token as used by the hub command
def get_github_token(can_fail=False):
  if Config.GITHUB_TOKEN is not None:
    return Config.GITHUB_TOKEN
  if os.path.isfile(os.path.expanduser(Config.HUB_CONFIG_FILE)):
    with open(os.path.expanduser(Config.HUB_CONFIG_FILE)) as f:
      for line in f:
        match = re.search(r'oauth_token: (\w+)', line)
        if match:
          return match.group(1)
  if can_fail:
    return None
  else:
    logfail("Github user not found")
    exit(6)


# query github
def github_request(api_url, comment, pr_url=None, post_data=None, repo=None, method=None):
  pr_id = None
  if pr_url is not None:
    # Validate PR url
    match = re.match(r'^http.*/(\d+)(/files|/commits)?$', pr_url)
    if match:
      pr_id = match.group(1)
    else:
      print("Can't find pull-request ID, you should warn the reviewer that you updated the pull-request")
      return False

  # get connection info
  if repo is None:
    repo = remote_repo()
  url = api_url.format(repo=repo, pr_id=pr_id)

  # Say what we are doing
  if comment is not None:
    print(comment)
    call_on = ""
    if pr_url is not None:
      call_on = "for " + pr_url
    print(" $ api-call " + url + " " + call_on)

  return github_call(url, post_data, method=method)

def github_call(url, post_data=None, fail_ok=False, method=None):
  token = get_github_token()
  # make query
  if post_data is not None:
    if sys.version_info[0] == 2:
      post_data = post_data.encode('utf-8')
    if method is None or method == "POST":
      ret = requests.post(url, headers = {'Authorization': 'token ' + token, 'Content-Type': 'application/json' }, data=post_data)
    elif method == "PATCH":
      ret = requests.patch(url, headers = {'Authorization': 'token ' + token, 'Content-Type': 'application/json' }, data=post_data)
    else:
      print("Unknown method call with data in github_call " + method)
      exit(1)
  elif method is None or method == "GET":
    ret = requests.get(url, headers = {'Authorization': 'token ' + token, 'Content-Type': 'application/json' })
  elif method == "DELETE":
    ret = requests.delete(url, headers = {'Authorization': 'token ' + token, 'Content-Type': 'application/json' })
  else:
    print("Unknown method call in github_call " + method)
    exit(1)

  # process output
  if ret.status_code < 200 or ret.status_code >= 300:
    if fail_ok:
      return None
    else:
      logfail("Github query error " + ret.reason)
      print(ret.text)
      if not Config.force:
        exit(12)

  # return result
  return ret.json()

