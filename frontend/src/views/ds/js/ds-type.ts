import mysql_ds from '@/assets/datasource/icon_mysql.png'
import excel from '@/assets/datasource/icon_excel.png'
import oracle from '@/assets/datasource/icon_oracle.png'
import pg from '@/assets/datasource/icon_PostgreSQL.png'
import sqlServer from '@/assets/datasource/icon_SQL_Server.png'
import ck from '@/assets/datasource/icon_ck.png'
import dm from '@/assets/datasource/icon_dm.png'
import doris from '@/assets/datasource/icon_doris.png'
import redshift from '@/assets/datasource/icon_redshift.png'
import es from '@/assets/datasource/icon_es.png'
import kingbase from '@/assets/datasource/icon_kingbase.png'
import starrocks from '@/assets/datasource/icon_starrocks.png'
import { i18n } from '@/i18n'

const t = i18n.global.t
export const dsType = [
  { label: t('ds.local_excelcsv'), value: 'excel' },
  { label: 'MySQL', value: 'mysql' },
  { label: 'Oracle', value: 'oracle' },
  { label: 'PostgreSQL', value: 'pg' },
  { label: 'SQL Server', value: 'sqlServer' },
  { label: 'ClickHouse', value: 'ck' },
  { label: '达梦', value: 'dm' },
  { label: 'Apache Doris', value: 'doris' },
  { label: 'AWS Redshift', value: 'redshift' },
  { label: 'Elasticsearch', value: 'es' },
  { label: 'Kingbase', value: 'kingbase' },
  { label: 'StarRocks', value: 'starrocks' },
]

export const dsTypeWithImg = [
  { name: t('ds.local_excelcsv'), type: 'excel', img: excel },
  { name: 'MySQL', type: 'mysql', img: mysql_ds },
  { name: 'Oracle', type: 'oracle', img: oracle },
  { name: 'PostgreSQL', type: 'pg', img: pg },
  { name: 'SQL Server', type: 'sqlServer', img: sqlServer },
  { name: 'ClickHouse', type: 'ck', img: ck },
  { name: '达梦', type: 'dm', img: dm },
  { name: 'Apache Doris', type: 'doris', img: doris },
  { name: 'AWS Redshift', type: 'redshift', img: redshift },
  { name: 'Elasticsearch', type: 'es', img: es },
  { name: 'Kingbase', type: 'kingbase', img: kingbase },
  { name: 'StarRocks', type: 'starrocks', img: starrocks },
]

export const haveSchema = ['sqlServer', 'pg', 'oracle', 'dm', 'redshift', 'kingbase']
