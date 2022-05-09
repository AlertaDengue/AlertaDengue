# Contributing with InfoDengue

### Pré-requisites

- Postgresql [(see documentation)](https://www.postgresql.org/download/linux/ubuntu/);
- Git [(see documentation)](https://git-scm.com/docs/gittutorial);
- Docker [(see documentation)](https://docs.docker.com/engine/install/ubuntu/);
- Poetry [(see documentation)](https://python-poetry.org/docs/);
- IDE (recommended: [VSCODE](https://code.visualstudio.com/download), [VSCODIUM](https://vscodium.com/#install) or [PYCHARM](https://www.jetbrains.com/pycharm/download/)).

### Setting up the environment

 1) Fork and clone both repositories:
        > AlertaDengue: https://github.com/AlertaDengue/AlertaDengue
        > Data: https://github.com/AlertaDengue/Data (Contains randomly generated data for testing and development, see more info [here](https://github.com/AlertaDengue/Data#readme))
        

 2) Open the repository AlertaDengue with your IDE and use [Miniforge](https://github.com/conda-forge/miniforge) to create and activate the working environment ```(alertadengue-dev)```:
 
        $ mamba env create -f conda/environment.yaml
        $ conda activate alertadengue-dev 

 3) Install the environment dependencies with [Poetry](https://python-poetry.org/docs/):
         
         $ poetry install

### Setting up Git, GitHub

Finished the environment settings, you will need to configure the remotes Upstream and Origin within your local repository following the steps below, this will ensure you are working with the most updated version of the project. _For more details about commiting, check the Git Guides [here](https://github.com/git-guides)._

1) Add Origin & Upstream:


        $ git remote add origin git@github.com:<user>/AlertaDengue.git
        $ git remote add upstream git@github.com:AlertaDengue/AlertaDengue.git
        
2) Fetch all branches:

        $ git fetch --all
        
3) Commit & Create pull request

    When the changes in your branch are done (_please, read about [Best Practices](https://gist.github.com/luismts/495d982e8c5b1a0ced4a57cf3d93cf60) with Git before commiting_), it's time to push the commits to your fork and create a pull request so the maintainers can review and merge into the AlertaDengue repository. 
        
        $ git push
        
    Your IDE should redirect you to the GitHub page with your Pull Request specifying the commits and the files that you have worked on. Write a message telling us about all your changes and click on Create Pull Request. 
