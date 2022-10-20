from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

requirements = [
    "docker",
    "docopt",
    "hvac",
    "pytest",
    "pyyaml",
    "vault_dev",
    "Pillow"]

setup(name="orderly_web",
      version="0.1.0",
      description="Deploy scripts for OrderlyWeb",
      long_description=long_description,
      classifiers=[
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent",
      ],
      url="https://github.com/vimc/orderly-web-deploy",
      author="Rich FitzJohn",
      author_email="r.fitzjohn@imperial.ac.uk",
      license='MIT',
      packages=find_packages(),
      entry_points={
          'console_scripts': ['orderly-web=orderly_web.cli:main'],
      },
      include_package_data=True,
      zip_safe=False,
      # Extra:
      long_description_content_type="text/markdown",
      setup_requires=["pytest-runner"],
      tests_require=[
          "vault_dev",
          "pytest"
      ],
      install_requires=requirements)
