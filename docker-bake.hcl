variable "PUSH_REGISTRY"    {}
variable "PUSH_NAMESPACE"   {}
variable "TAG"              { default = "latest" }
variable "PLATFORMS"        { default = "linux/amd64" }
variable "EXTRA_TAGS"       { default = "" }
variable "GIT_VERSION"      { default = "" }
variable "LIFECYCLE_TARGET" { default = "" }

function "image_tags" {
  params = [name]
  result = concat(
    ["${PUSH_REGISTRY}/${PUSH_NAMESPACE}/${name}:${TAG}"],
    [for t in split(",", EXTRA_TAGS) :
       "${PUSH_REGISTRY}/${PUSH_NAMESPACE}/${name}:${t}" if t != ""],
  )
}

target "_base" {
  platforms = split(",", PLATFORMS)
  args = {
    GIT_VERSION = GIT_VERSION
    DOCKER_TAG  = TAG
  }
}

group "default" {
  targets = ["lifecycle", "image-builder", "dashboard", "pub", "pgbouncer"]
}

target "lifecycle" {
  inherits   = ["_base"]
  context    = "."
  dockerfile = "lifecycle/Dockerfile"
  target     = LIFECYCLE_TARGET != "" ? LIFECYCLE_TARGET : null
  tags       = image_tags("lifecycle")
}

target "image-builder" {
  inherits   = ["_base"]
  context    = "."
  dockerfile = "image_builder/Dockerfile"
  tags       = image_tags("image-builder")
}

target "dashboard" {
  inherits   = ["_base"]
  context    = "."
  dockerfile = "dashboard/Dockerfile"
  tags       = image_tags("dashboard")
}

target "pub" {
  inherits   = ["_base"]
  context    = "pub"
  dockerfile = "Dockerfile"
  tags       = image_tags("pub")
}

target "pgbouncer" {
  platforms  = split(",", PLATFORMS)
  context    = "postgres/pgbouncer"
  dockerfile = "Dockerfile"
  tags       = image_tags("pgbouncer")
}
