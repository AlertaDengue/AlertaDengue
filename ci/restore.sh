#############
## restore.sh
#############
#!/bin/bash

/etc/init.d/postgresql restart
./_prepare_server.sh
./_create_db.sh
./_restore_db.sh
