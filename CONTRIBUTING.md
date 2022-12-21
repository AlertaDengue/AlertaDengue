# Contributing with InfoDengue

### Prerequisites

- Postgresql [(see documentation)](https://www.postgresql.org/download/linux/ubuntu/);
- Git [(see documentation)](https://git-scm.com/docs/gittutorial);
- Docker [(see documentation)](https://docs.docker.com/engine/install/ubuntu/);
- Poetry [(see documentation)](https://python-poetry.org/docs/);
- IDE (recommended: [VSCODE](https://code.visualstudio.com/download), [VSCODIUM](https://vscodium.com/#install) or [PYCHARM](https://www.jetbrains.com/pycharm/download/)).

### Setting up the environment

 1) Fork and clone both repositories:
        > AlertaDengue: https://github.com/AlertaDengue/AlertaDengue
        > Data: https://github.com/AlertaDengue/Data (Contains randomly generated data for testing and development.)

 2) Configure Demo Database in your local machine:

     Follow [Data/README.md](https://github.com/AlertaDengue/Data#readme) to build and deploy the Demo Database image.

 3) Open the repository AlertaDengue with your IDE and use Miniforge ([see documentation](https://github.com/conda-forge/miniforge)) to create and activate the working environment ```(alertadengue-dev)```:

        $ mamba env create -f conda/environment.yaml
        $ conda activate alertadengue-dev

 4) Install the environment dependencies with Poetry ([see documentation](https://python-poetry.org/docs/)):

         $ poetry install

### Building the app

With the environment dependencies set, it's time to prepare it to deploy. Use the Makefile in your terminal to create a .env file in the root of the project, this file will contain variables which will be needed to the building.

 1) Create .env file using Makefile:

        $ make prepare-env

 2) Synchronize all Map and Static Files:

        $ make sync-static-geofiles

 3) Build the app containers:

        $ make container-build

    _This step will possibly fail if the .env file isn't properly filled. Please check if there isn't any empty attribute that is stopping the build._

 4) After the build, start the Docker images with the command:

        $ make container-start


### Setting up Git, GitHub

In order to push your work to the main project, you will need to configure the remotes Upstream and Origin within your local repository following the steps below, this will ensure you are working with the most updated version of the project. _For more details about commiting, check the Git Guides [here](https://github.com/git-guides)._

1) Add Origin & Upstream:


        $ git remote add origin git@github.com:<user>/AlertaDengue.git
        $ git remote add upstream git@github.com:AlertaDengue/AlertaDengue.git

2) Fetch all branches:

        $ git fetch --all

3) Commit & Create pull request

    When the changes in your branch are done (_please, read about [Best Practices](https://gist.github.com/luismts/495d982e8c5b1a0ced4a57cf3d93cf60) with Git before commiting_), it's time to push the commits to your fork and create a pull request so the maintainers can review and merge into the AlertaDengue repository.

        $ git push

    Your IDE should redirect you to the GitHub page with your Pull Request specifying the commits and the files that you have worked on. Write a message telling us about all your changes and click on Create Pull Request.
