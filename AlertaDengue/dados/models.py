# coding=utf-8
# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Remove `managed = False` lines for those models you wish to give write DB access
# Feel free to rename the models, but don't rename db_table values or field names.
#
# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [appname]'
# into your database.
from __future__ import unicode_literals

from django.contrib.gis.db import models


class Dengue_2010(models.Model):
    pk_uid = models.IntegerField(db_column='PK_UID', primary_key=True)
    nu_notif = models.CharField(max_length=7, null=True)
    x = models.CharField(max_length=20, null=True)
    y = models.CharField(max_length=20, null=True)
    tp_not = models.CharField(max_length=1, null=True)
    id_agravo = models.CharField(max_length=4, null=True)
    dt_notific = models.DateField(null=True)
    sem_not = models.CharField(max_length=6, null=True)
    nu_ano = models.CharField(max_length=4, null=True)
    sg_uf_not = models.CharField(max_length=2, null=True)
    id_unidade = models.CharField(max_length=7, null=True)
    dt_sin_pri = models.DateField(null=True)
    sem_pri = models.CharField(max_length=6, null=True)
    cs_raca = models.CharField(max_length=1, null=True)
    cs_escol_n = models.CharField(max_length=2, null=True)
    id_cns_sus = models.CharField(max_length=15, null=True)
    sg_uf = models.CharField(max_length=2, null=True)
    nduplic_n = models.CharField(max_length=1, null=True)
    dt_digita = models.DateField(null=True)
    dt_transus = models.DateField(null=True)
    dt_transdm = models.DateField(null=True)
    dt_transsm = models.DateField(null=True)
    dt_transrm = models.DateField(null=True)
    dt_transrs = models.DateField(null=True)
    dt_transse = models.DateField(null=True)
    nu_lote_v = models.CharField(max_length=7, null=True)
    nu_lote_h = models.CharField(max_length=7, null=True)
    cs_flxret = models.CharField(max_length=1, null=True)
    flxrecebi = models.CharField(max_length=1, null=True)
    ident_micr = models.CharField(max_length=50, null=True)
    migrado_w = models.CharField(max_length=1, null=True)
    dt_invest = models.DateField(null=True)
    id_ocupa_n = models.CharField(max_length=6, null=True)
    dt_soro = models.DateField(null=True)
    resul_soro = models.CharField(max_length=1, null=True)
    dt_ns1 = models.DateField(null=True)
    resul_ns1 = models.CharField(max_length=1, null=True)
    dt_viral = models.DateField(null=True)
    resul_vi_n = models.CharField(max_length=1, null=True)
    dt_pcr = models.DateField(null=True)
    resul_pcr_field = models.CharField(max_length=1, null=True)
    sorotipo = models.CharField(max_length=1, null=True)
    histopa_n = models.CharField(max_length=1, null=True)
    imunoh_n = models.CharField(max_length=1, null=True)
    coufinf = models.CharField(max_length=2, null=True)
    copaisinf = models.CharField(max_length=4, null=True)
    comuninf = models.CharField(max_length=6, null=True)
    codisinf = models.CharField(max_length=4, null=True)
    doenca_tra = models.CharField(max_length=1, null=True)
    epistaxe = models.CharField(max_length=1, null=True)
    gengivo = models.CharField(max_length=1, null=True)
    metro = models.CharField(max_length=1, null=True)
    petequias = models.CharField(max_length=1, null=True)
    hematura = models.CharField(max_length=1, null=True)
    sangram = models.CharField(max_length=1, null=True)
    laco_n = models.CharField(max_length=1, null=True)
    plasmatico = models.CharField(max_length=1, null=True)
    evidencia = models.CharField(max_length=1, null=True)
    plaq_menor = models.FloatField(null=True)
    tp_sistema = models.CharField(max_length=1, null=True)
    fid_field = models.IntegerField(null=True)
    geom = models.PointField(srid=-1, null=True)
    objects = models.GeoManager()

    class Meta:
        managed = True
        db_table = 'Dengue_2010'


# Auto-generated `LayerMapping` dictionary for Dengue_2010 model
dengue_2010_mapping = {
    'nu_notif': 'NU_NOTIF',
    'x': 'X',
    'y': 'Y',
    'tp_not': 'TP_NOT',
    'id_agravo': 'ID_AGRAVO',
    'dt_notific': 'DT_NOTIFIC',
    'sem_not': 'SEM_NOT',
    'nu_ano': 'NU_ANO',
    'sg_uf_not': 'SG_UF_NOT',
    'id_unidade': 'ID_UNIDADE',
    'dt_sin_pri': 'DT_SIN_PRI',
    'sem_pri': 'SEM_PRI',
    'cs_raca': 'CS_RACA',
    'cs_escol_n': 'CS_ESCOL_N',
    'id_cns_sus': 'ID_CNS_SUS',
    'sg_uf': 'SG_UF',
    'nduplic_n': 'NDUPLIC_N',
    'dt_digita': 'DT_DIGITA',
    'dt_transus': 'DT_TRANSUS',
    'dt_transdm': 'DT_TRANSDM',
    'dt_transsm': 'DT_TRANSSM',
    'dt_transrm': 'DT_TRANSRM',
    'dt_transrs': 'DT_TRANSRS',
    'dt_transse': 'DT_TRANSSE',
    'nu_lote_v': 'NU_LOTE_V',
    'nu_lote_h': 'NU_LOTE_H',
    'cs_flxret': 'CS_FLXRET',
    'flxrecebi': 'FLXRECEBI',
    'ident_micr': 'IDENT_MICR',
    'migrado_w': 'MIGRADO_W',
    'dt_invest': 'DT_INVEST',
    'id_ocupa_n': 'ID_OCUPA_N',
    'dt_soro': 'DT_SORO',
    'resul_soro': 'RESUL_SORO',
    'dt_ns1': 'DT_NS1',
    'resul_ns1': 'RESUL_NS1',
    'dt_viral': 'DT_VIRAL',
    'resul_vi_n': 'RESUL_VI_N',
    'dt_pcr': 'DT_PCR',
    'resul_pcr_field': 'RESUL_PCR_',
    'sorotipo': 'SOROTIPO',
    'histopa_n': 'HISTOPA_N',
    'imunoh_n': 'IMUNOH_N',
    'coufinf': 'COUFINF',
    'copaisinf': 'COPAISINF',
    'comuninf': 'COMUNINF',
    'codisinf': 'CODISINF',
    'doenca_tra': 'DOENCA_TRA',
    'epistaxe': 'EPISTAXE',
    'gengivo': 'GENGIVO',
    'metro': 'METRO',
    'petequias': 'PETEQUIAS',
    'hematura': 'HEMATURA',
    'sangram': 'SANGRAM',
    'laco_n': 'LACO_N',
    'plasmatico': 'PLASMATICO',
    'evidencia': 'EVIDENCIA',
    'plaq_menor': 'PLAQ_MENOR',
    'tp_sistema': 'TP_SISTEMA',
    'fid_field': 'FID_',
    'geom': 'POINT',
}


class Dengue_2011(models.Model):
    pk_uid = models.IntegerField(db_column='PK_UID', primary_key=True)
    nu_notif = models.CharField(max_length=7, null=True)
    tp_not = models.CharField(max_length=1, null=True)
    id_agravo = models.CharField(max_length=4, null=True)
    dt_notific = models.DateField(null=True)
    sem_not = models.CharField(max_length=6, null=True)
    nu_ano = models.CharField(max_length=4, null=True)
    sg_uf_not = models.CharField(max_length=2, null=True)
    id_unidade = models.CharField(max_length=7, null=True)
    dt_sin_pri = models.DateField(null=True)
    sem_pri = models.CharField(max_length=6, null=True)
    cs_raca = models.CharField(max_length=1, null=True)
    cs_escol_n = models.CharField(max_length=2, null=True)
    id_cns_sus = models.CharField(max_length=15, null=True)
    sg_uf = models.CharField(max_length=2, null=True)
    nduplic_n = models.CharField(max_length=1, null=True)
    dt_digita = models.DateField(null=True)
    dt_transus = models.DateField(null=True)
    dt_transdm = models.DateField(null=True)
    dt_transsm = models.DateField(null=True)
    dt_transrm = models.DateField(null=True)
    dt_transrs = models.DateField(null=True)
    dt_transse = models.DateField(null=True)
    nu_lote_v = models.CharField(max_length=7, null=True)
    nu_lote_h = models.CharField(max_length=7, null=True)
    cs_flxret = models.CharField(max_length=1, null=True)
    flxrecebi = models.CharField(max_length=1, null=True)
    ident_micr = models.CharField(max_length=50, null=True)
    migrado_w = models.CharField(max_length=1, null=True)
    dt_invest = models.DateField(null=True)
    id_ocupa_n = models.CharField(max_length=6, null=True)
    dt_soro = models.DateField(null=True)
    resul_soro = models.CharField(max_length=1, null=True)
    dt_ns1 = models.DateField(null=True)
    resul_ns1 = models.CharField(max_length=1, null=True)
    dt_viral = models.DateField(null=True)
    resul_vi_n = models.CharField(max_length=1, null=True)
    dt_pcr = models.DateField(null=True)
    resul_pcr_field = models.CharField(max_length=1, null=True)
    sorotipo = models.CharField(max_length=1, null=True)
    histopa_n = models.CharField(max_length=1, null=True)
    imunoh_n = models.CharField(max_length=1, null=True)
    coufinf = models.CharField(max_length=2, null=True)
    copaisinf = models.CharField(max_length=4, null=True)
    comuninf = models.CharField(max_length=6, null=True)
    codisinf = models.CharField(max_length=4, null=True)
    co_bainf = models.CharField(max_length=8, null=True)
    nobaiinf = models.CharField(max_length=60, null=True)
    doenca_tra = models.CharField(max_length=1, null=True)
    epistaxe = models.CharField(max_length=1, null=True)
    gengivo = models.CharField(max_length=1, null=True)
    metro = models.CharField(max_length=1, null=True)
    petequias = models.CharField(max_length=1, null=True)
    hematura = models.CharField(max_length=1, null=True)
    sangram = models.CharField(max_length=1, null=True)
    laco_n = models.CharField(max_length=1, null=True)
    plasmatico = models.CharField(max_length=1, null=True)
    evidencia = models.CharField(max_length=1, null=True)
    plaq_menor = models.FloatField(null=True)
    uf = models.CharField(max_length=2, null=True)
    municipio = models.CharField(max_length=6, null=True)
    nu_lote_i = models.CharField(max_length=7, null=True)
    tp_sistema = models.CharField(max_length=1, null=True)
    x = models.CharField(max_length=20, null=True)
    y = models.CharField(max_length=20, null=True)
    geom = models.PointField(srid=-1, null=True)
    objects = models.GeoManager()

    class Meta:
        managed = True
        db_table = 'Dengue_2011'


# Auto-generated `LayerMapping` dictionary for Dengue_2011 model
dengue_2011_mapping = {
    'nu_notif': 'NU_NOTIF',
    'tp_not': 'TP_NOT',
    'id_agravo': 'ID_AGRAVO',
    'dt_notific': 'DT_NOTIFIC',
    'sem_not': 'SEM_NOT',
    'nu_ano': 'NU_ANO',
    'sg_uf_not': 'SG_UF_NOT',
    'id_unidade': 'ID_UNIDADE',
    'dt_sin_pri': 'DT_SIN_PRI',
    'sem_pri': 'SEM_PRI',
    'cs_raca': 'CS_RACA',
    'cs_escol_n': 'CS_ESCOL_N',
    'id_cns_sus': 'ID_CNS_SUS',
    'sg_uf': 'SG_UF',
    'nduplic_n': 'NDUPLIC_N',
    'dt_digita': 'DT_DIGITA',
    'dt_transus': 'DT_TRANSUS',
    'dt_transdm': 'DT_TRANSDM',
    'dt_transsm': 'DT_TRANSSM',
    'dt_transrm': 'DT_TRANSRM',
    'dt_transrs': 'DT_TRANSRS',
    'dt_transse': 'DT_TRANSSE',
    'nu_lote_v': 'NU_LOTE_V',
    'nu_lote_h': 'NU_LOTE_H',
    'cs_flxret': 'CS_FLXRET',
    'flxrecebi': 'FLXRECEBI',
    'ident_micr': 'IDENT_MICR',
    'migrado_w': 'MIGRADO_W',
    'dt_invest': 'DT_INVEST',
    'id_ocupa_n': 'ID_OCUPA_N',
    'dt_soro': 'DT_SORO',
    'resul_soro': 'RESUL_SORO',
    'dt_ns1': 'DT_NS1',
    'resul_ns1': 'RESUL_NS1',
    'dt_viral': 'DT_VIRAL',
    'resul_vi_n': 'RESUL_VI_N',
    'dt_pcr': 'DT_PCR',
    'resul_pcr_field': 'RESUL_PCR_',
    'sorotipo': 'SOROTIPO',
    'histopa_n': 'HISTOPA_N',
    'imunoh_n': 'IMUNOH_N',
    'coufinf': 'COUFINF',
    'copaisinf': 'COPAISINF',
    'comuninf': 'COMUNINF',
    'codisinf': 'CODISINF',
    'co_bainf': 'CO_BAINF',
    'nobaiinf': 'NOBAIINF',
    'doenca_tra': 'DOENCA_TRA',
    'epistaxe': 'EPISTAXE',
    'gengivo': 'GENGIVO',
    'metro': 'METRO',
    'petequias': 'PETEQUIAS',
    'hematura': 'HEMATURA',
    'sangram': 'SANGRAM',
    'laco_n': 'LACO_N',
    'plasmatico': 'PLASMATICO',
    'evidencia': 'EVIDENCIA',
    'plaq_menor': 'PLAQ_MENOR',
    'uf': 'UF',
    'municipio': 'MUNICIPIO',
    'nu_lote_i': 'NU_LOTE_I',
    'tp_sistema': 'TP_SISTEMA',
    'x': 'X',
    'y': 'Y',
    'geom': 'POINT',
}


class Dengue_2012(models.Model):
    pk_uid = models.IntegerField(db_column='PK_UID', primary_key=True)
    nu_notific = models.CharField(max_length=7, null=True)
    status_r = models.CharField(max_length=14, null=True)
    coord_x = models.FloatField(null=True)
    coord_y = models.FloatField(null=True)
    tp_not = models.CharField(max_length=1, null=True)
    id_agravo = models.CharField(max_length=4, null=True)
    dt_notific = models.DateField(null=True)
    sem_not = models.CharField(max_length=6, null=True)
    nu_ano = models.CharField(max_length=4, null=True)
    sg_uf_not = models.CharField(max_length=2, null=True)
    id_unidade = models.CharField(max_length=7, null=True)
    dt_sin_pri = models.DateField(null=True)
    sem_pri = models.CharField(max_length=6, null=True)
    cs_raca = models.CharField(max_length=1, null=True)
    cs_escol_n = models.CharField(max_length=2, null=True)
    id_cns_sus = models.CharField(max_length=15, null=True)
    sg_uf = models.CharField(max_length=2, null=True)
    nduplic_n = models.CharField(max_length=1, null=True)
    dt_digita = models.DateField(null=True)
    dt_transus = models.DateField(null=True)
    dt_transdm = models.DateField(null=True)
    dt_transsm = models.DateField(null=True)
    dt_transrm = models.DateField(null=True)
    dt_transrs = models.DateField(null=True)
    dt_transse = models.DateField(null=True)
    nu_lote_v = models.CharField(max_length=7, null=True)
    nu_lote_h = models.CharField(max_length=7, null=True)
    cs_flxret = models.CharField(max_length=1, null=True)
    flxrecebi = models.CharField(max_length=7, null=True)
    ident_micr = models.CharField(max_length=50, null=True)
    migrado_w = models.CharField(max_length=1, null=True)
    dt_invest = models.DateField(null=True)
    id_ocupa_n = models.CharField(max_length=6, null=True)
    dt_soro = models.DateField(null=True)
    resul_soro = models.CharField(max_length=1, null=True)
    histopa_n = models.CharField(max_length=1, null=True)
    dt_viral = models.DateField(null=True)
    resul_vi_n = models.CharField(max_length=1, null=True)
    sorotipo = models.CharField(max_length=1, null=True)
    imunoh_n = models.CharField(max_length=1, null=True)
    dt_pcr = models.DateField(null=True)
    resul_pcr_field = models.CharField(max_length=1, null=True)
    dt_ns1 = models.DateField(null=True)
    resul_ns1 = models.CharField(max_length=1, null=True)
    coufinf = models.CharField(max_length=2, null=True)
    copaisinf = models.CharField(max_length=4, null=True)
    doenca_tra = models.CharField(max_length=1, null=True)
    epistaxe = models.CharField(max_length=1, null=True)
    gengivo = models.CharField(max_length=1, null=True)
    metro = models.CharField(max_length=1, null=True)
    petequias = models.CharField(max_length=1, null=True)
    hematura = models.CharField(max_length=1, null=True)
    sangram = models.CharField(max_length=1, null=True)
    laco_n = models.CharField(max_length=1, null=True)
    plasmatico = models.CharField(max_length=1, null=True)
    plaq_menor = models.FloatField(null=True)
    uf = models.CharField(max_length=2, null=True)
    municipio = models.CharField(max_length=6, null=True)
    nu_lote_i = models.CharField(max_length=9, null=True)
    tp_sistema = models.CharField(max_length=1, null=True)
    geom = models.PointField(srid=-1, null=True)
    objects = models.GeoManager()

    class Meta:
        managed = True
        db_table = 'Dengue_2012'


# Auto-generated `LayerMapping` dictionary for Dengue_2012 model
dengue_2012_mapping = {
    'nu_notific': 'NU_NOTIFIC',
    'status_r': 'STATUS_R',
    'coord_x': 'COORD_X',
    'coord_y': 'COORD_Y',
    'tp_not': 'TP_NOT',
    'id_agravo': 'ID_AGRAVO',
    'dt_notific': 'DT_NOTIFIC',
    'sem_not': 'SEM_NOT',
    'nu_ano': 'NU_ANO',
    'sg_uf_not': 'SG_UF_NOT',
    'id_unidade': 'ID_UNIDADE',
    'dt_sin_pri': 'DT_SIN_PRI',
    'sem_pri': 'SEM_PRI',
    'cs_raca': 'CS_RACA',
    'cs_escol_n': 'CS_ESCOL_N',
    'id_cns_sus': 'ID_CNS_SUS',
    'sg_uf': 'SG_UF',
    'nduplic_n': 'NDUPLIC_N',
    'dt_digita': 'DT_DIGITA',
    'dt_transus': 'DT_TRANSUS',
    'dt_transdm': 'DT_TRANSDM',
    'dt_transsm': 'DT_TRANSSM',
    'dt_transrm': 'DT_TRANSRM',
    'dt_transrs': 'DT_TRANSRS',
    'dt_transse': 'DT_TRANSSE',
    'nu_lote_v': 'NU_LOTE_V',
    'nu_lote_h': 'NU_LOTE_H',
    'cs_flxret': 'CS_FLXRET',
    'flxrecebi': 'FLXRECEBI',
    'ident_micr': 'IDENT_MICR',
    'migrado_w': 'MIGRADO_W',
    'dt_invest': 'DT_INVEST',
    'id_ocupa_n': 'ID_OCUPA_N',
    'dt_soro': 'DT_SORO',
    'resul_soro': 'RESUL_SORO',
    'histopa_n': 'HISTOPA_N',
    'dt_viral': 'DT_VIRAL',
    'resul_vi_n': 'RESUL_VI_N',
    'sorotipo': 'SOROTIPO',
    'imunoh_n': 'IMUNOH_N',
    'dt_pcr': 'DT_PCR',
    'resul_pcr_field': 'RESUL_PCR_',
    'dt_ns1': 'DT_NS1',
    'resul_ns1': 'RESUL_NS1',
    'coufinf': 'COUFINF',
    'copaisinf': 'COPAISINF',
    'doenca_tra': 'DOENCA_TRA',
    'epistaxe': 'EPISTAXE',
    'gengivo': 'GENGIVO',
    'metro': 'METRO',
    'petequias': 'PETEQUIAS',
    'hematura': 'HEMATURA',
    'sangram': 'SANGRAM',
    'laco_n': 'LACO_N',
    'plasmatico': 'PLASMATICO',
    'plaq_menor': 'PLAQ_MENOR',
    'uf': 'UF',
    'municipio': 'MUNICIPIO',
    'nu_lote_i': 'NU_LOTE_I',
    'tp_sistema': 'TP_SISTEMA',
    'geom': 'POINT',
}


class Dengue_2013(models.Model):
    pk_uid = models.IntegerField(db_column='PK_UID', primary_key=True)
    nu_notific = models.CharField(max_length=7, null=True)
    coord_x = models.FloatField(null=True)
    coord_y = models.FloatField(null=True)
    tp_not = models.CharField(max_length=1, null=True)
    id_agravo = models.CharField(max_length=4, null=True)
    dt_notific = models.DateField(null=True)
    sem_not = models.CharField(max_length=6, null=True)
    nu_ano = models.CharField(max_length=4, null=True)
    sg_uf_not = models.CharField(max_length=2, null=True)
    dt_sin_pri = models.DateField(null=True)
    sem_pri = models.CharField(max_length=6, null=True)
    cs_raca = models.CharField(max_length=1, null=True)
    cs_escol_n = models.CharField(max_length=2, null=True)
    id_cns_sus = models.CharField(max_length=15, null=True)
    nduplic_n = models.CharField(max_length=1, null=True)
    dt_digita = models.DateField(null=True)
    dt_transus = models.DateField(null=True)
    dt_transdm = models.DateField(null=True)
    dt_transsm = models.DateField(null=True)
    dt_transrm = models.DateField(null=True)
    dt_transrs = models.DateField(null=True)
    dt_transse = models.DateField(null=True)
    nu_lote_v = models.CharField(max_length=7, null=True)
    nu_lote_h = models.CharField(max_length=7, null=True)
    cs_flxret = models.CharField(max_length=1, null=True)
    flxrecebi = models.CharField(max_length=7, null=True)
    ident_micr = models.CharField(max_length=50, null=True)
    migrado_w = models.CharField(max_length=1, null=True)
    dt_invest = models.DateField(null=True)
    id_ocupa_n = models.CharField(max_length=6, null=True)
    dt_soro = models.DateField(null=True)
    resul_soro = models.CharField(max_length=1, null=True)
    histopa_n = models.CharField(max_length=1, null=True)
    dt_viral = models.DateField(null=True)
    resul_vi_n = models.CharField(max_length=1, null=True)
    sorotipo = models.CharField(max_length=1, null=True)
    imunoh_n = models.CharField(max_length=1, null=True)
    dt_pcr = models.DateField(null=True)
    resul_pcr_field = models.CharField(max_length=1, null=True)
    dt_ns1 = models.DateField(null=True)
    resul_ns1 = models.CharField(max_length=1, null=True)
    doenca_tra = models.CharField(max_length=1, null=True)
    epistaxe = models.CharField(max_length=1, null=True)
    gengivo = models.CharField(max_length=1, null=True)
    metro = models.CharField(max_length=1, null=True)
    petequias = models.CharField(max_length=1, null=True)
    hematura = models.CharField(max_length=1, null=True)
    sangram = models.CharField(max_length=1, null=True)
    laco_n = models.CharField(max_length=1, null=True)
    plasmatico = models.CharField(max_length=1, null=True)
    evidencia = models.CharField(max_length=1, null=True)
    plaq_menor = models.FloatField(null=True)
    nu_lote_i = models.CharField(max_length=9, null=True)
    tp_sistema = models.CharField(max_length=1, null=True)
    geom = models.PointField(srid=-1, null=True)
    objects = models.GeoManager()

    class Meta:
        managed = True
        db_table = 'Dengue_2013'


# Auto-generated `LayerMapping` dictionary for Dengue_2013 model
dengue_2013_mapping = {
    'nu_notific': 'NU_NOTIFIC',
    'coord_x': 'COORD_X',
    'coord_y': 'COORD_Y',
    'tp_not': 'TP_NOT',
    'id_agravo': 'ID_AGRAVO',
    'dt_notific': 'DT_NOTIFIC',
    'sem_not': 'SEM_NOT',
    'nu_ano': 'NU_ANO',
    'sg_uf_not': 'SG_UF_NOT',
    'dt_sin_pri': 'DT_SIN_PRI',
    'sem_pri': 'SEM_PRI',
    'cs_raca': 'CS_RACA',
    'cs_escol_n': 'CS_ESCOL_N',
    'id_cns_sus': 'ID_CNS_SUS',
    'nduplic_n': 'NDUPLIC_N',
    'dt_digita': 'DT_DIGITA',
    'dt_transus': 'DT_TRANSUS',
    'dt_transdm': 'DT_TRANSDM',
    'dt_transsm': 'DT_TRANSSM',
    'dt_transrm': 'DT_TRANSRM',
    'dt_transrs': 'DT_TRANSRS',
    'dt_transse': 'DT_TRANSSE',
    'nu_lote_v': 'NU_LOTE_V',
    'nu_lote_h': 'NU_LOTE_H',
    'cs_flxret': 'CS_FLXRET',
    'flxrecebi': 'FLXRECEBI',
    'ident_micr': 'IDENT_MICR',
    'migrado_w': 'MIGRADO_W',
    'dt_invest': 'DT_INVEST',
    'id_ocupa_n': 'ID_OCUPA_N',
    'dt_soro': 'DT_SORO',
    'resul_soro': 'RESUL_SORO',
    'histopa_n': 'HISTOPA_N',
    'dt_viral': 'DT_VIRAL',
    'resul_vi_n': 'RESUL_VI_N',
    'sorotipo': 'SOROTIPO',
    'imunoh_n': 'IMUNOH_N',
    'dt_pcr': 'DT_PCR',
    'resul_pcr_field': 'RESUL_PCR_',
    'dt_ns1': 'DT_NS1',
    'resul_ns1': 'RESUL_NS1',
    'doenca_tra': 'DOENCA_TRA',
    'epistaxe': 'EPISTAXE',
    'gengivo': 'GENGIVO',
    'metro': 'METRO',
    'petequias': 'PETEQUIAS',
    'hematura': 'HEMATURA',
    'sangram': 'SANGRAM',
    'laco_n': 'LACO_N',
    'plasmatico': 'PLASMATICO',
    'evidencia': 'EVIDENCIA',
    'plaq_menor': 'PLAQ_MENOR',
    'nu_lote_i': 'NU_LOTE_I',
    'tp_sistema': 'TP_SISTEMA',
    'geom': 'POINT25D',
}


class DengueConfirmados_2013(models.Model):
    pk_uid = models.IntegerField(db_column='PK_UID', primary_key=True)
    nu_notific = models.CharField(max_length=7, null=True)
    coord_x = models.FloatField(null=True)
    coord_y = models.FloatField(null=True)
    tp_not = models.CharField(max_length=1, null=True)
    id_agravo = models.CharField(max_length=4, null=True)
    dt_notific = models.DateField(null=True)
    sem_not = models.CharField(max_length=6, null=True)
    nu_ano = models.CharField(max_length=4, null=True)
    id_unidade = models.CharField(max_length=7, null=True)
    dt_sin_pri = models.DateField(null=True)
    sem_pri = models.CharField(max_length=6, null=True)
    cs_raca = models.CharField(max_length=1, null=True)
    cs_escol_n = models.CharField(max_length=2, null=True)
    id_cns_sus = models.CharField(max_length=15, null=True)
    id_distrit = models.CharField(max_length=9, null=True)
    nduplic_n = models.CharField(max_length=1, null=True)
    dt_digita = models.DateField(null=True)
    dt_transus = models.DateField(null=True)
    dt_transdm = models.DateField(null=True)
    dt_transsm = models.DateField(null=True)
    dt_transrm = models.DateField(null=True)
    dt_transrs = models.DateField(null=True)
    dt_transse = models.DateField(null=True)
    nu_lote_v = models.CharField(max_length=7, null=True)
    nu_lote_h = models.CharField(max_length=7, null=True)
    cs_flxret = models.CharField(max_length=1, null=True)
    flxrecebi = models.CharField(max_length=7, null=True)
    ident_micr = models.CharField(max_length=50, null=True)
    migrado_w = models.CharField(max_length=1, null=True)
    dt_invest = models.DateField(null=True)
    id_ocupa_n = models.CharField(max_length=6, null=True)
    dt_soro = models.DateField(null=True)
    resul_soro = models.CharField(max_length=1, null=True)
    histopa_n = models.CharField(max_length=1, null=True)
    dt_viral = models.DateField(null=True)
    resul_vi_n = models.CharField(max_length=1, null=True)
    sorotipo = models.CharField(max_length=1, null=True)
    imunoh_n = models.CharField(max_length=1, null=True)
    dt_pcr = models.DateField(null=True)
    resul_pcr_field = models.CharField(max_length=1, null=True)
    dt_ns1 = models.DateField(null=True)
    resul_ns1 = models.CharField(max_length=1, null=True)
    coufinf = models.CharField(max_length=2, null=True)
    copaisinf = models.CharField(max_length=4, null=True)
    comuninf = models.CharField(max_length=6, null=True)
    codisinf = models.CharField(max_length=4, null=True)
    co_bainf = models.CharField(max_length=8, null=True)
    nobaiinf = models.CharField(max_length=60, null=True)
    doenca_tra = models.CharField(max_length=1, null=True)
    epistaxe = models.CharField(max_length=1, null=True)
    gengivo = models.CharField(max_length=1, null=True)
    metro = models.CharField(max_length=1, null=True)
    petequias = models.CharField(max_length=1, null=True)
    hematura = models.CharField(max_length=1, null=True)
    sangram = models.CharField(max_length=1, null=True)
    laco_n = models.CharField(max_length=1, null=True)
    plasmatico = models.CharField(max_length=1, null=True)
    evidencia = models.CharField(max_length=1, null=True)
    plaq_menor = models.FloatField(null=True)
    nu_lote_i = models.CharField(max_length=9, null=True)
    tp_sistema = models.CharField(max_length=1, null=True)
    geom = models.PointField(srid=-1, null=True)
    objects = models.GeoManager()

    class Meta:
        managed = True
        db_table = 'DengueConfirmados_2013'


dengueconfirmados_2013_mapping = {
    'nu_notific': 'NU_NOTIFIC',
    'coord_x': 'COORD_X',
    'coord_y': 'COORD_Y',
    'tp_not': 'TP_NOT',
    'id_agravo': 'ID_AGRAVO',
    'dt_notific': 'DT_NOTIFIC',
    'sem_not': 'SEM_NOT',
    'nu_ano': 'NU_ANO',
    'id_unidade': 'ID_UNIDADE',
    'dt_sin_pri': 'DT_SIN_PRI',
    'sem_pri': 'SEM_PRI',
    'cs_raca': 'CS_RACA',
    'cs_escol_n': 'CS_ESCOL_N',
    'id_cns_sus': 'ID_CNS_SUS',
    'id_distrit': 'ID_DISTRIT',
    'nduplic_n': 'NDUPLIC_N',
    'dt_digita': 'DT_DIGITA',
    'dt_transus': 'DT_TRANSUS',
    'dt_transdm': 'DT_TRANSDM',
    'dt_transsm': 'DT_TRANSSM',
    'dt_transrm': 'DT_TRANSRM',
    'dt_transrs': 'DT_TRANSRS',
    'dt_transse': 'DT_TRANSSE',
    'nu_lote_v': 'NU_LOTE_V',
    'nu_lote_h': 'NU_LOTE_H',
    'cs_flxret': 'CS_FLXRET',
    'flxrecebi': 'FLXRECEBI',
    'ident_micr': 'IDENT_MICR',
    'migrado_w': 'MIGRADO_W',
    'dt_invest': 'DT_INVEST',
    'id_ocupa_n': 'ID_OCUPA_N',
    'dt_soro': 'DT_SORO',
    'resul_soro': 'RESUL_SORO',
    'histopa_n': 'HISTOPA_N',
    'dt_viral': 'DT_VIRAL',
    'resul_vi_n': 'RESUL_VI_N',
    'sorotipo': 'SOROTIPO',
    'imunoh_n': 'IMUNOH_N',
    'dt_pcr': 'DT_PCR',
    'resul_pcr_field': 'RESUL_PCR_',
    'dt_ns1': 'DT_NS1',
    'resul_ns1': 'RESUL_NS1',
    'coufinf': 'COUFINF',
    'copaisinf': 'COPAISINF',
    'comuninf': 'COMUNINF',
    'codisinf': 'CODISINF',
    'co_bainf': 'CO_BAINF',
    'nobaiinf': 'NOBAIINF',
    'doenca_tra': 'DOENCA_TRA',
    'epistaxe': 'EPISTAXE',
    'gengivo': 'GENGIVO',
    'metro': 'METRO',
    'petequias': 'PETEQUIAS',
    'hematura': 'HEMATURA',
    'sangram': 'SANGRAM',
    'laco_n': 'LACO_N',
    'plasmatico': 'PLASMATICO',
    'evidencia': 'EVIDENCIA',
    'plaq_menor': 'PLAQ_MENOR',
    'nu_lote_i': 'NU_LOTE_I',
    'tp_sistema': 'TP_SISTEMA',
    'geom': 'POINT25D',
}
