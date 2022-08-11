# Go job type
"golang" job type is intended to handle the calls to your Go function.
Racetrack will wrap it up in a web server.

Set `lang: golang` in your `fatman.yaml` manifest file in order to use this type of job.

# Job standards
Let's assume you already have your code in a repository at `model.go`:
```go
package supersmart

func sumNumbers(numbers []float64) float64 {
	var sum float64 = 0
	for _, number := range inputFloats {
		sum += number
	}
	return sum
}
```
and you have some dependencies configured in `go.mod` file:
```
module supersmart

go 1.16

require github.com/pkg/errors v0.9.1
```

Now you need to make a few adjustments to adhere to job standards. 
Basically, you need to embed your code into a `Perform` function in your root Go module.
Create `fatman_entrypoint.go`:
```go
package supersmart

import (
	"github.com/pkg/errors"
)

func Perform(input map[string]interface{}) (interface{}, error) {
	numbers, ok := input["numbers"]
	if !ok {
		return nil, errors.New("'numbers' parameter was not given")
	}
	numbersList := numbers.([]interface{})
	inputFloats := make([]float64, len(numbersList))
	var err error
	for i, arg := range numbersList {
		inputFloats[i] = arg.(float64)
		if err != nil {
			return nil, errors.Wrap(err, "converting argument to float64")
		}
	}

    sum := sumNumbers(inputFloats)
	return sum, nil
}
```

Notice that `Perform` function should always have the following signature:
`func Perform(input map[string]interface{}) (interface{}, error)`

This method will be called by Racetrack when calling `/perform` endpoint on your job.

To sum up:
1. You MUST create entrypoint `.go` file
1. Entrypoint file MUST have `Perform` function with a signature: 
   `func Perform(input map[string]interface{}) (interface{}, error)`
1. Entrypoint file MUST be in the root package (the same package as declared in `go.mod`)
1. You SHOULD take care of error handling and return self-explanatory error in case of failure.
1. You SHOULD convert `interface{}` types in input to desired types on your own.
1. You MAY do some initialization in `func init()` [init function](https://golang.org/doc/effective_go#init)
1. You MAY fetch some data during initialization and keep them in a working directory 
   (eg. load model data from external sources).  Working directory is the root of your git repository.
1. You SHOULD use relative path `./file.txt` (instead of abs like `/src/fatman/file.txt`) 
   when accessing your model data.
1. You MUST create `fatman.yaml` at the root of your repo.
1. You MAY put some required modules to `go.mod` file and refer to it in a manifest file.
1. You MUST NOT refer to some local files that are not pushed to the repository. 
   Keep in mind that your job is built from your git repository.

# Manifest file
When using `golang` job type, you MUST include the following fields in a `fatman.yaml` manifest file:
- `name` - choose a meaningful text name for a job. It should be unique within the Racetrack cluster.
- `owner_email` - email address of the Fatman's owner to reach out
- `lang` - Set base image to "golang"
- `git.remote` - URL to your remote repo 

You MAY include the following fields:
- `git.branch` - git branch name (if different from "master").
- `git.directory` - subdirectory relative to git repo root where the project is
- `golang.gomod` - relative path to `go.mod` requirements
- `labels` - dictionary with metadata describing fatman for humans

The final `fatman.yaml` may look like this:
```yaml
name: supersmart
owner_email: nobody@example.com
lang: golang

git:
  remote: https://github.com/racetrack/supersmart-model
  branch: master

golang:
  gomod: 'go.mod'
```
