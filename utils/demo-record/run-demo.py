#!/usr/bin/env python3
import time
from simulatekey import countdown, type_command, type_text, ESCAPE

"""
Preparation:
rm -rf ~/prime-checker
mkdir -p ~/prime-checker
cd ~/prime-checker
tput reset
"""

if __name__ == '__main__':
    countdown()

    type_command('vim entrypoint.py')
    type_text('i')
    type_text('''
import math

class JobEntrypoint:

    def perform(self, number: int) -> bool:
        """Check if a number is prime"""
        if number < 2:
            return False
        for i in range(2, int(math.sqrt(number)) + 1):
            if number % i == 0:
                return False
        return True

    def docs_input_example(self) -> dict:
        """Return example input values for this model"""
        return {'number': 7907}
    '''.strip(), key_delay=0.01)
    type_command(ESCAPE + ':wq')

    type_command('vim job.yaml')
    type_text('i')
    type_text('''
name: primer
owner_email: sample@example.com
jobtype: python3:latest
git:
  remote: https://github.com/TheRacetrack/racetrack
jobtype_extra:
  entrypoint_path: 'entrypoint.py'
  entrypoint_class: 'JobEntrypoint'
    '''.strip(), key_delay=0.01)
    type_command(ESCAPE + ':wq')

    type_command('racetrack deploy --remote http://localhost:7102')
    time.sleep(6)

    type_command('''
curl -X POST "http://localhost:7105/pub/job/primer/latest/api/v1/perform" \\
  -H "Content-Type: application/json" \\
  -H "X-Racetrack-Auth: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI" \\
  -d '{"number": 7907}'
    '''.strip(), key_delay=0.01)

    print('Cut!')
