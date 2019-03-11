clean:
	python setup.py clean
	find ./ -name '*.pyc' -type f -delete
  
develop: clean
	python setup.py develop
	pre-commit install