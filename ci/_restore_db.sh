#################
## _restore_db.sh
#################

#!/bin/bash

#gzip -d dengue.sql.gz
psql -d dengue < alertademo_data.sql

#gzip -d infodengue.sql.gz
#psql -d infodengue < infodengue.sql

psql -d dengue < patch/notificacao.sql