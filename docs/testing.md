# Testing

Testing is done with pytest. 

First, install the dev dependencies:

```
pdm install -G test
```

Then you can run the tests, be sure all containers are built (analysis, netmon, Port4U):

```
pytest -s
```