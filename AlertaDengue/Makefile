clean:
	python setup.py clean
	find ./ -name '*.pyc' -type f -delete
  
develop: clean
	python setup.py develop
	pip install pre_commit
	cd ..
	pre-commit install
