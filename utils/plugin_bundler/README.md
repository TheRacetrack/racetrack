# Plugin Bundler
Plugin Bundler is a tool for generating Racetrack plugins from a source code.

## How to bundle a plugin?

1. Install `racetrack-plugin-bundler` tool:
    1. Clone Racetrack repository: `git clone https://github.com/TheRacetrack/racetrack`
    2. Run `make setup` inside Racetrack repository
    3. Activate Ractrack venv: `. venv/bin/activate`.
       (Now you can use `racetrack-plugin-bundler` command)
2. Go to the directory where your plugin is located.
3. Run `racetrack-plugin-bundler bundle` to bundle a plugin into a ZIP file.
  See the output to locate the outcome package.
