## AWS Frederick Infrastructure Code
### City on a Cloud Challenge

#### Setup

> pipenv --two

> pipenv install

> pipenv run python setup.py install


#### 2018

Create:

> python aws-frederick-env.py create --config-file 2018-config.yaml

Deploy:

> python aws-frederick-env.py deploy --config-file 2018-config.yaml

#### 2017
> export AWS_PROFILE=aws-frederick

> python aws-frederick-env.py create --config-file 2017-config.yaml
