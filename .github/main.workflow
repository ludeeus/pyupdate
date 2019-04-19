workflow "Trigger: push" {
  on = "push"
  resolves = ["ludeeus/action-push@master"]
}

action "ludeeus/action-pdoc@master" {
  uses = "ludeeus/action-pdoc@master"
  env = {
    ACTION_PACKAGE = "pyupdate"
  }
}

action "ludeeus/action-push@master" {
  uses = "ludeeus/action-push@master"
  needs = ["ludeeus/action-pdoc@master"]
  env = {
    ACTION_MAIL = "joasoe@gmail.com"
    ACTION_NAME = "ludeeus"
    ACTION_MESSAGE = "Documentation update"
  }
  secrets = ["GITHUB_TOKEN"]
}
