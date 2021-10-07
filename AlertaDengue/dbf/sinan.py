import logging
from datetime import date

import pandas as pd
import psycopg2

# from dbfread import DBF
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from psycopg2.extras import DictCursor

from .utils import FIELD_MAP, chunk_dbf_toparquet

logger = logging.getLogger(__name__)


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
        logger.info("Formatting fields and save chunks dbf to parquet")

        pq_files = chunk_dbf_toparquet(dbf_fname)

        logger.info("Read parquet files and concatenate in pandas")

        chunks_list = [
            pd.read_parquet(f, engine='fastparquet') for f in pq_files
        ]

        self.tabela = pd.concat(chunks_list, ignore_index=True)
        self.ano = ano

        logger.info(f"Instanciando SINAN ({dbf_fname}, {ano})")

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
            if FIELD_MAP[nm] not in self.tabela.columns:
                self.tabela[FIELD_MAP[nm]] = None

    def _get_postgres_connection(self):
        return psycopg2.connect(**self.db_config)

    def save_to_pgsql(
        self, table_name='"Municipio"."Notificacao"', default_cid=None
    ):
        connection = self._get_postgres_connection()
        logger.info("Escrevendo no PostgreSQL")

        with connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1;")
            col_names = [c.name for c in cursor.description if c.name != "id"]
            self._fill_missing_columns(col_names)
            df_names = [FIELD_MAP[n] for n in col_names]
            insert_sql = (
                'INSERT INTO {}({}) VALUES ({}) on conflict '
                'on CONSTRAINT casos_unicos do UPDATE SET {}'
            ).format(
                table_name,
                ','.join(col_names),
                ','.join(['%s' for i in col_names]),
                ','.join(['{0}=excluded.{0}'.format(j) for j in col_names]),
            )
            logger.info(f"Formatando linhas e inserindo em {table_name}")
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
                row[6] = (
                    None if pd.isnull(row[6]) else str(row[6])
                )  # nm_bairro
                row[7] = (
                    None if pd.isnull(row[7]) else int(row[7])
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
                row[13] = None if pd.isnull(row[13]) else int(row[13])
                cursor.execute(insert_sql, row)
                if (i % 1000 == 0) and (i > 0):
                    logger.info(
                        f"{i} linhas inseridas. Commitando mudanças "
                        "no banco"
                    )
                    connection.commit()

            connection.commit()
            logger.info(
                'Sinan {} rows in {} fields inserted in the database'.format(
                    self.tabela.shape[0], self.tabela.shape[1]
                )
            )
