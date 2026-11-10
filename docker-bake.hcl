variable "SQLBOT_BASE_TAGS" {
  default = "sqlbot-python-pg:local"
}

variable "SQLBOT_BUILD_TAGS" {
  default = "sqlbot-build-base:local"
}

variable "SQLBOT_APP_TAGS" {
  default = "sqlbot:local"
}

variable "SQLBOT_BASE_PLATFORMS" {
  default = ""
}

group "default" {
  targets = ["base", "build-base"]
}

target "pg-base" {
  dockerfile = "Dockerfile-base"
  target     = "pg-base"
  platforms  = compact(split(",", SQLBOT_BASE_PLATFORMS))
}

target "runtime-tools" {
  inherits = ["pg-base"]
  target   = "runtime-tools"
}

target "base" {
  inherits = ["runtime-tools"]
  target   = "runtime-base"
  tags     = split(",", SQLBOT_BASE_TAGS)
}

target "build-base" {
  dockerfile = "Dockerfile-build-base"
  contexts = {
    pg-base             = "target:pg-base"
    sqlbot-runtime-tools = "target:runtime-tools"
  }
  platforms  = compact(split(",", SQLBOT_BASE_PLATFORMS))
  tags       = split(",", SQLBOT_BUILD_TAGS)
}

target "app" {
  dockerfile = "Dockerfile"
  contexts = {
    sqlbot-runtime    = "target:base"
    sqlbot-build-base = "target:build-base"
  }
  args = {
    SQLBOT_RUNTIME_IMAGE = "sqlbot-runtime"
    SQLBOT_BUILD_IMAGE   = "sqlbot-build-base"
  }
  platforms = compact(split(",", SQLBOT_BASE_PLATFORMS))
  tags      = split(",", SQLBOT_APP_TAGS)
}
