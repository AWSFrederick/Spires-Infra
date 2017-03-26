from setuptools import setup

setup(
    name="AWS-Frederick",
    version="0.1",
    install_requires=[
        'cfn-environment-base==0.9.15',
        'troposphere==1.9.2'
    ],
    dependency_links=[
        'https://github.com/ion-channel/cloudformation-environmentbase/archive/0.9.15.zip#egg=cfn-environment-base-0.9.15'
    ],
    include_package_data=True,
    zip_safe=True
)
