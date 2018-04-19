from setuptools import setup

setup(
    name="AWS-Frederick",
    version="0.1",
    install_requires=[
        'cfn-environment-base==0.9.22',
        'troposphere==2.2.1'
    ],
    dependency_links=[
        'https://github.com/AWSFrederick/cloudformation-environmentbase/archive/0.9.22.zip#egg=cfn-environment-base-0.9.22'
    ],
    include_package_data=True,
    zip_safe=True
)
