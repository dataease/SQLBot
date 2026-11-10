variable "SQLBOT_BASE_TAGS" {
  default = "sqlbot-python-pg:local"
}

variable "SQLBOT_BASE_PLATFORMS" {
  default = ""
}

group "default" {
  targets = ["base"]
}

target "pg-base" {
  dockerfile = "Dockerfile-pg-base"
  platforms  = compact(split(",", SQLBOT_BASE_PLATFORMS))
}

target "base" {
  dockerfile = "Dockerfile-base"
  contexts   = { pg-base = "target:pg-base" }
  platforms  = compact(split(",", SQLBOT_BASE_PLATFORMS))
  tags       = split(",", SQLBOT_BASE_TAGS)
}

target "app" {
  dockerfile = "Dockerfile"
  contexts   = { sqlbot-runtime = "target:base" }
  args       = { SQLBOT_RUNTIME_IMAGE = "sqlbot-runtime" }
  platforms  = compact(split(",", SQLBOT_BASE_PLATFORMS))
  tags       = ["sqlbot:local"]
}
