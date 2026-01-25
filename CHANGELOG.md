Release Notes
---

## [4.2.6](https://github.com/AlertaDengue/AlertaDengue/compare/4.2.5...4.2.6) (2026-01-25)

### Bug Fixes

* **env:** align dev/staging/prod settings and staging compose vars ([#821](https://github.com/AlertaDengue/AlertaDengue/issues/821)) ([6ecee0b](https://github.com/AlertaDengue/AlertaDengue/commit/6ecee0b65f1146c109083f12ae8b01a4b11a1514))

## [4.2.5](https://github.com/AlertaDengue/AlertaDengue/compare/4.2.4...4.2.5) (2026-01-21)

### Bug Fixes

* **sqlalchemy:** replace string SQL execution with executable statements ([#825](https://github.com/AlertaDengue/AlertaDengue/issues/825)) ([01e57c4](https://github.com/AlertaDengue/AlertaDengue/commit/01e57c4249dd39704cdee8bd79a3baeff6bab42d))

## [4.2.4](https://github.com/AlertaDengue/AlertaDengue/compare/4.2.3...4.2.4) (2026-01-08)

### Bug Fixes

* **compose:** mount upload/dbf volumes in worker to match base service ([#816](https://github.com/AlertaDengue/AlertaDengue/issues/816)) ([6026170](https://github.com/AlertaDengue/AlertaDengue/commit/602617053449290202e34f3fa4b4244b312d1832))

## [4.2.3](https://github.com/AlertaDengue/AlertaDengue/compare/4.2.2...4.2.3) (2025-12-08)

### Bug Fixes

* **css:** restore collapse styles in report-state ([#807](https://github.com/AlertaDengue/AlertaDengue/issues/807)) ([8c935ad](https://github.com/AlertaDengue/AlertaDengue/commit/8c935ad789056ccbffc88e1c66874b8812cdfcab))

## [4.2.2](https://github.com/AlertaDengue/AlertaDengue/compare/4.2.1...4.2.2) (2025-12-01)

### Bug Fixes

* **base:** restore jquery/bootstrap order to reenable accordion ([#801](https://github.com/AlertaDengue/AlertaDengue/issues/801)) ([dbbb708](https://github.com/AlertaDengue/AlertaDengue/commit/dbbb708cd5d45b3d2f53eba5fa6fae78a9ebdc3c))

## [4.2.1](https://github.com/AlertaDengue/AlertaDengue/compare/4.2.0...4.2.1) (2025-11-29)

### Bug Fixes

* **about-us:** resolve youtube embed error with nocookie player ([#799](https://github.com/AlertaDengue/AlertaDengue/issues/799)) ([45dfe0a](https://github.com/AlertaDengue/AlertaDengue/commit/45dfe0a9f93ca8528620040085f1d6191fab98ac))

## [4.2.0](https://github.com/AlertaDengue/AlertaDengue/compare/4.1.0...4.2.0) (2025-11-29)

### Features

* **about:** update text and images in 'about-us' section ([#797](https://github.com/AlertaDengue/AlertaDengue/issues/797)) ([512d0f3](https://github.com/AlertaDengue/AlertaDengue/commit/512d0f3e1cc37d752993d95bd1a2574ce3b3cc39))

## [4.1.0](https://github.com/AlertaDengue/AlertaDengue/compare/4.0.0...4.1.0) (2025-11-18)

### Features

* **about-us:** link technical reports to zenodo ([#795](https://github.com/AlertaDengue/AlertaDengue/issues/795)) ([5ef31f9](https://github.com/AlertaDengue/AlertaDengue/commit/5ef31f9d3b912171ec17b2295e357684ee47fac4))
* **home,i18n:** add localized banners and refine home menu styles ([#794](https://github.com/AlertaDengue/AlertaDengue/issues/794)) ([41cca34](https://github.com/AlertaDengue/AlertaDengue/commit/41cca34109a4c506c3a2d18817b66072bb7ece03))
* **home:** refactor layout with responsive banners and feature buttons ([#792](https://github.com/AlertaDengue/AlertaDengue/issues/792)) ([25b6e5d](https://github.com/AlertaDengue/AlertaDengue/commit/25b6e5de8e184936013ec73815f5f52e2b7cc47e))

## [4.0.0](https://github.com/AlertaDengue/AlertaDengue/compare/3.8.0...4.0.0) (2025-11-10)

### ⚠ BREAKING CHANGES

* Refactor base structure to enhance template extension

* feat(templates): Refactor main Django templates for semantic structure

* fix: Change base template and Improve footer

* Minor changes

* Fix btn sponsor

* fix: Add 'extrahead' tag for searchbox component

* feat: Create functions to handle data for alert page

* feat: Optimize NotificationResume with Materialized Views

* fix: Rename from chik to chikungunya materialized view

* fix: Add JS into template for AlertaCityView

* fix: Add JS into template for AlertaStateView

* chore: Fix visualization

* refactor: Change tag names for altair chart

* feat: Move all content from template tag module to dbdata and views to render altair chart

* chore: Add Altair and Pin sqlglot version

* feat: Add script to create epiyears materialized views

* BREAKING CHANG: WIP

### Features

* **about:** include Technical Report on about page ([#682](https://github.com/AlertaDengue/AlertaDengue/issues/682)) ([77ff759](https://github.com/AlertaDengue/AlertaDengue/commit/77ff759a8c068b386b96367ce901cd2935b38586))
* Add link to the report "Reflexões sobre o risco de arboviroses" on the home page ([#690](https://github.com/AlertaDengue/AlertaDengue/issues/690)) ([aa54a26](https://github.com/AlertaDengue/AlertaDengue/commit/aa54a26e614206e57af1487427c1daecf8f41520))
* Initial implementation for Minio collector ([#650](https://github.com/AlertaDengue/AlertaDengue/issues/650)) ([d065892](https://github.com/AlertaDengue/AlertaDengue/commit/d065892ff71d8971dcd5281626a98137a5058e55))
* Introduce Django cache management and memcached service expose port ([#688](https://github.com/AlertaDengue/AlertaDengue/issues/688)) ([646d275](https://github.com/AlertaDengue/AlertaDengue/commit/646d275a247fb6ea19d2dcd490e34184c84cd0f7))
* Remove 'e-vigilancia' modal from home template ([#684](https://github.com/AlertaDengue/AlertaDengue/issues/684)) ([961a3c9](https://github.com/AlertaDengue/AlertaDengue/commit/961a3c9f21fc9080110010d2e224f84d250d89a0))
* Spanish Translation and Layout Improvements ([#653](https://github.com/AlertaDengue/AlertaDengue/issues/653)) ([526a918](https://github.com/AlertaDengue/AlertaDengue/commit/526a918ec6cfe3b770802bb017df24f5ceaf6f84))
* Standardize Docker compose configuration and Update Sugar and Makim specs ([#678](https://github.com/AlertaDengue/AlertaDengue/issues/678)) ([ae2f5c6](https://github.com/AlertaDengue/AlertaDengue/commit/ae2f5c6aad5702a9594c9d750db0166bd4a479f8))
* **upload-sinan:** refactor SINAN file upload ([#710](https://github.com/AlertaDengue/AlertaDengue/issues/710)) ([7a945ef](https://github.com/AlertaDengue/AlertaDengue/commit/7a945ef4a7e6803bee456e6014b1d2a365691385))
* **upload:** improve SINAN upload; add helpers, validations & views to upload large files ([#732](https://github.com/AlertaDengue/AlertaDengue/issues/732)) ([623cf21](https://github.com/AlertaDengue/AlertaDengue/commit/623cf21ec9be1367bf1488f1c39c4d289d2bf50e))
* **upload:** include SINANUpload rollback ([9f15066](https://github.com/AlertaDengue/AlertaDengue/commit/9f15066092e5421878b2f2ec2ff58a031f1517ba))
* **web:** include info tooltips template ([e1451d1](https://github.com/AlertaDengue/AlertaDengue/commit/e1451d169ca4c10a2615cda09e664c7e3bec8953))

### Bug Fixes

* **770:** fix issue [#770](https://github.com/AlertaDengue/AlertaDengue/issues/770) ([cef887f](https://github.com/AlertaDengue/AlertaDengue/commit/cef887f708c1dc731eb2bc2651d5e6d32f146cd8))
* **alert:** fix municipal alert chart ([2363223](https://github.com/AlertaDengue/AlertaDengue/commit/236322328446df005f4ee29953ffe82e0dd13737))
* **alerts:** use most recent 'SE' to set the dates on city and state Alert views ([61fd3bc](https://github.com/AlertaDengue/AlertaDengue/commit/61fd3bcf1615759b3ba1094b7ee8055b061fb47b))
* **api:** fix minor error on api notif ([c01af40](https://github.com/AlertaDengue/AlertaDengue/commit/c01af4020962efd11d47653f31fb73d1b8c2b62d))
* **api:** remove incorrect conditional on table lookup ([#725](https://github.com/AlertaDengue/AlertaDengue/issues/725)) ([43674d6](https://github.com/AlertaDengue/AlertaDengue/commit/43674d6ba35a8e781aa0500c162afff8ec1171b0))
* **charts:** change 'Epidemy' by 'High activity' on charts ([#672](https://github.com/AlertaDengue/AlertaDengue/issues/672)) ([9847ec1](https://github.com/AlertaDengue/AlertaDengue/commit/9847ec1224df6891f1aa9918ceddab0a58ef86e0))
* **charts:** fix epiweek on home's stack_chart ([6001b1c](https://github.com/AlertaDengue/AlertaDengue/commit/6001b1c1e4d20129216541143d318521a9bc5ce0))
* **dados:** geo_info.json file lookup error ([5cc43f4](https://github.com/AlertaDengue/AlertaDengue/commit/5cc43f45882e41ecf11767d4f79ebbdbc6fa9e4a))
* **dbf:** Correct string variables in dbf_upload template ([#662](https://github.com/AlertaDengue/AlertaDengue/issues/662)) ([32de480](https://github.com/AlertaDengue/AlertaDengue/commit/32de480f735ffdce6aab9bf5f663e247534498c3))
* **db:** fix 'undefined' value passed to NotificationQueries ([a3b806b](https://github.com/AlertaDengue/AlertaDengue/commit/a3b806bdfb8ab4d84bacf13f964a5f45993f3f72))
* **dependabot:** dependabot is failing due to a lint problem ([c0f6348](https://github.com/AlertaDengue/AlertaDengue/commit/c0f63486bc562943b9e67029a2844650e5877ff0))
* **deps:** resolve Makim vs SQLAlchemy clash via conda toolchain ([#783](https://github.com/AlertaDengue/AlertaDengue/issues/783)) ([a9f0403](https://github.com/AlertaDengue/AlertaDengue/commit/a9f0403002168efea38a24c29bfea59f74a3d976))
* **deps:** set fiona dep to < 1.10 ([#742](https://github.com/AlertaDengue/AlertaDengue/issues/742)) ([da1da70](https://github.com/AlertaDengue/AlertaDengue/commit/da1da70c472fd2edc415a710c7a99392b022a793))
* **docker networks:** replace default docker network by a predefined one ([#676](https://github.com/AlertaDengue/AlertaDengue/issues/676)) ([78d2016](https://github.com/AlertaDengue/AlertaDengue/commit/78d2016f43e1bb45106a69874d687dfcfd84429a))
* **docker-compose:** Migrate to Compose-Go to Fix PyYAML Issue ([#661](https://github.com/AlertaDengue/AlertaDengue/issues/661)) ([4202d8d](https://github.com/AlertaDengue/AlertaDengue/commit/4202d8d481c84711e3092078eb19d6d7ffaf582a))
* **home:** fix see more, include disease on btn's url ([e746b1a](https://github.com/AlertaDengue/AlertaDengue/commit/e746b1a2a3489cacba428bcd59b20f0208d79258))
* **pdf:** fix technical-pdf download ([#683](https://github.com/AlertaDengue/AlertaDengue/issues/683)) ([33f3bb8](https://github.com/AlertaDengue/AlertaDengue/commit/33f3bb8002a9a68d6d26513b228e1fdf0bdc57e7))
* **reports:** fix chikungunya epiyears-chart ([4d6b82c](https://github.com/AlertaDengue/AlertaDengue/commit/4d6b82c69bcf478421f7d4053f8edff9268cb99f))
* **reports:** fix disease-chart on state report ([bea987f](https://github.com/AlertaDengue/AlertaDengue/commit/bea987f56a96ebaeff8fda9ca3c308e839ae423a))
* **reports:** fix week cases on state reports & more ([19d9258](https://github.com/AlertaDengue/AlertaDengue/commit/19d92584a97a4c461bb5f80c8171d147db2d33e2))
* **reports:** include epiweek on chart-stage ([f659ac9](https://github.com/AlertaDengue/AlertaDengue/commit/f659ac9e261c00ccfa579f1a146e7ca7d2db389d))
* **reports:** include text on header ([3b86586](https://github.com/AlertaDengue/AlertaDengue/commit/3b865868212920a3b8b6cdaf177df850f1956a5e))
* **upload:** auto detect csv encoding on upload ([9699b50](https://github.com/AlertaDengue/AlertaDengue/commit/9699b5097071805cdf2e479c67eb12e9db6f6378))
* **upload:** automatically detect CSV sep on read_csv() ([#738](https://github.com/AlertaDengue/AlertaDengue/issues/738)) ([919c3ec](https://github.com/AlertaDengue/AlertaDengue/commit/919c3ec28408b2d80656deb4ed315ad0288e1593))
* **upload:** improve parse_dates; fix parse_data; include residue CSV download on overview/ ([85f5b56](https://github.com/AlertaDengue/AlertaDengue/commit/85f5b56985811691859986e7ceb79f8ae516c89f))
* **upload:** include dayfirst on date parsing ([d159886](https://github.com/AlertaDengue/AlertaDengue/commit/d1598868e1897bc3d51dcb51e83d3470383286c0))
* **upload:** int(None) error on df.SEM_PRI parse_data ([#737](https://github.com/AlertaDengue/AlertaDengue/issues/737)) ([6faacbc](https://github.com/AlertaDengue/AlertaDengue/commit/6faacbcf570a92dca099801f8a5e8c7c5677f250))
* **upload:** minor fix on SINAN upload ([c4a0f8f](https://github.com/AlertaDengue/AlertaDengue/commit/c4a0f8fce58a336ec18be5599a97b46887bac158))
* **upload:** SINAN Upload minor fixes and upload pagination ([#735](https://github.com/AlertaDengue/AlertaDengue/issues/735)) ([064781a](https://github.com/AlertaDengue/AlertaDengue/commit/064781a0188180ee46ec2e3b8a350fb7f8a966a4))

### Reverts

* Recent updates to alerta_state_view ([#711](https://github.com/AlertaDengue/AlertaDengue/issues/711)) ([f9a5768](https://github.com/AlertaDengue/AlertaDengue/commit/f9a5768f0f6c8e861878d77c6212005587c5d100))

### Code Refactoring

* Remove all outdated code for AlertaStateView ([#699](https://github.com/AlertaDengue/AlertaDengue/issues/699)) ([ec3c6ee](https://github.com/AlertaDengue/AlertaDengue/commit/ec3c6ee2393e9cc78c7ec4db69030bfe374ddec8))

## [3.8.0](https://github.com/AlertaDengue/AlertaDengue/compare/3.7.0...3.8.0) (2023-06-21)


### Features

* Add new style to change color of selected item in select2 dropdown ([#649](https://github.com/AlertaDengue/AlertaDengue/issues/649)) ([2ab8993](https://github.com/AlertaDengue/AlertaDengue/commit/2ab89937570e52bfd0e74b4417b07188f768af16))

## [3.7.0](https://github.com/AlertaDengue/AlertaDengue/compare/3.6.1...3.7.0) (2023-06-20)


### Features

* **docker:** Add Minio service to docker-compose.yaml ([#638](https://github.com/AlertaDengue/AlertaDengue/issues/638)) ([0c1f900](https://github.com/AlertaDengue/AlertaDengue/commit/0c1f900fafc791f9529f11387a53e2d47f41b2bc))
* Fix error in sync_geofiles command ([#647](https://github.com/AlertaDengue/AlertaDengue/issues/647)) ([8cc2f1f](https://github.com/AlertaDengue/AlertaDengue/commit/8cc2f1f0d1a9e896c17570355cbbe0143a8fe481))
* Remove Episcanner-downloader ([#641](https://github.com/AlertaDengue/AlertaDengue/issues/641)) ([1dcd2fb](https://github.com/AlertaDengue/AlertaDengue/commit/1dcd2fbb0db5017de3804923cfe7320fc1debb51))
* Update Menubar ([#632](https://github.com/AlertaDengue/AlertaDengue/issues/632)) ([beefe8d](https://github.com/AlertaDengue/AlertaDengue/commit/beefe8debc5dba85e1831249e58d180ab21312b3))


### Bug Fixes

* **legacy:** remove Twitter references from project ([#635](https://github.com/AlertaDengue/AlertaDengue/issues/635)) ([02a6fe9](https://github.com/AlertaDengue/AlertaDengue/commit/02a6fe946cf7c522097d415b0557b5fe8544bdf1))
* **searchbox:** improve searchbox speed and recognition ([#633](https://github.com/AlertaDengue/AlertaDengue/issues/633)) ([78d2617](https://github.com/AlertaDengue/AlertaDengue/commit/78d2617e9f77209608e198ee8a2a2ab919176866)), closes [#2](https://github.com/AlertaDengue/AlertaDengue/issues/2) [#3](https://github.com/AlertaDengue/AlertaDengue/issues/3) [#4](https://github.com/AlertaDengue/AlertaDengue/issues/4) [#2](https://github.com/AlertaDengue/AlertaDengue/issues/2) [#3](https://github.com/AlertaDengue/AlertaDengue/issues/3) [#4](https://github.com/AlertaDengue/AlertaDengue/issues/4) [#5](https://github.com/AlertaDengue/AlertaDengue/issues/5) [#6](https://github.com/AlertaDengue/AlertaDengue/issues/6) [#7](https://github.com/AlertaDengue/AlertaDengue/issues/7)
* Update DBF file import functionality ([#636](https://github.com/AlertaDengue/AlertaDengue/issues/636)) ([7848b8e](https://github.com/AlertaDengue/AlertaDengue/commit/7848b8e528432b4fdf499b2c380bb79d421307f1))

## [3.6.1](https://github.com/AlertaDengue/AlertaDengue/compare/3.6.0...3.6.1) (2023-04-26)


### Bug Fixes

* **django:** fix broken iframe and add pysus to the API tutorial ([#630](https://github.com/AlertaDengue/AlertaDengue/issues/630)) ([3b41f7b](https://github.com/AlertaDengue/AlertaDengue/commit/3b41f7b3976eea157a6f5e132e3864a2776204e2))

## [3.6.0](https://github.com/AlertaDengue/AlertaDengue/compare/3.5.0...3.6.0) (2023-02-28)


### Features

* **settings:** Improve database connections ([#623](https://github.com/AlertaDengue/AlertaDengue/issues/623)) ([2393b04](https://github.com/AlertaDengue/AlertaDengue/commit/2393b04a1f17478ef39fbed9f78be6839b584776))

## [3.5.0](https://github.com/AlertaDengue/AlertaDengue/compare/3.4.0...3.5.0) (2023-02-25)


### Features

* **postgres:** Add new volume to production database ([#619](https://github.com/AlertaDengue/AlertaDengue/issues/619)) ([5e9cb75](https://github.com/AlertaDengue/AlertaDengue/commit/5e9cb75c0f2a55060230c13a17c61644d99a5891))

## [3.4.0](https://github.com/AlertaDengue/AlertaDengue/compare/3.3.2...3.4.0) (2023-02-24)


### Features

* **postgres:** Add script to change permissions for roles in database ([#617](https://github.com/AlertaDengue/AlertaDengue/issues/617)) ([8bfacdb](https://github.com/AlertaDengue/AlertaDengue/commit/8bfacdbd07afa1101e325be7e0e59bf11e620e8c))

## [3.3.2](https://github.com/AlertaDengue/AlertaDengue/compare/3.3.1...3.3.2) (2023-02-17)


### Bug Fixes

* **workflow:** Minor updates ([#616](https://github.com/AlertaDengue/AlertaDengue/issues/616)) ([de50b99](https://github.com/AlertaDengue/AlertaDengue/commit/de50b997c8425f7f3a63ac2d9bb5bea67dfe9c40))

## [3.3.1](https://github.com/AlertaDengue/AlertaDengue/compare/3.3.0...3.3.1) (2023-01-31)


### Bug Fixes

* **pyproject:** Update linting package versions ([#601](https://github.com/AlertaDengue/AlertaDengue/issues/601)) ([979d4f9](https://github.com/AlertaDengue/AlertaDengue/commit/979d4f99ced10a35f09b88a1fdf2ccc3eeed0f1d))

## [3.3.0](https://github.com/AlertaDengue/AlertaDengue/compare/3.2.0...3.3.0) (2023-01-26)


### Features

* **build:** Add semantic-release ([#591](https://github.com/AlertaDengue/AlertaDengue/issues/591)) ([7264126](https://github.com/AlertaDengue/AlertaDengue/commit/72641261c474825dc91e3c99112e6041bddd63d2))
* **release:** Remove poetry publish ([#593](https://github.com/AlertaDengue/AlertaDengue/issues/593)) ([b420244](https://github.com/AlertaDengue/AlertaDengue/commit/b4202446cdc6139bc98c11cb4019f43c8e5486d1))


### Bug Fixes

* **release:** Add regex match version ([#594](https://github.com/AlertaDengue/AlertaDengue/issues/594)) ([d031d30](https://github.com/AlertaDengue/AlertaDengue/commit/d031d3095f20cbf6fde40efb2d51cfc174cd300a))
* **release:** Fix white spaces ([#596](https://github.com/AlertaDengue/AlertaDengue/issues/596)) ([21ca7c3](https://github.com/AlertaDengue/AlertaDengue/commit/21ca7c380ecdf1983cf1311600629a7244245452))
