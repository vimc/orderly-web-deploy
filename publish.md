## Publishing

The python installer is mysterious and is liable to not reflect your sources if old files are around, even if it _seems_ like things have changed.  Deleting some things first helps:

```
rm -rf orderly_web.egg-info dist
```

Build the source distribution for publishing

```
python3 setup.py sdist
```

To testing

```
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

Test the installation

```
docker run --rm -it --entrypoint bash python
```

then

```
pip3 install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple orderly-web
```

Then upload to the main index

```
twine upload dist/*
```
