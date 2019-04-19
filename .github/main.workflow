workflow "Trigger: push" {
  on = "push"
  resolves = ["ludeeus/action-pdoc@master"]
}

action "ludeeus/action-pdoc@master" {
  uses = "ludeeus/action-pdoc@master"
  env = {
    ACTION_PACKAGE = "pyupdate"
  }
}
