from __future__ import annotations

SINAN_REQUIRED_COLS: list[str] = [
    "ID_MUNICIP",
    "ID_AGRAVO",
    "DT_SIN_PRI",
    "DT_NOTIFIC",
    "DT_DIGITA",
    "DT_NASC",
    "NU_ANO",
    "NU_IDADE_N",
    "NU_NOTIFIC",
    "SEM_NOT",
    "SEM_PRI",
    "CS_SEXO",
]

SINAN_SYNONYMS_FIELDS: dict[str, list[str]] = {
    "ID_MUNICIP": ["ID_MN_RESI"],
}

SINAN_SOURCE_TO_DEST_COLUMNS: dict[str, str] = {
    "DT_NOTIFIC": "dt_notific",
    "SEM_NOT": "se_notif",
    "NU_ANO": "ano_notif",
    "DT_SIN_PRI": "dt_sin_pri",
    "SEM_PRI": "se_sin_pri",
    "DT_DIGITA": "dt_digita",
    "ID_MUNICIP": "municipio_geocodigo",
    "NU_NOTIFIC": "nu_notific",
    "ID_AGRAVO": "cid10_codigo",
    "DT_NASC": "dt_nasc",
    "CS_SEXO": "cs_sexo",
    "NU_IDADE_N": "nu_idade_n",
    "RESUL_PCR_": "resul_pcr",
    "CRITERIO": "criterio",
    "CLASSI_FIN": "classi_fin",
    "DT_CHIK_S1": "dt_chik_s1",
    "DT_CHIK_S2": "dt_chik_s2",
    "DT_PRNT": "dt_prnt",
    "RES_CHIKS1": "res_chiks1",
    "RES_CHIKS2": "res_chiks2",
    "RESUL_PRNT": "resul_prnt",
    "DT_SORO": "dt_soro",
    "RESUL_SORO": "resul_soro",
    "DT_NS1": "dt_ns1",
    "RESUL_NS1": "resul_ns1",
    "DT_VIRAL": "dt_viral",
    "RESUL_VI_N": "resul_vi_n",
    "DT_PCR": "dt_pcr",
    "SOROTIPO": "sorotipo",
    "ID_DISTRIT": "id_distrit",
    "ID_BAIRRO": "id_bairro",
    "NM_BAIRRO": "nm_bairro",
    "ID_UNIDADE": "id_unidade",
}

SINAN_DEST_COLUMNS: list[str] = list(SINAN_SOURCE_TO_DEST_COLUMNS.values())
