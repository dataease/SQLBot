<template>
  <el-dropdown trigger="hover" @command="changeLanguage">
    <div class="lang-switch">
      <span>{{ displayLanguageName }}</span>
      <el-icon class="el-icon--right">
        <ArrowDown />
      </el-icon>
    </div>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="option in languageOptions"
          :key="option.value"
          :command="option.value"
          :class="{ 'selected-lang': selectedLanguage === option.value }"
        >
          {{ option.label }}
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/stores/user'
import { ArrowDown } from '@element-plus/icons-vue'
import { userApi } from '@/api/auth'

const { t, locale } = useI18n()
const userStore = useUserStore()

const languageOptions = computed(() => [
  { value: 'en', label: t('common.english') },
  { value: 'zh-CN', label: t('common.simplified_chinese') },
  { value: 'ko-KR', label: t('common.korean') },
])

const selectedLanguage = computed(() => {
  return userStore.language
})

const displayLanguageName = computed(() => {
  const current = languageOptions.value.find((item) => item.value === selectedLanguage.value)
  return current?.label ?? t('common.language')
})

const changeLanguage = (lang: string) => {
  locale.value = lang
  userStore.setLanguage(lang)

  const param = {
    language: lang,
  }
  userApi.language(param)
}
</script>

<style scoped lang="less">
.lang-switch {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: var(--el-text-color-primary);

  .el-icon--right {
    margin-left: 8px;
    font-size: 12px;
  }
}

.selected-lang {
  color: var(--el-color-primary);
}
</style>