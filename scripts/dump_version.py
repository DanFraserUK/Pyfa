"""
This script is solely used when generating builds. It generates a version number automatically using
git tags as it's basis. Whenever a build is created, run this file beforehand and it should replace
the old version number with the new one in VERSION.YML
"""

import yaml
import subprocess
import os


with open("version.yml", 'r+') as file:
    data = yaml.load(file)
    file.seek(0)
    file.truncate()

    # python's versioning spec doesn't handle the same format git describe outputs, so convert it.
    label = os.environ["PYFA_VERSION"] if os.environ["PYFA_VERSION"] else subprocess.check_output(["git", "describe", "--tags"]).strip().decode().split('-')
    label = '-'.join(label[:-2])+'+'+'-'.join(label[-2:])
    print(label)
    data['version'] = label
    yaml.dump(data, file, default_flow_style=False)

