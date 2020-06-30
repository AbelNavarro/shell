#!/usr/bin/env python2

# API reference:
# https://docs.atlassian.com/bitbucket-server/rest/5.16.0/bitbucket-rest.html

import json
import requests
import subprocess
import os
import sys
import time
import argparse

def parse_args(args):
  parser = argparse.ArgumentParser(description='Creates a repository in Bitbucket.')
  parser.add_argument('-a', '--address', required=True, help='Address of the bitbucket server (IP or FQDN)')
  parser.add_argument('-p', '--ssh_git_port', type=int, default=7999, help='Port to use when using ssh_git')
  parser.add_argument('-P', '--project_name', required=True, help='Name of the Bitbucket project where the repository is to be created')
  parser.add_argument('-r', '--repository_name', required=True, help='Name of the Bitbucket repository to be created')
  parser.add_argument('-t', '--token', required=True, help='Bitbucket API token with Admin rights')
  parser.add_argument('-m', '--mandatory_reviewers', nargs='+', required=True, help='Mandatory reviewers')
  parser.add_argument('-o', '--optional_reviewers', nargs='+', default=[], help='Optional reviewers')
  parser.add_argument('-y', '--type', required=False, choices=['Gradle', 'NodeJS'], default='Gradle', help='Type of repository to create')

  opts = parser.parse_args(args)

  # sanity checks for opts

  return opts

  
def call(cmd):
  ret_value = subprocess.call(cmd, shell=True, stdout=None, stderr=None)
  if not ret_value == 0:
    print "Error: %s, return value: %d" % (cmd, ret_value)
    exit()


def initialize_repo(url, project, repository):
  call("git --version")

  # TODO: check that git is configured with proper username to be able to push
  #       probably check with 'git config --local or --global'

  # Create a tmp directory to initialize the repo
  current_time = int(time.time())
  path = "/tmp/%s.%d" % (repository, current_time)
  os.makedirs(path)

  # TODO: delete directory in case of error

  repo_url = "%s/%s/%s.git" % (url, project, repository)
  # (for HTTPS) repo_url = "%s/scm/%s/%s.git" % (url, project, repository)
  call("git clone %s %s" % (repo_url, path))

  f = open("%s/README.md" % path, "w+")
  f.write("Blank on purpose")
  f.close()

  call("git -C %s add --all" % path)
  call("git -C %s commit -m 'Initial commit'" % path)
  call("git -C %s push -u origin master" % path)


class Bitbucket:
  address = None
  port = 7999
  token = None

  url = None
  ssh_url = None
  headers = None


  def __init__(self, address, port, token):
    self.address = address
    self.port = port
    self.token = token

    self.url = "https://%s" % address
    self.ssh_url = "ssh://git@%s:%d" % (address, port)
    self.headers = { 'Authorization' : 'Bearer ' + token }


  def project_exists(self, project):
    path = "%s/rest/api/1.0/projects/%s" % (self.url, project)
    res = requests.get(path, headers=self.headers)
    if res.status_code == 200:
      return True

    if res.status_code == 404:
      return False

    print "Error: %d, GET %s" % (res.status_code, path)
    exit()
 

  def repository_exists(self, project, repository):
    if not self.project_exists(project):
      return False

    path = "%s/rest/api/1.0/projects/%s/repos/%s" % (self.url, project, repository)
    res = requests.get(path, headers=self.headers)
    if res.status_code == 200:
      return True

    if res.status_code == 404:
      return False

    print "Error: %d, GET %s" % (res.status_code, path)
    exit()


  def repository_create(self, project, repository, forkable):
    data = {
      "name": repository,
      "scmId": "git",
      "forkable": forkable
    }

    path = "%s/rest/api/1.0/projects/%s/repos" % (self.url, project)
    res = requests.post(path, headers=self.headers, json=data)
    if res.status_code != 201:
      print ("Error (%d) creating repository %s." % (res.status_code, repository))
      print ("POST %s" % path)
      exit()


  def get_branches(self, project, repository):
    path = "%s/rest/api/1.0/projects/%s/repos/%s/branches" % (self.url, project, repository)
    res = requests.get(path, headers=self.headers)
    if res.status_code == 200:
      return [ branch["displayId"] for branch in res.json()["values"] ]

    print "Error: %d, GET %s" % (res.status_code, path)
    exit()


  def create_branch(self, project, repository, branch, commit):
    data = {
      "name": branch,
      "startPoint": "%s" % commit,
      "message": "Created %s branch" % branch
    }
    path = "%s/rest/api/1.0/projects/%s/repos/%s/branches" % (self.url, project, repository)
    res = requests.post(path, headers=self.headers, json=data)
    if res.status_code != 200:
      print ("Error (%d) creating branch %s." % (res.status_code, branch))
      print ("POST %s" % path)
      exit()

  def get_branch_latest_commit(self, project, repository, branch):
    path = "%s/rest/api/1.0/projects/%s/repos/%s/branches" % (self.url, project, repository)
    res = requests.get(path, headers=self.headers)
    if res.status_code == 200:
      return [ br["latestCommit"] if br["displayId"] == branch else None for br in res.json()["values"] ][0]

    print "Error: %d, GET %s" % (res.status_code, path)
    exit()


  def set_default_branch(self, project, repository, branch):
    data = {
      "id": "refs/heads/%s" % branch
    }
    path = "%s/rest/api/1.0/projects/%s/repos/%s/branches/default" % (self.url, project, repository)
    res = requests.put(path, headers=self.headers, json=data)
    if res.status_code != 204:
      print "Error: %d, PUT %s" % (res.status_code, path)
      exit()


  # Post Webhooks is an AddOn for Bitbucket, and uses its specific API
  # References:
  #   https://moveworkforward.atlassian.net/wiki/spaces/DOCS/pages/867205121/Atlassian+Bitbucket+Post+Webhook+API
  def webhook_exists(self, project, repository, hook_name):
    path = "%s/rest/webhook/1.0/projects/%s/repos/%s/configurations" % (self.url, project, repository)
    res = requests.get(path, headers=self.headers)
    if res.status_code == 200:
      data = res.json()
      if len(data) > 0:
        return [ True if webhook["title"] == hook_name else False for webhook in res.json() ][0]
      return False

    print "Error: %d, GET %s" % (res.status_code, path)
    exit()


  def create_webhook(self, project, repository, hook_type):
    # Check supported hook types
    supported_hook_types = [ 'gradle', 'nodejs' ]
    hook_type = hook_type.lower()
    if not hook_type in supported_hook_types:
      print("Error: unsupported webhook type %s" % hook_type)
      print("       supported types: ".join(supported_hook_types))
      exit()

    if hook_type == 'gradle':
      data = {
        "title": "Jenkins",
        "url": "http://ttbsbld102.dev.ttw:8080/bitbucket-scmsource-hook/notify",
        "enabled": True,
        "committersToIgnore": "jenkinsPusher",
        "branchesToIgnore": "",

        # Repository events
        "repoPush": True,
        "branchCreated": True,
        "branchDeleted": True,
        "tagCreated": False,
        "buildStatus": False,
        # Pull request events
        "prCreated": True,
        "prUpdated": True,
        "prMerged": True,
        "prDeclined": True,
        "prReopened": True,
        "prRescoped": True,
        "prCommented": False
      }
    elif hook_type == 'nodejs':
      data = {
        "title": "Jenkins",
        "url": "http://ttbsbld102.dev.ttw:8080/bitbucket-hook",
        "enabled": True,
        "committersToIgnore": "",
        "branchesToIgnore": "",

        # Repository events
        "repoPush": False,
        "branchCreated": False,
        "branchDeleted": False,
        "tagCreated": False,
        "buildStatus": False,
        # Pull request events
        "prCreated": True,
        "prUpdated": True,
        "prMerged": True,
        "prDeclined": False,
        "prReopened": True,
        "prRescoped": True,
        "prCommented": False
      }


    # This should be a POST, but we may have and old version of the plugin and must be a PUT
    path = "%s/rest/webhook/1.0/projects/%s/repos/%s/configurations" % (self.url, project, repository)
    res = requests.put(path, headers=self.headers, json=data)
    if res.status_code != 200:
      print "Error: %d, PUT %s" % (res.status_code, path)
      exit()


  def mark_unapproval_on_changes(self, project, repository):
    path = "%s/rest/api/1.0/projects/%s/repos/%s/settings/pull-requests" % (self.url, project, repository)
    res = requests.get(path, headers=self.headers)
    if res.status_code != 200:
      print "Error: %d, GET %s" % (res.status_code, path)
      exit()

    data = {
      "unapproveOnUpdate": True
    }
    res = requests.post(path, headers=self.headers, json=data)
    if res.status_code != 200:
      print "Error: %d, POST %s" % (res.status_code, path)
      exit()


  # Workzone
  # https://bitbucket.org/izymesdev/workzone/issues/125/document-rest-api-for-configuring-workzone
  def set_reviewers(self, project, repository, mandatory, optional):
    path = "%s/rest/workzoneresource/latest/branch/reviewers/%s/%s" % (self.url, project, repository)
    res = requests.get(path, headers=self.headers)
    if res.status_code != 200:
      print "Error: %d, GET %s" % (res.status_code, path)
      exit()

    res_data = res.json()
    branch_patterns = [ "refs/heads/develop", "release/*" ]
    for branch_pattern in branch_patterns:
      pattern_found = False
      for existing_branch in res_data:
        if existing_branch["refPattern"] == branch_pattern:
          pattern_found = True

      # TODO maybe we want to UPDATE a pattern (delete + create new)
      if not pattern_found:
        data = {
          "projectKey": project,
          "repoSlug": repository,
          "refPattern": branch_pattern,
          "mandatoryUsers": [ { "name": user } for user in mandatory ],
          "users" : [ { "name": user } for user in optional ]
        }
        res = requests.post(path, headers=self.headers, json=data)
        if res.status_code != 200:
          print "Error: %d, POST %s" % (res.status_code, path)
          exit()



def create_repo(address, port, project, repository, token, mandatory_reviewers, optional_reviewers, hook_type):

  ## Main stuff
  bitbucket = Bitbucket(address, port, token)

  # Check if repository already exists
  repo_exists = bitbucket.repository_exists(project, repository)

  # Create repository
  if not repo_exists:
    bitbucket.repository_create(project, repository, forkable=False)

  # No transcode diff option configurable via API

  # create branches {develop, release}
  develop_found = False
  release_found = False

  branches = bitbucket.get_branches(project, repository)

  if len(branches) == 0:
    # No branches there, repository needs to be initialized
    ssh_url = "ssh://git@%s:%d" % (address, port)
    initialize_repo(ssh_url, project, repository)

  # Need to fetch branches again, to get master
  branches = bitbucket.get_branches(project, repository)

  for branch in branches:
    if branch == "develop":
      develop_found = True

    if branch == "release":
      release_found = True

    if branch == "master":
      # We need the lastest commit to create the branches
      # In a new project, after git initialization, latestCommit == initialCommit
      commit = bitbucket.get_branch_latest_commit(project, repository, branch)


  if not develop_found:
    bitbucket.create_branch(project, repository, "develop", commit)

  if not release_found:
    bitbucket.create_branch(project, repository, "release", commit)

  # Set develop branch as default
  bitbucket.set_default_branch(project, repository, "develop")

  # TODO: Do we have to delete "master" branch?

  # check if webhook already exists
  webhook_found = bitbucket.webhook_exists(project, repository, "Jenkins")

  # Create jenkins post webhook (for gradle)
  # TODO: create for NodeJS (freestyle projects)
  if not webhook_found:
    bitbucket.create_webhook(project, repository, hook_type)

  # Pull requests: mark unapproval on changes
  bitbucket.mark_unapproval_on_changes(project, repository)

  # Set reviewers
  bitbucket.set_reviewers(project.upper(), repository, mandatory_reviewers, optional_reviewers)


def main():
  opts = parse_args(sys.argv[1:])
  create_repo(
    opts.address,
    opts.ssh_git_port,
    opts.project_name,
    opts.repository_name,
    opts.token,
    opts.mandatory_reviewers,
    opts.optional_reviewers,
    opts.type
  )
  
  print "Repository created/updated successfully"


if __name__ == '__main__':
  main()
