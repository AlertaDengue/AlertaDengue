## External foreign keys retained in archive schemas

The archive export intentionally retains four validated foreign keys to active
lookup tables:

- the three regional-alert constraints reference
  `Dengue_global.regional(id)`;
- `archive_tweets.Tweet.Tweet_CID10` references
  `Dengue_global.CID10(codigo)`.

All use `ON DELETE NO ACTION` and `ON UPDATE NO ACTION`.

Decision:

- keep the external archive foreign keys;
- do not modify the active reference tables;
- do not remove the constraints during this refactor;
- handle a completely standalone restore in a future task.

A full-fidelity restore requires compatible `Dengue_global.regional` and
`Dengue_global.CID10` reference structures before restoring these constraints.

The exported archive also retains the materialized-view definition for
`archive_historico_casos.historico_casos`. Local validation on July 29, 2026
confirmed that PostgreSQL repopulates that archived materialized view from the
retained `"Municipio"."Historico_alerta"` and
`"Municipio"."Historico_alerta_chik"` source tables during
`MATERIALIZED VIEW DATA` restore. A restore that must recover the archived
historico contents therefore also needs compatible copies of those retained
source rows or a future decoupling step.
