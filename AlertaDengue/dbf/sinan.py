from datetime import date
from psycopg2.extras import DictCursor
from dbfread import DBF
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

import pandas as pd
import psycopg2
import logging

logger = logging.getLogger(__name__)

field_map = {
    'dt_notific': "DT_NOTIFIC",
    'se_notif': "SEM_NOT",
    'ano_notif': "NU_ANO",
    'dt_sin_pri': "DT_SIN_PRI",
    'se_sin_pri': "SEM_PRI",
    'dt_digita': "DT_DIGITA",
    'bairro_nome': "NM_BAIRRO",
    'bairro_bairro_id': "ID_BAIRRO",
    'municipio_geocodigo': "ID_MUNICIP",
    'nu_notific': "NU_NOTIFIC",
    'cid10_codigo': "ID_AGRAVO",
    'cs_sexo': "CS_SEXO",
    'dt_nasc': "DT_NASC",
    'nu_idade_n': "NU_IDADE_N",
}


def calculate_digit(dig):
    """
    Calcula o digito verificador do geocódigo de município
    :param dig: geocódigo com 6 dígitos
    :return: dígito verificador
    """
    peso = [1, 2, 1, 2, 1, 2, 0]
    soma = 0
    dig = str(dig)
    for i in range(6):
        valor = int(dig[i]) * peso[i]
        soma += sum([int(d) for d in str(valor)]) if valor > 9 else valor
    dv = 0 if soma % 10 == 0 else (10 - (soma % 10))
    return dv


def add_dv(geocodigo):
    """
    Retorna o geocóodigo do município adicionando o digito verificador,
    se necessário.
    :param geocodigo: geocóodigo com 6 ou 7 dígitos
    """
    if len(str(geocodigo)) == 7:
        return geocodigo
    elif len(str(geocodigo)) == 6:
        return int(str(geocodigo) + str(calculate_digit(geocodigo)))
    else:
        raise ValueError('geocode does not match!')


class Sinan(object):
    """
    Introspecta arquivo DBF do SINAN preparando-o para inserção em outro banco.
    """

    db_config = {
        'database': settings.PSQL_DB,
        'user': settings.PSQL_USER,
        'password': settings.PSQL_PASSWORD,
        'host': settings.PSQL_HOST,
        'port': settings.PSQL_PORT,
    }

    def __init__(self, dbf_fname, ano, encoding="iso=8859-1"):
        """
        Instancia Objeto SINAN carregando-o a partir do arquivo indicado
        :param dbf_fname: Nome do arquivo dbf do Sinan
        :param ano: Ano dos dados
        :return:
        """
        logger.info("Instanciando SINAN ({}, {})".format(dbf_fname, ano))
        self.ano = ano
        self.dbf = DBF(dbf_fname, encoding=encoding)
        self.colunas_entrada = self.dbf.field_names
        self.tabela = pd.DataFrame(list(self.dbf))
        if "ID_MUNICIP" in self.tabela.columns:
            self.geocodigos = self.tabela.ID_MUNICIP.dropna().unique()
        elif "ID_MN_RESI" in self.tabela.columns:
            # print(self.tabela.columns)
            self.geocodigos = self.tabela.ID_MN_RESI.dropna().unique()
            self.tabela["ID_MUNICIP"] = self.tabela.ID_MN_RESI
            del self.tabela['ID_MN_RESI']
        self._parse_date_cols()

    def _parse_date_cols(self):
        logger.info("Formatando as datas")
        for col in filter(lambda x: x.startswith("DT"), self.tabela.columns):
            try:
                self.tabela[col] = pd.to_datetime(
                    self.tabela[col]
                )  # , errors='coerce')
            except ValueError:
                self.tabela[col] = pd.to_datetime(
                    self.tabela[col], format='%d/%m/%y', errors='coerce'
                )

    @property
    def time_span(self):
        """
        Escopo temporal do banco
        :return: (data_inicio, data_fim)
        """
        data_inicio = self.tabela['DT_NOTIFIC'].min()
        data_fim = self.tabela['DT_NOTIFIC'].max()
        return data_inicio, data_fim

    def _fill_missing_columns(self, col_names):
        """
        checks if the table to be inserted contains all columns required in
            the database model.
        If not create this columns filled with Null values, to allow for
            database insertion.
        :param col_names:
        """
        for nm in col_names:
            if field_map[nm] not in self.tabela.columns:
                self.tabela[field_map[nm]] = None

    def _get_postgres_connection(self):
        return psycopg2.connect(**self.db_config)

    def save_to_pgsql(
        self, table_name='"Municipio"."Notificacao"', default_cid=None
    ):
        connection = self._get_postgres_connection()
        logger.info("Escrevendo no PostgreSQL")

        with connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("select * from {} limit 1;".format(table_name))
            col_names = [c.name for c in cursor.description if c.name != "id"]
            self._fill_missing_columns(col_names)
            df_names = [field_map[n] for n in col_names]
            insert_sql = (
                'INSERT INTO {}({}) VALUES ({}) on conflict '
                'on CONSTRAINT casos_unicos do UPDATE SET {}'
            ).format(
                table_name,
                ','.join(col_names),
                ','.join(['%s' for i in col_names]),
                ','.join(['{0}=excluded.{0}'.format(j) for j in col_names]),
            )
            logger.info(
                "Formatando linhas e inserindo em {}".format(table_name)
            )
            for row in self.tabela[df_names].iterrows():
                i = row[0]
                row = row[1]
                row[0] = (
                    None
                    if isinstance(row[0], type(pd.NaT))
                    else date.fromordinal(row[0].to_pydatetime().toordinal())
                )  # dt_notific
                row[1] = int(str(int(row[1]))[-2:])  # se_notific
                row[2] = (
                    int(self.ano) if pd.isnull(row[2]) else int(row[2])
                )  # ano_notific
                row[3] = (
                    None
                    if isinstance(row[3], type(pd.NaT))
                    else date.fromordinal(row[3].to_pydatetime().toordinal())
                )  # dt_sin_pri
                row[4] = (
                    None if not row[4] else int(str(row[4])[-2:])
                )  # se_sin_pri
                row[5] = (
                    None
                    if isinstance(row[5], type(pd.NaT))
                    else date.fromordinal(row[5].to_pydatetime().toordinal())
                )  # dt_digita
                row[7] = (
                    None if not row[7] else int(row[7])
                )  # bairro_bairro_id
                row[8] = (
                    None if row[8] == '' else add_dv(int(row[8]))
                )  # municipio_geocodigo
                row[9] = int(row[9])  # nu_notific
                if row[10] is None:
                    if default_cid is None:
                        raise ValidationError(
                            _(
                                "Existem nesse arquivo notificações "
                                "que não incluem a coluna ID_AGRAVO."
                            )
                        )
                    else:
                        row[10] = default_cid

                row[11] = (
                    None
                    if (isinstance(row[11], type(pd.NaT)) or row[11] is None)
                    else date.fromordinal(row[11].to_pydatetime().toordinal())
                )  # dt_nasc
                row[13] = None if not row[13] else int(row[13])  # nu_idade_n
                cursor.execute(insert_sql, row)
                if (i % 1000 == 0) and (i > 0):
                    logger.info(
                        "{} linhas inseridas. Commitando mudanças "
                        "no banco".format(i)
                    )
                    connection.commit()

            connection.commit()
            logger.info("Sinan {} inserido no banco".format(self.dbf))
