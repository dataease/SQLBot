<script setup lang="ts">
import { datetimeFormat } from '@/utils/utils.ts'
import SQLServerDs from '@/assets/svg/ds/sqlServer-ds.svg'
import ExcelDs from '@/assets/svg/ds/Excel-ds.svg'
import PgDs from '@/assets/svg/ds/pg-ds.svg'
import MysqlDs from '@/assets/svg/ds/mysql-ds.svg'
import OracleDs from '@/assets/svg/ds/oracle-ds.svg'

defineProps<{
  ds: any
}>()

// const getStatus = (status: string) => {
//   if (status === 'Success') {
//     return 'connected'
//   }
//   if (status === 'Fail') {
//     return 'failed'
//   }
//   if (status === 'Checking') {
//     return 'needs-verification'
//   }
// }
</script>

<template>
  <div class="connection-card">
    <div class="connection-icon">
      <Icon>
        <MysqlDs v-if="ds.type === 'mysql'" />
        <SQLServerDs v-else-if="ds.type === 'sqlServer'" />
        <PgDs v-else-if="ds.type === 'pg'" />
        <ExcelDs v-else-if="ds.type === 'excel'" />
        <OracleDs v-else-if="ds.type === 'oracle'" />
      </Icon>
    </div>
    <div class="connection-details">
      <div class="connection-name">{{ ds.name }}</div>
      <div class="connection-type">{{ ds.type_name }}</div>
      <div class="connection-host">{{ ds.description }}</div>
      <div class="connection-last">{{ datetimeFormat(ds.create_time) }}</div>
    </div>
    <!-- <div class="connection-status" :class="`${getStatus(ds.status)}`">{{ ds.status }}</div> -->
    <slot></slot>
  </div>
</template>

<style scoped lang="less">
.connection-card {
  background-color: white;
  border-radius: 16px;
  padding: 24px 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  display: flex;
  position: relative;
  transition: all 0.2s ease;
  align-items: center;
}

.connection-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  background-color: #e8f0fe;
  color: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  flex-shrink: 0;
}

.connection-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;

  .connection-name {
    font-weight: 600;
    font-size: 18px;
    color: #202124;
    margin-bottom: 8px;
    line-height: 1.3;
    display: flex;
  }

  .connection-type {
    color: #5f6368;
    margin-bottom: 8px;
    font-size: 14px;
    display: flex;
  }

  .connection-host {
    color: #5f6368;
    margin-bottom: 8px;
    font-size: 14px;
    display: flex;
    align-items: center;
  }

  .connection-last {
    color: #5f6368;
    font-size: 14px;
    margin-bottom: 0;
    display: flex;
    align-items: center;
  }
}

.connection-status {
  position: absolute;
  right: 20px;
  top: 18px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  display: flex;
  align-items: center;
  max-width: 50px;
  text-align: center;
  justify-content: center;
  opacity: 0.9;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.connection-status.connected {
  background-color: #e6f4ea;
  color: #34a853;
}

.connection-status.failed {
  background-color: #fce8e6;
  color: #ea4335;
}

.connection-status.needs-verification {
  background-color: #fef7e0;
  color: #fbbc05;
}
</style>
